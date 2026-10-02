"""Tool Gateway (TDR §17). Central access layer for filesystem, terminal, git, and security tools.
Supports both sandboxed and computer-wide access modes (ALLOW_GLOBAL_READ & ALLOW_FULL_FS_ACCESS).
"""

import os
import re
import fnmatch
import subprocess
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List

logger = logging.getLogger("tool_gateway")


class ToolGateway:
    def __init__(
        self,
        workspace_root: str,
        allow_network: bool = False,
        allow_sudo: bool = False,
        allow_global_read: bool = False,
        allow_full_fs_access: bool = False,
        mode: str = "freeAi"
    ):
        self.workspace_root = Path(workspace_root).resolve()
        self.allow_network = allow_network
        self.allow_sudo = allow_sudo
        self.allow_global_read = allow_global_read
        self.allow_full_fs_access = allow_full_fs_access
        self.mode = mode
        self._ensure_workspace()

    def set_mode(self, mode_name: str) -> Dict[str, Any]:
        """Dynamically switches permissions between standard freeAi mode and super-user lesaintAi mode."""
        clean_mode = (mode_name or "").strip().lower()
        if clean_mode in ("lesaintai", "lesaint", "super", "root"):
            self.mode = "lesaintAi"
            self.allow_sudo = True
            self.allow_full_fs_access = True
            self.allow_global_read = True
            logger.info("[TOOL_GATEWAY] Mode switched -> lesaintAi (Super-User: Sudo enabled, unrestricted FS access)")
            return {
                "success": True,
                "mode": "lesaintAi",
                "allow_sudo": True,
                "allow_full_fs_access": True,
                "allow_global_read": True,
                "description": "Mode Super-Utilisateur actif (déverrouillage total, sudo activé, écriture et exécution sur tout le PC)"
            }
        else:
            self.mode = "freeAi"
            self.allow_sudo = False
            self.allow_full_fs_access = False
            self.allow_global_read = True
            logger.info("[TOOL_GATEWAY] Mode switched -> freeAi (Standard: Sudo disabled, workspace-confined writes, global read)")
            return {
                "success": True,
                "mode": "freeAi",
                "allow_sudo": False,
                "allow_full_fs_access": False,
                "allow_global_read": True,
                "description": "Mode Standard sécurisé (sudo désactivé, écriture confinée au workspace, lecture globale autorisée, compression Neon)"
            }

    def _ensure_workspace(self):
        if not self.workspace_root.exists():
            self.workspace_root.mkdir(parents=True, exist_ok=True)

    def _resolve_target_path(self, raw_path: str) -> Path:
        """Resolves target path, supporting absolute paths or workspace-relative paths."""
        p = Path(raw_path).expanduser()
        if p.is_absolute():
            return p.resolve()
        return (self.workspace_root / p).resolve()

    def _is_safe_path(self, path: Path) -> bool:
        """Verifies that the target path does not escape the workspace root."""
        try:
            resolved = path.resolve()
            return resolved == self.workspace_root or self.workspace_root in resolved.parents
        except Exception:
            return False

    def _is_safe_read_path(self, path: Path) -> bool:
        """Checks if reading from path is allowed (global or workspace-scoped)."""
        if self.allow_global_read or self.allow_full_fs_access:
            return True
        return self._is_safe_path(path)

    def _is_safe_write_path(self, path: Path) -> bool:
        """Checks if writing to path is allowed."""
        if self.allow_full_fs_access:
            return True
        return self._is_safe_path(path)

    def _is_privileged_command(self, command: str) -> bool:
        """Detects attempts to execute privileged commands (sudo, doas, pkexec, su)."""
        pattern = r'(?:^|[;&|`$()\s])(?:[\w./-]*/)?\\?(sudo|doas|pkexec|su)(?:[;&|`$()\s]|$)'
        return bool(re.search(pattern, command.strip()))

    # --- Filesystem Tools ---
    def read_file(self, target_path: str, max_chars: int = 20000) -> Dict[str, Any]:
        target = self._resolve_target_path(target_path)
        if not self._is_safe_read_path(target):
            return {"success": False, "error": f"Path outside workspace: {target_path}"}
        if not target.exists():
            return {"success": False, "error": f"File not found: {target_path}"}
        if target.is_dir():
            return {"success": False, "error": f"Target is a directory: {target_path}"}
        try:
            content = target.read_text(encoding="utf-8", errors="replace")
            truncated = False
            if len(content) > max_chars:
                content = content[:max_chars]
                truncated = True
            return {"success": True, "content": content, "truncated": truncated, "path": str(target)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def write_file(self, target_path: str, content: str) -> Dict[str, Any]:
        target = self._resolve_target_path(target_path)
        if not self._is_safe_write_path(target):
            return {"success": False, "error": f"Path outside workspace: {target_path}"}
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
            logger.info(f"[TOOL:WRITE] {target} ({len(content)} bytes)")
            return {"success": True, "path": str(target), "bytes_written": len(content)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def list_files(self, target_path: str = ".") -> Dict[str, Any]:
        target = self._resolve_target_path(target_path)
        if not self._is_safe_read_path(target):
            return {"success": False, "error": f"Path outside workspace: {target_path}"}
        if not target.exists():
            return {"success": False, "error": f"Directory not found: {target_path}"}
        try:
            items = []
            for item in target.iterdir():
                items.append({
                    "name": item.name,
                    "is_dir": item.is_dir(),
                    "size": item.stat().st_size if item.is_file() else 0
                })
            return {"success": True, "items": items, "directory": str(target)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def search_files(self, pattern: str, search_dir: Optional[str] = None, max_results: int = 50) -> Dict[str, Any]:
        """Scours the computer or specified directory to find files matching a name/pattern."""
        root = self._resolve_target_path(search_dir) if search_dir else self.workspace_root
        if not self._is_safe_read_path(root):
            return {"success": False, "error": f"Path outside allowed read scope: {search_dir}"}

        matches = []
        excluded_dirs = {
            "node_modules", "__pycache__", "venv", ".venv", ".git", ".cache",
            "proc", "sys", "dev", "run", "snap", "timeshift"
        }
        try:
            for dirpath, dirnames, filenames in os.walk(root, topdown=True, onerror=lambda err: None):
                dirnames[:] = [d for d in dirnames if not d.startswith(".") and d not in excluded_dirs]
                for filename in filenames:
                    if fnmatch.fnmatch(filename, pattern):
                        matches.append(os.path.join(dirpath, filename))
                        if len(matches) >= max_results:
                            break
                if len(matches) >= max_results:
                    break
            return {"success": True, "pattern": pattern, "root": str(root), "matches": matches, "count": len(matches)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def search_code(self, query: str, search_dir: Optional[str] = None, file_pattern: str = "*", max_matches: int = 30) -> Dict[str, Any]:
        """Searches across files on the computer for code snippets, functions, or solutions."""
        root = self._resolve_target_path(search_dir) if search_dir else self.workspace_root
        if not self._is_safe_read_path(root):
            return {"success": False, "error": f"Path outside allowed read scope: {search_dir}"}

        results = []
        excluded_dirs = {
            "node_modules", "__pycache__", "venv", ".venv", ".git", ".cache",
            "proc", "sys", "dev", "run", "snap", "timeshift"
        }
        try:
            for dirpath, dirnames, filenames in os.walk(root, topdown=True, onerror=lambda err: None):
                dirnames[:] = [d for d in dirnames if not d.startswith(".") and d not in excluded_dirs]
                for filename in filenames:
                    if fnmatch.fnmatch(filename, file_pattern):
                        filepath = os.path.join(dirpath, filename)
                        try:
                            # Skip large files > 2MB
                            if os.path.getsize(filepath) > 2 * 1024 * 1024:
                                continue
                            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                                for line_num, line in enumerate(f, 1):
                                    if query.lower() in line.lower():
                                        results.append({
                                            "file": filepath,
                                            "line": line_num,
                                            "content": line.strip()[:200]
                                        })
                                        if len(results) >= max_matches:
                                            break
                        except Exception:
                            pass
                    if len(results) >= max_matches:
                        break
                if len(results) >= max_matches:
                    break
            return {"success": True, "query": query, "root": str(root), "matches": results, "count": len(results)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # --- Terminal Execution ---
    def execute_command(self, command: str, cwd: Optional[str] = None, timeout_sec: int = 30) -> Dict[str, Any]:
        """Executes a shell command with timeout and safety checks."""
        # Safety checks
        if not self.allow_sudo and self._is_privileged_command(command):
            return {"success": False, "error": "Sudo is disabled in security policy (ALLOW_SUDO=false)."}

        if cwd:
            exec_cwd = self._resolve_target_path(cwd)
        else:
            exec_cwd = self.workspace_root

        if not self._is_safe_read_path(exec_cwd):
            return {"success": False, "error": f"Working directory outside workspace: {exec_cwd}"}

        logger.info(f"[TOOL:TERMINAL] cwd={exec_cwd} cmd='{command}'")
        try:
            res = subprocess.run(
                command,
                shell=True,
                cwd=str(exec_cwd),
                capture_output=True,
                text=True,
                timeout=timeout_sec
            )
            return {
                "success": res.returncode == 0,
                "exit_code": res.returncode,
                "stdout": res.stdout,
                "stderr": res.stderr
            }
        except subprocess.TimeoutExpired:
            logger.error(f"[TOOL:TERMINAL TIMEOUT] '{command}' exceeded {timeout_sec}s")
            return {"success": False, "error": f"Command timed out after {timeout_sec} seconds"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # --- Git Operations & Checkpoints (TDR §31 Rollback) ---
    def git_checkpoint(self, message: str = "auto-checkpoint") -> Dict[str, Any]:
        """Creates a local commit checkpoint for instant rollback."""
        git_dir = self.workspace_root / ".git"
        target_cwd = self.workspace_root
        if not git_dir.exists():
            cwd_git = Path.cwd().resolve() / ".git"
            if cwd_git.exists():
                target_cwd = Path.cwd().resolve()
            else:
                return {"success": False, "error": f"Aucun dépôt Git trouvé dans {self.workspace_root}"}
        return self.execute_command(f'git add -A && git commit -m "{message}" || true', cwd=str(target_cwd))

    def git_rollback(self) -> Dict[str, Any]:
        """Rolls back uncommitted changes or resets to last commit."""
        git_dir = self.workspace_root / ".git"
        target_cwd = self.workspace_root
        if not git_dir.exists():
            cwd_git = Path.cwd().resolve() / ".git"
            if cwd_git.exists():
                target_cwd = Path.cwd().resolve()
            else:
                return {
                    "success": False,
                    "error": f"Aucun dépôt Git trouvé dans le workspace ({self.workspace_root}) pour effectuer le rollback."
                }
        return self.execute_command("git reset --hard HEAD", cwd=str(target_cwd))
