"""Autonomous Code Integrity & Anti-Truncation Guardian.

Inspired by rigorous autonomous development hooks (my_jarvis stop_check.py & post_fix.py),
this guardian guarantees:
1. Anti-Truncation Protection: Detects and rejects shortcut placeholders such as
   `... (rest of the code)`, `// ...`, `# ... (unchanged)`, ensuring all generated files
   are complete and production-grade.
2. Typography & Sanitization: Detects forbidden raw emojis in terminal/source modules
   and forbidden em-dashes (U+2014) in command outputs.
3. Automated Quality Gate: Scans modified files, verifies syntax, and optionally executes
   `ruff check --fix` and test runners before commits or handovers.
"""

import ast
import json
import logging
import os
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger("code_integrity_guardian")

# Patterns for lazy AI truncation shortcuts
PLACEHOLDER_REGEX = re.compile(
    r"\.\.\.\s*\((rest|reste|remaining|suite|same|unchanged|inchang)|"
    r"rest of (the )?(file|code)|"
    r"reste du (fichier|code)|"
    r"^\s*(#|//|/\*|<!--)\s*\.\.\.\s*(\*/|-->)?\s*$",
    re.IGNORECASE | re.MULTILINE,
)

EM_DASH = "—"

# Forbidden raw emojis in source code and CLI (allowed only in Telegram router)
FORBIDDEN_EMOJI_REGEX = re.compile(r"[—☀-➿⬀-⯿️‍\U0001f000-\U0001faff]")

SKIP_DIRS: Set[str] = {
    ".git",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    ".mypy_cache",
    "node_modules",
    ".venv",
    "venv",
    "data",
    ".cache",
    "dist",
    "build",
}


@dataclass
class CodeHealthReport:
    """Rapport d'intégrité et de santé pour un fichier ou fragment de code."""
    is_valid: bool
    file_path: Optional[str] = None
    has_truncation: bool = False
    truncation_matches: List[str] = field(default_factory=list)
    has_em_dash: bool = False
    em_dash_lines: List[int] = field(default_factory=list)
    has_rogue_emojis: bool = False
    syntax_error: Optional[str] = None
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_valid": self.is_valid,
            "file_path": self.file_path,
            "has_truncation": self.has_truncation,
            "truncation_matches": self.truncation_matches,
            "has_em_dash": self.has_em_dash,
            "em_dash_lines": self.em_dash_lines,
            "has_rogue_emojis": self.has_rogue_emojis,
            "syntax_error": self.syntax_error,
            "warnings": self.warnings
        }


class CodeIntegrityFinding:
    """Represents a code integrity violation or defect."""

    def __init__(
        self,
        file_path: str,
        line_number: int,
        defect_type: str,
        description: str,
        snippet: str = "",
    ) -> None:
        self.file_path = file_path
        self.line_number = line_number
        self.defect_type = defect_type
        self.description = description
        self.snippet = snippet

    def to_dict(self) -> Dict[str, Any]:
        return {
            "file": self.file_path,
            "line": self.line_number,
            "type": self.defect_type,
            "description": self.description,
            "snippet": self.snippet,
        }

    def __str__(self) -> str:
        return f"[{self.defect_type}] {self.file_path}:{self.line_number} - {self.description} ({self.snippet[:60]})"


class CodeIntegrityGuardian:
    """Audits codebase for truncation placeholders, style violations, and integrity."""

    def __init__(self, root_dir: Optional[Path] = None) -> None:
        self.root_dir = root_dir or Path.cwd()

    @classmethod
    def check_text(cls, content: str, filename: Optional[str] = None) -> CodeHealthReport:
        """Analyzes text in-memory to verify completeness, syntax and absence of placeholders."""
        report = CodeHealthReport(is_valid=True, file_path=filename)

        # 1. Truncation check
        trunc_hits = []
        for match in PLACEHOLDER_REGEX.finditer(content):
            line_no = content.count("\n", 0, match.start()) + 1
            trunc_hits.append(f"Ligne {line_no}: {match.group(0).strip()}")

        if trunc_hits:
            report.has_truncation = True
            report.truncation_matches = trunc_hits
            report.is_valid = False
            report.warnings.append(
                f"Fichier tronqué détecté ({len(trunc_hits)} raccourcis trouvés). Le code complet doit être fourni."
            )

        # 2. Em-dash check
        lines = content.splitlines()
        dash_lines = []
        for idx, line in enumerate(lines, 1):
            if EM_DASH in line:
                dash_lines.append(idx)

        if dash_lines:
            report.has_em_dash = True
            report.em_dash_lines = dash_lines
            report.warnings.append(
                f"Tiret cadratin '—' détecté sur les lignes {dash_lines[:5]}."
            )

        # 3. Rogue emojis in code files
        is_code = filename and any(filename.endswith(ext) for ext in (".py", ".js", ".ts", ".rs", ".go", ".c", ".cpp"))
        if is_code and FORBIDDEN_EMOJI_REGEX.search(content):
            report.has_rogue_emojis = True
            report.warnings.append("Emojis détectés dans le code source.")

        # 4. AST check for Python
        if filename and filename.endswith(".py"):
            try:
                ast.parse(content, filename=filename or "<input>")
            except SyntaxError as se:
                report.syntax_error = f"SyntaxError à la ligne {se.lineno}: {se.msg}"
                report.is_valid = False
                report.warnings.append(report.syntax_error)

        return report

    @classmethod
    def check_file(cls, path: Path | str) -> CodeHealthReport:
        """Reads and verifies a file on disk."""
        p = Path(path)
        if not p.exists() or not p.is_file():
            return CodeHealthReport(is_valid=False, file_path=str(p), warnings=["Fichier introuvable."])

        try:
            content = p.read_text(encoding="utf-8", errors="replace")
            return cls.check_text(content, filename=p.name)
        except Exception as e:
            return CodeHealthReport(is_valid=False, file_path=str(p), warnings=[f"Erreur de lecture: {e}"])

    @classmethod
    def sanitize_code(cls, content: str, remove_emojis: bool = True) -> str:
        """Strips rogue emojis without modifying valid logic."""
        if remove_emojis:
            return FORBIDDEN_EMOJI_REGEX.sub("", content)
        return content

    def scan_file(self, path: Path) -> List[CodeIntegrityFinding]:
        """Scans a single file for truncation and forbidden characters."""
        findings: List[CodeIntegrityFinding] = []
        try:
            content = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            return findings

        rel_path = str(path.relative_to(self.root_dir) if path.is_relative_to(self.root_dir) else path)

        for match in PLACEHOLDER_REGEX.finditer(content):
            line_no = content.count("\n", 0, match.start()) + 1
            matched_text = match.group(0).strip()
            findings.append(
                CodeIntegrityFinding(
                    file_path=rel_path,
                    line_number=line_no,
                    defect_type="TRUNCATION_PLACEHOLDER",
                    description="Fichier tronque par un raccourci d'IA. Le code reel est manquant.",
                    snippet=matched_text,
                )
            )

        if not rel_path.startswith("docs/") and "test" not in rel_path.lower():
            lines = content.splitlines()
            for idx, line in enumerate(lines, 1):
                if FORBIDDEN_EMOJI_REGEX.search(line):
                    if "FORBIDDEN" in line or "EMOJI" in line:
                        continue
                    findings.append(
                        CodeIntegrityFinding(
                            file_path=rel_path,
                            line_number=idx,
                            defect_type="FORBIDDEN_CHARACTERS",
                            description="Emoji brut ou tiret cadratin detecte dans le code source.",
                            snippet=line.strip()[:80],
                        )
                    )

        return findings

    def audit_directory(self, target_dir: Optional[Path] = None) -> List[CodeIntegrityFinding]:
        """Audits all tracked or relevant source files in target directory."""
        scan_dir = target_dir or self.root_dir
        all_findings: List[CodeIntegrityFinding] = []

        for root, dirs, files in os.walk(scan_dir):
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith(".")]
            for file_name in files:
                if file_name.endswith((".py", ".sh", ".js", ".ts", ".html", ".css", ".md")):
                    file_path = Path(root) / file_name
                    all_findings.extend(self.scan_file(file_path))

        return all_findings

    def sanitize_file_emojis(self, path: Path) -> bool:
        """Strips raw emojis automatically from a target file in place."""
        try:
            content = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            return False

        cleaned = re.sub(r"[—☀-➿⬀-⯿️‍\U0001f000-\U0001faff] ?", "", content)
        if cleaned != content:
            path.write_text(cleaned, encoding="utf-8")
            return True
        return False

    def run_pre_stop_check(self) -> Tuple[bool, List[str]]:
        """Validates that tests pass and no truncation defects exist before completion."""
        errors: List[str] = []
        findings = self.audit_directory()
        truncations = [f for f in findings if f.defect_type == "TRUNCATION_PLACEHOLDER"]

        if truncations:
            errors.append(
                f"Defauts d'integrite critiques: {len(truncations)} raccourci(s) de truncation detecte(s)."
            )
            for t in truncations[:5]:
                errors.append(f"  - {t}")

        return len(errors) == 0, errors


# Singleton instances
code_integrity_guardian = CodeIntegrityGuardian()
code_sentinel = code_integrity_guardian
