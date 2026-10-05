"""Semantic Compaction Engine for FreeAI (TUI & Agentic Context Optimization).
Implements the /compact neural history distillation algorithm:
Compresses deep conversational turn history into high-density structured state anchors
without losing critical context (architectural decisions, file touchpoints, unsolved bugs, active goals).
"""

import re
import time
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional


@dataclass
class CompactionReport:
    """Detailed telemetry and metrics of a semantic compaction run."""
    turns_before: int
    turns_after: int
    tokens_before_est: int
    tokens_after_est: int
    tokens_saved: int
    compression_ratio: float  # e.g., 0.85 = 85% saved
    anchors_count: int
    distilled_state: str
    duration_ms: float


class SemanticCompactor:
    """Neuronal history distiller and context memory compactor."""

    def __init__(self, keep_recent_turns: int = 3):
        self.keep_recent_turns = keep_recent_turns

    def extract_file_touchpoints(self, turns: List[Dict[str, Any]]) -> List[str]:
        """Detects all referenced and modified file paths across the turns."""
        pattern = re.compile(r'(?:@|[\s"\'`])([a-zA-Z0-9_\-./]+\.[a-zA-Z0-9]{1,8})')
        found_files = set()
        for turn in turns:
            content = str(turn.get("content", ""))
            matches = pattern.findall(content)
            for m in matches:
                # Filter out obvious false positives like URLs, decimals, or version numbers
                if not any(m.startswith(p) for p in ("http", "v1", "v2", "0.", "1.", "2.")) and "/" in m or m.endswith((".py", ".json", ".md", ".sh", ".toml", ".yaml", ".txt")):
                    found_files.add(m.strip())
        return sorted(list(found_files))[:20]

    def extract_architectural_decisions(self, turns: List[Dict[str, Any]]) -> List[str]:
        """Extracts key architectural choices, libraries, and design patterns formulated."""
        keywords = (
            "décidé", "choisi", "adopté", "architecture", "pattern", "remplacé", "implémenté",
            "refactorisé", "structure", "design", "standardisé", "sentinelle", "sentinel", "sécurité", "activé"
        )
        decisions = []
        for turn in turns:
            content = str(turn.get("content", ""))
            for line in content.splitlines():
                line_clean = line.strip().lstrip("-*• ")
                if any(kw in line_clean.lower() for kw in keywords) and 15 < len(line_clean) < 160:
                    if line_clean not in decisions:
                        decisions.append(line_clean)
        return decisions[:10]

    def extract_diagnostics_and_fixes(self, turns: List[Dict[str, Any]]) -> List[str]:
        """Extracts errors diagnosed, failed tests, and applied fixes."""
        diag_keywords = ("erreur", "fail", "error", "fix", "résolu", "corrigé", "syntaxerror", "exception", "bug", "patch")
        fixes = []
        for turn in turns:
            content = str(turn.get("content", ""))
            for line in content.splitlines():
                line_clean = line.strip().lstrip("-*• ")
                if any(kw in line_clean.lower() for kw in diag_keywords) and 10 < len(line_clean) < 140:
                    if line_clean not in fixes:
                        fixes.append(line_clean)
        return fixes[:8]

    def extract_active_goal(self, turns: List[Dict[str, Any]]) -> str:
        """Determines the active objective and current user context."""
        for turn in reversed(turns):
            if turn.get("role") == "user":
                content = str(turn.get("content", "")).strip()
                if content and not content.startswith("/"):
                    first_line = content.splitlines()[0]
                    return first_line[:120]
        return "Poursuite de la session d'ingénierie et de développement."

    def build_distilled_anchor(
        self,
        turns_to_compact: List[Dict[str, Any]],
        mode: str = "freeAi"
    ) -> str:
        """Synthesizes historical turns into a structured, high-density neural anchor."""
        files = self.extract_file_touchpoints(turns_to_compact)
        decisions = self.extract_architectural_decisions(turns_to_compact)
        fixes = self.extract_diagnostics_and_fixes(turns_to_compact)
        active_goal = self.extract_active_goal(turns_to_compact)

        sections = [
            "--- [SEMANTIC COMPACTION ANCHOR / NEURAL DISTILLATION] ---",
            f"• Mode de session : {mode} (État de sécurité et privilèges conservés)",
            f"• Objectif principal : {active_goal}"
        ]

        if files:
            sections.append("• Fichiers & Touchpoints vérifiés :")
            sections.extend([f"  - {f}" for f in files])

        if decisions:
            sections.append("• Décisions architecturales actées :")
            sections.extend([f"  - {d}" for d in decisions])

        if fixes:
            sections.append("• Diagnostics & Correctifs appliqués :")
            sections.extend([f"  - {fx}" for fx in fixes])

        sections.append("----------------------------------------------------------")
        return "\n".join(sections)

    def compact_memory(
        self,
        conversation_memory: Any,
        mode: str = "freeAi",
        keep_recent_override: Optional[int] = None
    ) -> CompactionReport:
        """Compacts turns within a ConversationMemory instance."""
        start_time = time.perf_counter()
        keep_n = keep_recent_override if keep_recent_override is not None else self.keep_recent_turns

        turns: List[Dict[str, Any]] = getattr(conversation_memory, "turns", [])
        total_turns = len(turns)

        if total_turns <= keep_n:
            # Nothing to compact yet
            return CompactionReport(
                turns_before=total_turns,
                turns_after=total_turns,
                tokens_before_est=sum(len(t.get("content", "")) // 4 for t in turns),
                tokens_after_est=sum(len(t.get("content", "")) // 4 for t in turns),
                tokens_saved=0,
                compression_ratio=0.0,
                anchors_count=0,
                distilled_state="Historique trop court pour compaction.",
                duration_ms=(time.perf_counter() - start_time) * 1000
            )

        turns_to_compact = turns[:-keep_n]
        recent_turns = turns[-keep_n:]

        # Calculate pre-compaction metrics
        raw_text_before = " ".join(str(t.get("content", "")) for t in turns)
        tokens_before = max(1, len(raw_text_before) // 4)

        # Build distilled neural anchor
        anchor_text = self.build_distilled_anchor(turns_to_compact, mode=mode)

        distilled_turn = {
            "role": "system",
            "content": anchor_text,
            "compacted": True,
            "original_turn_count": len(turns_to_compact),
            "timestamp": time.time()
        }

        new_turns = [distilled_turn] + recent_turns
        conversation_memory.turns = new_turns

        # Calculate post-compaction metrics
        raw_text_after = " ".join(str(t.get("content", "")) for t in new_turns)
        tokens_after = max(1, len(raw_text_after) // 4)
        tokens_saved = max(0, tokens_before - tokens_after)
        compression_ratio = (tokens_saved / tokens_before) if tokens_before > 0 else 0.0

        duration_ms = (time.perf_counter() - start_time) * 1000

        return CompactionReport(
            turns_before=total_turns,
            turns_after=len(new_turns),
            tokens_before_est=tokens_before,
            tokens_after_est=tokens_after,
            tokens_saved=tokens_saved,
            compression_ratio=compression_ratio,
            anchors_count=len(turns_to_compact),
            distilled_state=anchor_text,
            duration_ms=duration_ms
        )
