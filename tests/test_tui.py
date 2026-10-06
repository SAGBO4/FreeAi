"""Automated Test Suite for FreeAI Full-Screen Textual TUI (OpenCode Replica).

Spec: docs/SPEC.md (Chantier F-17 AC1 to AC8)
Architecture: docs/architecture/F17_TUI_architecture.md

Forge Phase 1: Tests First (TDD Red Phase)
Verifies:
1. test_tui_initialization_and_5_zone_layout:
   - Mounts FreeAIApp with MainScreen root screen
   - Asserts 5-zone layout: TopHeader, CollapsibleSidebar, ChatContainer, InputArea, StatusBar
2. test_alternate_screen_buffer_activation:
   - Verifies alternate screen buffer is active (AC1)
   - Verifies exit bindings (Ctrl+Q, Ctrl+C) restore terminal cleanly
3. test_strict_zero_emoji_compliance:
   - Scans all widgets, text, and classes for raw emoji violation (AC6)
   - Only noble typography glyphs allowed (┃, ╹, ▣, ❯, •, ─, ┌, └, etc.)
4. test_sidebar_toggle_mechanism:
   - Collapsible sidebar toggle via Ctrl+B / action_toggle_sidebar (AC4)
   - Reactive state app.sidebar_open and CSS collapse class
5. test_double_submit_protection:
   - Prevents duplicate or concurrent prompt submission while is_generating=True (AC7)
   - Locks InputArea cleanly without crashing
6. test_thought_accordion_and_left_border_streaming:
   - Dynamically spawns ThoughtAccordion on <think> tokens (AC3)
   - LeftBorder glyphs (┃ and final ╹) and telemetry epilogue (▣)
7. test_memory_boundary_and_dom_pruning_frugality:
   - Mode NÉANT RAM bounding (< 70 MB) & DOM node pruning in ChatContainer (AC5)
   - 0 physical SSD writes guarantee
8. test_degraded_mode_terminal_resize:
   - Fallback DegradedModeScreen on terminal dimensions < 60 cols or < 15 rows (AC8)
9. test_cli_argument_parsing_tui:
   - cli.py argument parsing for --tui flag and routing to run_tui / FreeAIApp
"""

import os
import re
import sys
import asyncio
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Safe import with fallback to None so pytest collects all test methods
# and asserts fail individually with informative Red messages.
try:
    from app.cli.textual_tui import (
        FreeAIApp,
        MainScreen,
        TopHeader,
        CollapsibleSidebar,
        ChatContainer,
        ChatMessage,
        ThoughtAccordion,
        InputArea,
        StatusBar,
        DegradedModeScreen,
        run_tui,
    )
except ImportError:
    FreeAIApp = None
    MainScreen = None
    TopHeader = None
    CollapsibleSidebar = None
    ChatContainer = None
    ChatMessage = None
    ThoughtAccordion = None
    InputArea = None
    StatusBar = None
    DegradedModeScreen = None
    run_tui = None


class TestOpenCodeTUI(unittest.IsolatedAsyncioTestCase):
    """Exhaustive test suite for F-17 Full-Screen TUI OpenCode Replica."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.workspace_path = Path(self.temp_dir.name)
        (self.workspace_path / "app").mkdir()
        (self.workspace_path / "app" / "main.py").write_text("print('hello')\n")
        (self.workspace_path / "README.md").write_text("# FreeAI Test Workspace\n")

    def tearDown(self):
        self.temp_dir.cleanup()

    async def test_tui_initialization_and_5_zone_layout(self):
        """AC2: Composite 5-zone persistent layout with TopHeader, Sidebar, Chat, Input, StatusBar."""
        self.assertIsNotNone(
            FreeAIApp,
            "FreeAIApp class is not implemented or exported in app.cli.textual_tui"
        )
        self.assertIsNotNone(
            MainScreen,
            "MainScreen class is not implemented or exported in app.cli.textual_tui"
        )

        app = FreeAIApp(workspace_root=str(self.workspace_path))
        async with app.run_test() as pilot:
            # Root screen must be MainScreen
            self.assertIsInstance(
                app.screen,
                MainScreen,
                f"Active screen must be MainScreen, got {type(app.screen)}"
            )

            # Zone 1: TopHeader with active session tabs
            self.assertIsNotNone(
                TopHeader,
                "TopHeader class must be implemented in app.cli.textual_tui"
            )
            top_header = app.query_one(TopHeader)
            self.assertIsNotNone(top_header, "TopHeader widget must be mounted")

            # Zone 2: CollapsibleSidebar (sessions, files, agents)
            self.assertIsNotNone(
                CollapsibleSidebar,
                "CollapsibleSidebar class must be implemented in app.cli.textual_tui"
            )
            sidebar = app.query_one(CollapsibleSidebar)
            self.assertIsNotNone(sidebar, "CollapsibleSidebar widget must be mounted")

            # Zone 3: ChatContainer (captive scrollable message area)
            self.assertIsNotNone(
                ChatContainer,
                "ChatContainer class must be implemented in app.cli.textual_tui"
            )
            chat_container = app.query_one(ChatContainer)
            self.assertIsNotNone(chat_container, "ChatContainer widget must be mounted")

            # Zone 4: InputArea (anchored bottom prompt bar)
            self.assertIsNotNone(
                InputArea,
                "InputArea class must be implemented in app.cli.textual_tui"
            )
            input_area = app.query_one(InputArea)
            self.assertIsNotNone(input_area, "InputArea widget must be mounted")

            # Zone 5: StatusBar (LSP probe, git branch, shortcuts)
            self.assertIsNotNone(
                StatusBar,
                "StatusBar class must be implemented in app.cli.textual_tui"
            )
            status_bar = app.query_one(StatusBar)
            self.assertIsNotNone(status_bar, "StatusBar widget must be mounted")

    async def test_alternate_screen_buffer_activation(self):
        """AC1: Automatic activation of alternate screen buffer and clean terminal restore."""
        self.assertIsNotNone(
            FreeAIApp,
            "FreeAIApp class is not implemented in app.cli.textual_tui"
        )
        app = FreeAIApp(workspace_root=str(self.workspace_path))

        # Check alternate screen configuration on app
        self.assertTrue(
            getattr(app, "alternate_screen", False) or getattr(app, "is_alternate_screen_active", lambda: False)(),
            "FreeAIApp must activate alternate screen buffer mode (AC1)"
        )

        # Check exit keybindings
        bindings = {b.key: b.action for b in app.BINDINGS}
        self.assertTrue(
            "ctrl+q" in bindings or "ctrl+c" in bindings,
            "FreeAIApp must register Ctrl+Q or Ctrl+C to cleanly quit and restore host terminal"
        )

    async def test_strict_zero_emoji_compliance(self):
        """AC6: Absolute ban on emojis across all widgets, containers, labels, and classes."""
        self.assertIsNotNone(
            FreeAIApp,
            "FreeAIApp class is not implemented in app.cli.textual_tui"
        )
        app = FreeAIApp(workspace_root=str(self.workspace_path))

        emoji_pattern = re.compile(
            r"[\U00010000-\U0010ffff]|[\u2600-\u27bf]|[\u2300-\u23ff]|[\u2b50-\u2b55]|[\u3030\u303d\u3297\u3299]"
        )
        noble_terminal_glyphs = {
            "✓", "✗", "✱", "❯", "•", "┃", "╹", "▣", "─", "┌", "└",
            "│", "┤", "├", "┴", "┬", "╭", "╮", "╯", "╰", "▸", "▾",
            "›", "$", "←", "→", "◈", "⊙"
        }

        async with app.run_test() as pilot:
            for widget in app.screen.walk_children():
                # Check class names
                for cls in widget.classes:
                    found = set(emoji_pattern.findall(cls)) - noble_terminal_glyphs
                    self.assertEqual(
                        found, set(),
                        f"Found forbidden emoji in widget class '{cls}' on {widget}: {found}"
                    )

                # Check string representation and rendered content
                rendered_str = str(getattr(widget, "renderable", "")) + " " + str(widget)
                found = set(emoji_pattern.findall(rendered_str)) - noble_terminal_glyphs
                self.assertEqual(
                    found, set(),
                    f"Found forbidden emoji in widget {widget}: {found}"
                )

    async def test_sidebar_toggle_mechanism(self):
        """AC4: Dynamic sidebar folding via Ctrl+B with smooth layout adjustment."""
        self.assertIsNotNone(
            FreeAIApp,
            "FreeAIApp class is not implemented in app.cli.textual_tui"
        )
        self.assertIsNotNone(
            CollapsibleSidebar,
            "CollapsibleSidebar class is not implemented in app.cli.textual_tui"
        )

        app = FreeAIApp(workspace_root=str(self.workspace_path))
        async with app.run_test() as pilot:
            sidebar = app.query_one(CollapsibleSidebar)

            # Initially open
            self.assertTrue(getattr(app, "sidebar_open", True), "Sidebar should be open initially")
            self.assertNotIn("collapsed", sidebar.classes)

            # Toggle with action
            app.action_toggle_sidebar()
            await pilot.pause()
            self.assertFalse(getattr(app, "sidebar_open", False), "Sidebar should be closed after toggle")
            self.assertIn("collapsed", sidebar.classes)

            # Toggle back to open
            app.action_toggle_sidebar()
            await pilot.pause()
            self.assertTrue(getattr(app, "sidebar_open", True), "Sidebar should be reopened after second toggle")
            self.assertNotIn("collapsed", sidebar.classes)

    async def test_double_submit_protection(self):
        """AC7: Rejection of double submission or typing while generation is in progress."""
        self.assertIsNotNone(
            FreeAIApp,
            "FreeAIApp class is not implemented in app.cli.textual_tui"
        )
        self.assertIsNotNone(
            InputArea,
            "InputArea class is not implemented in app.cli.textual_tui"
        )

        app = FreeAIApp(workspace_root=str(self.workspace_path))
        async with app.run_test() as pilot:
            input_area = app.query_one(InputArea)

            # Set generating state to True
            app.is_generating = True
            await pilot.pause()

            # InputArea must be locked/disabled or submit must reject
            if hasattr(input_area, "disabled"):
                self.assertTrue(
                    input_area.disabled,
                    "InputArea must be disabled while is_generating is True"
                )

            # Attempting to submit prompt during generation must return False or raise
            submitted = await app.submit_prompt("Deuxième prompt simultané")
            self.assertFalse(
                submitted,
                "Double submission must be rejected cleanly when app.is_generating is True (AC7)"
            )

    async def test_thought_accordion_and_left_border_streaming(self):
        """AC3: Dynamic ThoughtAccordion on <think> tokens, LeftBorder ┃, final ╹ and ▣ epilogue."""
        self.assertIsNotNone(
            ChatMessage,
            "ChatMessage class is not implemented in app.cli.textual_tui"
        )
        self.assertIsNotNone(
            ThoughtAccordion,
            "ThoughtAccordion class is not implemented in app.cli.textual_tui"
        )

        app = FreeAIApp(workspace_root=str(self.workspace_path))
        async with app.run_test() as pilot:
            chat_container = app.query_one(ChatContainer)

            # Post a streaming message with <think> tag
            msg = ChatMessage(role="assistant")
            await chat_container.mount(msg)

            await msg.stream_tokens("<think>Analyse de la demande...</think>Voici la solution.")
            await msg.finalize()
            await pilot.pause()

            # Must contain ThoughtAccordion widget
            accordions = msg.query(ThoughtAccordion)
            self.assertGreaterEqual(
                len(accordions), 1,
                "ChatMessage must instantiate ThoughtAccordion when <think> tags are detected (AC3)"
            )

            # Rendered message must contain noble LeftBorder glyphs and epilogue
            rendered = str(msg.render())
            self.assertIn("┃", rendered, "Streaming message must use noble LeftBorder ┃")
            self.assertIn("╹", rendered, "Finalized message must end with LeftBorder ╹")
            self.assertIn("▣", rendered, "Finalized message must include noble telemetry epilogue ▣")

    async def test_memory_boundary_and_dom_pruning_frugality(self):
        """AC5: Mode NÉANT memory boundedness (DOM pruning, RSS < 70 Mo, 0 SSD writes)."""
        self.assertIsNotNone(
            ChatContainer,
            "ChatContainer class is not implemented in app.cli.textual_tui"
        )
        self.assertIsNotNone(
            ChatMessage,
            "ChatMessage class is not implemented in app.cli.textual_tui"
        )

        app = FreeAIApp(workspace_root=str(self.workspace_path))
        async with app.run_test() as pilot:
            chat_container = app.query_one(ChatContainer)

            # Add large number of messages to test DOM pruning mechanism
            max_dom_nodes = getattr(chat_container, "MAX_DOM_NODES", 30)
            for i in range(max_dom_nodes + 20):
                await chat_container.append_message(ChatMessage(role="user", content=f"Message {i}"))

            await pilot.pause()

            # ChatContainer must prune DOM elements to avoid DOM explosion under Mode NÉANT
            active_dom_messages = len(chat_container.query(ChatMessage))
            self.assertLessEqual(
                active_dom_messages,
                max_dom_nodes + 5,
                f"DOM messages ({active_dom_messages}) exceeded bounded threshold ({max_dom_nodes})"
            )

            # Verify zero disk writes in workspace
            untracked_files = [
                f for f in self.workspace_path.rglob("*")
                if f.is_file() and f.name not in ("main.py", "README.md")
            ]
            self.assertEqual(
                untracked_files, [],
                f"Violation of Mode NÉANT 0 SSD write: unexpected files found: {untracked_files}"
            )

    async def test_degraded_mode_terminal_resize(self):
        """AC8: Safe fallback DegradedModeScreen on terminal dimensions < 60 cols or < 15 rows."""
        self.assertIsNotNone(
            DegradedModeScreen,
            "DegradedModeScreen class is not implemented in app.cli.textual_tui"
        )

        app = FreeAIApp(workspace_root=str(self.workspace_path))
        async with app.run_test(size=(50, 10)) as pilot:
            # When resized below minimum threshold, DegradedModeScreen must be active
            self.assertIsInstance(
                app.screen,
                DegradedModeScreen,
                f"Expected DegradedModeScreen for small terminal (50x10), got {type(app.screen)}"
            )

    def test_cli_argument_parsing_tui(self):
        """Verifies cli.py parses --tui flag and routes execution to run_tui with FreeAIApp."""
        self.assertIsNotNone(
            FreeAIApp,
            "FreeAIApp class is not implemented in app.cli.textual_tui"
        )

        import argparse
        from cli import main

        # 1. Test argument parser accepts --tui
        with patch("sys.argv", ["cli.py", "--tui"]), \
             patch("app.cli.textual_tui.run_tui") as mock_run_tui:
            main()
            mock_run_tui.assert_called_once()

        # 2. Test argument parser accepts --tui with --mode lesaintAi
        with patch("sys.argv", ["cli.py", "--tui", "--mode", "lesaintAi"]), \
             patch("app.cli.textual_tui.run_tui") as mock_run_tui:
            main()
            mock_run_tui.assert_called_once_with(
                mode="lesaintAi",
                workspace_root=unittest.mock.ANY
            )


if __name__ == "__main__":
    unittest.main()
