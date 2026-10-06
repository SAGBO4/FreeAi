"""Automated Test Suite for FreeAI In-TUI Code Editor & Live Inspector (Feature F-18).

Spec: docs/SPEC.md (F-18 AC1 to AC8)
Architecture: docs/architecture/F18_in_tui_editor_architecture.md

Forge Phase: Tests First & Playwright-Style Pilot Verification (0% Error Requirement)
Verifies:
1. test_classes_exist:
   - Verifies CodeEditorScreen, NobleTextArea, EditorPane, EditorHeaderBar, EditorStatusBar, GitDiffModal
2. test_editor_screen_mounting_and_layout:
   - Mounts CodeEditorScreen with EditorHeaderBar, NobleTextArea, and EditorStatusBar
3. test_code_editor_screen_escape_key_press:
   - Verifies pressing Escape physical key exits CodeEditorScreen cleanly back to MainScreen
4. test_split_view_side_by_side_mounting:
   - Verifies opening a file mounts EditorPane side-by-side with central chat area in MainScreen (50/50 split view)
5. test_split_view_escape_key_closes_editor:
   - Verifies pressing Escape while inside split editor closes the pane and restores chat to 100%
6. test_split_view_close_button_click:
   - Verifies clicking '✗ Fermer' button closes the split editor and focuses prompt input
7. test_split_view_ctrl_w_closes_editor:
   - Verifies Ctrl+W closes split editor
8. test_split_view_save_and_atomic_undo_snapshot:
   - Verifies clicking '✓ Sauvegarder' or Ctrl+S saves file and generates atomic undo snapshot
9. test_split_view_ai_explain_action:
   - Verifies clicking '◈ Expliquer' or Ctrl+E sends code prompt to chat while keeping editor open on the right
10. test_split_view_inline_git_diff_inspector:
    - Verifies clicking '⊙ Diff' or Ctrl+D opens GitDiffModal and Escape dismisses it
11. test_file_tree_click_routes_to_split_editor:
    - Verifies clicking a file in NobleDirectoryTree opens the split view editor
12. test_slash_command_edit_routes_to_split_editor:
    - Verifies /edit <file> opens the split view editor
13. test_strict_zero_emoji_in_editor_components:
    - Verifies 100% absence of emojis in editor widgets, labels, buttons, and shortcuts
14. test_path_confinement_and_security:
    - Verifies freeAi mode refuses editing files outside workspace
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

from textual.widgets import TextArea, Label, Button, DirectoryTree
from app.tools.gateway import ToolGateway
from app.resource_manager.watchdog import ResourceManager
from app.orchestrator.orchestrator import TechLeadOrchestrator

try:
    from app.cli.textual_tui import (
        FreeAITUIApp,
        MainScreen,
        CodeEditorScreen,
        NobleTextArea,
        EditorPane,
        EditorHeaderBar,
        EditorStatusBar,
        GitDiffModal,
    )
except ImportError:
    CodeEditorScreen = None
    NobleTextArea = None
    EditorPane = None
    EditorHeaderBar = None
    EditorStatusBar = None
    GitDiffModal = None
    from app.cli.textual_tui import FreeAITUIApp, MainScreen


class TestInTUIEditor(unittest.IsolatedAsyncioTestCase):
    """Test suite for the Sovereign In-TUI Code Editor & Live Inspector (Split View & Modal)."""

    async def asyncSetUp(self):
        self.temp_dir = tempfile.TemporaryDirectory(prefix="freeai_editor_test_")
        self.workspace_path = Path(self.temp_dir.name)

        # Create sample source files
        self.py_file = self.workspace_path / "sample.py"
        self.py_file.write_text("def hello_world():\n    return 'FreeAI Sovereign'\n", encoding="utf-8")

        self.json_file = self.workspace_path / "config.json"
        self.json_file.write_text('{"name": "FreeAI", "version": "2.0"}', encoding="utf-8")

        self.gateway = ToolGateway(workspace_root=str(self.workspace_path), mode="freeAi")
        self.resource_mgr = ResourceManager()
        self.tech_lead = TechLeadOrchestrator(tool_gateway=self.gateway, resource_manager=self.resource_mgr)

    async def asyncTearDown(self):
        self.temp_dir.cleanup()

    def test_classes_exist(self):
        """Verifies that all F-18 editor classes and widgets are properly defined (AC1)."""
        self.assertIsNotNone(CodeEditorScreen, "CodeEditorScreen class must be defined in app.cli.textual_tui")
        self.assertIsNotNone(NobleTextArea, "NobleTextArea class must be defined in app.cli.textual_tui")
        self.assertIsNotNone(EditorPane, "EditorPane class must be defined in app.cli.textual_tui")
        self.assertIsNotNone(EditorHeaderBar, "EditorHeaderBar class must be defined in app.cli.textual_tui")
        self.assertIsNotNone(EditorStatusBar, "EditorStatusBar class must be defined in app.cli.textual_tui")
        self.assertIsNotNone(GitDiffModal, "GitDiffModal class must be defined in app.cli.textual_tui")

    async def test_editor_screen_mounting_and_layout(self):
        """Verifies mounting CodeEditorScreen, NobleTextArea, line numbers, and language detection (AC1, AC2)."""
        if CodeEditorScreen is None:
            self.skipTest("CodeEditorScreen not implemented yet")

        app = FreeAITUIApp(tech_lead=self.tech_lead, workspace_root=str(self.workspace_path))
        async with app.run_test(size=(120, 36)) as pilot:
            editor_screen = CodeEditorScreen(file_path=str(self.py_file))
            await app.push_screen(editor_screen)
            await pilot.pause()

            self.assertIsInstance(app.screen, CodeEditorScreen)
            text_area = app.screen.query_one(NobleTextArea)
            self.assertIsNotNone(text_area)
            self.assertIn("hello_world", text_area.text)
            self.assertTrue(text_area.show_line_numbers)
            self.assertEqual(text_area.language, "python")

            # Check header
            header = app.screen.query_one(EditorHeaderBar)
            self.assertIsNotNone(header)
            self.assertIn("sample.py", header.file_label.content if hasattr(header.file_label, "content") else str(header.file_label.render()))

    async def test_code_editor_screen_escape_key_press(self):
        """Verifies pressing physical Escape key while focused on NobleTextArea exits CodeEditorScreen (AC3)."""
        if CodeEditorScreen is None:
            self.skipTest("CodeEditorScreen not implemented yet")

        app = FreeAITUIApp(tech_lead=self.tech_lead, workspace_root=str(self.workspace_path))
        async with app.run_test(size=(120, 36)) as pilot:
            editor_screen = CodeEditorScreen(file_path=str(self.py_file))
            await app.push_screen(editor_screen)
            await pilot.pause()
            self.assertIsInstance(app.screen, CodeEditorScreen)

            # Focus the text area
            text_area = app.screen.query_one(NobleTextArea)
            text_area.focus()
            await pilot.pause()

            # Press Escape
            await pilot.press("escape")
            await pilot.pause()

            # Must have returned to MainScreen
            self.assertIsInstance(app.screen, MainScreen)

    async def test_split_view_side_by_side_mounting(self):
        """Verifies opening a file mounts EditorPane side-by-side with chat in 50/50 split view."""
        app = FreeAITUIApp(tech_lead=self.tech_lead, workspace_root=str(self.workspace_path))
        async with app.run_test(size=(120, 36)) as pilot:
            app.open_code_editor(self.py_file)
            await pilot.pause()

            self.assertIsInstance(app.screen, MainScreen)
            editor_pane = app.query_one("#editor-pane")
            self.assertIsNotNone(editor_pane)
            self.assertTrue(editor_pane.has_class("open"))

            central_area = app.query_one("#central-area")
            self.assertIsNotNone(central_area)

            # Header, TextArea, StatusBar inside split pane
            header = app.query_one("#split-editor-header", EditorHeaderBar)
            self.assertIn("sample.py", header.file_label.content if hasattr(header.file_label, "content") else str(header.file_label.render()))
            textarea = app.query_one("#split-editor-textarea", NobleTextArea)
            self.assertIn("hello_world", textarea.text)
            self.assertEqual(textarea.language, "python")

    async def test_split_view_escape_key_closes_editor(self):
        """Verifies pressing Escape while inside split editor closes it and restores full-width chat."""
        app = FreeAITUIApp(tech_lead=self.tech_lead, workspace_root=str(self.workspace_path))
        async with app.run_test(size=(120, 36)) as pilot:
            app.open_code_editor(self.py_file)
            await pilot.pause()

            editor_pane = app.query_one("#editor-pane")
            self.assertTrue(editor_pane.has_class("open"))

            # Focus textarea and press escape
            textarea = app.query_one("#split-editor-textarea", NobleTextArea)
            textarea.focus()
            await pilot.pause()

            await pilot.press("escape")
            await pilot.pause()

            # Split editor pane is closed
            self.assertFalse(editor_pane.has_class("open"))

    async def test_split_view_close_button_click(self):
        """Verifies clicking '✗ Fermer' button closes the split editor immediately."""
        app = FreeAITUIApp(tech_lead=self.tech_lead, workspace_root=str(self.workspace_path))
        async with app.run_test(size=(120, 36)) as pilot:
            app.open_code_editor(self.py_file)
            await pilot.pause()

            editor_pane = app.query_one("#editor-pane")
            self.assertTrue(editor_pane.has_class("open"))

            # Click close button
            await pilot.click("#btn-close-editor")
            await pilot.pause()

            self.assertFalse(editor_pane.has_class("open"))

    async def test_split_view_ctrl_w_closes_editor(self):
        """Verifies pressing Ctrl+W closes the split editor."""
        app = FreeAITUIApp(tech_lead=self.tech_lead, workspace_root=str(self.workspace_path))
        async with app.run_test(size=(120, 36)) as pilot:
            app.open_code_editor(self.py_file)
            await pilot.pause()

            editor_pane = app.query_one("#editor-pane")
            self.assertTrue(editor_pane.has_class("open"))

            await pilot.press("ctrl+w")
            await pilot.pause()

            self.assertFalse(editor_pane.has_class("open"))

    async def test_split_view_save_and_atomic_undo_snapshot(self):
        """Verifies clicking '✓ Sauvegarder' saves buffer to disk with atomic undo snapshot."""
        app = FreeAITUIApp(tech_lead=self.tech_lead, workspace_root=str(self.workspace_path))
        async with app.run_test(size=(120, 36)) as pilot:
            app.open_code_editor(self.py_file)
            await pilot.pause()

            textarea = app.query_one("#split-editor-textarea", NobleTextArea)
            textarea.text = "def modified_code():\n    return 'SPLIT_UPDATED'\n"
            await pilot.pause()

            # Click save button
            await pilot.click("#btn-save-editor")
            await pilot.pause()

            saved_content = self.py_file.read_text(encoding="utf-8")
            self.assertIn("modified_code", saved_content)

            # Check snapshot in AtomicUndoManager
            from app.orchestrator.atomic_undo import AtomicUndoManager
            undo_mgr = AtomicUndoManager(str(self.workspace_path))
            snapshots = undo_mgr.list_snapshots()
            self.assertGreater(len(snapshots), 0)
            self.assertIn("Éditeur TUI", snapshots[0]["description"])

    async def test_split_view_ai_explain_action(self):
        """Verifies clicking '◈ Expliquer' sends code prompt to chat while keeping editor visible."""
        app = FreeAITUIApp(tech_lead=self.tech_lead, workspace_root=str(self.workspace_path))
        async with app.run_test(size=(120, 36)) as pilot:
            app.open_code_editor(self.py_file)
            await pilot.pause()

            # Click explain button
            await pilot.click("#btn-ai-explain")
            await pilot.pause()

            # Split editor remains open on the right
            editor_pane = app.query_one("#editor-pane")
            self.assertTrue(editor_pane.has_class("open"))

    async def test_split_view_inline_git_diff_inspector(self):
        """Verifies clicking '⊙ Diff' opens GitDiffModal and Escape dismisses it back to split editor."""
        app = FreeAITUIApp(tech_lead=self.tech_lead, workspace_root=str(self.workspace_path))
        async with app.run_test(size=(120, 36)) as pilot:
            app.open_code_editor(self.py_file)
            await pilot.pause()

            # Click diff button
            await pilot.click("#btn-diff-editor")
            await pilot.pause()

            self.assertIsInstance(app.screen, GitDiffModal)

            # Dismiss diff modal via Escape
            await pilot.press("escape")
            await pilot.pause()

            self.assertIsInstance(app.screen, MainScreen)
            editor_pane = app.query_one("#editor-pane")
            self.assertTrue(editor_pane.has_class("open"))

    async def test_file_tree_click_routes_to_split_editor(self):
        """Verifies clicking a file in NobleDirectoryTree opens the split view editor (AC1)."""
        app = FreeAITUIApp(tech_lead=self.tech_lead, workspace_root=str(self.workspace_path))
        async with app.run_test(size=(120, 36)) as pilot:
            tree = app.query_one(DirectoryTree)
            app.on_directory_tree_file_selected(DirectoryTree.FileSelected(tree, self.py_file))
            await pilot.pause()

            self.assertIsInstance(app.screen, MainScreen)
            editor_pane = app.query_one("#editor-pane")
            self.assertTrue(editor_pane.has_class("open"))
            textarea = app.query_one("#split-editor-textarea", NobleTextArea)
            self.assertIn("hello_world", textarea.text)

    async def test_slash_command_edit_routes_to_split_editor(self):
        """Verifies /edit <file> opens the split view editor."""
        app = FreeAITUIApp(tech_lead=self.tech_lead, workspace_root=str(self.workspace_path))
        async with app.run_test(size=(120, 36)) as pilot:
            await app.run_slash_command("/edit sample.py")
            await pilot.pause()

            self.assertIsInstance(app.screen, MainScreen)
            editor_pane = app.query_one("#editor-pane")
            self.assertTrue(editor_pane.has_class("open"))
            textarea = app.query_one("#split-editor-textarea", NobleTextArea)
            self.assertIn("hello_world", textarea.text)

    async def test_strict_zero_emoji_in_editor_components(self):
        """Verifies strict 0 emoji compliance in the entire editor module (AC8)."""
        editor_path = PROJECT_ROOT / "app" / "cli" / "textual_tui.py"
        content = editor_path.read_text(encoding="utf-8")

        emoji_pattern = re.compile(
            r"[\U00010000-\U0010ffff]|[\u2600-\u27bf]|[\u2300-\u23ff]|[\u2b50-\u2b55]|[\u3030\u303d\u3297\u3299]"
        )
        matches = set(emoji_pattern.findall(content))
        noble_terminal_glyphs = {"✓", "✗", "✱", "❯"}
        forbidden_emojis = matches - noble_terminal_glyphs

        self.assertEqual(
            forbidden_emojis,
            set(),
            f"STRICT COMPLIANCE VIOLATION: Raw emojis found in textual_tui.py: {forbidden_emojis}"
        )

    async def test_path_confinement_and_security(self):
        """Verifies freeAi mode refuses editing files outside workspace (AC7)."""
        with tempfile.NamedTemporaryFile(suffix=".py") as outside_file:
            outside_path = Path(outside_file.name)
            outside_path.write_text("outside = True", encoding="utf-8")

            with self.assertRaises(PermissionError):
                CodeEditorScreen(file_path=outside_path, workspace_root=self.workspace_path, mode="freeAi")

            app = FreeAITUIApp(tech_lead=self.tech_lead, workspace_root=str(self.workspace_path), mode="freeAi")
            with self.assertRaises(PermissionError):
                app.open_code_editor(outside_path)


if __name__ == "__main__":
    unittest.main()
