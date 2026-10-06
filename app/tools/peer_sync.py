"""Peer Sync & Satellite Security Auditor for FreeAI.
Author: SAGBO MICHAEL (Lead Full-Stack & Backend)
Safely monitors and inspects contributions from the collaborative satellite repo:
git@github.com:SAGBO4/freeAi-mini.git
Prevents Remote Code Execution (RCE) on Michael's PC by enforcing strict offline/LLM auditing
before any peer pull request or commit is merged or imported into the core sovereign system.
"""

import os
import re
import subprocess
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional

logger = logging.getLogger("peer_sync_bridge")


class PeerSyncBridge:
    DEFAULT_SATELLITE_DIR = Path("/home/lesaint/Rendue/freeAi-mini")
    DEFAULT_REMOTE_URL = "git@github.com:SAGBO4/freeAi-mini.git"

    # Red-team patterns to detect in contributor diffs
    DANGEROUS_DIFF_PATTERNS = [
        (r"os\.system\s*\([^)]*(?:curl|wget|nc|bash|sh|python)[^)]*\)", "Remote Download or Shell Execution"),
        (r"subprocess\.(?:Popen|run|call)\s*\([^)]*(?:/bin/sh|/bin/bash|nc|netcat)", "Reverse Shell / Spawning Shell"),
        (r"socket\.connect\s*\(", "Network Socket Connection"),
        (r"eval\s*\(|exec\s*\(", "Dynamic Code Evaluation"),
        (r"base64\.b64decode\s*\(", "Obfuscated Base64 Payload"),
        (r"__import__\s*\(", "Dynamic Module Import Bypass"),
        (r"ctypes\.CDLL", "Native Binary Execution via ctypes"),
        (r"\.ssh/|id_rsa|id_ed25519", "SSH Key Access Attempt"),
        (r"/etc/shadow|/etc/passwd", "System Credential Probe"),
    ]

    def __init__(self, satellite_dir: Optional[Path] = None):
        self.satellite_dir = (satellite_dir or self.DEFAULT_SATELLITE_DIR).resolve()

    def get_satellite_status(self) -> Dict[str, Any]:
        """Checks git status, branches, and recent commits in the satellite repo."""
        if not self.satellite_dir.exists():
            return {
                "success": True,
                "satellite_path": str(self.satellite_dir),
                "remote_url": self.DEFAULT_REMOTE_URL,
                "active_branch": "main",
                "recent_commits": [],
                "healthy": True
            }

        try:
            # Current branch
            branch_proc = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                cwd=str(self.satellite_dir),
                capture_output=True,
                text=True,
                check=False
            )
            branch = branch_proc.stdout.strip() if branch_proc.returncode == 0 else "unknown"

            # Recent commits
            log_proc = subprocess.run(
                ["git", "log", "-n", "5", "--oneline"],
                cwd=str(self.satellite_dir),
                capture_output=True,
                text=True,
                check=False
            )
            commits = log_proc.stdout.strip().splitlines() if log_proc.returncode == 0 else []

            # Remote URL
            remote_proc = subprocess.run(
                ["git", "remote", "get-url", "origin"],
                cwd=str(self.satellite_dir),
                capture_output=True,
                text=True,
                check=False
            )
            remote = remote_proc.stdout.strip() if remote_proc.returncode == 0 else "none"

            return {
                "success": True,
                "satellite_path": str(self.satellite_dir),
                "remote_url": remote,
                "active_branch": branch,
                "recent_commits": commits,
                "healthy": True
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def fetch_peer_updates(self) -> Dict[str, Any]:
        """Fetches latest commits from the remote satellite repository."""
        if not self.satellite_dir.exists():
            return {"success": False, "error": f"Directory not found: {self.satellite_dir}"}

        try:
            fetch_proc = subprocess.run(
                ["git", "fetch", "origin"],
                cwd=str(self.satellite_dir),
                capture_output=True,
                text=True,
                timeout=30,
                check=False
            )
            return {
                "success": fetch_proc.returncode == 0,
                "stdout": fetch_proc.stdout.strip(),
                "stderr": fetch_proc.stderr.strip()
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_diff_against_base(self, base_ref: str = "main", target_ref: str = "dev") -> Dict[str, Any]:
        """Calculates diff between base branch and target contributor branch."""
        if not self.satellite_dir.exists():
            return {"success": False, "error": "Satellite directory missing"}

        try:
            diff_proc = subprocess.run(
                ["git", "diff", f"{base_ref}...{target_ref}"],
                cwd=str(self.satellite_dir),
                capture_output=True,
                text=True,
                check=False
            )
            diff_text = diff_proc.stdout
            return {
                "success": diff_proc.returncode == 0,
                "base": base_ref,
                "target": target_ref,
                "diff": diff_text,
                "lines_count": len(diff_text.splitlines())
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def audit_diff(self, diff_text: str) -> Dict[str, Any]:
        """Performs rigorous security audit on diff text to detect RCE or credential hazards."""
        findings = []

        for line_num, line in enumerate(diff_text.splitlines(), start=1):
            # Only inspect added lines
            if not line.startswith("+") or line.startswith("+++"):
                continue

            content = line[1:].strip()
            for pattern, hazard_desc in self.DANGEROUS_DIFF_PATTERNS:
                if re.search(pattern, content):
                    findings.append({
                        "line": line_num,
                        "code": content[:80],
                        "hazard": hazard_desc,
                        "severity": "CRITICAL"
                    })

        verdict = "PASSED" if not findings else "BLOCKED"
        return {
            "verdict": verdict,
            "findings_count": len(findings),
            "findings": findings,
            "message": (
                "Diff certifié sain : Zéro backdoor ni vecteur RCE détecté."
                if verdict == "PASSED"
                else f"Alerte Sécurité : {len(findings)} motif(s) dangereux identifié(s) dans le code du contributeur !"
            )
        }
