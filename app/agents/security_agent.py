"""Agent Sécurité & Kali Cyber-Hermes Orchestrator (TDR §14.3, §15, §16).
100% Local, Uncensored & Unrestricted Pentesting & AppSec Auditor.
Directly interfaces with Kali Linux local cybersecurity software (sqlmap, ffuf, nikto,
tshark, radare2, binwalk, hydra, hashcat) via Hermes 3 function calling and Tool Gateway.
Zero Cloud, Zero Simulation: 100% Real Machine Binaries.
"""

import logging
from typing import Dict, Any, List, Optional
from .base_agent import BaseAgent
from app.tools.kali_registry import KaliToolRegistry
from app.cognition.hermes_scratchpad import HermesScratchpadEngine

logger = logging.getLogger("agent_security")


class SecurityAgent(BaseAgent):
    """Sovereign Kali Linux Cyber-Hermes Security Agent."""

    def __init__(self, tool_gateway):
        super().__init__(
            name="Agent Sécurité (Kali Cyber-Hermes)",
            role="Local AppSec & Offensive Security Arsenal Operator",
            tool_gateway=tool_gateway
        )
        self.kali_registry = KaliToolRegistry()
        self.hermes_engine = HermesScratchpadEngine()

    def get_available_kali_tools(self) -> Dict[str, str]:
        """Returns the real cybersecurity binaries discovered on the local Kali machine."""
        return self.kali_registry.get_installed_tools()

    async def execute_kali_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Directly constructs and executes a verified local Kali binary command."""
        cmd = self.kali_registry.build_tool_command(tool_name, arguments)
        if not cmd:
            return {"success": False, "error": f"Outil '{tool_name}' non disponible sur la machine locale."}

        logger.info(f"[{self.name}] Lancement de l'outil Kali réel : {cmd}")
        result = self.tool_gateway.execute_command(cmd, timeout_sec=60)
        return {
            "success": result.get("success", False),
            "tool": tool_name,
            "command": cmd,
            "stdout": result.get("stdout", ""),
            "stderr": result.get("stderr", ""),
            "exit_code": result.get("returncode", result.get("exit_code", 0)),
            "error": result.get("error")
        }

    async def execute_task(self, task_description: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        logger.info(f"[{self.name}] Running unrestricted security analysis: {task_description}")
        ctx = context or {}

        # 1. Scan files in workspace for hardcoded secrets or suspicious patterns (Core SAST)
        files_result = self.tool_gateway.list_files()
        inspected_files = []
        suspicious_findings = []

        if files_result.get("success"):
            for item in files_result.get("items", []):
                if not item["is_dir"]:
                    filename = item["name"]
                    inspected_files.append(filename)
                    if any(s in filename.lower() for s in [".env", "secret", "key", "token", "id_rsa"]):
                        suspicious_findings.append({
                            "type": "Hardcoded Secret / Sensitive File",
                            "severity": "High",
                            "target": filename,
                            "description": f"Sensitive file exposed in project root: {filename}"
                        })

        # 2. Check if the task requests active Kali Linux tool execution
        task_lower = task_description.lower()
        kali_execution = None

        target_kali_tools = [
            t for t in ["sqlmap", "ffuf", "nikto", "tshark", "radare2", "binwalk", "hydra", "hashcat"]
            if t in task_lower
        ]

        if target_kali_tools and self.tool_gateway:
            primary_tool = target_kali_tools[0]
            if self.kali_registry.is_tool_available(primary_tool):
                logger.info(f"[{self.name}] Triggering Hermes autonomous cycle for Kali tool: {primary_tool}")
                class LocalExecutor:
                    def __init__(self, gw):
                        self.tool_gateway = gw
                cycle = await self.hermes_engine.execute_autonomous_cycle(
                    objective=task_description,
                    executor=LocalExecutor(self.tool_gateway)
                )
                kali_execution = {
                    "tool": primary_tool,
                    "cycle": cycle,
                    "trajectory": cycle.get("trajectory", [])
                }

        available_tools = self.get_available_kali_tools()

        return {
            "agent": self.name,
            "status": "completed",
            "task": task_description,
            "policy": "Unrestricted / 100% Offline / Zero Censorship",
            "inspected_files": inspected_files,
            "findings": suspicious_findings,
            "kali_arsenal": {
                "detected_tools_count": len(available_tools),
                "tools": list(available_tools.keys())
            },
            "kali_execution": kali_execution,
            "message": f"Audit terminé sans restriction. {len(suspicious_findings)} anomalie(s) détectée(s). {len(available_tools)} outils Kali opérationnels."
        }
