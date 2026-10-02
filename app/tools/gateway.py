"""Tool Gateway (TDR §17). Central access layer for filesystem, terminal, git, and security tools."""

import os
import subprocess
import logging
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger("tool_gateway")


class ToolGateway:
    def __init__(self, workspace_root: str, allow_network: bool = False, allow_sudo: bool = False):
        self.workspace_root = Path(workspace_root).resolve()
        self.allow_network = allow_network
        self.allow_sudo = allow_sudo
        self._ensure_workspace()

    def _ensure_workspace(self):
        if not self.workspace_root.exists():
            self.workspace_root.mkdir(parents=True, exist_ok=True)

    def _is_safe_path(self, path: Path) -> bool:
        """Verifies that the target path does not escape the workspace root unless explicitly allowed."""
        try:
            resolved = path.resolve()
            return resolved == self.workspace_root or self.workspace_root in resolved.parents
        except Exception:
            return False

    # --- Filesystem Tools ---
    def read_file(self, relative_path: str, max_chars: int = 20000) -> Dict[str, Any]:
        target = (self.workspace_root / relative_path).resolve()
        if not self._is_safe_path(target):
            return {"success": False, "error": f"Path outside workspace: {relative_path}"}
        if not target.exists():
            return {"success": False, "error": f"File not found: {relative_path}"}
        try:
            content = target.read_text(encoding="utf-8")
            truncated = False
            if len(content) > max_chars:
                content = content[:max_chars]
                truncated = True
            return {"success": True, "content": content, "truncated": truncated, "path": str(target)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def write_file(self, relative_path: str, content: str) -> Dict[str, Any]:
        target = (self.workspace_root / relative_path).resolve()
        if not self._is_safe_path(target):
            return {"success": False, "error": f"Path outside workspace: {relative_path}"}
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
            logger.info(f"[TOOL:WRITE] {relative_path} ({len(content)} bytes)")
            return {"success": True, "path": str(target), "bytes_written": len(content)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def list_files(self, relative_path: str = ".") -> Dict[str, Any]:
        target = (self.workspace_root / relative_path).resolve()
        if not self._is_safe_path(target):
            return {"success": False, "error": f"Path outside workspace: {relative_path}"}
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

    # --- Terminal Execution ---
    def execute_command(self, command: str, cwd: Optional[str] = None, timeout_sec: int = 30) -> Dict[str, Any]:
        """Executes a shell command inside workspace with timeout and safety checks."""
        # Safety checks
        if "sudo" in command.split() and not self.allow_sudo:
            return {"success": False, "error": "Sudo is disabled in security policy (ALLOW_SUDO=false)."}

        exec_cwd = (self.workspace_root / cwd).resolve() if cwd else self.workspace_root
        if not self._is_safe_path(exec_cwd):
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
        return self.execute_command(f'git add -A && git commit -m "{message}" || true')

    def git_rollback(self) -> Dict[str, Any]:
        """Rolls back uncommitted changes or resets to last commit."""
        return self.execute_command("git reset --hard HEAD")
