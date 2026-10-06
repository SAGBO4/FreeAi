"""Automated Test Suite for FreeAI Full-Screen Textual TUI (OpenCode Replica).

Verifies:
1. Headless instantiation and mounting of all core widgets:
   - Header (top bar with dynamic session tabs, badges)
   - Sidebar (sessions, NobleDirectoryTree, agent selector, resource gauge)
   - ChatPane (VerticalScroll, welcome card, dynamic cards)
   - InputBar (prompt input, OpenCode styling, metadata row)
   - StatusBar (workspace:branch, LSP probe, Neon sync, Sentinel status)
2. Absolute absence of raw emoji in textual_tui.py, CSS, and rendered widgets.
3. Collapsible sidebar (Ctrl+B) and dynamic session tabs (Ctrl+N, + New session).
4. Command Palette integration (Ctrl+P) with zero emoji search icon.
5. Agent selector and slash command execution (/help, /status, /lsp, /mode, /agent).
6. Complete end-to-end integration and compatibility with TechLeadOrchestrator:
   - UserMessageCard
   - Retractable ThoughtCard (+ Thought: ... · duration)
   - ToolExecutionCard with authentic OpenCode glyphs ($, ←, →, ✱, ◈, ⊙, ✓, ✗)
   - AssistantMessageCard (StreamingLeftBorder & LeftBorderFinal)
   - TelemetryEpilogueCard (▣ agent · model · duration · tok/s)
"""

import os
import re
import sys
import asyncio
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from textual.command import CommandPalette, SearchIcon
from textual.widgets import DirectoryTree, Input, Label, Static, Button, Collapsible

from app.cli.textual_tui import (
    FreeAITUIApp,
    NobleDirectoryTree,
    UserMessageCard,
    ThoughtCard,
    ToolExecutionCard,
    AssistantMessageCard,
    TelemetryEpilogueCard,
    ChatSession,
)
from app.tools.gateway import ToolGateway
from app.resource_manager.watchdog import ResourceManager
from app.orchestrator.orchestrator import TechLeadOrchestrator


class TestTextualTUI(unittest.IsolatedAsyncioTestCase):
    """Exhaustive test suite for FreeAI OpenCode Textual TUI."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.workspace_path = Path(self.temp_dir.name)
        # Create dummy file structure
        (self.workspace_path / "app").mkdir()
        (self.workspace_path / "app" / "core.py").write_text("def hello(): pass")
        (self.workspace_path / "README.md").write_text("# FreeAI Workspace")

        # Mock gateway & resource manager
        self.gw = ToolGateway(workspace_root=str(self.workspace_path))
        self.rm = ResourceManager()
        self.tech_lead = TechLeadOrchestrator(tool_gateway=self.gw, resource_manager=self.rm)

    def tearDown(self):
        self.temp_dir.cleanup()

    async def test_headless_instantiation_and_widget_mounting(self):
        """Verifies headless mounting of Header, Sidebar, ChatPane, InputBar, and StatusBar."""
        app = FreeAITUIApp(tech_lead=self.tech_lead, workspace_root=str(self.workspace_path))

        async with app.run_test() as pilot:
            # 1. Header widgets
            self.assertIsNotNone(app.query_one("#top-header"))
            self.assertIsNotNone(app.query_one("#brand-label"))
            self.assertIsNotNone(app.query_one("#session-tabs-bar"))
            self.assertIsNotNone(app.query_one("#tab-sess-1"))
            self.assertIsNotNone(app.query_one("#btn-new-session"))
            self.assertIsNotNone(app.query_one("#mode-badge"))
            self.assertIsNotNone(app.query_one("#model-badge"))

            # 2. Sidebar widgets
            self.assertIsNotNone(app.query_one("#sidebar"))
            self.assertIsNotNone(app.query_one("#sessions-list"))
            self.assertIsNotNone(app.query_one("#workspace-tree"))
            self.assertIsNotNone(app.query_one("#agent-options"))
            self.assertIsNotNone(app.query_one("#resource-box"))
            self.assertIsNotNone(app.query_one("#res-ram"))
            self.assertIsNotNone(app.query_one("#res-neant"))
            self.assertIsNotNone(app.query_one("#res-neon"))
            self.assertIsNotNone(app.query_one("#res-sentinel"))

            # 3. Central ChatPane widgets
            self.assertIsNotNone(app.query_one("#central-area"))
            self.assertIsNotNone(app.query_one("#chat-scroll"))
            self.assertIsNotNone(app.query_one("#welcome-msg"))

            # 4. PromptBar widgets
            self.assertIsNotNone(app.query_one("#prompt-container"))
            self.assertIsNotNone(app.query_one("#prompt-input-row"))
            self.assertIsNotNone(app.query_one("#prompt-prefix"))
            self.assertIsNotNone(app.query_one("#prompt-input"))
            self.assertIsNotNone(app.query_one("#prompt-meta-row"))
            self.assertIsNotNone(app.query_one("#prompt-meta-left"))
            self.assertIsNotNone(app.query_one("#prompt-meta-right"))

            # 5. StatusBar widgets
            self.assertIsNotNone(app.query_one("#status-bar"))
            self.assertIsNotNone(app.query_one("#status-left"))
            self.assertIsNotNone(app.query_one("#status-right"))

    def test_strict_zero_raw_emoji_compliance(self):
        """Strictly verifies ZERO raw emojis in textual_tui.py source and CSS."""
        target_file = PROJECT_ROOT / "app" / "cli" / "textual_tui.py"
        content = target_file.read_text(encoding="utf-8")

        emoji_pattern = re.compile(
            r"[\U00010000-\U0010ffff]|[\u2600-\u27bf]|[\u2300-\u23ff]|[\u2b50-\u2b55]|[\u3030\u303d\u3297\u3299]"
        )
        matches = set(emoji_pattern.findall(content))
        noble_terminal_glyphs = {"✓", "✗", "✱", "❯"}
        forbidden_emojis = matches - noble_terminal_glyphs

        self.assertEqual(
            forbidden_emojis,
            set(),
            f"STRICT COMPLIANCE VIOLATION: Found raw emojis in textual_tui.py: {forbidden_emojis}"
        )

    async def test_sidebar_toggle_action(self):
        """Verifies collapsible sidebar toggling with Ctrl+B action."""
        app = FreeAITUIApp(tech_lead=self.tech_lead, workspace_root=str(self.workspace_path))

        async with app.run_test() as pilot:
            sidebar = app.query_one("#sidebar")
            self.assertNotIn("collapsed", sidebar.classes)

            # Toggle collapse
            app.action_toggle_sidebar()
            self.assertIn("collapsed", sidebar.classes)

            # Toggle expand
            app.action_toggle_sidebar()
            self.assertNotIn("collapsed", sidebar.classes)

    async def test_dynamic_session_lifecycle(self):
        """Verifies dynamic session creation (+ New session / Ctrl+N) and switching."""
        app = FreeAITUIApp(tech_lead=self.tech_lead, workspace_root=str(self.workspace_path))

        async with app.run_test() as pilot:
            self.assertEqual(app.current_session_id, "1")
            self.assertIn("1", app.sessions)

            # Create new session
            await app.action_new_session()
            self.assertEqual(app.current_session_id, "2")
            self.assertIn("2", app.sessions)
            self.assertIsNotNone(app.query_one("#tab-sess-2"))

            # Switch back to session 1
            await app.switch_session("1")
            self.assertEqual(app.current_session_id, "1")

            # Verify active class on session tab 1
            tab1 = app.query_one("#tab-sess-1", Button)
            self.assertIn("active", tab1.classes)

    async def test_command_palette_ctrl_p_and_zero_emoji_icon(self):
        """Verifies Command Palette activation via Ctrl+P and SearchIcon noble glyph."""
        app = FreeAITUIApp(tech_lead=self.tech_lead, workspace_root=str(self.workspace_path))

        async with app.run_test() as pilot:
            await pilot.press("ctrl+p")
            await pilot.pause()

            # Confirm CommandPalette screen is mounted
            self.assertIsInstance(app.screen, CommandPalette)

            # Confirm SearchIcon does NOT contain raw emoji
            icon_widget = app.screen.query_one(SearchIcon)
            rendered_icon = str(icon_widget.render())
            self.assertNotIn("🔎", rendered_icon)
            self.assertIn("›", rendered_icon)

            # Close palette with Escape
            await pilot.press("escape")
            await pilot.pause()
            self.assertNotIsInstance(app.screen, CommandPalette)

    async def test_agent_selector_and_options(self):
        """Verifies agent selector in the sidebar updates active agent and session."""
        app = FreeAITUIApp(tech_lead=self.tech_lead, workspace_root=str(self.workspace_path))

        async with app.run_test() as pilot:
            self.assertEqual(app.active_agent, "Tech Lead")

            # Switch to Code agent
            app.set_active_agent("Code")
            self.assertEqual(app.active_agent, "Code")
            self.assertEqual(app.sessions[app.current_session_id].agent, "Code")

            # Switch to Security agent
            app.set_active_agent("Security")
            self.assertEqual(app.active_agent, "Security")

    async def test_slash_commands_in_chat(self):
        """Verifies slash commands execution inside TUI chat panel."""
        app = FreeAITUIApp(tech_lead=self.tech_lead, workspace_root=str(self.workspace_path))

        async with app.run_test() as pilot:
            # 1. /help
            await app.run_slash_command("/help")
            asst_cards = app.query(AssistantMessageCard)
            self.assertGreater(len(asst_cards), 0)
            self.assertIn("Arsenal des Commandes", asst_cards.last().raw_text)

            # 2. /status
            await app.run_slash_command("/status")
            self.assertIn("Télémétrie Système Souveraine", app.query(AssistantMessageCard).last().raw_text)

            # 3. /lsp
            await app.run_slash_command("/lsp")
            self.assertIn("Sonde LSP active", app.query(AssistantMessageCard).last().raw_text)

            # 4. /mode lesaintAi
            await app.run_slash_command("/mode lesaintAi")
            self.assertEqual(app.mode, "lesaintAi")

            # 5. /clear
            await app.action_clear_chat()
            self.assertEqual(len(app.query(AssistantMessageCard)), 0)

    async def test_tech_lead_orchestrator_integration(self):
        """Verifies full execution lifecycle with TechLeadOrchestrator and OpenCode glyph cards."""
        app = FreeAITUIApp(tech_lead=self.tech_lead, workspace_root=str(self.workspace_path))

        async with app.run_test() as pilot:
            mock_result = {
                "success": True,
                "assigned_agent": "Code",
                "plan": [
                    "1. Analyser le code source",
                    "2. Écrire le module sovereign_bridge.py",
                    "3. Valider avec Sentinel",
                ],
                "result": {
                    "message": "Synthèse de code réussie avec 100% de conformité.",
                    "commands": ["pytest tests/test_bridge.py -v"],
                    "files_written": ["app/sovereign_bridge.py"],
                    "files": ["app/core.py"],
                    "findings": ["def hello():"],
                },
                "external_resourcing_used": True,
                "neon_cloud_sync": True,
                "model": "groq/llama-3.3-70b-versatile",
            }

            with patch.object(self.tech_lead, "handle_objective", new_callable=AsyncMock) as mock_handle:
                mock_handle.return_value = mock_result

                await app.process_user_objective("Implémenter sovereign_bridge.py")

                # Verify UserMessageCard
                user_cards = app.query(UserMessageCard)
                self.assertEqual(len(user_cards), 1)
                self.assertEqual(user_cards.first().prompt, "Implémenter sovereign_bridge.py")

                # Verify ThoughtCard
                thought_cards = app.query(ThoughtCard)
                self.assertEqual(len(thought_cards), 1)
                self.assertIn("Thought:", thought_cards.first().title)
                self.assertEqual(len(thought_cards.first().steps), 3)

                # Verify ToolExecutionCard with noble glyphs
                tool_cards = app.query(ToolExecutionCard)
                self.assertEqual(len(tool_cards), 1)
                tool_card = tool_cards.first()
                rendered_tools = str(tool_card.render())
                self.assertIn("$", rendered_tools)
                self.assertIn("←", rendered_tools)
                self.assertIn("→", rendered_tools)
                self.assertIn("✱", rendered_tools)
                self.assertIn("◈", rendered_tools)
                self.assertIn("⊙", rendered_tools)
                self.assertIn("✓", rendered_tools)

                # Verify AssistantMessageCard
                asst_cards = app.query(AssistantMessageCard)
                self.assertEqual(len(asst_cards), 1)
                self.assertIn("Synthèse de code réussie", asst_cards.first().raw_text)

                # Verify TelemetryEpilogueCard
                telemetry_cards = app.query(TelemetryEpilogueCard)
                self.assertEqual(len(telemetry_cards), 1)
                t_card = telemetry_cards.first()
                self.assertEqual(t_card.agent, "Code")
                self.assertEqual(t_card.model, "groq/llama-3.3-70b-versatile")
                self.assertGreater(t_card.duration_sec, 0)
                rendered_tel = str(t_card.render())
                self.assertIn("▣", rendered_tel)
                self.assertIn("tok/s", rendered_tel)
                self.assertIn("0 B SSD", rendered_tel)


if __name__ == "__main__":
    unittest.main()
