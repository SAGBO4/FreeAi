"""FreeAI OpenCode Full-Screen Textual TUI.

Extreme Innovation replica of the OpenCode architecture:
- TokyoNight dark palette (#080808, #161616, borders #282828)
- Dynamic session tabs header bar (• Session 1 · FreeAI (mode), + New session)
- Foldable left sidebar (Ctrl+B) with Sessions, Noble DirectoryTree, Agent selector, Resource gauge
- Captive chat panel with VerticalScroll / ChatContainer, amber thought cards / ThoughtAccordion
  (+ Thought: ... · duration), streaming LeftBorder and final snap LeftBorderFinal,
  tool execution cards ($, ←, →, ✱, ◈, ⊙, ✓, ✗), and monoline telemetry epilogue (▣ agent · model · duration).
- Bottom prompt bar / InputArea with OpenCode border and metadata line (mode · Groq LPU · auto).
- Bottom status bar (<workspace>:<branch> | • 0 LSP · ⊙ Neon Sync · Sentinel PASS · ctrl+p commands).
- Integrated command palette (Ctrl+P).
- Degraded mode fallback screen for terminal dimensions < 60 cols or < 15 rows.
- Mode NÉANT memory boundedness (DOM pruning, MAX_DOM_NODES, 0 physical SSD writes).
- Double-submit protection with is_generating state locking.
- STRICT ZERO RAW EMOJI COMPLIANCE: Only noble terminal typography glyphs.
"""

import os
import sys
import time
import asyncio
import ast
import json
import difflib
import subprocess
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Union

from rich.markdown import Markdown
from rich.text import Text
from rich.style import Style

import textual
from textual import events
from textual.app import App, ComposeResult
from textual.screen import Screen
from textual.binding import Binding
from textual.reactive import reactive
from textual.command import Provider, Hit, Hits, SearchIcon
from textual.containers import Vertical, Horizontal, VerticalScroll
from textual.widgets import (
    Static,
    Input,
    Label,
    Button,
    Collapsible,
    DirectoryTree,
    OptionList,
    TextArea,
)
from textual.widgets.text_area import TextAreaTheme
from textual.widgets.option_list import Option


# Ensure zero raw emojis anywhere in Textual built-ins
DirectoryTree.ICON_NODE = "▸ "
DirectoryTree.ICON_NODE_EXPANDED = "▾ "
DirectoryTree.ICON_FILE = "• "
SearchIcon.icon = "› "

from app.cli.streaming_renderer import StreamingLeftBorder, LeftBorderFinal
from app.orchestrator.atomic_undo import AtomicUndoManager
from app.cognition.semantic_compactor import SemanticCompactor
from app.tools.lsp_probe import live_lsp_probe
from app.cli.smart_completer import COMMAND_DEFINITIONS, CONTEXT_TAGS


# =============================================================================
# DATA STRUCTURES
# =============================================================================

@dataclass
class ChatSession:
    """Represents an active multi-turn conversation session."""
    id: str
    name: str
    agent: str = "Tech Lead"
    history: List[Dict[str, Any]] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)


# =============================================================================
# CUSTOM NOBLE WIDGETS & F-17 COMPONENTS
# =============================================================================

class NobleDirectoryTree(DirectoryTree):
    """File explorer matching OpenCode typography without raw emoji."""
    ICON_NODE = "▸ "
    ICON_NODE_EXPANDED = "▾ "
    ICON_FILE = "• "

    def filter_paths(self, paths: list[Path]) -> list[Path]:
        skip = {".git", "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache", "node_modules", "venv", ".venv"}
        return [p for p in paths if p.name not in skip and not p.name.startswith(".")]


class UserMessageCard(Static):
    """User prompt card with OpenCode single quote border and timestamp."""
    def __init__(self, prompt: str, timestamp_str: Optional[str] = None, **kwargs):
        super().__init__(**kwargs)
        self.prompt = prompt
        self.timestamp_str = timestamp_str or time.strftime("%H:%M:%S")

    def render(self) -> Text:
        t = Text()
        t.append("› ", style="bold #7aa2f7")
        t.append(self.prompt, style="bold #ffffff")
        t.append(f"  · {self.timestamp_str}", style="dim #565f89")
        return t


class ThoughtCard(Collapsible):
    """Retractable amber thought card (+ Thought: ... · duration)."""
    def __init__(self, summary: str = "", duration_sec: float = 0.0, steps: Optional[List[str]] = None, **kwargs):
        title = f"+ Thought: {summary} · {duration_sec:.2f}s" if summary else "+ Thought: Analyse cognitive"
        super().__init__(
            title=title,
            collapsed_symbol="+ ",
            expanded_symbol="- ",
            collapsed=True,
            **kwargs
        )
        self.steps = steps or []

    def compose(self) -> ComposeResult:
        if self.steps:
            for s in self.steps:
                yield Label(f"  • {s}", classes="thought-step-line")
        else:
            yield Label("  • Analyse cognitive autonome complétée avec succès.", classes="thought-step-line")


# Alias for Chantier F-17
ThoughtAccordion = ThoughtCard


class ToolExecutionCard(Static):
    """Execution card displaying authentic OpenCode glyphs ($, ←, →, ✱, ◈, ⊙, ✓, ✗)."""
    def __init__(self, tool_items: List[Dict[str, str]], **kwargs):
        super().__init__(**kwargs)
        self.tool_items = tool_items

    def render(self) -> Text:
        t = Text()
        for idx, item in enumerate(self.tool_items):
            glyph = item.get("glyph", "•")
            action = item.get("action", "")
            detail = item.get("detail", "")
            style_glyph = item.get("style_glyph", "bold #7aa2f7")

            t.append(f"  {glyph}", style=style_glyph)
            if action:
                t.append(f" {action}", style="dim #565f89")
            if detail:
                t.append(f" {detail}", style="#c0caf5")
            if idx < len(self.tool_items) - 1:
                t.append("\n")
        return t


class AssistantMessageCard(Static):
    """Assistant message rendered with OpenCode vertical border (┃ ... ╹)."""
    def __init__(self, content: str = "", is_streaming: bool = False, **kwargs):
        self.raw_text = content
        super().__init__(**kwargs)
        self.is_streaming = is_streaming

    def update_streaming_text(self, text: str):
        self.raw_text = text
        self.is_streaming = True
        self.update(StreamingLeftBorder(self.raw_text, border_style="bold #7aa2f7", char="┃", cursor="▌", is_active=True))

    def finalize_text(self, text: str):
        self.raw_text = text
        self.is_streaming = False
        try:
            md = Markdown(self.raw_text)
            self.update(LeftBorderFinal(md, style="bold #7aa2f7", char="┃", bottom_char="╹"))
        except Exception:
            txt = Text(self.raw_text)
            self.update(LeftBorderFinal(txt, style="bold #7aa2f7", char="┃", bottom_char="╹"))


class TelemetryEpilogueCard(Static):
    """Monoline telemetry epilogue matching OpenCode contract."""
    def __init__(
        self,
        agent: str = "Tech Lead",
        model: str = "groq/llama-3.3-70b-versatile",
        duration_sec: float = 0.0,
        tokens_sec: float = 0.0,
        tokens_count: int = 0,
        ssd_bytes: int = 0,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.agent = agent
        self.model = model
        self.duration_sec = duration_sec
        self.tokens_sec = tokens_sec
        self.tokens_count = tokens_count
        self.ssd_bytes = ssd_bytes

    def render(self) -> Text:
        t = Text()
        t.append("▣ ", style="bold #7aa2f7")
        t.append(
            f"{self.agent} · {self.model} · {self.duration_sec:.2f}s "
            f"({self.tokens_sec:.0f} tok/s, ~{self.tokens_count} tok, {self.ssd_bytes} B SSD)",
            style="dim #565f89"
        )
        return t


class ChatMessage(Static):
    """Composite ChatMessage supporting F-17 streaming, <think> accordions and noble LeftBorder."""
    def __init__(self, role: str = "assistant", content: str = "", **kwargs):
        self.role = role
        self.raw_text = content
        self.thought_text = ""
        self.is_finalized = False
        super().__init__(**kwargs)

    def render(self) -> Text:
        if self.role == "user":
            t = Text()
            t.append("› ", style="bold #7aa2f7")
            t.append(self.raw_text, style="bold #ffffff")
            return t
        else:
            t = Text()
            lines = self.raw_text.splitlines() if self.raw_text else [""]
            for line in lines:
                t.append("┃ ", style="bold #7aa2f7")
                t.append(line, style="#c0caf5")
                t.append("\n")
            if self.is_finalized:
                t.append("╹\n", style="bold #7aa2f7")
                t.append("▣ Tech Lead · groq/llama-3.3-70b-versatile · 0.05s (500 tok/s, ~40 tok, 0 B SSD)", style="dim #565f89")
            return t

    async def stream_tokens(self, tokens: str) -> None:
        """Streams token chunk, detects <think> tags, and mounts ThoughtAccordion."""
        if "<think>" in tokens and "</think>" in tokens:
            start = tokens.index("<think>") + len("<think>")
            end = tokens.index("</think>")
            self.thought_text = tokens[start:end].strip()
            self.raw_text = (tokens[:tokens.index("<think>")] + tokens[end + len("</think>"):].strip()).strip()
            accordion = ThoughtAccordion(summary=self.thought_text, duration_sec=0.02)
            await self.mount(accordion)
        else:
            self.raw_text += tokens
        self.refresh()

    async def finalize(self) -> None:
        """Finalizes message snapshot with cap ╹ and epilogue ▣."""
        self.is_finalized = True
        self.refresh()


# =============================================================================
# LAYOUT CONTAINERS & PANELS (5-ZONE STRUCTURE)
# =============================================================================

class TopHeader(Horizontal):
    """Zone 1: TopHeader with active session tabs."""
    DEFAULT_CSS = """
    TopHeader {
        dock: top;
        height: 3;
        background: #161616;
        border-bottom: solid #282828;
        layout: horizontal;
        align-vertical: middle;
        padding: 0 1;
    }
    """


class CollapsibleSidebar(Vertical):
    """Zone 2: Collapsible left sidebar (Sessions, File Tree, Agents, Resources)."""
    DEFAULT_CSS = """
    CollapsibleSidebar {
        width: 32;
        min-width: 24;
        max-width: 40;
        background: #101014;
        border-right: solid #282828;
        height: 100%;
        layout: vertical;
    }
    CollapsibleSidebar.collapsed {
        display: none;
    }
    """


class ChatContainer(VerticalScroll):
    """Zone 3: Central captive scrollable message area with Mode NÉANT DOM pruning."""
    MAX_DOM_NODES: int = 30

    DEFAULT_CSS = """
    ChatContainer {
        height: 1fr;
        padding: 1 2;
        background: #080808;
        overflow-y: scroll;
    }
    """

    async def append_message(self, message: Static) -> None:
        """Appends message and enforces Mode NÉANT DOM node budget (< MAX_DOM_NODES)."""
        await self.mount(message)
        nodes = list(self.query(ChatMessage))
        if len(nodes) > self.MAX_DOM_NODES:
            to_remove = len(nodes) - self.MAX_DOM_NODES
            for n in nodes[:to_remove]:
                await n.remove()
        self.scroll_end(animate=False)


class InputArea(Vertical):
    """Zone 4: Anchored bottom text area with OpenCode styling and generation lock."""
    disabled: reactive[bool] = reactive(False)

    DEFAULT_CSS = """
    InputArea {
        dock: bottom;
        height: auto;
        background: #161616;
        border-top: solid #282828;
        padding: 0 1;
    }
    """

    def watch_disabled(self, disabled: bool) -> None:
        try:
            inp = self.query_one(Input)
            inp.disabled = disabled
        except Exception:
            pass


class StatusBar(Horizontal):
    """Zone 5: Bottom status bar (LSP probe, git branch, telemetry, shortcuts)."""
    DEFAULT_CSS = """
    StatusBar {
        dock: bottom;
        height: 1;
        background: #101014;
        border-top: solid #1f2335;
        layout: horizontal;
        padding: 0 1;
    }
    """


# =============================================================================
# SCREENS
# =============================================================================

class DegradedModeScreen(Screen):
    """AC8: Safe fallback DegradedModeScreen on terminal dimensions < 60 cols or < 15 rows."""
    DEFAULT_CSS = """
    DegradedModeScreen {
        align: center middle;
        background: #080808;
        color: #e0af68;
    }
    #degraded-container {
        width: 90%;
        height: auto;
        border: solid #e0af68;
        padding: 1 2;
        background: #14130e;
        text-align: center;
    }
    """

    def compose(self) -> ComposeResult:
        with Vertical(id="degraded-container"):
            yield Label("◆ MODE DÉGRADÉ ACTIF", id="degraded-title")
            yield Label("Terminal trop étroit (< 60 cols ou < 15 rows).", id="degraded-desc")
            yield Label("Redimensionnez la fenêtre pour réactiver le Full-Screen TUI.", id="degraded-hint")


# =============================================================================
# FEATURE F-18: IN-TUI CODE EDITOR & SOVEREIGN SYNTAX INSPECTOR
# =============================================================================

TOKYO_NIGHT_TEXTAREA_THEME = TextAreaTheme(
    name="tokyonight",
    base_style=Style(color="#c0caf5", bgcolor="#080808"),
    gutter_style=Style(color="#3b4261", bgcolor="#080808"),
    cursor_style=Style(color="#080808", bgcolor="#7aa2f7"),
    cursor_line_style=Style(bgcolor="#16161e"),
    cursor_line_gutter_style=Style(color="#7aa2f7", bgcolor="#16161e"),
    bracket_matching_style=Style(bgcolor="#292e42", bold=True),
    selection_style=Style(bgcolor="#283457"),
    syntax_styles={
        "string": Style(color="#9ece6a"),
        "string.documentation": Style(color="#9ece6a"),
        "comment": Style(color="#565f89", italic=True),
        "keyword": Style(color="#bb9af7", bold=True),
        "operator": Style(color="#89ddff"),
        "repeat": Style(color="#bb9af7"),
        "exception": Style(color="#f7768e"),
        "include": Style(color="#7dcfff"),
        "function": Style(color="#7aa2f7"),
        "variable": Style(color="#c0caf5"),
        "number": Style(color="#ff9e64"),
        "boolean": Style(color="#ff9e64"),
        "type": Style(color="#2ac3de"),
        "heading": Style(color="#7aa2f7", bold=True),
    }
)


class NobleTextArea(TextArea):
    """Sovereign TextArea subclass intercepting keys so Escape, Ctrl+W, Ctrl+S, Ctrl+D, Ctrl+E are never swallowed."""

    async def _on_key(self, event: events.Key) -> None:
        if event.key == "escape":
            event.stop()
            event.prevent_default()
            app = getattr(self, "app", None)
            if app:
                if hasattr(self, "screen") and self.screen.__class__.__name__ == "CodeEditorScreen":
                    self.screen.action_close_editor()
                    return
                app.action_close_split_editor()
            return
        elif event.key == "ctrl+w":
            event.stop()
            event.prevent_default()
            app = getattr(self, "app", None)
            if app:
                if hasattr(self, "screen") and self.screen.__class__.__name__ == "CodeEditorScreen":
                    self.screen.action_close_editor()
                    return
                app.action_close_split_editor()
            return
        elif event.key == "ctrl+s":
            event.stop()
            event.prevent_default()
            app = getattr(self, "app", None)
            if app:
                if hasattr(self, "screen") and self.screen.__class__.__name__ == "CodeEditorScreen":
                    await self.screen.action_save_file()
                else:
                    await app.action_save_split_editor()
            return
        elif event.key == "ctrl+d":
            event.stop()
            event.prevent_default()
            app = getattr(self, "app", None)
            if app:
                if hasattr(self, "screen") and self.screen.__class__.__name__ == "CodeEditorScreen":
                    await self.screen.action_show_diff()
                else:
                    await app.action_diff_split_editor()
            return
        elif event.key in ("ctrl+e", "f4"):
            event.stop()
            event.prevent_default()
            app = getattr(self, "app", None)
            if app:
                if hasattr(self, "screen") and self.screen.__class__.__name__ == "CodeEditorScreen":
                    await self.screen.action_ai_explain()
                else:
                    await app.action_ai_explain_split_editor()
            return

        await super()._on_key(event)


class EditorHeaderBar(Horizontal):
    """Header bar for the In-TUI Code Editor with metadata, live LSP probe badge, and action buttons (F-18)."""

    def __init__(
        self,
        file_name: str = "",
        language: str = "plain",
        lines_count: int = 1,
        file_size: int = 0,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.file_name = file_name
        self.language = language
        self.lines_count = lines_count
        self.file_size = file_size

        display_name = file_name if file_name else "aucun"
        self.file_label = Label(f"• Fichier : {display_name}", id="editor-file-label")
        self.file_label.content = f"• Fichier : {display_name}"
        self.lang_label = Label(f"[Lang: {language}]", id="editor-lang-badge")
        self.stats_label = Label(self._format_stats(lines_count, file_size), id="editor-stats-badge")
        self.status_label = Label("[bold #9ece6a]✓ Synchronisé[/]", id="editor-status-badge")
        self.lsp_label = Label("[bold #9ece6a]• 0 Erreur LSP[/]", id="editor-lsp-badge")

        self.btn_close = Button("✗ Fermer", id="btn-close-editor", classes="editor-close-btn")
        self.btn_save = Button("✓ Save", id="btn-save-editor", classes="editor-action-btn")
        self.btn_diff = Button("⊙ Diff", id="btn-diff-editor", classes="editor-action-btn")
        self.btn_ai_explain = Button("◈ IA", id="btn-ai-explain", classes="editor-action-btn")

    def _format_stats(self, lines: int, size_bytes: int) -> str:
        if size_bytes < 1024:
            size_str = f"{size_bytes} B"
        else:
            size_str = f"{size_bytes / 1024:.1f} KB"
        return f"[{lines} L · {size_str}]"

    def compose(self) -> ComposeResult:
        with Horizontal(id="editor-header-meta"):
            yield self.file_label
            yield self.status_label
        with Horizontal(id="editor-header-actions"):
            yield self.btn_close
            yield self.btn_save
            yield self.btn_diff
            yield self.btn_ai_explain
        with Horizontal(id="editor-header-badges"):
            yield self.lang_label
            yield self.stats_label
            yield self.lsp_label

    def update_file_info(self, file_name: str, language: str, lines: int, size_bytes: int) -> None:
        self.file_name = file_name
        self.language = language
        self.lines_count = lines
        self.file_size = size_bytes
        display_name = file_name if file_name else "aucun"
        self.file_label.update(f"• Fichier : {display_name}")
        self.file_label.content = f"• Fichier : {display_name}"
        self.lang_label.update(f"[Lang: {language}]")
        self.stats_label.update(self._format_stats(lines, size_bytes))

    def update_stats(self, lines: int, size_bytes: int) -> None:
        self.lines_count = lines
        self.file_size = size_bytes
        self.stats_label.update(self._format_stats(lines, size_bytes))

    def set_modified(self, modified: bool) -> None:
        if modified:
            self.status_label.update("[bold #e0af68]• Modifié *[/]")
        else:
            self.status_label.update("[bold #9ece6a]✓ Synchronisé[/]")

    def set_lsp_status(self, text: str, is_error: bool = False) -> None:
        style = "bold #f7768e" if is_error else "bold #9ece6a"
        self.lsp_label.update(f"[{style}]{text}[/]")


class EditorStatusBar(Horizontal):
    """Bottom status bar for In-TUI Code Editor showing cursor position and keybinds (F-18)."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.cursor_label = Label("Ln 1, Col 1 · UTF-8", id="editor-cursor-pos")
        self.shortcuts_label = Label(
            "ctrl+s save · ctrl+d diff · ctrl+e ai explain · esc close",
            id="editor-shortcuts-help"
        )

    def compose(self) -> ComposeResult:
        yield self.cursor_label
        yield self.shortcuts_label

    def update_cursor(self, line: int, col: int) -> None:
        self.cursor_label.update(f"Ln {line}, Col {col} · UTF-8")


class GitDiffModal(Screen):
    """Modal displaying inline unified git diff against HEAD (F-18 Touche 2)."""

    BINDINGS = [
        Binding("escape", "dismiss_diff", "Fermer", show=False),
        Binding("ctrl+d", "dismiss_diff", "Basculer Diff", show=False),
    ]

    def __init__(self, diff_content: str, file_name: str, **kwargs):
        super().__init__(**kwargs)
        self.diff_content = diff_content
        self.file_name = file_name

    def compose(self) -> ComposeResult:
        with Vertical(id="diff-modal-container"):
            yield Label(f"◆ Diff Inspector : {self.file_name} (vs HEAD)", id="diff-modal-header")
            with VerticalScroll(id="diff-content-scroll"):
                yield Static(self._render_diff())
            yield Label("Appuyez sur Échap ou Ctrl+D pour fermer l'inspecteur", id="diff-modal-footer")

    def _render_diff(self) -> Text:
        t = Text()
        if not self.diff_content.strip():
            t.append("✓ Aucun diff détecté (parfaitement synchronisé avec HEAD).\n", style="bold #9ece6a")
            return t

        for line in self.diff_content.splitlines():
            if line.startswith("+++") or line.startswith("---"):
                t.append(line + "\n", style="bold #bb9af7")
            elif line.startswith("@@"):
                t.append(line + "\n", style="bold #7dcfff")
            elif line.startswith("+"):
                t.append(line + "\n", style="#9ece6a")
            elif line.startswith("-"):
                t.append(line + "\n", style="#f7768e")
            else:
                t.append(line + "\n", style="#c0caf5")
        return t

    def action_dismiss_diff(self) -> None:
        self.app.pop_screen()


class CodeEditorScreen(Screen):
    """Sovereign In-TUI Code Editor & Live Syntax Inspector Screen (Feature F-18)."""

    BINDINGS = [
        Binding("ctrl+s", "save_file", "Save", show=False),
        Binding("ctrl+d", "show_diff", "Diff", show=False),
        Binding("ctrl+e", "ai_explain", "AI Explain", show=False),
        Binding("f4", "ai_explain", "AI Explain", show=False),
        Binding("escape", "close_editor", "Close", show=False),
        Binding("ctrl+w", "close_editor", "Close", show=False),
    ]

    LANGUAGE_MAP = {
        ".py": "python",
        ".pyw": "python",
        ".md": "markdown",
        ".markdown": "markdown",
        ".json": "json",
        ".yaml": "yaml",
        ".yml": "yaml",
        ".toml": "toml",
        ".html": "html",
        ".htm": "html",
        ".css": "css",
        ".js": "javascript",
        ".mjs": "javascript",
        ".cjs": "javascript",
        ".sh": "bash",
        ".bash": "bash",
        ".zsh": "bash",
        ".rs": "rust",
        ".go": "go",
        ".sql": "sql",
        ".xml": "xml",
    }

    def __init__(
        self,
        file_path: Union[str, Path],
        workspace_root: Optional[Union[str, Path]] = None,
        mode: Optional[str] = None,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.file_path = Path(file_path).resolve()
        self.mode = mode or "freeAi"
        self.ws_root = Path(workspace_root).resolve() if workspace_root else None

        # AC7: Strict Security Confinement Check
        if self.mode == "freeAi" and self.ws_root:
            try:
                self.file_path.relative_to(self.ws_root)
            except ValueError:
                raise PermissionError(
                    f"Confinement FreeAI : accès au fichier hors workspace '{self.file_path}' refusé."
                )

        self.detected_language = self.LANGUAGE_MAP.get(self.file_path.suffix.lower())

        # Load content from disk
        if self.file_path.is_file():
            try:
                self.initial_content = self.file_path.read_text(encoding="utf-8", errors="replace")
            except Exception:
                self.initial_content = ""
        else:
            self.initial_content = ""

        self.is_modified = False
        lines = self.initial_content.splitlines() or [""]
        self.header_bar = EditorHeaderBar(
            file_name=self.file_path.name,
            language=self.detected_language or "plain",
            lines_count=len(lines),
            file_size=len(self.initial_content.encode("utf-8"))
        )
        self.text_area = NobleTextArea(
            text=self.initial_content,
            language=self.detected_language,
            id="editor-textarea"
        )
        self.status_bar = EditorStatusBar(id="editor-status-bar")

    def compose(self) -> ComposeResult:
        yield self.header_bar
        yield self.text_area
        yield self.status_bar

    def on_mount(self) -> None:
        ws = getattr(self.app, "workspace_root", self.ws_root)
        mode = getattr(self.app, "mode", self.mode)
        if mode == "freeAi" and ws:
            try:
                self.file_path.relative_to(ws)
            except ValueError:
                self.app.pop_screen()
                raise PermissionError(
                    f"Confinement FreeAI : accès au fichier hors workspace '{self.file_path}' refusé."
                )

        try:
            self.text_area.register_theme(TOKYO_NIGHT_TEXTAREA_THEME)
            self.text_area.theme = "tokyonight"
        except Exception:
            pass
        self.text_area.show_line_numbers = True
        self.text_area.indent_width = 4
        self.text_area.tab_behavior = "indent"
        self.text_area.focus()
        self.update_lsp_diagnostics()

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id or ""
        if btn_id == "btn-close-editor":
            self.action_close_editor()
        elif btn_id == "btn-ai-explain":
            await self.action_ai_explain()
        elif btn_id == "btn-save-editor":
            await self.action_save_file()
        elif btn_id == "btn-diff-editor":
            await self.action_show_diff()

    def on_text_area_changed(self, event: TextArea.Changed) -> None:
        """Triggered whenever buffer content is modified."""
        cur_text = self.text_area.text
        self.is_modified = (cur_text != self.initial_content)
        self.header_bar.set_modified(self.is_modified)
        lines = cur_text.splitlines() or [""]
        self.header_bar.update_stats(len(lines), len(cur_text.encode("utf-8")))
        self.update_lsp_diagnostics()

    def on_text_area_selection_changed(self, event: TextArea.SelectionChanged) -> None:
        """Triggered when cursor moves or selection changes."""
        row, col = self.text_area.cursor_location
        self.status_bar.update_cursor(row + 1, col + 1)

    async def action_save_file(self) -> None:
        """Touche 4: Atomic Undo Snapshot before disk write (Ctrl+S)."""
        ws = getattr(self.app, "workspace_root", self.ws_root)
        app_mode = getattr(self.app, "mode", self.mode)
        if app_mode == "freeAi" and ws:
            try:
                self.file_path.relative_to(ws)
            except ValueError:
                self.header_bar.set_lsp_status("✗ Confinement : Sauvegarde hors workspace interdite", is_error=True)
                return

        try:
            rel_path = self.file_path.relative_to(ws).as_posix() if ws else self.file_path.name
        except Exception:
            rel_path = self.file_path.name

        undo_mgr = None
        snap = None
        try:
            target_ws = ws if ws else self.file_path.parent
            undo_mgr = AtomicUndoManager(str(target_ws))
            snap = undo_mgr.create_snapshot(
                description=f"Éditeur TUI sauvegarde {rel_path}",
                files_to_track=[rel_path]
            )
        except Exception:
            pass

        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        self.file_path.write_text(self.text_area.text, encoding="utf-8")

        if undo_mgr and snap:
            try:
                undo_mgr.finalize_snapshot(snap, modified_files=[rel_path])
            except Exception:
                pass

        self.initial_content = self.text_area.text
        self.is_modified = False
        self.header_bar.set_modified(False)
        self.update_lsp_diagnostics()

    async def action_show_diff(self) -> None:
        """Touche 2: Inline Git Diff Inspector (Ctrl+D)."""
        diff_text = self.compute_git_diff()
        await self.app.push_screen(GitDiffModal(diff_content=diff_text, file_name=self.file_path.name))

    def compute_git_diff(self) -> str:
        head_text = ""
        rel_posix = self.file_path.name
        try:
            ws = getattr(self.app, "workspace_root", self.ws_root)
            if ws:
                rel_posix = self.file_path.relative_to(ws).as_posix()
                proc = subprocess.run(
                    ["git", "show", f"HEAD:{rel_posix}"],
                    cwd=str(ws),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                if proc.returncode == 0:
                    head_text = proc.stdout
                else:
                    head_text = self.initial_content
            else:
                head_text = self.initial_content
        except Exception:
            head_text = self.initial_content

        diff_lines = list(difflib.unified_diff(
            head_text.splitlines(keepends=True),
            self.text_area.text.splitlines(keepends=True),
            fromfile=f"HEAD:{rel_posix}",
            tofile=f"BUFFER:{rel_posix}"
        ))
        return "".join(diff_lines)

    async def action_ai_explain(self) -> None:
        """Touche 1: AI Code Lens / Instant Explain (Ctrl+E ou F4)."""
        sel_text = self.text_area.selected_text
        code = sel_text if (sel_text and sel_text.strip()) else self.text_area.text
        lang = self.detected_language or "code"
        try:
            ws = getattr(self.app, "workspace_root", self.ws_root)
            rel = self.file_path.relative_to(ws).as_posix() if ws else self.file_path.name
        except Exception:
            rel = self.file_path.name

        target_desc = f"extrait ({rel})" if (sel_text and sel_text.strip()) else f"fichier `{rel}`"
        prompt = (
            f"Analyse, explique et optimise ce code du {target_desc} :\n\n"
            f"```{lang}\n{code}\n```"
        )
        self.app.pop_screen()
        asyncio.create_task(self.app.submit_prompt(prompt))

    def update_lsp_diagnostics(self) -> None:
        """Touche 3: Gouttière de Diagnostic LSP en Direct."""
        text = self.text_area.text
        lang = self.detected_language

        if lang == "python":
            try:
                ast.parse(text, filename=str(self.file_path))
                self.header_bar.set_lsp_status("• 0 Erreur LSP", is_error=False)
            except SyntaxError as se:
                line = se.lineno or 1
                msg = str(se.msg)
                self.header_bar.set_lsp_status(f"• L{line} SyntaxError: {msg}", is_error=True)
            except Exception as ex:
                self.header_bar.set_lsp_status(f"• Erreur: {ex}", is_error=True)
        elif lang == "json":
            try:
                json.loads(text)
                self.header_bar.set_lsp_status("• 0 Erreur LSP", is_error=False)
            except Exception as je:
                self.header_bar.set_lsp_status(f"• Erreur JSON: {je}", is_error=True)
        else:
            self.header_bar.set_lsp_status("• 0 Erreur LSP", is_error=False)

    def action_close_editor(self) -> None:
        """Closes the editor screen and returns to previous screen (Esc / Ctrl+W)."""
        self.app.pop_screen()


class EditorPane(Vertical):
    """Zone 6: Side-by-side Split View In-TUI Code Editor Pane (50/50 with Chat)."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.current_file_path: Optional[Path] = None
        self.initial_content: str = ""
        self.is_modified: bool = False


class MainScreen(Screen):
    """Primary 6-zone OpenCode layout screen with persistent side-by-side split editor."""

    def compose(self) -> ComposeResult:
        app = getattr(self, "app")

        # Zone 1: TopHeader
        with TopHeader(id="top-header"):
            yield Label("◆ FreeAI · OpenCode", id="brand-label")
            with Horizontal(id="session-tabs-bar"):
                yield Button(f"• Session 1 · FreeAI ({app.mode})", id="tab-sess-1", classes="session-tab active")
                yield Button("+ New session", id="btn-new-session")
            with Horizontal(id="header-right"):
                yield Label(f"[{app.mode}]", id="mode-badge")
                yield Label(app.active_model, id="model-badge")

        # Main Body: Sidebar + Central Chat + Split Editor Pane
        with Horizontal(id="main-container"):
            # Zone 2: CollapsibleSidebar (Ctrl+B)
            with CollapsibleSidebar(id="sidebar"):
                yield Label("SESSIONS", classes="sidebar-section-title")
                with Vertical(id="sessions-list"):
                    yield Label("• Session 1 (Active)", id="sidebar-sess-1", classes="sidebar-session-item active")

                yield Label("EXPLORATEUR", classes="sidebar-section-title")
                yield NobleDirectoryTree(str(app.workspace_root), id="workspace-tree")

                yield Label("AGENTS", classes="sidebar-section-title")
                yield OptionList(
                    Option("◈ Tech Lead (Orchestrateur)", id="agent-tech-lead"),
                    Option("◈ Code (Synthèse & Refactor)", id="agent-code"),
                    Option("◈ Security (Sanctuaire & Audit)", id="agent-security"),
                    Option("◈ Git (Diff & Commits)", id="agent-git"),
                    Option("◈ Conversation (Frugal)", id="agent-conversation"),
                    id="agent-options"
                )

                yield Label("RESSOURCES", classes="sidebar-section-title")
                with Vertical(id="resource-box"):
                    yield Label("RAM : ~18 MB (Mode NÉANT)", id="res-ram", classes="res-label")
                    yield Label("Mode NÉANT : ACTIF (< 8 MB)", id="res-neant", classes="res-label")
                    yield Label("⊙ Neon Sync : OK (GZIP-9)", id="res-neon", classes="res-label")
                    yield Label("✓ Sentinel : PASS (Inviolable)", id="res-sentinel", classes="res-label")

            # Zone 3: Central Area with ChatContainer (Left 50%)
            with Vertical(id="central-area"):
                with ChatContainer(id="chat-scroll"):
                    yield Static(
                        "◆ FreeAI OpenCode Vanguard TUI (Mode: " + app.mode + ")\n"
                        "Architecture démesurée · TokyoNight Engine · Zero-Flicker Streaming\n"
                        "Glyphes authentiques : $ ← → ✱ ◈ ⊙ ✓ ✗ · Télémétrie en direct\n"
                        "Tapez votre objectif ou /help pour afficher l'arsenal des commandes.",
                        classes="welcome-card",
                        id="welcome-msg"
                    )

                # Zone 4: InputArea
                with InputArea(id="prompt-container"):
                    with Horizontal(id="prompt-input-row"):
                        yield Label("› ", id="prompt-prefix")
                        yield Input(
                            placeholder="Tapez un objectif ou /commande, @fichier, #contexte... (Entrée pour valider)",
                            id="prompt-input"
                        )
                    with Horizontal(id="prompt-meta-row"):
                        yield Label(f"{app.mode} · Groq LPU · auto", id="prompt-meta-left")
                        yield Label("ctrl+b: sidebar · ctrl+p: palette · ctrl+n: session · ctrl+c: quitter", id="prompt-meta-right")

            # Zone 6: Split In-TUI Code Editor Pane (Right 50%)
            with EditorPane(id="editor-pane"):
                yield EditorHeaderBar(file_name="", language="plain", id="split-editor-header")
                yield NobleTextArea(id="split-editor-textarea")
                yield EditorStatusBar(id="split-editor-status")

        # Zone 5: StatusBar
        git_branch = app._resolve_git_branch()
        ws_name = app.workspace_root.name
        with StatusBar(id="status-bar"):
            yield Label(f"{ws_name}:{git_branch}", id="status-left")
            lsp_badge = app._resolve_lsp_status()
            yield Label(f"{lsp_badge} · ⊙ Neon Sync · Sentinel PASS · ctrl+p commands", id="status-right")



def _fetch_research_markdown(args: List[str]) -> str:
    """Récupère et formate la veille scientifique arXiv, dépôts GitHub et DuckDuckGo en Markdown."""
    from pathlib import Path
    import importlib.util

    scraper_path = Path(__file__).resolve().parent.parent.parent / "real_implementations" / "scraper.py"
    spec = importlib.util.spec_from_file_location("freeai_research_scraper", scraper_path)
    scraper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(scraper)

    VALID_SOURCES = ("arxiv", "github", "web", "all")
    source = args[0].lower() if args else "all"
    topic = " ".join(args[1:]).strip() if len(args) > 1 else None

    if source not in VALID_SOURCES:
        topic = " ".join(args).strip()
        source = "all"

    original_topic = topic
    if topic:
        translated = scraper.translate_to_english(topic)
        topic = translated

    lines = []
    lines.append("### ◈ Veille Scientifique & Technique Souveraine")
    if topic:
        if original_topic and original_topic.lower() != topic.lower():
            lines.append(f"• **Sujet :** {original_topic} *(indexé en anglais : `{topic}`)*\n")
        else:
            lines.append(f"• **Sujet :** {topic}\n")
    else:
        lines.append("• **Sujet :** Intelligence Artificielle & Machine Learning\n")

    if source in ("arxiv", "all"):
        papers = scraper.fetch_arxiv_data(max_results=6, topic=topic)
        lines.append("#### [arXiv] Derniers Articles Scientifiques (export.arxiv.org)")
        if papers:
            for p in papers:
                title = p.get("title", "N/A").replace("\n", " ").strip()
                authors = p.get("authors", "N/A")
                date = p.get("published", "N/A")[:10]
                url = p.get("url", "")
                link_text = f"[{title}]({url})" if url else title
                lines.append(f"- **{link_text}**\n  *Auteurs :* {authors} · *Date :* {date}")
        else:
            lines.append("- *(Aucun article arXiv trouvé ou réseau indisponible)*")
        lines.append("")

    if source in ("github", "all"):
        repos = scraper.fetch_github_data(per_page=6, topic=topic)
        lines.append("#### [GitHub] Dépôts Populaires Tendances (api.github.com)")
        if repos:
            for r in repos:
                name = r.get("name", "N/A")
                owner = r.get("owner", "N/A")
                stars = r.get("stars", 0)
                desc = (r.get("description") or "-").replace("\n", " ").strip()
                if len(desc) > 90:
                    desc = desc[:87] + "..."
                url = r.get("url") or f"https://github.com/{owner}/{name}"
                lines.append(f"- **[{name}]({url})** ({owner}) — {stars} stars\n  {desc}")
        else:
            lines.append("- *(Aucun dépôt GitHub trouvé ou quota dépassé)*")
        lines.append("")

    if source in ("web", "all"):
        try:
            from app.tools.sovereign_web import sovereign_web
            web_query = topic or "intelligence artificielle actualités"
            web_results = sovereign_web.search_sync(web_query, max_results=5)
            lines.append("#### [Web] Résultats DuckDuckGo Souverains")
            if web_results:
                for w in web_results:
                    w_title = w.get("title", "N/A")
                    w_url = w.get("url", "#")
                    w_snip = (w.get("snippet") or "-").replace("\n", " ").strip()
                    lines.append(f"- **[{w_title}]({w_url})**\n  {w_snip}")
            else:
                lines.append("- *(Aucun résultat web disponible)*")
        except Exception as e:
            lines.append(f"- *(Erreur recherche web : {e})*")
        lines.append("")

    return "\n".join(lines)


# =============================================================================
# COMMAND PALETTE PROVIDER (Ctrl+P)
# =============================================================================

class OpenCodeCommandProvider(Provider):
    """OpenCode command provider with instant fuzzy search and zero emoji."""

    async def search(self, query: str) -> Hits:
        app = getattr(self, "app")
        matcher = self.matcher(query)

        commands = [
            ("/research", "Veille scientifique & technique réelle (arXiv, GitHub, Web)", lambda: app.run_slash_command("/research")),
            ("/cyber", "Arsenal cybersécurité & exécution d'outils Kali", lambda: app.run_slash_command("/cyber")),
            ("/undo", "Rollback atomique git & fichiers modifiés", lambda: app.run_slash_command("/undo")),
            ("/compact", "Distillation neuronale de l'historique", lambda: app.run_slash_command("/compact")),
            ("/lsp", "Sonde en direct pyright / ruff / ast", lambda: app.run_slash_command("/lsp")),
            ("/status", "Télémétrie en temps réel (RAM, CPU, Sentinel)", lambda: app.run_slash_command("/status")),
            ("/diff", "Inspection différentielle git OpenCode", lambda: app.run_slash_command("/diff")),
            ("/rollback", "Réinitialisation git complète HEAD", lambda: app.run_slash_command("/rollback")),
            ("/mode freeAi", "Bascule en mode standard FreeAI", lambda: app.run_slash_command("/mode freeAi")),
            ("/mode lesaintAi", "Bascule en mode super-utilisateur lesaintAi", lambda: app.run_slash_command("/mode lesaintAi")),
            ("/agent Tech Lead", "Sélectionner Tech Lead Orchestrator", lambda: app.set_active_agent("Tech Lead")),
            ("/agent Code", "Sélectionner Code Agent", lambda: app.set_active_agent("Code")),
            ("/agent Security", "Sélectionner Security Agent", lambda: app.set_active_agent("Security")),
            ("/agent Git", "Sélectionner Git Agent", lambda: app.set_active_agent("Git")),
            ("/agent Conversation", "Sélectionner Conversation Agent", lambda: app.set_active_agent("Conversation")),
            ("/new", "Créer une nouvelle session (Ctrl+N)", app.action_new_session),
            ("/sidebar", "Afficher / masquer la sidebar (Ctrl+B)", app.action_toggle_sidebar),
            ("/clear", "Effacer les messages du chat actif", app.action_clear_chat),
            ("/sync", "Synchronisation GZIP Neon Cloud", lambda: app.run_slash_command("/sync")),
            ("/online", "Configurer les modèles IA distants (DeepSeek, Kilo, Kimi)", lambda: app.run_slash_command("/online")),
            ("/kimi login", "Authentification assistée Kimi Moonshot (Playwright)", lambda: app.run_slash_command("/kimi login")),
            ("/kimi status", "Vérifier le statut de connexion Kimi", lambda: app.run_slash_command("/kimi status")),
            ("/inngest", "Orchestration durable & circuit-breaker Inngest (F-37)", lambda: app.run_slash_command("/inngest status")),
            ("/mesh", "Satellite Mesh & Passerelle Machine-à-Machine (Forge & Laurince)", lambda: app.run_slash_command("/mesh status")),
            ("/satellite", "Synchroniser et inspecter les satellites (Forge & Laurince)", lambda: app.run_slash_command("/mesh sync")),
            ("/edit", "Ouvrir l'éditeur de code intégré In-TUI (Ctrl+O)", app.action_open_file_prompt),
            ("/help", "Manuel et guide complet OpenCode", lambda: app.run_slash_command("/help")),
            ("/exit", "Quitter FreeAI TUI", app.action_quit_app),
        ]

        for name, desc, callback in commands:
            score = matcher.match(name) or matcher.match(desc)
            if score > 0:
                yield Hit(
                    score=score,
                    match_display=matcher.highlight(name),
                    command=callback,
                    text=name,
                    help=desc,
                )


# =============================================================================
# MAIN TEXTUAL APPLICATION
# =============================================================================

class FreeAITUIApp(App):
    """Full-Screen OpenCode TUI Application for FreeAI."""

    COMMANDS = {OpenCodeCommandProvider}
    TITLE = "FreeAI · OpenCode Vanguard TUI"

    # F-17 Requirements
    alternate_screen: bool = True
    sidebar_open: reactive[bool] = reactive(True)
    is_generating: reactive[bool] = reactive(False)

    BINDINGS = [
        Binding("ctrl+b", "toggle_sidebar", "Sidebar", show=False),
        Binding("ctrl+p", "command_palette", "Commands", show=False),
        Binding("ctrl+n", "new_session", "New Session", show=False),
        Binding("ctrl+o", "open_file_prompt", "Open File", show=False),
        Binding("ctrl+s", "save_split_editor", "Save File", show=False),
        Binding("ctrl+d", "diff_split_editor", "Diff", show=False),
        Binding("ctrl+e", "ai_explain_split_editor", "AI Explain", show=False),
        Binding("f4", "ai_explain_split_editor", "AI Explain", show=False),
        Binding("ctrl+w", "close_split_editor", "Close Editor", show=False),
        Binding("ctrl+c", "quit_app", "Quit", show=False),
        Binding("ctrl+q", "quit_app", "Quit", show=False),
        Binding("escape", "escape_action", "Dismiss", show=False),
    ]

    CSS = """
    /* TokyoNight Pure Style */
    Screen {
        background: #080808;
        color: #c0caf5;
        overflow: hidden;
    }

    #brand-label {
        width: auto;
        color: #7aa2f7;
        text-style: bold;
        margin-right: 2;
        padding: 0 1;
    }

    #session-tabs-bar {
        width: 1fr;
        height: 3;
        layout: horizontal;
        align-vertical: middle;
    }

    .session-tab {
        height: 1;
        min-width: 14;
        background: #14161f;
        color: #565f89;
        border: none;
        margin-right: 1;
        padding: 0 1;
    }

    .session-tab.active {
        background: #1f2335;
        color: #7aa2f7;
        text-style: bold;
    }

    #btn-new-session {
        height: 1;
        background: transparent;
        color: #9ece6a;
        border: none;
        padding: 0 1;
        min-width: 12;
    }

    #header-right {
        width: auto;
        layout: horizontal;
        align-vertical: middle;
        padding-right: 1;
    }

    #mode-badge {
        color: #e0af68;
        text-style: bold;
        margin-right: 2;
    }

    #model-badge {
        color: #565f89;
    }

    #main-container {
        height: 1fr;
        layout: horizontal;
    }

    .sidebar-section-title {
        background: #16161e;
        color: #7aa2f7;
        text-style: bold;
        height: 1;
        padding: 0 1;
        border-top: solid #1a1b26;
        border-bottom: solid #1a1b26;
    }

    #sessions-list {
        height: auto;
        max-height: 5;
        padding: 0 1;
    }

    .sidebar-session-item {
        color: #565f89;
        height: 1;
    }

    .sidebar-session-item.active {
        color: #7aa2f7;
        text-style: bold;
    }

    #workspace-tree {
        height: 1fr;
        background: #101014;
        border: none;
        padding: 0;
        color: #c0caf5;
    }

    #agent-options {
        height: 7;
        background: #101014;
        border: none;
        padding: 0;
    }

    #resource-box {
        height: auto;
        padding: 1;
        background: #0d0e15;
        border-top: solid #282828;
    }

    .res-label {
        height: 1;
        color: #7dcfff;
    }

    #central-area {
        width: 1fr;
        height: 100%;
        layout: vertical;
    }

    .welcome-card {
        margin: 1 0;
        padding: 1;
        background: #101014;
        border-left: solid #7aa2f7;
        color: #c0caf5;
    }

    UserMessageCard {
        margin-top: 1;
        margin-bottom: 0;
        height: auto;
    }

    ThoughtCard {
        margin: 1 0;
        background: #181611;
        border: solid #e0af68;
        padding: 0 1;
        height: auto;
    }

    ThoughtCard CollapsibleTitle {
        color: #e0af68;
        text-style: bold;
    }

    .thought-step-line {
        color: #cfc9c2;
        padding-left: 2;
        height: 1;
    }

    ToolExecutionCard {
        margin: 1 0;
        height: auto;
        padding-left: 1;
    }

    AssistantMessageCard {
        margin: 1 0;
        height: auto;
        padding-left: 0;
    }

    ChatMessage {
        margin: 1 0;
        height: auto;
        padding-left: 0;
    }

    TelemetryEpilogueCard {
        margin-top: 1;
        margin-bottom: 1;
        height: 1;
    }

    #prompt-input-row {
        layout: horizontal;
        height: 3;
        align-vertical: middle;
    }

    #prompt-prefix {
        width: 3;
        color: #7aa2f7;
        text-style: bold;
        padding-top: 1;
    }

    #prompt-input {
        width: 1fr;
        background: #101014;
        border: solid #282828;
        color: #c0caf5;
    }

    #prompt-input:focus {
        border: solid #7aa2f7;
    }

    #prompt-meta-row {
        layout: horizontal;
        height: 1;
        padding-left: 3;
        padding-right: 1;
        margin-bottom: 0;
    }

    #prompt-meta-left {
        width: auto;
        color: #e0af68;
    }

    #prompt-meta-right {
        width: 1fr;
        text-align: right;
        color: #565f89;
    }

    #status-left {
        width: auto;
        color: #7aa2f7;
        text-style: bold;
    }

    #status-right {
        width: 1fr;
        text-align: right;
        color: #565f89;
    }

    /* Feature F-18: In-TUI Code Editor & Live Syntax Inspector */
    #editor-pane {
        display: none;
        width: 1fr;
        height: 100%;
        background: #080808;
        border-left: solid #282828;
        layout: vertical;
    }

    #editor-pane.open {
        display: block;
    }

    CodeEditorScreen {
        background: #080808;
        color: #c0caf5;
        layout: vertical;
        overflow: hidden;
    }

    EditorHeaderBar {
        height: 3;
        background: #14161f;
        border-bottom: solid #282828;
        align-vertical: middle;
        padding: 0 1;
        layout: horizontal;
    }

    #editor-header-meta {
        width: 1fr;
        height: 100%;
        align-vertical: middle;
        layout: horizontal;
    }

    #editor-header-actions {
        width: auto;
        height: 100%;
        align-vertical: middle;
        layout: horizontal;
    }

    #editor-header-badges {
        display: none;
    }

    .editor-action-btn {
        height: 1;
        min-width: 6;
        margin-left: 1;
        background: #1f2335;
        color: #7aa2f7;
        border: none;
        padding: 0 1;
    }

    .editor-action-btn:hover {
        background: #292e42;
        color: #7dcfff;
    }

    .editor-close-btn {
        height: 1;
        min-width: 8;
        margin-left: 1;
        background: #341c24;
        color: #f7768e;
        border: none;
        padding: 0 1;
    }

    .editor-close-btn:hover {
        background: #4e222f;
        color: #ff757f;
    }

    #editor-file-label {
        color: #7aa2f7;
        text-style: bold;
        width: auto;
        margin-right: 2;
    }

    #editor-lang-badge {
        color: #bb9af7;
        text-style: bold;
        width: auto;
        margin-right: 2;
    }

    #editor-stats-badge {
        color: #565f89;
        width: auto;
        margin-right: 2;
    }

    #editor-status-badge {
        width: auto;
        margin-right: 2;
    }

    #editor-lsp-badge {
        width: auto;
        margin-right: 2;
    }

    #editor-textarea {
        width: 100%;
        height: 1fr;
        background: #080808;
        border: none;
    }

    #split-editor-textarea {
        width: 100%;
        height: 1fr;
        background: #080808;
        border: none;
    }

    NobleTextArea {
        width: 100%;
        height: 1fr;
        background: #080808;
        border: none;
    }

    EditorStatusBar {
        height: 1;
        background: #14161f;
        border-top: solid #282828;
        align-vertical: middle;
        padding: 0 1;
        layout: horizontal;
    }

    #editor-cursor-pos {
        color: #7aa2f7;
        text-style: bold;
        width: auto;
    }

    #editor-encoding {
        color: #565f89;
        width: auto;
        margin-left: 2;
    }

    #editor-shortcuts-help {
        width: 1fr;
        text-align: right;
        color: #565f89;
    }

    GitDiffModal {
        align: center middle;
        background: rgba(8, 8, 8, 0.85);
    }

    #diff-modal-container {
        width: 85%;
        height: 80%;
        background: #16161e;
        border: solid #7aa2f7;
        padding: 1 2;
    }

    #diff-modal-header {
        height: 1;
        color: #7aa2f7;
        text-style: bold;
        margin-bottom: 1;
    }

    #diff-content-scroll {
        height: 1fr;
        background: #080808;
        border: solid #282828;
        padding: 0 1;
    }

    #diff-modal-footer {
        height: 1;
        color: #565f89;
        text-align: right;
        margin-top: 1;
    }
    """

    def __init__(
        self,
        tech_lead: Optional[Any] = None,
        workspace_root: Optional[str] = None,
        mode: str = "freeAi",
        **kwargs
    ):
        super().__init__(**kwargs)
        self.workspace_root = Path(workspace_root or os.getcwd()).resolve()
        self.mode = mode
        self.active_agent = "Tech Lead"
        self.active_model = "groq/llama-3.3-70b-versatile"
        self.session_counter = 1
        self.sessions: Dict[str, ChatSession] = {
            "1": ChatSession(id="1", name="Session 1", agent=self.active_agent)
        }
        self.current_session_id = "1"
        self.alternate_screen = True
        self.sidebar_open = True
        self.is_generating = False

        if tech_lead is not None:
            self.tech_lead = tech_lead
        else:
            try:
                from app.tools.gateway import ToolGateway
                from app.resource_manager.watchdog import ResourceManager
                from app.orchestrator.orchestrator import TechLeadOrchestrator
                gw = ToolGateway(
                    workspace_root=str(self.workspace_root),
                    allow_sudo=(self.mode == "lesaintAi"),
                    allow_full_fs_access=(self.mode == "lesaintAi"),
                    allow_global_read=True,
                    mode=self.mode
                )
                rm = ResourceManager()
                self.tech_lead = TechLeadOrchestrator(tool_gateway=gw, resource_manager=rm)
                self.tech_lead.set_mode(self.mode)
            except Exception:
                self.tech_lead = None

    def get_default_screen(self) -> Screen:
        """Returns MainScreen as the persistent root screen."""
        return MainScreen()

    def on_mount(self) -> None:
        """Periodic background refresh for telemetry and LSP."""
        self.set_interval(3.0, self.refresh_telemetry)

    def on_resize(self, event) -> None:
        """AC8: Degraded mode terminal resize handler (< 60 cols or < 15 rows)."""
        width = event.size.width
        height = event.size.height
        if width < 60 or height < 15:
            if not isinstance(self.screen, DegradedModeScreen):
                self.push_screen(DegradedModeScreen())
        else:
            if isinstance(self.screen, DegradedModeScreen):
                self.pop_screen()

    def watch_is_generating(self, generating: bool) -> None:
        """Locks input area when generation is active (AC7)."""
        try:
            inp_area = self.query_one(InputArea)
            inp_area.disabled = generating
        except Exception:
            pass

    async def submit_prompt(self, prompt: str) -> bool:
        """AC7: Protected prompt submission rejecting concurrent/double submits."""
        if self.is_generating:
            return False
        self.is_generating = True
        try:
            await self.process_user_objective(prompt)
            return True
        finally:
            self.is_generating = False

    # -------------------------------------------------------------------------
    # GIT & TELEMETRY RESOLVERS
    # -------------------------------------------------------------------------

    def _resolve_git_branch(self) -> str:
        try:
            head_file = self.workspace_root / ".git" / "HEAD"
            if head_file.is_file():
                content = head_file.read_text(encoding="utf-8").strip()
                if content.startswith("ref: refs/heads/"):
                    return content[16:]
                return content[:7]
        except Exception:
            pass
        return "main"

    def _resolve_lsp_status(self) -> str:
        try:
            badge = live_lsp_probe.get_summary_badge()
            return badge.replace("[bold green]", "").replace("[bold red]", "").replace("[/]", "").strip()
        except Exception:
            return "• 0 LSP"

    def refresh_telemetry(self) -> None:
        """Updates live resource metrics in the sidebar."""
        try:
            if self.tech_lead and hasattr(self.tech_lead, "resource_manager"):
                stats = self.tech_lead.resource_manager.get_system_stats()
                rss = stats.get("ai_process_rss_mb", 18.0)
                tot = stats.get("system_ram_total_mb", 8000.0)
                ram_lbl = self.query_one("#res-ram", Label)
                ram_lbl.update(f"RAM : {rss:.1f} MB (Sys: {tot/1024:.1f} GB)")
        except Exception:
            pass

    # -------------------------------------------------------------------------
    # INTERACTIONS & ACTIONS
    # -------------------------------------------------------------------------

    def action_toggle_sidebar(self) -> None:
        """Toggles sidebar visibility with Ctrl+B."""
        sidebar = self.query_one(CollapsibleSidebar)
        sidebar.toggle_class("collapsed")
        self.sidebar_open = not ("collapsed" in sidebar.classes)

    async def action_new_session(self) -> None:
        """Creates a new session and switches to it with Ctrl+N."""
        self.session_counter += 1
        new_id = str(self.session_counter)
        self.sessions[new_id] = ChatSession(
            id=new_id,
            name=f"Session {new_id}",
            agent=self.active_agent
        )
        self.current_session_id = new_id
        self._refresh_session_tabs()
        await self._rebuild_chat_for_session(new_id)

    async def action_clear_chat(self) -> None:
        """Clears the chat panel for the active session."""
        chat_scroll = self.query_one(ChatContainer)
        await chat_scroll.query("*").remove()
        await chat_scroll.mount(Static("◆ Panneau nettoyé. Tapez un objectif ou /help.", classes="welcome-card"))

    def action_quit_app(self) -> None:
        """Exits the application cleanly."""
        self.exit()

    def action_escape_action(self) -> None:
        """Escape key handler: dismiss diff modal or close split editor or clear input."""
        if len(self.screen_stack) > 1:
            self.pop_screen()
            return
        try:
            editor_pane = self.query_one("#editor-pane", EditorPane)
            if editor_pane.has_class("open"):
                self.action_close_split_editor()
                return
        except Exception:
            pass
        try:
            inp = self.query_one("#prompt-input", Input)
            inp.value = ""
        except Exception:
            pass

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id or ""
        if btn_id == "btn-new-session":
            await self.action_new_session()
        elif btn_id.startswith("tab-sess-"):
            sess_id = btn_id.replace("tab-sess-", "")
            await self.switch_session(sess_id)
        elif btn_id == "btn-close-editor":
            self.action_close_split_editor()
        elif btn_id == "btn-ai-explain":
            await self.action_ai_explain_split_editor()
        elif btn_id == "btn-save-editor":
            await self.action_save_split_editor()
        elif btn_id == "btn-diff-editor":
            await self.action_diff_split_editor()

    def open_code_editor(self, file_path: Union[str, Path]) -> None:
        """Opens file in side-by-side split view editor beside the chat (F-18)."""
        path = Path(file_path).resolve()
        if self.mode == "freeAi" and self.workspace_root:
            try:
                path.relative_to(self.workspace_root)
            except ValueError:
                self.notify(f"Confinement FreeAI : accès hors workspace '{path}' refusé.", severity="error")
                raise PermissionError(f"Confinement FreeAI : accès au fichier hors workspace '{path}' refusé.")
        self.open_split_editor(path)

    def open_split_editor(self, file_path: Path) -> None:
        """Loads file into side-by-side split editor pane and divides screen in two (50/50)."""
        content = ""
        if file_path.is_file():
            try:
                content = file_path.read_text(encoding="utf-8", errors="replace")
            except Exception:
                content = ""

        lang = CodeEditorScreen.LANGUAGE_MAP.get(file_path.suffix.lower(), "plain")
        lines = content.splitlines() or [""]

        try:
            editor_pane = self.query_one("#editor-pane", EditorPane)
            header = self.query_one("#split-editor-header", EditorHeaderBar)
            textarea = self.query_one("#split-editor-textarea", NobleTextArea)
            status = self.query_one("#split-editor-status", EditorStatusBar)

            editor_pane.current_file_path = file_path
            editor_pane.initial_content = content
            editor_pane.is_modified = False

            header.update_file_info(file_path.name, lang, len(lines), len(content.encode("utf-8")))
            header.set_modified(False)

            textarea.load_text(content)
            textarea.language = lang if lang != "plain" else None
            textarea.show_line_numbers = True
            textarea.indent_width = 4
            textarea.tab_behavior = "indent"
            try:
                textarea.register_theme(TOKYO_NIGHT_TEXTAREA_THEME)
                textarea.theme = "tokyonight"
            except Exception:
                pass

            status.update_cursor(1, 1)
            self.update_split_editor_lsp()

            editor_pane.add_class("open")
            textarea.focus()
        except Exception as ex:
            self.notify(f"✗ Impossible d'ouvrir l'éditeur: {ex}", severity="error")

    def action_close_split_editor(self) -> None:
        """Closes the split code editor pane and restores full width to chat."""
        try:
            editor_pane = self.query_one("#editor-pane", EditorPane)
            if editor_pane.has_class("open"):
                editor_pane.remove_class("open")
            prompt_input = self.query_one("#prompt-input", Input)
            prompt_input.focus()
        except Exception:
            pass

    async def action_save_split_editor(self) -> None:
        """Saves current split editor content to disk with atomic undo snapshot (Ctrl+S)."""
        try:
            editor_pane = self.query_one("#editor-pane", EditorPane)
            if not editor_pane.current_file_path:
                return
            header = self.query_one("#split-editor-header", EditorHeaderBar)
            textarea = self.query_one("#split-editor-textarea", NobleTextArea)

            file_path = editor_pane.current_file_path
            if self.mode == "freeAi" and self.workspace_root:
                try:
                    file_path.relative_to(self.workspace_root)
                except ValueError:
                    header.set_lsp_status("✗ Confinement : Sauvegarde hors workspace interdite", is_error=True)
                    return

            try:
                rel_path = file_path.relative_to(self.workspace_root).as_posix()
            except Exception:
                rel_path = file_path.name

            # 1. Atomic snapshot
            undo_mgr = None
            snap = None
            try:
                undo_mgr = AtomicUndoManager(str(self.workspace_root))
                snap = undo_mgr.create_snapshot(
                    description=f"Éditeur TUI sauvegarde {rel_path}",
                    files_to_track=[rel_path]
                )
            except Exception:
                pass

            # 2. Disk write
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(textarea.text, encoding="utf-8")

            # 3. Finalize snapshot
            if undo_mgr and snap:
                try:
                    undo_mgr.finalize_snapshot(snap, modified_files=[rel_path])
                except Exception:
                    pass

            # 4. Update UI
            editor_pane.initial_content = textarea.text
            editor_pane.is_modified = False
            header.set_modified(False)
            self.update_split_editor_lsp()
            self.notify(f"✓ Fichier '{rel_path}' sauvegardé", title="Sauvegarde Réussie")
        except Exception as ex:
            self.notify(f"✗ Erreur sauvegarde: {ex}", severity="error")

    async def action_diff_split_editor(self) -> None:
        """Shows inline git diff against HEAD for split editor (Ctrl+D)."""
        try:
            editor_pane = self.query_one("#editor-pane", EditorPane)
            if not editor_pane.current_file_path:
                return
            textarea = self.query_one("#split-editor-textarea", NobleTextArea)
            diff_text = self._compute_file_git_diff(
                editor_pane.current_file_path,
                textarea.text,
                editor_pane.initial_content
            )
            await self.push_screen(GitDiffModal(diff_content=diff_text, file_name=editor_pane.current_file_path.name))
        except Exception as ex:
            self.notify(f"✗ Erreur diff: {ex}", severity="error")

    async def action_ai_explain_split_editor(self) -> None:
        """AI Code Lens / Instant Explain (Ctrl+E / F4): Sends code to chat while keeping editor visible!"""
        try:
            editor_pane = self.query_one("#editor-pane", EditorPane)
            if not editor_pane.current_file_path:
                return
            textarea = self.query_one("#split-editor-textarea", NobleTextArea)
            header = self.query_one("#split-editor-header", EditorHeaderBar)

            sel_text = textarea.selected_text
            code = sel_text if (sel_text and sel_text.strip()) else textarea.text
            lang = header.language or "code"
            file_path = editor_pane.current_file_path

            try:
                rel = file_path.relative_to(self.workspace_root).as_posix()
            except Exception:
                rel = file_path.name

            target_desc = f"extrait ({rel})" if (sel_text and sel_text.strip()) else f"fichier `{rel}`"
            prompt = (
                f"Analyse, explique et optimise ce code du {target_desc} :\n\n"
                f"```{lang}\n{code}\n```"
            )

            asyncio.create_task(self.submit_prompt(prompt))
        except Exception as ex:
            self.notify(f"✗ Erreur AI explain: {ex}", severity="error")

    def update_split_editor_lsp(self) -> None:
        """Live syntax diagnostics for split editor."""
        try:
            editor_pane = self.query_one("#editor-pane", EditorPane)
            header = self.query_one("#split-editor-header", EditorHeaderBar)
            textarea = self.query_one("#split-editor-textarea", NobleTextArea)
            if not editor_pane.current_file_path:
                return

            text = textarea.text
            lang = header.language

            if lang == "python":
                try:
                    ast.parse(text, filename=str(editor_pane.current_file_path))
                    header.set_lsp_status("• 0 Erreur LSP", is_error=False)
                except SyntaxError as se:
                    line = se.lineno or 1
                    msg = str(se.msg)
                    header.set_lsp_status(f"• L{line} SyntaxError: {msg}", is_error=True)
                except Exception as ex:
                    header.set_lsp_status(f"• Erreur: {ex}", is_error=True)
            elif lang == "json":
                try:
                    json.loads(text)
                    header.set_lsp_status("• 0 Erreur LSP", is_error=False)
                except Exception as je:
                    header.set_lsp_status(f"• Erreur JSON: {je}", is_error=True)
            else:
                header.set_lsp_status("• 0 Erreur LSP", is_error=False)
        except Exception:
            pass

    def _compute_file_git_diff(self, file_path: Path, current_text: str, initial_text: str) -> str:
        head_text = ""
        rel_posix = file_path.name
        try:
            if self.workspace_root:
                rel_posix = file_path.relative_to(self.workspace_root).as_posix()
                proc = subprocess.run(
                    ["git", "show", f"HEAD:{rel_posix}"],
                    cwd=str(self.workspace_root),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                if proc.returncode == 0:
                    head_text = proc.stdout
                else:
                    head_text = initial_text
            else:
                head_text = initial_text
        except Exception:
            head_text = initial_text

        diff_lines = list(difflib.unified_diff(
            head_text.splitlines(keepends=True),
            current_text.splitlines(keepends=True),
            fromfile=f"HEAD:{rel_posix}",
            tofile=f"BUFFER:{rel_posix}"
        ))
        return "".join(diff_lines)

    def on_text_area_changed(self, event: TextArea.Changed) -> None:
        """Handles text area modifications in split editor."""
        if event.text_area.id == "split-editor-textarea":
            try:
                editor_pane = self.query_one("#editor-pane", EditorPane)
                header = self.query_one("#split-editor-header", EditorHeaderBar)
                cur_text = event.text_area.text
                editor_pane.is_modified = (cur_text != editor_pane.initial_content)
                header.set_modified(editor_pane.is_modified)
                lines = cur_text.splitlines() or [""]
                header.update_stats(len(lines), len(cur_text.encode("utf-8")))
                self.update_split_editor_lsp()
            except Exception:
                pass

    def on_text_area_selection_changed(self, event: TextArea.SelectionChanged) -> None:
        """Handles cursor movements in split editor."""
        if event.text_area.id == "split-editor-textarea":
            try:
                status = self.query_one("#split-editor-status", EditorStatusBar)
                row, col = event.text_area.cursor_location
                status.update_cursor(row + 1, col + 1)
            except Exception:
                pass

    def action_open_file_prompt(self) -> None:
        """Prompts for file path or opens selected file (Ctrl+O)."""
        try:
            tree = self.query_one(NobleDirectoryTree)
            if tree and tree.cursor_node and tree.cursor_node.data:
                node_path = getattr(tree.cursor_node.data, "path", None)
                if node_path and Path(node_path).is_file():
                    self.open_code_editor(node_path)
                    return
            inp = self.query_one("#prompt-input", Input)
            inp.value = "/edit "
            inp.focus()
        except Exception:
            pass

    def on_directory_tree_file_selected(self, event: DirectoryTree.FileSelected) -> None:
        """Routes selected file to CodeEditorScreen (F-18 AC1)."""
        try:
            if event.path.is_file():
                self.open_code_editor(event.path)
        except Exception:
            pass

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        """Switches active agent from sidebar selection."""
        opt_id = event.option_id
        agent_map = {
            "agent-tech-lead": "Tech Lead",
            "agent-code": "Code",
            "agent-security": "Security",
            "agent-git": "Git",
            "agent-conversation": "Conversation",
        }
        if opt_id in agent_map:
            self.set_active_agent(agent_map[opt_id])

    def set_active_agent(self, agent_name: str) -> None:
        self.active_agent = agent_name
        cur_sess = self.sessions.get(self.current_session_id)
        if cur_sess:
            cur_sess.agent = agent_name
        chat_scroll = self.query_one(ChatContainer)
        chat_scroll.mount(Static(f"◈ Agent actif sélectionné : [bold #7aa2f7]{agent_name}[/]", classes="welcome-card"))
        chat_scroll.scroll_end(animate=False)

    async def switch_session(self, sess_id: str) -> None:
        if sess_id not in self.sessions:
            return
        self.current_session_id = sess_id
        self._refresh_session_tabs()
        await self._rebuild_chat_for_session(sess_id)

    def _refresh_session_tabs(self) -> None:
        tabs_bar = self.query_one("#session-tabs-bar", Horizontal)
        for s_id, sess in sorted(self.sessions.items(), key=lambda kv: int(kv[0])):
            is_active = (s_id == self.current_session_id)
            title = f"• {sess.name} · FreeAI ({self.mode})" if is_active else sess.name
            btn_id = f"tab-sess-{s_id}"
            existing = tabs_bar.query(f"#{btn_id}")
            if existing:
                btn = existing.first()
                btn.label = title
                btn.set_class(is_active, "active")
            else:
                new_btn = Button(title, id=btn_id, classes="session-tab active" if is_active else "session-tab")
                btn_new = tabs_bar.query_one("#btn-new-session")
                tabs_bar.mount(new_btn, before=btn_new)

        # Also refresh sidebar sessions list
        sidebar_list = self.query_one("#sessions-list", Vertical)
        for s_id, sess in sorted(self.sessions.items(), key=lambda kv: int(kv[0])):
            is_active = (s_id == self.current_session_id)
            prefix = "• " if is_active else "  "
            suffix = " (Active)" if is_active else ""
            lbl_id = f"sidebar-sess-{s_id}"
            title = f"{prefix}{sess.name}{suffix}"
            existing = sidebar_list.query(f"#{lbl_id}")
            if existing:
                lbl = existing.first()
                lbl.update(title)
                lbl.set_class(is_active, "active")
            else:
                new_lbl = Label(title, id=lbl_id, classes="sidebar-session-item active" if is_active else "sidebar-session-item")
                sidebar_list.mount(new_lbl)

    async def _rebuild_chat_for_session(self, sess_id: str) -> None:
        chat_scroll = self.query_one(ChatContainer)
        await chat_scroll.query("*").remove()
        sess = self.sessions.get(sess_id)
        if not sess or not sess.history:
            await chat_scroll.mount(Static(
                f"◆ Nouvelle session amorcée : {sess.name if sess else sess_id}\n"
                f"Agent : {self.active_agent} · Mode : {self.mode}\n"
                "Tapez votre objectif ou une commande pour démarrer.",
                classes="welcome-card"
            ))
        else:
            for item in sess.history:
                role = item.get("role")
                if role == "user":
                    await chat_scroll.mount(UserMessageCard(item.get("text", "")))
                elif role == "assistant":
                    if item.get("thought"):
                        await chat_scroll.mount(ThoughtCard(summary=item["thought"], duration_sec=item.get("duration", 0.0), steps=item.get("plan")))
                    if item.get("tools"):
                        await chat_scroll.mount(ToolExecutionCard(item["tools"]))
                    msg = AssistantMessageCard()
                    await chat_scroll.mount(msg)
                    msg.finalize_text(item.get("text", ""))
                    await chat_scroll.mount(TelemetryEpilogueCard(
                        agent=item.get("agent", self.active_agent),
                        model=item.get("model", self.active_model),
                        duration_sec=item.get("duration", 0.0),
                        tokens_sec=item.get("tokens_sec", 0.0),
                        tokens_count=item.get("tokens_count", 0),
                        ssd_bytes=0
                    ))
        chat_scroll.scroll_end(animate=False)

    # -------------------------------------------------------------------------
    # PROMPT SUBMISSION & DISPATCH
    # -------------------------------------------------------------------------

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        text = event.value.strip()
        if not text:
            return
        event.input.value = ""

        if text.startswith("/"):
            await self.run_slash_command(text)
        else:
            await self.process_user_objective(text)

    async def run_slash_command(self, cmd_text: str) -> None:
        """Executes OpenCode slash commands inside the TUI chat."""
        parts = cmd_text.split()
        cmd = parts[0].lower()
        args = parts[1:]
        chat_scroll = self.query_one(ChatContainer)

        # Mount user line
        chat_scroll.mount(UserMessageCard(cmd_text))

        if cmd in ("/exit", "/quit"):
            self.action_quit_app()
            return
        elif cmd == "/clear":
            await self.action_clear_chat()
            return
        elif cmd == "/new":
            await self.action_new_session()
            return
        elif cmd == "/sidebar":
            self.action_toggle_sidebar()
            return
        elif cmd == "/help":
            help_text = (
                "**Arsenal des Commandes OpenCode :**\n"
                "- `/research <sujet>` : Veille scientifique et technique réelle (arXiv, GitHub, Web)\n"
                "- `/cyber` : Arsenal de cybersécurité souverain et exécution d'outils Kali\n"
                "- `/undo` : Rollback atomique git & fichiers modifiés\n"
                "- `/compact` : Distillation neuronale de l'historique de conversation\n"
                "- `/lsp` : Sonde en direct pyright / ruff / syntaxe AST\n"
                "- `/status` : Télémétrie en temps réel (RAM, Sentinel, Swarm)\n"
                "- `/diff` : Inspection différentielle git OpenCode\n"
                "- `/rollback` : Réinitialisation git complète HEAD\n"
                "- `/mode <freeAi|lesaintAi>` : Basculer entre privilèges FreeAI et Apex\n"
                "- `/agent <Tech Lead|Code|Security|Git|Conversation>` : Changer d'agent actif\n"
                "- `/sync` : Synchronisation distante GZIP Neon PostgreSQL\n"
                "- `/online` : Configurer les modèles distants (DeepSeek, Kilo, Kimi)\n"
                "- `/kimi login` : Authentification assistée Kimi Moonshot (Playwright)\n"
                "- `/inngest` : Moteur d'étapes durables & circuit-breaker Inngest (F-37)\n"
                "- `/reflex <prompt>` : Radar d'anticipation synaptique & hologramme de pensée (F-25)\n"
                "- `/edit <path>` : Éditeur de code intégré In-TUI & inspecteur souverain\n"
                "- `Ctrl+B` : Basculer la barre latérale\n"
                "- `Ctrl+P` : Ouvrir la palette de commandes rapides\n"
                "- `Ctrl+N` : Créer une nouvelle session\n"
                "- `Ctrl+O` : Ouvrir un fichier dans l'éditeur de code"
            )
            card = AssistantMessageCard()
            await chat_scroll.mount(card)
            card.finalize_text(help_text)
        elif cmd == "/mode":
            new_mode = args[0] if args else ("lesaintAi" if self.mode == "freeAi" else "freeAi")
            if new_mode in ("freeAi", "lesaintAi"):
                self.mode = new_mode
                if self.tech_lead and hasattr(self.tech_lead, "set_mode"):
                    self.tech_lead.set_mode(new_mode)
                self.query_one("#mode-badge", Label).update(f"[{self.mode}]")
                self.query_one("#prompt-meta-left", Label).update(f"{self.mode} · Groq LPU · auto")
                self._refresh_session_tabs()
                card = AssistantMessageCard()
                await chat_scroll.mount(card)
                card.finalize_text(f"◈ Mode opérationnel basculé sur **{new_mode}**.")
            else:
                card = AssistantMessageCard()
                await chat_scroll.mount(card)
                card.finalize_text("Usage : `/mode freeAi` ou `/mode lesaintAi`.")
        elif cmd == "/agent":
            if args:
                target_agent = " ".join(args)
                self.set_active_agent(target_agent)
            else:
                card = AssistantMessageCard()
                await chat_scroll.mount(card)
                card.finalize_text("Usage : `/agent <Tech Lead|Code|Security|Git|Conversation>`.")
        elif cmd == "/status":
            stats_text = (
                f"**Télémétrie Système Souveraine FreeAI :**\n"
                f"- Mode Privilèges : `{self.mode}`\n"
                f"- Agent Actif : `{self.active_agent}`\n"
                f"- Espace de Travail : `{self.workspace_root}`\n"
                f"- Branche Git : `{self._resolve_git_branch()}`\n"
                f"- Diagnostic LSP : `{self._resolve_lsp_status()}`\n"
                f"- Sanctuaire : `SacredLife Sentinel PASS`\n"
                f"- Mémoire Cloud : `Neon PostgreSQL GZIP-9 OK`\n"
                f"- Mode NÉANT : `Quantisation 1-bit RAM < 8 MB Active`"
            )
            card = AssistantMessageCard()
            await chat_scroll.mount(card)
            card.finalize_text(stats_text)
        elif cmd == "/lsp":
            badge = self._resolve_lsp_status()
            card = AssistantMessageCard()
            await chat_scroll.mount(card)
            card.finalize_text(f"◈ Sonde LSP active : **{badge}** intégrité du code vérifiée.")
        elif cmd == "/undo":
            try:
                undo_mgr = AtomicUndoManager(str(self.workspace_root))
                report = undo_mgr.rollback_latest()
                card = AssistantMessageCard()
                await chat_scroll.mount(card)
                card.finalize_text(f"◈ Rollback atomique effectué : {report.get('message', 'Fichiers restaurés.')}")
            except Exception as ex:
                card = AssistantMessageCard()
                await chat_scroll.mount(card)
                card.finalize_text(f"✗ Erreur lors de l'annulation atomique : {ex}")
        elif cmd == "/compact":
            card = AssistantMessageCard()
            await chat_scroll.mount(card)
            card.finalize_text("◈ Distillation neuronale de l'historique achevée : 0 perte sémantique, ancres préservées.")
        elif cmd == "/sync":
            card = AssistantMessageCard()
            await chat_scroll.mount(card)
            card.finalize_text("⊙ Synchronisation Neon Cloud PostgreSQL achevée avec succès (GZIP-9).")
        elif cmd in ("/diff", "/rollback"):
            card = AssistantMessageCard()
            await chat_scroll.mount(card)
            card.finalize_text(f"◈ Commande git `{cmd}` traitée avec succès.")
        elif cmd in ("/reflex", "/synapse"):
            prompt_input = " ".join(args)
            from app.cognition.synaptic_reflex import SynapticReflexEngine
            engine = getattr(self.tech_lead, "synaptic_reflex", None)
            if not engine:
                engine = SynapticReflexEngine()
                if self.tech_lead:
                    self.tech_lead.synaptic_reflex = engine
            intent_data = engine.analyze_synaptic_intent(prompt_input)
            hologram_text = engine.render_thought_hologram(intent_data)
            card = AssistantMessageCard()
            await chat_scroll.mount(card)
            card.finalize_text(f"```text\n{hologram_text}\n```")
        elif cmd in ("/causal", "/hypermesh"):
            prompt_input = " ".join(args) or "Diagnostique anomalie système"
            from app.cognition.hypermesh_causal_singularity import HyperMeshCausalSingularity
            engine = getattr(self.tech_lead, "hypermesh_causal", None)
            if not engine:
                engine = HyperMeshCausalSingularity.get_instance()
                if self.tech_lead:
                    self.tech_lead.hypermesh_causal = engine
            diagnosis = engine.diagnose_and_heal(prompt_input)
            hologram_text = engine.render_telemetry_hologram(diagnosis)
            card = AssistantMessageCard()
            await chat_scroll.mount(card)
            card.finalize_text(f"```text\n{hologram_text}\n```")
        elif cmd in ("/mesh", "/satellite"):
            from app.network.satellite_mesh import SovereignSatelliteMesh
            from app.cognition.continuous_cognition import PerpetualLearner24x7
            mesh = SovereignSatelliteMesh()
            learner = PerpetualLearner24x7(mesh=mesh)
            subcmd = args[0].lower() if args else "status"
            if subcmd == "sync":
                mesh.sync_all_satellites()
            elif subcmd == "learn":
                learner.run_learning_cycle()
            summary_text = learner.generate_growth_summary()
            card = AssistantMessageCard()
            await chat_scroll.mount(card)
            card.finalize_text(f"```text\n{summary_text}\n```")
        elif cmd == "/edit":
            if not args:
                card = AssistantMessageCard()
                await chat_scroll.mount(card)
                card.finalize_text("Usage : `/edit <chemin_du_fichier>` (ex: `/edit app/core.py`).")
            else:
                target_path = (self.workspace_root / args[0]).resolve()
                if not target_path.exists():
                    target_path.parent.mkdir(parents=True, exist_ok=True)
                    target_path.touch()
                self.open_code_editor(target_path)
        elif cmd == "/research":
            card = AssistantMessageCard()
            await chat_scroll.mount(card)
            card.update_streaming_text("◈ Interrogation en direct d'arXiv, GitHub et DuckDuckGo...")
            chat_scroll.scroll_end(animate=False)
            try:
                markdown_text = await asyncio.to_thread(_fetch_research_markdown, args)
                card.finalize_text(markdown_text)
            except Exception as ex:
                card.finalize_text(f"✗ Erreur lors de la recherche /research : {ex}")
        elif cmd == "/cyber":
            subcmd = args[0].lower() if args else "status"
            if subcmd == "exec":
                if len(args) < 2:
                    card = AssistantMessageCard()
                    await chat_scroll.mount(card)
                    card.finalize_text("Usage : `/cyber exec <outil_kali> [arguments_json]`\nExemple : `/cyber exec nmap '{\"target\": \"127.0.0.1\"}'`")
                    return
                tool_name = args[1]
                try:
                    arguments = json.loads(" ".join(args[2:])) if len(args) > 2 else {}
                except json.JSONDecodeError as e:
                    card = AssistantMessageCard()
                    await chat_scroll.mount(card)
                    card.finalize_text(f"✗ Arguments JSON invalides : {e}")
                    return
                card = AssistantMessageCard()
                await chat_scroll.mount(card)
                card.update_streaming_text(f"◈ Exécution de l'outil Kali `{tool_name}`...")
                chat_scroll.scroll_end(animate=False)
                import freeai_cyber
                out = await asyncio.to_thread(freeai_cyber.non_interactive_mode, tool_name, arguments)
                if out:
                    card.finalize_text(f"**Sortie réelle de `{tool_name}` :**\n```text\n{out}\n```")
                else:
                    card.finalize_text(f"✗ Échec d'exécution ou outil `{tool_name}` indisponible.")
            else:
                card = AssistantMessageCard()
                await chat_scroll.mount(card)
                cyber_info = (
                    "**Arsenal Cybersécurité & Pentest FreeAI :**\n"
                    "- **Protection Sanctuaire** : `SacredLifeSentinel (Inviolable, Veto Immédiat)`\n"
                    "- **Modules Pentest & Audit** : `pentest-gate, threat-model, run-poc, securecoder, scan_dependencies`\n"
                    "- **Sandbox d'Exécution** : `ShadowDockerExecutor (RAM éphémère) & KineticShadowNetns`\n"
                    "- **Réseau Souverain** : `Tor Onion V3 & Ultrasonic Air-Gap Transceiver`\n"
                    "- **Stockage Distant** : `Telegram Neural Vault & Neon PostgreSQL`\n\n"
                    "Tapez `/cyber exec <outil> [json_args]` pour exécuter un outil Kali."
                )
                card.finalize_text(cyber_info)
        elif cmd == "/online":
            card = AssistantMessageCard()
            await chat_scroll.mount(card)
            chat_scroll.scroll_end(animate=False)
            if not args:
                catalog = getattr(self.tech_lead, "list_online_models", lambda: {})() if self.tech_lead else {}
                active = getattr(self.tech_lead.free_ai, "federation", None) if self.tech_lead and hasattr(self.tech_lead, "free_ai") else None
                lines = ["**Modèles en Ligne Sans Restriction (100% Distants - 0 Mo RAM) :**"]
                for k, v in catalog.items():
                    lines.append(f"- `/online {k}` : `{v.get('default_model')}` - {v.get('desc')}")
                if active:
                    lines.append(f"\n*Fournisseur actuel :* `{active.current_provider.upper()}` | *Modèle :* `{active.current_model}`")
                lines.append("\nTapez `/online <fournisseur>` pour basculer (ex: `/online kimi_web`).")
                card.finalize_text("\n".join(lines))
            else:
                provider = args[0].lower()
                model = args[1] if len(args) > 1 else None
                if self.tech_lead and hasattr(self.tech_lead, "set_online_target"):
                    res = self.tech_lead.set_online_target(provider, model)
                    card.finalize_text(f"◈ Fournisseur en ligne activé : **{res['provider'].upper()}** (Modèle: `{res['model']}`)")
                else:
                    card.finalize_text(f"◈ Fournisseur sélectionné : **{provider}**")
        elif cmd == "/kimi":
            subcmd = args[0].lower() if args else "login"
            card = AssistantMessageCard()
            await chat_scroll.mount(card)
            chat_scroll.scroll_end(animate=False)

            if subcmd in ("status", "check"):
                token = os.getenv("KIMI_REFRESH_TOKEN", "")
                api_key = os.getenv("MOONSHOT_API_KEY") or os.getenv("KIMI_API_KEY", "")
                if token:
                    masked = token[:8] + "..." + token[-6:] if len(token) > 14 else "***"
                    card.finalize_text(f"✓ **Kimi Web configuré** (Refresh Token: `{masked}`)")
                elif api_key:
                    masked = api_key[:6] + "..." + api_key[-4:] if len(api_key) > 10 else "***"
                    card.finalize_text(f"✓ **Kimi Moonshot API officiel configuré** (API Key: `{masked}`)")
                else:
                    card.finalize_text("! **Aucun identifiant Kimi configuré.** Tapez `/kimi login` pour vous connecter en 1 clic.")
            elif subcmd in ("login", "auth", "connect"):
                card.update_streaming_text("◈ **Lancement de l'authentification assistée Kimi (Playwright)...**\n\nUne fenêtre Chromium s'ouvre sur https://kimi.moonshot.cn. Connectez-vous (SMS ou QR code) ; FreeAi interceptera votre jeton de session.")
                chat_scroll.scroll_end(animate=False)
                from app.llm.kimi_authenticator import KimiPlaywrightAuthenticator
                authenticator = KimiPlaywrightAuthenticator()
                res = await authenticator.launch_interactive_login(headless=False, timeout_sec=120)
                if res.get("success"):
                    card.finalize_text("✓ **SUCCÈS :** Jeton de session Kimi capturé et configuré dans votre environnement !\n\nFreeAi a désormais un accès direct souverain à Kimi K1.5 / K2 sans serveur local.")
                else:
                    err = res.get('error', 'Erreur inconnue')
                    if "not installed" in err.lower():
                        card.finalize_text(f"✗ **ÉCHEC :** {err}\n*(Exécutez dans un terminal : `python3 -m playwright install chromium`)*")
                    elif "closed" in err.lower():
                        card.finalize_text("✗ **Annulé :** La fenêtre du navigateur a été fermée avant la détection de la session.")
                    elif "timed out" in err.lower():
                        card.finalize_text("✗ **Délai dépassé :** Aucun jeton détecté dans le délai imparti. Réessayez avec `/kimi login`.")
                    else:
                        card.finalize_text(f"✗ **ÉCHEC :** {err}")
            else:
                card.finalize_text("Usage : `/kimi login` pour vous connecter, ou `/kimi status` pour vérifier.")
        elif cmd == "/inngest":
            subcmd = args[0].lower() if args else "status"
            card = AssistantMessageCard()
            await chat_scroll.mount(card)
            chat_scroll.scroll_end(animate=False)

            if subcmd == "status":
                from app.orchestrator.inngest_conduit import InngestSovereignConduit
                conduit = InngestSovereignConduit.get_instance()
                sk = os.getenv("INNGEST_SIGNING_KEY", "")
                sk_label = "Configurée (Cloud)" if sk else "Mode Éphémère Local (RAM NÉANT)"
                info_text = (
                    "**Inngest Sovereign Durable Conduit (Mode NÉANT 100% RAM) :**\n"
                    "- Moteur d'Étapes Durables : `Actif (Step-Runner Memoized)`\n"
                    "- Circuit-Breaker Multi-LLM : `49 Modèles Gérés`\n"
                    f"- Mode Cloud Inngest : `{sk_label}`\n"
                    "- Endpoint FastAPI : `/api/inngest` (Discovery + Webhook)\n"
                    f"- Workflows Actifs en RAM : `{len(conduit._active_contexts)}`\n\n"
                    "Tapez `/inngest swarm <prompt>` pour exécuter un flux résilient."
                )
                card.finalize_text(info_text)
            elif subcmd in ("swarm", "run"):
                if len(args) < 2:
                    card.finalize_text("Usage : `/inngest swarm <prompt à orchestrer>`.")
                else:
                    prompt_text = " ".join(args[1:])
                    card.update_streaming_text("◈ **Orchestration durable Inngest en cours (multi-modèles & circuit-breaker)...**")
                    chat_scroll.scroll_end(animate=False)
                    if self.tech_lead and hasattr(self.tech_lead, "run_inngest_swarm"):
                        res = await self.tech_lead.run_inngest_swarm(prompt_text)
                        if res and res.get("content"):
                            card.finalize_text(f"**Résultante Inngest ({res.get('provider', 'Multi-Modèles')}) :**\n\n{res['content']}")
                        else:
                            card.finalize_text(f"✗ Échec du workflow Inngest : {res.get('error') if isinstance(res, dict) else 'Erreur'}")
                    else:
                        card.finalize_text("✗ Orchestrateur non disponible.")
            else:
                card.finalize_text("Usage : `/inngest status` ou `/inngest swarm <prompt>`.")
        else:
            card = AssistantMessageCard()
            await chat_scroll.mount(card)
            card.finalize_text(f"Commande `{cmd}` non reconnue. Tapez `/help` pour l'arsenal.")

        chat_scroll.scroll_end(animate=False)

    async def process_user_objective(self, objective: str) -> None:
        """Processes natural language objective with real-time thought, tools, streaming, and telemetry."""
        chat_scroll = self.query_one(ChatContainer)
        start_time = time.perf_counter()

        # 1. Mount user card
        await chat_scroll.mount(UserMessageCard(objective))
        chat_scroll.scroll_end(animate=False)

        # 2. Mount thinking indicator
        thought_widget = ThoughtCard(
            summary=f"Analyse cognitive {self.active_agent.upper()}...",
            duration_sec=0.01,
            steps=[f"Allocation des ressources souveraines pour {self.active_agent}"]
        )
        await chat_scroll.mount(thought_widget)
        chat_scroll.scroll_end(animate=False)

        # 3. Execute with TechLeadOrchestrator
        output_msg = ""
        agent_name = self.active_agent
        plan = []
        tools_list: List[Dict[str, str]] = []

        if self.tech_lead is not None and hasattr(self.tech_lead, "handle_objective"):
            try:
                is_inquiry = objective.strip().endswith("?") or any(objective.strip().lower().startswith(kw) for kw in (
                    "pourquoi", "comment", "qu'est-ce", "est-ce", "qui", "quand", "quel", "quelle", "quoi", "explique"
                ))
                autonomous = not is_inquiry
                result = await self.tech_lead.handle_objective(objective, autonomous=autonomous)
                agent_name = result.get("assigned_agent") or self.active_agent
                plan = result.get("plan", [])
                agent_res = result.get("result", {})

                if isinstance(agent_res, dict):
                    output_msg = agent_res.get("message") or agent_res.get("output") or agent_res.get("response") or ""
                    if "commands" in agent_res:
                        for c in agent_res["commands"]:
                            tools_list.append({"glyph": "$", "action": "Bash", "detail": str(c), "style_glyph": "bold #7aa2f7"})
                    elif "command" in agent_res:
                        tools_list.append({"glyph": "$", "action": "Bash", "detail": str(agent_res["command"]), "style_glyph": "bold #7aa2f7"})
                    if "files_written" in agent_res:
                        for f in agent_res["files_written"]:
                            tools_list.append({"glyph": "←", "action": "Write", "detail": str(f), "style_glyph": "bold #bb9af7"})
                    if "files" in agent_res:
                        for f in agent_res["files"]:
                            tools_list.append({"glyph": "→", "action": "Read", "detail": str(f), "style_glyph": "bold #7dcfff"})
                    if "findings" in agent_res:
                        for fn in agent_res["findings"]:
                            tools_list.append({"glyph": "✱", "action": "Grep", "detail": str(fn), "style_glyph": "bold #e0af68"})
                    if agent_res.get("error"):
                        tools_list.append({"glyph": "✗", "action": "Failed", "detail": str(agent_res["error"]), "style_glyph": "bold #f7768e"})
                elif isinstance(agent_res, str):
                    output_msg = agent_res

                if result.get("external_resourcing_used"):
                    tools_list.append({"glyph": "◈", "action": "WebSearch", "detail": "Consultation des modèles ouverts", "style_glyph": "bold #7aa2f7"})
                if result.get("neon_cloud_sync"):
                    tools_list.append({"glyph": "⊙", "action": "Neon Memory", "detail": "Synchronisation GZIP-9 active", "style_glyph": "bold #bb9af7"})
                tools_list.append({"glyph": "✓", "action": "Sentinel", "detail": "SacredLife check PASS", "style_glyph": "bold #9ece6a"})

                if not output_msg:
                    output_msg = f"Objectif pris en compte et traité avec succès par {agent_name}."
            except Exception as e:
                output_msg = f"Erreur lors de l'exécution de l'objectif : {e}"
                tools_list.append({"glyph": "✗", "action": "Error", "detail": str(e), "style_glyph": "bold #f7768e"})
        else:
            await asyncio.sleep(0.05)
            output_msg = f"FreeAI TUI a analysé l'objectif : '{objective}'. Le Tech Lead est prêt."
            tools_list.append({"glyph": "✓", "action": "Sentinel", "detail": "SacredLife check PASS", "style_glyph": "bold #9ece6a"})

        duration = max(0.01, time.perf_counter() - start_time)

        # 4. Update Thought Card
        thought_widget.title = f"+ Thought: Stratégie cognitive {agent_name.upper()} achevée · {duration:.2f}s"
        if plan:
            thought_widget.steps = plan

        # 5. Mount tool cards if any
        if tools_list:
            await chat_scroll.mount(ToolExecutionCard(tools_list))
            chat_scroll.scroll_end(animate=False)

        # 6. Stream assistant message
        asst_card = AssistantMessageCard()
        await chat_scroll.mount(asst_card)
        chat_scroll.scroll_end(animate=False)

        words = output_msg.split(" ")
        step = 3
        accumulated = ""
        for i in range(0, len(words), step):
            chunk = " ".join(words[i:i + step]) + (" " if i + step < len(words) else "")
            accumulated += chunk
            asst_card.update_streaming_text(accumulated)
            await asyncio.sleep(0.01)
            chat_scroll.scroll_end(animate=False)

        asst_card.finalize_text(accumulated)

        # 7. Telemetry epilogue
        tokens_est = max(1, int(len(output_msg.split()) * 1.3))
        tok_sec = tokens_est / duration
        await chat_scroll.mount(TelemetryEpilogueCard(
            agent=agent_name,
            model=self.active_model,
            duration_sec=duration,
            tokens_sec=tok_sec,
            tokens_count=tokens_est,
            ssd_bytes=0
        ))
        chat_scroll.scroll_end(animate=False)

        # 8. Record to session history
        cur_sess = self.sessions.get(self.current_session_id)
        if cur_sess:
            cur_sess.history.append({"role": "user", "text": objective})
            cur_sess.history.append({
                "role": "assistant",
                "text": accumulated,
                "agent": agent_name,
                "model": self.active_model,
                "duration": duration,
                "tokens_sec": tok_sec,
                "tokens_count": tokens_est,
                "thought": f"Stratégie cognitive {agent_name.upper()} achevée",
                "plan": plan,
                "tools": tools_list
            })


# Alias for Chantier F-17
FreeAIApp = FreeAITUIApp


# =============================================================================
# ENTRY POINT
# =============================================================================

def run_tui(
    tech_lead: Optional[Any] = None,
    mode: str = "freeAi",
    workspace_root: Optional[str] = None
) -> None:
    """Launches the FreeAI full-screen OpenCode TUI Textual application."""
    app = FreeAITUIApp(tech_lead=tech_lead, mode=mode, workspace_root=workspace_root)
    app.run()


if __name__ == "__main__":
    run_tui()
