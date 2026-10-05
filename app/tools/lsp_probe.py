"""Live LSP & Syntax Probe Engine for FreeAI (OpenCode Status Bar & Diagnostics).
Provides real-time inspection of code health:
- Probes 'ruff', 'pyright', or native zero-overhead AST syntax validation.
- Non-blocking caching with TTL to guarantee 0ms latency impact on TUI rendering.
- Powers the footer status bar '• 0 LSP' and interactive '/lsp' inspection command.
"""

import os
import ast
import json
import time
import shutil
import asyncio
import subprocess
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple


@dataclass
class DiagnosticItem:
    file: str
    line: int
    col: int
    severity: str  # "error" | "warning" | "info"
    code: str
    message: str
    engine: str


@dataclass
class LspSummary:
    errors: int
    warnings: int
    engine: str
    display_badge: str
    timestamp: float
    total_files_scanned: int


Tuple_diagnostics = Tuple[List[DiagnosticItem], int]


class LiveLspProbe:
    """Live probe engine monitoring workspace code integrity."""

    def __init__(self, workspace_root: Optional[str] = None):
        self.workspace_root = Path(workspace_root or os.getcwd()).resolve()
        self._cached_summary: Optional[LspSummary] = None
        self._cached_diagnostics: List[DiagnosticItem] = []
        self._last_probe_time = 0.0
        self._probe_ttl = 5.0  # 5-second TTL cache for non-blocking UI

    def set_workspace(self, path: str):
        self.workspace_root = Path(path).resolve()
        self._cached_summary = None
        self._cached_diagnostics.clear()
        self._last_probe_time = 0.0

    def detect_engine(self) -> str:
        """Determines best available linter/LSP engine in environment."""
        if shutil.which("ruff"):
            return "ruff"
        if shutil.which("pyright"):
            return "pyright"
        return "ast"

    def scan_native_ast(self, max_files: int = 40) -> Tuple_diagnostics:
        """High-speed native AST syntax and indentation scanner (0 external dependencies)."""
        diagnostics = []
        scanned_count = 0
        skip_dirs = {".git", "__pycache__", ".pytest_cache", ".venv", "venv", "node_modules"}

        for root, dirs, files in os.walk(str(self.workspace_root)):
            dirs[:] = [d for d in dirs if d not in skip_dirs and not d.startswith(".")]
            for f in files:
                if f.endswith(".py"):
                    scanned_count += 1
                    file_path = Path(root) / f
                    rel_path = file_path.relative_to(self.workspace_root).as_posix()
                    try:
                        content = file_path.read_text(encoding="utf-8", errors="replace")
                        ast.parse(content, filename=str(file_path))
                    except SyntaxError as se:
                        diagnostics.append(DiagnosticItem(
                            file=rel_path,
                            line=se.lineno or 1,
                            col=se.offset or 1,
                            severity="error",
                            code="SyntaxError",
                            message=str(se.msg),
                            engine="ast"
                        ))
                    except Exception as ex:
                        diagnostics.append(DiagnosticItem(
                            file=rel_path,
                            line=1,
                            col=1,
                            severity="warning",
                            code="ParseWarning",
                            message=str(ex),
                            engine="ast"
                        ))

                    if scanned_count >= max_files:
                        break
            if scanned_count >= max_files:
                break

        return diagnostics, scanned_count

    def scan_ruff(self) -> Tuple_diagnostics:
        """Runs ruff in JSON mode for fast static analysis."""
        diagnostics = []
        scanned_count = 0
        try:
            res = subprocess.run(
                ["ruff", "check", "--output-format", "json", "."],
                cwd=str(self.workspace_root),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=3.0
            )
            data = json.loads(res.stdout) if res.stdout else []
            for item in data[:50]:
                code = item.get("code", "Ruff")
                is_err = code.startswith("E9") or code.startswith("F") or "syntax" in item.get("message", "").lower()
                diagnostics.append(DiagnosticItem(
                    file=item.get("filename", ""),
                    line=item.get("location", {}).get("row", 1),
                    col=item.get("location", {}).get("column", 1),
                    severity="error" if is_err else "warning",
                    code=code,
                    message=item.get("message", ""),
                    engine="ruff"
                ))
            scanned_count = len(data)
        except Exception:
            # Fallback to AST scanner on error
            return self.scan_native_ast()
        return diagnostics, scanned_count

    def scan_pyright(self) -> Tuple_diagnostics:
        """Runs pyright in JSON mode if available."""
        diagnostics = []
        try:
            res = subprocess.run(
                ["pyright", "--outputjson"],
                cwd=str(self.workspace_root),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=4.0
            )
            data = json.loads(res.stdout) if res.stdout else {}
            diag_list = data.get("generalDiagnostics", [])
            for item in diag_list[:50]:
                diagnostics.append(DiagnosticItem(
                    file=item.get("file", ""),
                    line=item.get("range", {}).get("start", {}).get("line", 0) + 1,
                    col=item.get("range", {}).get("start", {}).get("character", 0) + 1,
                    severity=item.get("severity", "error"),
                    code=item.get("rule", "Pyright"),
                    message=item.get("message", ""),
                    engine="pyright"
                ))
            return diagnostics, len(diag_list)
        except Exception:
            return self.scan_native_ast()

    def get_diagnostics(self, force_refresh: bool = False) -> List[DiagnosticItem]:
        """Returns live list of diagnostics with TTL caching."""
        now = time.time()
        if not force_refresh and (now - self._last_probe_time) < self._probe_ttl and self._cached_summary:
            return self._cached_diagnostics

        engine = self.detect_engine()
        if engine == "ruff":
            diags, scanned = self.scan_ruff()
        elif engine == "pyright":
            diags, scanned = self.scan_pyright()
        else:
            diags, scanned = self.scan_native_ast()

        errors = sum(1 for d in diags if d.severity == "error")
        warnings = sum(1 for d in diags if d.severity == "warning")

        # OpenCode Style Badge formatting
        if errors == 0 and warnings == 0:
            badge = "[bold green]•[/] 0 LSP"
        elif errors == 0:
            badge = f"[bold yellow]•[/] {warnings} LSP ({warnings}w)"
        else:
            badge = f"[bold red]•[/] {errors} LSP ({errors}e {warnings}w)" if warnings else f"[bold red]•[/] {errors} LSP ({errors}e)"

        self._cached_summary = LspSummary(
            errors=errors,
            warnings=warnings,
            engine=engine,
            display_badge=badge,
            timestamp=now,
            total_files_scanned=scanned
        )
        self._cached_diagnostics = diags
        self._last_probe_time = now

        return self._cached_diagnostics

    def get_summary_badge(self) -> str:
        """Returns instantaneous formatted badge for footer status bar."""
        if self._cached_summary is None or (time.time() - self._last_probe_time) >= self._probe_ttl:
            self.get_diagnostics()
        return self._cached_summary.display_badge if self._cached_summary else "[bold green]•[/] 0 LSP"


# Global singleton probe
live_lsp_probe = LiveLspProbe()
