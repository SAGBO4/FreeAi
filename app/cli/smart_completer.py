"""OpenCode Dynamic Path & Context Completer for prompt_toolkit.
Provides high-speed intelligent autocompletion for:
- Slash commands ('/cmd') with inline descriptions and noble styling.
- File and directory paths ('@path') with workspace resolution and directory chaining.
- Context anchors ('#tag') for session telemetry and sentinels.
"""

import os
import time
from pathlib import Path
from typing import Iterable, List, Tuple, Optional
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.document import Document


COMMAND_DEFINITIONS: List[Tuple[str, str]] = [
    ("/undo", "Rollback atomique git & fichiers modifiés"),
    ("/compact", "Distillation neuronale de l'historique"),
    ("/lsp", "Sonde en direct pyright / ruff / ast"),
    ("/status", "Télémétrie en temps réel (RAM, CPU, Sentinel)"),
    ("/diff", "Inspection différentielle git OpenCode"),
    ("/rollback", "Réinitialisation git complète HEAD"),
    ("/mode", "Bascule libre / Apex (freeAi vs lesaintAi)"),
    ("/theme", "Bascule de thème TUI OpenCode"),
    ("/search", "Recherche ultra-rapide de fichiers"),
    ("/code", "Recherche syntaxique dans le code"),
    ("/agent", "Mission autonome ReAct"),
    ("/think", "Raisonnement profond arborescent"),
    ("/swarm", "Supervision de l'essaim d'agents"),
    ("/sync", "Synchronisation GZIP Neon Cloud"),
    ("/tui", "Interface plein écran OpenCode Textual"),
    ("/commands", "Palette de navigation rapide (Ctrl+P)"),
    ("/clear", "Nettoie l'écran et réaffiche l'en-tête"),
    ("/help", "Manuel et guide d'utilisation"),
    ("/exit", "Arrêt propre de la session FreeAI"),
]

CONTEXT_TAGS: List[Tuple[str, str]] = [
    ("#git", "Contexte de branche et commits récents"),
    ("#status", "Métriques RAM, CPU et Sentinel"),
    ("#lsp", "Diagnostics et intégrité syntaxique"),
    ("#memory", "Mémoire vectorielle et GZIP active"),
    ("#defense", "État du bouclier autonome SovereignFortress"),
]


class OpenCodePromptCompleter(Completer):
    """Dynamic prompt_toolkit completer matching OpenCode TUI ergonomics."""

    def __init__(self, workspace_root: Optional[str] = None):
        self.workspace_root = Path(workspace_root or os.getcwd()).resolve()
        self._fs_cache: List[Path] = []
        self._last_scan_time = 0.0
        self._cache_ttl = 2.5  # 2.5 seconds cache TTL

    def set_workspace(self, path: str):
        self.workspace_root = Path(path).resolve()
        self._fs_cache.clear()
        self._last_scan_time = 0.0

    def _refresh_fs_cache(self):
        now = time.time()
        if (now - self._last_scan_time) < self._cache_ttl and self._fs_cache:
            return

        cache = []
        skip_dirs = {".git", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", "node_modules", "venv", ".venv"}
        try:
            for root, dirs, files in os.walk(str(self.workspace_root)):
                # Prune skipped directories
                dirs[:] = [d for d in dirs if d not in skip_dirs and not d.startswith(".")]
                root_path = Path(root)
                rel_root = root_path.relative_to(self.workspace_root)

                # Add directories
                for d in dirs:
                    rel_dir = rel_root / d if str(rel_root) != "." else Path(d)
                    cache.append((rel_dir, True))

                # Add files
                for f in files:
                    if not f.startswith("."):
                        rel_file = rel_root / f if str(rel_root) != "." else Path(f)
                        cache.append((rel_file, False))

                if len(cache) > 1200:
                    break
        except Exception:
            pass

        self._fs_cache = cache
        self._last_scan_time = now

    def get_completions(self, document: Document, complete_event) -> Iterable[Completion]:
        text_before_cursor = document.text_before_cursor
        word = document.get_word_before_cursor(WORD=True)

        # 1. Path Completion (@path)
        if "@" in word:
            at_idx = word.rfind("@")
            prefix = word[at_idx + 1:]
            start_pos = -len(prefix)

            self._refresh_fs_cache()

            clean_prefix = prefix.replace("\\", "/")
            matches = []

            for rel_path, is_dir in self._fs_cache:
                posix_str = rel_path.as_posix()
                if posix_str.lower().startswith(clean_prefix.lower()) or clean_prefix.lower() in posix_str.lower():
                    matches.append((posix_str, is_dir))

            # Sort matches: exact prefix matches first, then directory, then alphabetically
            matches.sort(key=lambda m: (not m[0].lower().startswith(clean_prefix.lower()), not m[1], len(m[0])))

            for path_str, is_dir in matches[:25]:
                if is_dir:
                    comp_text = f"{path_str}/"
                    disp_text = f"▪ {path_str}/"
                    meta = "DIR"
                else:
                    comp_text = path_str
                    ext = Path(path_str).suffix.lstrip(".").upper() or "FILE"
                    disp_text = f"• {path_str}"
                    meta = ext

                yield Completion(
                    text=comp_text,
                    start_position=start_pos,
                    display=disp_text,
                    display_meta=f"[{meta}]"
                )
            return

        # 2. Context Tag Completion (#tag)
        if word.startswith("#"):
            tag_prefix = word.lower()
            for tag, desc in CONTEXT_TAGS:
                if tag.startswith(tag_prefix):
                    yield Completion(
                        text=tag,
                        start_position=-len(word),
                        display=f"◈ {tag}",
                        display_meta=desc
                    )
            return

        # 3. Slash Command Completion (/cmd)
        if word.startswith("/") or text_before_cursor.strip().startswith("/"):
            clean_word = word.lower()
            for cmd, desc in COMMAND_DEFINITIONS:
                if cmd.lower().startswith(clean_word):
                    yield Completion(
                        text=cmd,
                        start_position=-len(word),
                        display=f"› {cmd}",
                        display_meta=desc
                    )
            return
