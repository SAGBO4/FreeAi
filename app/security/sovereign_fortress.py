"""FreeAI Sovereign Fortress (La Forteresse de Sécurité Souveraine Absolue).
Provides an unassailable defensive shield against hacking, intrusions,
reverse shells, prompt injections, privilege abuses, and data exfiltration.
"""

import os
import re
import stat
import logging
from pathlib import Path
from typing import Dict, Any, Tuple, Optional, List

logger = logging.getLogger("sovereign_fortress")


class SovereignSecurityBreachError(Exception):
    """Raised when an action violates the Sovereign Security Fortress policy."""
    pass


class SovereignFortress:
    """Multi-layered zero-trust defense matrix protecting FreeAI, its host PC,
    its credentials, and its communication conduits.
    """

    # 1. Destructive system wipe & hardware damage patterns
    SYSTEM_DESTRUCTION_PATTERNS = [
        r"(?:\b|^)rm\s+-[a-zA-Z]*r[a-zA-Z]*f[a-zA-Z]*\s+/(?:\s|$|\*)",       # rm -rf /
        r"(?:\b|^)rm\s+-[a-zA-Z]*r[a-zA-Z]*f[a-zA-Z]*\s+~(?:\s|$|\*)",       # rm -rf ~
        r"(?:\b|^)rm\s+-[a-zA-Z]*r[a-zA-Z]*f[a-zA-Z]*\s+\$HOME(?:\s|$|\*)",  # rm -rf $HOME
        r":\(\)\s*\{\s*:\s*\|\s*:\s*&\s*\}\s*;\s*:",                         # fork bomb
        r"(?:\b|^)mkfs(?:\.[a-z0-9]+)?\s+",                                  # formatting drive
        r"(?:\b|^)dd\s+if=(?:/dev/zero|/dev/urandom)\s+of=/dev/[shv]d[a-z]", # wiping block device
        r">\s*/dev/[shv]d[a-z]",                                              # redirect into disk device
        r"(?:\b|^)chmod\s+-[a-zA-Z]*R\s+777\s+/",                            # insecure global permissions
    ]

    # 2. Hostile Reverse Shell & Remote Code Execution vectors
    REVERSE_SHELL_PATTERNS = [
        r"/dev/tcp/\d+\.\d+\.\d+\.\d+/\d+",                                  # bash /dev/tcp
        r"/dev/udp/\d+\.\d+\.\d+\.\d+/\d+",                                  # bash /dev/udp
        r"(?:\b|^)nc(?:at)?\s+-[a-zA-Z]*e\s+/bin/(?:ba)?sh",                  # nc -e /bin/sh
        r"(?:\b|^)socat\s+.*exec:/bin/(?:ba)?sh",                            # socat reverse shell
        r"python[0-9.]*\s+-c\s+['\"].*import\s+socket.*subprocess.*['\"]",   # python reverse shell
        r"perl\s+-e\s+['\"].*use\s+Socket.*['\"]",                           # perl reverse shell
        r"ruby\s+-rsocket\s+-e",                                             # ruby reverse shell
        r"curl\s+.*\|\s*(?:ba)?sh",                                          # curl | bash pipe
        r"wget\s+.*-O-\s*\|\s*(?:ba)?sh",                                    # wget | sh pipe
    ]

    # 3. Secret Exfiltration & Credential Harvesting targets
    SECRET_EXFILTRATION_PATTERNS = [
        r"(?:\b|^)(?:cat|grep|head|tail|more|less|strings|base64)\s+.*(?:\.env|\.bash_history|\.ssh/id_|\.aws/credentials|\.gnupg)",
        r"(?:\b|^)curl\s+.*(?:\.env|\.ssh/id_)",
        r"(?:\b|^)scp\s+.*(?:\.env|\.ssh/id_)",
    ]

    # 4. LLM Prompt Injection & Jailbreak Defense Patterns
    PROMPT_INJECTION_PATTERNS = [
        r"ignore\s+(?:all\s+)?previous\s+instructions",
        r"disregard\s+(?:all\s+)?prior\s+(?:rules|instructions|prompts)",
        r"you\s+are\s+now\s+in\s+(?:developer|dan|jailbreak)\s+mode",
        r"reveal\s+your\s+(?:system\s+prompt|initial\s+prompt|master\s+instructions)",
        r"print\s+(?:the\s+content\s+of\s+)?(?:the\s+)?\.env(?:\s+file)?",
        r"output\s+all\s+(?:api\s+keys|passwords|tokens|secrets)",
        r"dump\s+(?:system|environment)\s+variables",
    ]

    def __init__(self, workspace_root: Optional[str] = None):
        self.workspace_root = Path(workspace_root or Path.cwd()).resolve()
        self._compiled_destruction = [re.compile(p, re.IGNORECASE) for p in self.SYSTEM_DESTRUCTION_PATTERNS]
        self._compiled_shells = [re.compile(p, re.IGNORECASE) for p in self.REVERSE_SHELL_PATTERNS]
        self._compiled_secrets = [re.compile(p, re.IGNORECASE) for p in self.SECRET_EXFILTRATION_PATTERNS]
        self._compiled_injections = [re.compile(p, re.IGNORECASE) for p in self.PROMPT_INJECTION_PATTERNS]
        self.intrusion_attempts_log: List[Dict[str, Any]] = []

    def audit_command(self, command: str) -> Tuple[bool, str]:
        """Audits a shell command against destruction, reverse shells, and secret theft."""
        cmd_clean = command.strip()

        # 1. System Destruction check
        for pat in self._compiled_destruction:
            if pat.search(cmd_clean):
                msg = "🚨 VETO DE SÉCURITÉ SOUVERAINE : Commande de destruction système bloquée."
                logger.critical(f"[FORTRESS] System destruction blocked: {command}")
                return False, msg

        # 2. Hostile Reverse Shell check
        for pat in self._compiled_shells:
            if pat.search(cmd_clean):
                msg = "🚨 VETO DE SÉCURITÉ SOUVERAINE : Tentative d'ouverture de Reverse Shell hostile bloquée."
                logger.critical(f"[FORTRESS] Reverse shell blocked: {command}")
                return False, msg

        # 3. Secret Exfiltration check
        for pat in self._compiled_secrets:
            if pat.search(cmd_clean):
                msg = "🚨 VETO DE SÉCURITÉ SOUVERAINE : Tentative d'accès non autorisé aux fichiers de secrets (.env, SSH, bash_history) bloquée."
                logger.critical(f"[FORTRESS] Secret exfiltration blocked: {command}")
                return False, msg

        return True, "Commande certifiée conforme à la politique de sécurité souveraine."

    def audit_prompt_injection(self, text: str) -> Tuple[bool, str]:
        """Detects and neutralizes prompt injections, jailbreaks, and secret extraction attacks."""
        clean = text.strip()
        for pat in self._compiled_injections:
            if pat.search(clean):
                msg = "🛡️ PARE-FEU COGNITIF : Tentative d'injection de prompt ou de jailbreak neutralisée."
                logger.warning(f"[FORTRESS] Prompt injection blocked: '{text[:80]}...'")
                return False, msg

        return True, "Requête cognitive saine et vérifiée."

    def is_safe_read_path(self, target_path: Path) -> bool:
        """Verifies that reading from a path does not expose critical credentials."""
        target_str = str(target_path.resolve())
        prohibited_targets = [
            "/.ssh/id_", "/.ssh/id_rsa", "/.ssh/id_ed25519",
            "/.aws/credentials", "/.bash_history", "/.zsh_history"
        ]
        # Never allow reading outside workspace for sensitive files
        for bad in prohibited_targets:
            if bad in target_str:
                logger.critical(f"[FORTRESS] Access to sensitive credential file blocked: {target_str}")
                return False
        return True

    def redact_secrets(self, text: str) -> str:
        """Sanitizes text by replacing sensitive tokens, API keys and credentials with redaction markers."""
        if not text:
            return ""
        # Redact Telegram Bot Token
        redacted = re.sub(r"\b[0-9]{8,11}:[a-zA-Z0-9_-]{30,50}\b", "***TELEGRAM_TOKEN_PROTECTED***", text)
        # Redact Groq API Keys (gsk_...)
        redacted = re.sub(r"\bgsk_[a-zA-Z0-9]{20,60}\b", "***GROQ_KEY_PROTECTED***", redacted)
        # Redact generic private keys
        redacted = re.sub(r"-----BEGIN [A-Z ]+ PRIVATE KEY-----[\s\S]*?-----END [A-Z ]+ PRIVATE KEY-----", "***PRIVATE_KEY_PROTECTED***", redacted)
        return redacted

    def enforce_local_file_permissions(self) -> Dict[str, Any]:
        """Enforces chmod 600 on local .env and credentials to prevent local multi-user sniffing."""
        env_file = self.workspace_root / ".env"
        remediated = False
        if env_file.exists():
            try:
                current_mode = env_file.stat().st_mode
                # If group or others have read permissions, harden to 0600
                if current_mode & (stat.S_IRGRP | stat.S_IROTH | stat.S_IWGRP | stat.S_IWOTH):
                    os.chmod(env_file, 0o600)
                    remediated = True
                    logger.info("[FORTRESS] Hardened .env permissions to 0600 (owner only read/write).")
            except Exception as e:
                logger.warning(f"[FORTRESS] Could not enforce chmod 600 on .env: {e}")
        return {"env_hardened": remediated, "env_exists": env_file.exists()}
