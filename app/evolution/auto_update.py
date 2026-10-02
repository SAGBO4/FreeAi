"""FreeAI Sovereign Auto-Evolution & Self-Updating Engine.
Enables FreeAI to autonomously diagnose, test, self-patch, and safely update its own codebase
with mandatory zero-regression rollback protections (TDR §13, §17).
"""

import os
import sys
import shutil
import logging
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional, List

logger = logging.getLogger("freeai_auto_update")


class AutoUpdateEngine:
    """Manages autonomous self-updates, git synchronization, self-healing patches,
    and hot-reloading with instant rollback upon regression.
    """

    def __init__(self, workspace_root: Optional[str] = None):
        self.workspace_root = Path(workspace_root or Path.cwd()).resolve()

    def check_git_status(self) -> Dict[str, Any]:
        """Checks local git status, uncommitted changes, and remote commit differences."""
        try:
            # Check current commit and branch
            branch_res = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                cwd=str(self.workspace_root),
                capture_output=True,
                text=True,
                timeout=5
            )
            branch = branch_res.stdout.strip() if branch_res.returncode == 0 else "master"

            commit_res = subprocess.run(
                ["git", "rev-parse", "--short", "HEAD"],
                cwd=str(self.workspace_root),
                capture_output=True,
                text=True,
                timeout=5
            )
            commit = commit_res.stdout.strip() if commit_res.returncode == 0 else "unknown"

            # Check dirty files
            status_res = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=str(self.workspace_root),
                capture_output=True,
                text=True,
                timeout=5
            )
            is_dirty = bool(status_res.stdout.strip())
            dirty_files = [line.strip() for line in status_res.stdout.strip().splitlines()] if is_dirty else []

            # Check remote status if remote configured
            remote_res = subprocess.run(
                ["git", "remote"],
                cwd=str(self.workspace_root),
                capture_output=True,
                text=True,
                timeout=5
            )
            has_remote = bool(remote_res.stdout.strip())

            return {
                "success": True,
                "branch": branch,
                "current_commit": commit,
                "is_dirty": is_dirty,
                "dirty_files_count": len(dirty_files),
                "dirty_files": dirty_files[:10],
                "has_remote": has_remote
            }
        except Exception as e:
            logger.error(f"[AUTO-UPDATE] Error checking git status: {e}")
            return {"success": False, "error": str(e)}

    def run_safety_verification_tests(self, timeout_sec: int = 180) -> Dict[str, Any]:
        """Runs the entire automated test suite to ensure 100% zero-regression."""
        logger.info("[AUTO-UPDATE] Running comprehensive safety tests (pytest)...")
        try:
            cmd = [sys.executable, "-m", "pytest", "tests/", "-q"]
            res = subprocess.run(
                cmd,
                cwd=str(self.workspace_root),
                capture_output=True,
                text=True,
                timeout=timeout_sec
            )
            passed = res.returncode == 0
            output_tail = res.stdout.strip().splitlines()[-5:] if res.stdout else []
            return {
                "success": passed,
                "returncode": res.returncode,
                "summary": "\n".join(output_tail),
                "raw_output": res.stdout[-1500:] if res.stdout else res.stderr[-1500:]
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Banc de test dépassé (délai d'attente expiré)"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def apply_git_pull_update(self) -> Dict[str, Any]:
        """Pulls latest updates from git remote with automatic test verification and rollback."""
        status = self.check_git_status()
        if not status.get("has_remote"):
            return {
                "success": False,
                "error": "Aucun dépôt distant (remote) configuré pour 'git pull'. Utilisez l'auto-optimisation locale."
            }

        # Save previous commit hash
        old_commit = status.get("current_commit")

        try:
            # 1. Fetch & pull
            pull_res = subprocess.run(
                ["git", "pull", "--rebase"],
                cwd=str(self.workspace_root),
                capture_output=True,
                text=True,
                timeout=30
            )
            if pull_res.returncode != 0:
                return {
                    "success": False,
                    "error": f"Échec du pull git : {pull_res.stderr.strip()}"
                }

            # 2. Run safety tests
            test_res = self.run_safety_verification_tests()
            if not test_res.get("success"):
                logger.critical("[AUTO-UPDATE] Tests failed after pull! Rolling back immediately...")
                subprocess.run(
                    ["git", "reset", "--hard", old_commit],
                    cwd=str(self.workspace_root),
                    capture_output=True
                )
                return {
                    "success": False,
                    "rolled_back": True,
                    "error": f"Régression détectée lors des tests post-mise à jour ! Rollback automatique vers {old_commit} exécuté avec succès.",
                    "test_output": test_res.get("summary")
                }

            # 3. New commit
            new_status = self.check_git_status()
            return {
                "success": True,
                "old_commit": old_commit,
                "new_commit": new_status.get("current_commit"),
                "tests_passed": True,
                "message": f"Mise à jour réussie de {old_commit} vers {new_status.get('current_commit')} avec validation 100% tests."
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def apply_self_evolution_patch(self, patch_description: str, file_path: str, new_content: str) -> Dict[str, Any]:
        """Applies an autonomous patch or improvement to FreeAI's own source code,
        verifies that 100% of integration tests pass, and rolls back if any test fails.
        """
        target = (self.workspace_root / file_path).resolve()
        try:
            target.relative_to(self.workspace_root)
        except ValueError:
            return {"success": False, "error": "Sécurité : tentative de patch en dehors du workspace."}

        if not target.exists():
            return {"success": False, "error": f"Fichier cible introuvable : {file_path}"}

        # Backup original content in memory
        original_content = target.read_text(encoding="utf-8")

        try:
            # 1. Apply proposed modification
            target.write_text(new_content, encoding="utf-8")
            logger.info(f"[AUTO-UPDATE] Applied provisional self-patch to {file_path}")

            # 2. Run test verification suite
            test_res = self.run_safety_verification_tests()
            if not test_res.get("success"):
                # Instant rollback
                target.write_text(original_content, encoding="utf-8")
                logger.warning(f"[AUTO-UPDATE] Self-patch failed tests. Rolled back {file_path} cleanly.")
                return {
                    "success": False,
                    "rolled_back": True,
                    "error": "Échec des tests de validation sur le patch autonome. Rollback immédiat effectué.",
                    "test_summary": test_res.get("summary")
                }

            # 3. Success: Commit self-patch into git
            subprocess.run(["git", "add", str(target)], cwd=str(self.workspace_root), check=False)
            commit_msg = f"auto-evolve: {patch_description}"
            subprocess.run(["git", "commit", "-m", commit_msg], cwd=str(self.workspace_root), check=False)

            return {
                "success": True,
                "file_patched": file_path,
                "description": patch_description,
                "tests_passed": True,
                "message": f"Auto-évolution validée et appliquée avec succès sur {file_path} (100% tests passés)."
            }

        except Exception as e:
            # Safety restore
            target.write_text(original_content, encoding="utf-8")
            return {"success": False, "error": f"Erreur inattendue pendant l'auto-patch : {e}"}

    def trigger_hot_reload(self) -> Dict[str, Any]:
        """Triggers a clean process restart or module reload to activate new code."""
        return {
            "success": True,
            "can_exec": True,
            "python_executable": sys.executable,
            "argv": sys.argv,
            "message": "Prêt pour le redémarrage à chaud. Lancez '/restart' ou relancez le CLI."
        }
