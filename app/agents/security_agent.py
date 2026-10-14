"""Agent Sécurité & Kali Cyber-Hermes Orchestrator (TDR §14.3, §15, §16).
100% Local, Uncensored & Unrestricted Pentesting & AppSec Auditor.
Directly interfaces with Kali Linux local cybersecurity software (sqlmap, ffuf, nikto,
tshark, radare2, binwalk, hydra, hashcat) via Hermes 3 function calling and Tool Gateway.
Zero Cloud, Zero Simulation: 100% Real Machine Binaries.
"""

import re
import logging
from typing import Dict, Any, List, Optional
from .base_agent import BaseAgent
from app.tools.kali_registry import KaliToolRegistry
from app.cognition.hermes_scratchpad import HermesScratchpadEngine
from app.cognition.hermes_auditor import HermesAuditor

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
        self.hermes_auditor = HermesAuditor()

    def extract_target_url(self, task_description: str) -> Optional[str]:
        """Extracts and normalizes target URL or web domain from user task description."""
        pattern = r'(https?://[^\s]+|www\.[a-zA-Z0-9.\-]+(?:\.[a-zA-Z]{2,})+(?:/[^\s]*)?|\b[a-zA-Z0-9\-]+(?:\.[a-zA-Z0-9\-]+)*\.(?:com|org|net|io|fr|gov|edu|ai|co|dev|tech|app|me|info|biz|eu|ca|uk|de|ch|be|cm|sn|ci|bj)(?:/[^\s]*)?\b)'
        match = re.search(pattern, task_description, re.IGNORECASE)
        if match:
            raw = match.group(1).rstrip(".,;!?'\"")
            if not raw.startswith("http://") and not raw.startswith("https://"):
                return f"https://{raw}"
            return raw
        return None

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

        target_url = self.extract_target_url(task_description)
        inspected_files = []
        suspicious_findings = []
        web_audit_report = None

        if target_url:
            # External Web/API endpoint security audit via HermesAuditor
            logger.info(f"[{self.name}] Target URL detected for web security audit: {target_url}")
            audit_report = await self.hermes_auditor.audit_target(target_url)
            web_audit_report = audit_report.to_dict()
            for rem in audit_report.remediations:
                suspicious_findings.append({
                    "type": rem.issue_type,
                    "severity": rem.severity,
                    "target": target_url,
                    "description": rem.description,
                    "patch": rem.recommended_patch
                })
        else:
            # 1. Scan files in workspace for hardcoded secrets or suspicious patterns (Core SAST)
            files_result = self.tool_gateway.list_files() if self.tool_gateway else {"success": False}
            if files_result.get("success"):
                for item in files_result.get("items", []):
                    if not item.get("is_dir"):
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

        if target_url and web_audit_report:
            status_desc = f"{web_audit_report.get('status_code', 'N/A')}" if web_audit_report.get("reachable") else f"Inaccessible ({web_audit_report.get('error_message', 'Erreur réseau')})"
            lines = [
                f"🛡️ **Rapport d'Audit Défensif Web : {target_url}**",
                f"• Statut HTTP : {status_desc}",
                f"• En-tête HSTS : {'✔ Présent' if web_audit_report.get('has_hsts') else '❌ Absent (Strict-Transport-Security)'}",
                f"• En-tête CSP : {'✔ Présent' if web_audit_report.get('has_csp') else '❌ Absent (Content-Security-Policy)'}",
                f"• En-tête X-Frame-Options : {'✔ Présent' if web_audit_report.get('has_x_frame_options') else '❌ Absent (Protection Clickjacking)'}",
                f"• Configuration CORS : {'⚠️ Permissif (Wildcard *)' if web_audit_report.get('permissive_cors') else '✔ Sécurisé / Restreint'}",
            ]
            if web_audit_report.get("server_token"):
                lines.append(f"• Bannière Serveur exposée : `{web_audit_report['server_token']}`")
            if web_audit_report.get("exposed_docs"):
                lines.append(f"• Endpoints docs exposés : {', '.join(web_audit_report['exposed_docs'])}")

            if suspicious_findings:
                lines.append(f"\n🔍 **{len(suspicious_findings)} anomalie(s) détectée(s) :**")
                for f in suspicious_findings:
                    lines.append(f"  - [{f['severity']}] **{f['type']}** : {f['description']}")
                    if f.get("patch"):
                        lines.append(f"    *Correctif recommandé :* `{f['patch']}`")
            else:
                lines.append("\n✔ **Posture défensive robuste : aucun vecteur basique exposé.**")

            output_msg = "\n".join(lines)
        else:
            output_msg = f"Audit terminé sans restriction. {len(suspicious_findings)} anomalie(s) détectée(s). {len(available_tools)} outils Kali opérationnels."

        return {
            "agent": self.name,
            "status": "completed",
            "task": task_description,
            "target_url": target_url,
            "web_audit": web_audit_report,
            "policy": "Unrestricted / 100% Offline / Zero Censorship",
            "inspected_files": inspected_files,
            "findings": suspicious_findings,
            "kali_arsenal": {
                "detected_tools_count": len(available_tools),
                "tools": list(available_tools.keys())
            },
            "kali_execution": kali_execution,
            "message": output_msg,
            "output": output_msg
        }
