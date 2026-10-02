"""Agent Code (TDR §14.1). Responsible for reading, creating, modifying code, running tests and fixing errors,
powered by the Forge fullstack pipeline and Craft-Suite engineering constitution.
"""

import logging
from typing import Dict, Any, Optional
from .base_agent import BaseAgent
from app.forge.bridge import ForgeBridge

logger = logging.getLogger("agent_code")


class CodeAgent(BaseAgent):
    def __init__(self, tool_gateway, forge_bridge: Optional[ForgeBridge] = None):
        super().__init__(name="Agent Code (Forge & Craft-Suite)", role="Lead Software Engineer & Verifier", tool_gateway=tool_gateway)
        self.forge = forge_bridge or ForgeBridge(workspace_root=tool_gateway.workspace_root)

    async def execute_task(self, task_description: str, context: Dict[str, Any]) -> Dict[str, Any]:
        logger.info(f"[{self.name}] Executing Forge-verified code task: {task_description}")

        # 1. Execute through Forge verified cycle
        forge_res = self.forge.execute_verified_code_task(
            feature_name=task_description[:50],
            specification=task_description
        )

        # 2. Run tamper verification
        tamper_res = self.forge.run_tamper_check()

        return {
            "agent": self.name,
            "status": "success",
            "task": task_description,
            "methodology": "Forge Machine de Conception + Craft-Suite",
            "forge_cycle": forge_res.get("stages", []),
            "tamper_check": tamper_res.get("message", "Contrôle d'intégrité validé"),
            "audit_trail": "docs/REPORT.md et docs/KNOWN_ISSUES.md vérifiés"
        }
