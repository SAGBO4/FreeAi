"""Tech Lead Orchestrator (TDR §13 & §45).
Acts as the engineering lead: breaks down objectives, routes to specialized agents,
monitors resources, and guarantees stability, unrestricted autonomy, and rollback safety.
"""

import logging
from typing import Dict, Any, List, Optional
from app.resource_manager.watchdog import ResourceManager
from app.tools.gateway import ToolGateway
from app.agents.code_agent import CodeAgent
from app.agents.security_agent import SecurityAgent
from app.agents.git_agent import GitAgent
from app.llm.engine import LocalIntelligenceEngine

logger = logging.getLogger("tech_lead_orchestrator")


class TechLeadOrchestrator:
    def __init__(self, tool_gateway: ToolGateway, resource_manager: ResourceManager):
        self.tool_gateway = tool_gateway
        self.resource_manager = resource_manager

        # Local Unrestricted Intelligence Engine (100% offline, zero internet)
        self.llm_engine = LocalIntelligenceEngine()

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
        """Uses local intelligence engine to determine the domain."""
        plan = self.llm_engine.reason_and_plan(objective, {})
        return plan["domain"]

    async def handle_objective(self, objective: str, autonomous: bool = False) -> Dict[str, Any]:
        """Main entry point for handling user objectives."""
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

        # 3. Local unrestricted reasoning & plan
        reasoning = self.llm_engine.reason_and_plan(objective, {"autonomous": autonomous})
        agent_type = reasoning["domain"]
        context = {
            "autonomous": autonomous,
            "memory_status": mem_status,
            "reasoning": reasoning
        }

        if agent_type == "security":
            result = await self.security_agent.execute_task(objective, context)
        elif agent_type == "git":
            result = await self.git_agent.execute_task(objective, context)
        else:
            result = await self.code_agent.execute_task(objective, context)

        # 4. Final check and report
        stats = self.resource_manager.get_system_stats()
        return {
            "success": True,
            "orchestrator": "Tech Lead (100% Local & Unrestricted)",
            "assigned_agent": agent_type,
            "objective": objective,
            "plan": reasoning.get("strategy", []),
            "result": result,
            "resource_stats": stats
        }
