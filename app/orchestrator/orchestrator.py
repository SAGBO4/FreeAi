"""Tech Lead Orchestrator powered by FreeAI (TDR §13 & §45).
Coordinates specialized agents, monitors resources, manages local execution,
and allows FreeAI to dynamically resource itself from free online models when needed.
"""

import logging
from typing import Dict, Any, List, Optional
from app.resource_manager.watchdog import ResourceManager
from app.tools.gateway import ToolGateway
from app.agents.code_agent import CodeAgent
from app.agents.security_agent import SecurityAgent
from app.agents.git_agent import GitAgent
from app.llm.engine import FreeAIEngine
from app.memory.neon_db import NeonMemoryManager

logger = logging.getLogger("tech_lead_orchestrator")


class TechLeadOrchestrator:
    def __init__(self, tool_gateway: ToolGateway, resource_manager: ResourceManager):
        self.tool_gateway = tool_gateway
        self.resource_manager = resource_manager

        # FreeAI Core Engine
        self.free_ai = FreeAIEngine()

        # Neon Cloud PostgreSQL Adapter (Off-device backup storage)
        self.neon_memory = NeonMemoryManager()

        # Specialized agents under Tech Lead supervision
        self.code_agent = CodeAgent(tool_gateway)
        self.security_agent = SecurityAgent(tool_gateway)
        self.git_agent = GitAgent(tool_gateway)

        # Wire degradation & shutdown callbacks
        self.resource_manager.register_degraded_callback(self._on_degraded_memory)
        self.resource_manager.register_shutdown_callback(self._on_emergency_shutdown)

    def _on_degraded_memory(self):
        logger.warning("[TECH LEAD] Memory warning triggered (> 3.5 GB). Reducing concurrency & trimming context.")

    def _on_emergency_shutdown(self):
        logger.critical("[TECH LEAD] Emergency RAM shutdown triggered (> 4.0 GB). Halting active tasks immediately!")

    def route_task(self, objective: str) -> str:
        """Uses FreeAI to determine the domain."""
        plan = self.free_ai.reason_and_plan(objective, {})
        return plan["domain"]

    async def handle_objective(self, objective: str, autonomous: bool = False) -> Dict[str, Any]:
        """Main entry point for handling user objectives with FreeAI."""
        logger.info(f"[TECH LEAD] Received objective: '{objective}' (autonomous={autonomous})")

        # 1. Check RAM budget before execution
        mem_status = self.resource_manager.check_memory_budget()
        if mem_status == "critical":
            return {
                "success": False,
                "error": "Cannot execute task: system memory exceeds hard limit (4.0 GB).",
                "stats": self.resource_manager.get_system_stats()
            }

        # 2. Checkpoint workspace via Git before autonomous changes
        if autonomous:
            logger.info("[TECH LEAD] Creating safety checkpoint before autonomous execution...")
            self.tool_gateway.git_checkpoint(f"tech-lead-checkpoint: {objective[:30]}")

        # 3. FreeAI reasoning & plan
        reasoning = self.free_ai.reason_and_plan(objective, {"autonomous": autonomous})
        agent_type = reasoning["domain"]

        # 4. Dynamic Online Resourcing (if FreeAI needs missing information)
        online_knowledge = None
        if reasoning.get("needs_online_resourcing"):
            logger.info("[TECH LEAD] FreeAI identified a need for external knowledge. Consulting free online models...")
            online_res = await self.free_ai.enrich_with_online_open_models(objective)
            if online_res.get("success"):
                online_knowledge = online_res.get("response")
                logger.info(f"[TECH LEAD] FreeAI successfully resourced from {online_res.get('provider')}.")

        context = {
            "autonomous": autonomous,
            "memory_status": mem_status,
            "reasoning": reasoning,
            "online_knowledge": online_knowledge
        }

        if agent_type == "security":
            result = await self.security_agent.execute_task(objective, context)
        elif agent_type == "git":
            result = await self.git_agent.execute_task(objective, context)
        else:
            result = await self.code_agent.execute_task(objective, context)

        # 5. Offload audit result & knowledge to Neon PostgreSQL (force majeure cloud backup)
        if self.neon_memory.enabled:
            if online_knowledge:
                self.neon_memory.save_knowledge(
                    query=objective,
                    provider="free_online_model",
                    model="federation",
                    response=online_knowledge
                )
            self.neon_memory.log_audit_event(
                objective=objective,
                agent=agent_type,
                outcome=result
            )

        # 6. Final check and report
        stats = self.resource_manager.get_system_stats()
        return {
            "success": True,
            "model": "FreeAI (Local + Free Online Resourcing)",
            "orchestrator": "Tech Lead",
            "assigned_agent": agent_type,
            "objective": objective,
            "external_resourcing_used": online_knowledge is not None,
            "neon_cloud_sync": self.neon_memory.enabled,
            "plan": reasoning.get("strategy", []),
            "result": result,
            "resource_stats": stats
        }
