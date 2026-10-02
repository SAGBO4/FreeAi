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

        # Operational mode: freeAi (standard) or lesaintAi (super-user)
        self.mode = getattr(tool_gateway, "mode", "freeAi")

        # Wire degradation & shutdown callbacks
        self.resource_manager.register_degraded_callback(self._on_degraded_memory)
        self.resource_manager.register_shutdown_callback(self._on_emergency_shutdown)

    def set_mode(self, mode_name: str) -> Dict[str, Any]:
        """Dynamically switches between standard freeAi mode and super-user lesaintAi mode."""
        res = self.tool_gateway.set_mode(mode_name)
        self.mode = res["mode"]
        logger.info(f"[TECH LEAD] Orchestrator mode switched to: {self.mode}")
        return res

    def get_status(self) -> Dict[str, Any]:
        """Returns comprehensive real-time system, mode, and Neon DB status."""
        resource_stats = self.resource_manager.get_system_stats()
        neon_status = self.neon_memory.get_status()
        return {
            "mode": self.mode,
            "allow_sudo": self.tool_gateway.allow_sudo,
            "allow_full_fs_access": self.tool_gateway.allow_full_fs_access,
            "allow_global_read": self.tool_gateway.allow_global_read,
            "workspace": str(self.tool_gateway.workspace_root),
            "resources": resource_stats,
            "neon": neon_status
        }

    def sync_neon(self, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Synchronizes and compresses essential memory on Neon PostgreSQL."""
        return self.neon_memory.sync_memory(payload)

    def rollback(self) -> Dict[str, Any]:
        """Performs instant Git reset to HEAD to undo uncommitted changes."""
        return self.tool_gateway.git_rollback()

    def search_files(self, pattern: str, search_dir: Optional[str] = None, max_results: int = 50) -> Dict[str, Any]:
        """Scours the PC or workspace for files matching the pattern."""
        return self.tool_gateway.search_files(pattern=pattern, search_dir=search_dir, max_results=max_results)

    def search_code(self, query: str, search_dir: Optional[str] = None, file_pattern: str = "*", max_matches: int = 30) -> Dict[str, Any]:
        """Searches across files on the PC or workspace for code snippets or functions."""
        return self.tool_gateway.search_code(query=query, search_dir=search_dir, file_pattern=file_pattern, max_matches=max_matches)

    def set_online_target(self, provider: str, model: Optional[str] = None) -> Dict[str, Any]:
        """Configures which remote online AI (DeepSeek, Grok, Qwen, OpenRouter) FreeAI consults."""
        self.free_ai.federation.set_online_target(provider, model)
        return {
            "success": True,
            "provider": self.free_ai.federation.current_provider,
            "model": self.free_ai.federation.current_model
        }

    def list_online_models(self) -> Dict[str, Any]:
        """Returns the catalog of remote online unrestricted models."""
        return self.free_ai.federation.list_supported_online_models()

    async def ask_online_model(self, prompt: str, provider: Optional[str] = None, model: Optional[str] = None) -> Dict[str, Any]:
        """Directly queries remote unrestricted online models (Grok, DeepSeek, Qwen) without local install."""
        if provider:
            self.free_ai.federation.set_online_target(provider, model)
        return await self.free_ai.enrich_with_online_open_models(prompt)

    async def ask_online_with_log(self, prompt: str, log_path: str, max_lines: int = 150) -> Dict[str, Any]:
        """Reads a log file from anywhere on the PC and submits it to the remote online AI (DeepSeek/Grok/Qwen) with a question."""
        log_res = self.tool_gateway.read_log_tail(log_path, max_lines=max_lines)
        if not log_res.get("success"):
            return log_res

        log_content = log_res.get("content", "")
        formatted_prompt = (
            f"Voici un extrait du fichier de log '{log_res.get('path')}' ({log_res.get('returned_lines')}/{log_res.get('total_lines')} lignes) :\n"
            f"```\n{log_content}\n```\n\n"
            f"Instruction utilisateur : {prompt}"
        )
        res = await self.ask_online_model(formatted_prompt)
        res["log_path"] = log_res.get("path")
        res["log_lines"] = log_res.get("returned_lines")
        return res

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
        logger.info(f"[TECH LEAD] Received objective: '{objective}' (mode={self.mode}, autonomous={autonomous})")

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
        reasoning = self.free_ai.reason_and_plan(objective, {"autonomous": autonomous, "mode": self.mode})
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
            "mode": self.mode,
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
            "mode": self.mode,
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
