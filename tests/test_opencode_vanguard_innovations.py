"""Comprehensive Automated Test Suite for FreeAI OpenCode Vanguard Innovations.
Validates:
1. LeftBorderStreamer: progressive token streaming, LeftBorder framing, pacing & telemetry.
2. SemanticCompactor: /compact neural history distillation, anchor preservation, token savings.
3. AtomicUndoManager: /undo file snapshotting, atomic rollback, redo, and dirty tracking.
4. OpenCodePromptCompleter: dynamic @path completion, /slash commands, #context tags.
5. LiveLspProbe: live • LSP probe, non-blocking TTL caching, AST/Ruff diagnostics.
6. Typographic Integrity: STRICT ZERO EMOJI verification in cli.py.
"""

import os
import re
import sys
import tempfile
import asyncio
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.cli.streaming_renderer import LeftBorderStreamer, StreamingLeftBorder, LeftBorderFinal
from app.cognition.semantic_compactor import SemanticCompactor, CompactionReport
from app.cognition.conversation_memory import ConversationMemory
from app.orchestrator.atomic_undo import AtomicUndoManager, UndoSnapshot
from app.cli.smart_completer import OpenCodePromptCompleter
from app.tools.lsp_probe import LiveLspProbe, DiagnosticItem, live_lsp_probe
from prompt_toolkit.document import Document


class TestLeftBorderStreamer(unittest.TestCase):
    """Verifies token-by-token streaming without terminal flicker."""

    def test_streaming_left_border_renderable(self):
        console_mock = MagicMock()
        console_mock.get_style.return_value = "bold cyan"
        border = StreamingLeftBorder("Line 1\nLine 2", border_style="bold cyan", char="┃", cursor="▌", is_active=True)
        segments = list(border.__rich_console__(console_mock, None))
        text_collected = "".join(str(getattr(s, "text", "")) for s in segments)
        self.assertIn("┃", text_collected)
        self.assertIn("Line 1", text_collected)
        self.assertIn("Line 2▌", text_collected)

    def test_left_border_final_cap(self):
        console_mock = MagicMock()
        console_mock.get_style.return_value = "bold cyan"
        console_mock.render_lines.return_value = [
            [MagicMock(text="Line 1")],
            [MagicMock(text="Line 2")]
        ]
        border_final = LeftBorderFinal("dummy", style="bold cyan", char="┃", bottom_char="╹")
        segments = list(border_final.__rich_console__(console_mock, None))
        text_collected = "".join(str(getattr(s, "text", "")) for s in segments)
        self.assertIn("┃", text_collected)
        self.assertIn("╹", text_collected)

    def test_token_streaming_accumulation_and_telemetry(self):
        async def _run():
            streamer = LeftBorderStreamer(frame_interval_sec=0.01)
            
            async def _fake_token_generator():
                tokens = ["FreeAI ", "OpenCode ", "Streaming ", "TUI\n", "Second ", "Line."]
                for t in tokens:
                    yield t

            full_text = await streamer.stream_tokens(_fake_token_generator())
            self.assertEqual(full_text, "FreeAI OpenCode Streaming TUI\nSecond Line.")
            
            telemetry = streamer.get_telemetry()
            self.assertEqual(telemetry["tokens"], 6)
            self.assertGreater(telemetry["tokens_per_sec"], 0)
            self.assertEqual(telemetry["char_count"], len(full_text))

        asyncio.run(_run())


class TestSemanticCompactor(unittest.TestCase):
    """Verifies /compact neural history distillation without losing critical state."""

    def setUp(self):
        self.compactor = SemanticCompactor(keep_recent_turns=2)
        self.memory = ConversationMemory()

    def test_short_history_no_compaction(self):
        self.memory.add_turn("user", "Hello")
        self.memory.add_turn("assistant", "Hi")
        report = self.compactor.compact_memory(self.memory)
        self.assertEqual(report.turns_before, 2)
        self.assertEqual(report.turns_after, 2)
        self.assertEqual(report.compression_ratio, 0.0)

    def test_compaction_with_anchor_preservation(self):
        # Populate realistic turns with decisions, files, and fixes
        turns_data = [
            ("user", "Configure le projet et analyse @app/llm/engine.py"),
            ("assistant", "Décision: adopté l'architecture modulaire avec Groq LPU."),
            ("user", "Corrige le bug de mémoire dans @app/resource_manager/watchdog.py"),
            ("assistant", "Fix résolu: patch appliqué pour éviter les fuites RAM."),
            ("user", "Vérifie les tests de @tests/test_cli.py"),
            ("assistant", "Tous les tests sont PASS."),
            ("user", "Active la sentinelle pour le déploiement."),
            ("assistant", "Décision: activé SacredLifeSentinel avec veto immuable."),
            # Recent turns to keep verbatim
            ("user", "Quel est l'état actuel ?"),
            ("assistant", "Système opérationnel et stable.")
        ]
        for role, text in turns_data:
            self.memory.add_turn(role, text)

        self.assertEqual(self.memory.turn_count, 10)
        report = self.compactor.compact_memory(self.memory, mode="lesaintAi")

        self.assertEqual(report.turns_after, 3)  # 1 distilled anchor + 2 recent turns
        self.assertEqual(self.memory.turns[0]["role"], "system")
        self.assertTrue(self.memory.turns[0]["compacted"])

        # Check preserved anchors
        anchor_content = self.memory.turns[0]["content"]
        self.assertIn("SEMANTIC COMPACTION ANCHOR", anchor_content)
        self.assertIn("lesaintAi", anchor_content)
        self.assertIn("app/llm/engine.py", anchor_content)
        self.assertIn("watchdog.py", anchor_content)
        self.assertIn("Groq LPU", anchor_content)
        self.assertIn("SacredLifeSentinel", anchor_content)

        # Check recent turns are intact
        self.assertEqual(self.memory.turns[1]["content"], "Quel est l'état actuel ?")
        self.assertEqual(self.memory.turns[2]["content"], "Système opérationnel et stable.")


class TestAtomicUndoManager(unittest.TestCase):
    """Verifies atomic rollback, snapshotting, and redo functionality."""

    def test_undo_and_redo_cycle(self):
        with tempfile.TemporaryDirectory() as td:
            mgr = AtomicUndoManager(td)
            test_file = Path(td) / "code.py"
            test_file.write_text("initial code")

            # 1. Capture snapshot before modification
            snap = mgr.create_snapshot("Refactor code.py", ["code.py"])
            self.assertEqual(len(mgr.undo_stack), 1)

            # 2. Simulate tool modifying the file
            test_file.write_text("buggy code with syntax error")
            mgr.finalize_snapshot(snap, ["code.py"])

            # 3. Trigger /undo
            undo_res = mgr.undo()
            self.assertTrue(undo_res["success"])
            self.assertEqual(test_file.read_text(), "initial code")
            self.assertEqual(len(mgr.redo_stack), 1)

            # 4. Trigger /redo
            redo_res = mgr.redo()
            self.assertTrue(redo_res["success"])
            self.assertEqual(test_file.read_text(), "buggy code with syntax error")

    def test_undo_newly_created_file(self):
        with tempfile.TemporaryDirectory() as td:
            mgr = AtomicUndoManager(td)
            new_file_rel = "created.py"
            new_file_abs = Path(td) / new_file_rel

            # Snapshot taken when file does not exist
            snap = mgr.create_snapshot("Generate created.py", [new_file_rel])
            
            # File is created
            new_file_abs.write_text("print('hello')")
            mgr.finalize_snapshot(snap, [new_file_rel])
            self.assertTrue(new_file_abs.exists())

            # Undo must delete the newly created file
            res = mgr.undo()
            self.assertTrue(res["success"])
            self.assertFalse(new_file_abs.exists())


class TestOpenCodePromptCompleter(unittest.TestCase):
    """Verifies dynamic @path, /slash commands, and #context completion."""

    def test_slash_command_completion(self):
        completer = OpenCodePromptCompleter(str(PROJECT_ROOT))
        doc = Document("/und")
        completions = list(completer.get_completions(doc, None))
        texts = [c.text for c in completions]
        self.assertIn("/undo", texts)

        doc_comp = Document("/comp")
        completions = list(completer.get_completions(doc_comp, None))
        texts = [c.text for c in completions]
        self.assertIn("/compact", texts)

        doc_lsp = Document("/ls")
        completions = list(completer.get_completions(doc_lsp, None))
        texts = [c.text for c in completions]
        self.assertIn("/lsp", texts)

    def test_at_path_workspace_completion(self):
        with tempfile.TemporaryDirectory() as td:
            (Path(td) / "app").mkdir()
            (Path(td) / "app" / "core.py").write_text("core")
            (Path(td) / "cli.py").write_text("cli")

            completer = OpenCodePromptCompleter(td)
            
            # Complete @cl -> cli.py
            doc = Document("inspect @cl")
            completions = list(completer.get_completions(doc, None))
            texts = [c.text for c in completions]
            self.assertIn("cli.py", texts)

            # Complete @ap -> app/ (directory with trailing slash)
            doc_dir = Document("explore @ap")
            completions = list(completer.get_completions(doc_dir, None))
            texts = [c.text for c in completions]
            self.assertIn("app/", texts)

    def test_context_tag_completion(self):
        completer = OpenCodePromptCompleter(str(PROJECT_ROOT))
        doc = Document("#gi")
        completions = list(completer.get_completions(doc, None))
        texts = [c.text for c in completions]
        self.assertIn("#git", texts)


class TestLiveLspProbe(unittest.TestCase):
    """Verifies live LSP probe, syntax scanning, and status badge formatting."""

    def test_badge_formatting_clean(self):
        probe = LiveLspProbe(str(PROJECT_ROOT))
        probe._cached_summary = MagicMock(display_badge="[bold green]•[/] 0 LSP")
        probe._last_probe_time = 10000000000.0  # Far future to test cache hit
        self.assertEqual(probe.get_summary_badge(), "[bold green]•[/] 0 LSP")

    def test_native_ast_syntax_error_detection(self):
        with tempfile.TemporaryDirectory() as td:
            bad_file = Path(td) / "broken.py"
            bad_file.write_text("def syntax_error(\n    print('unclosed')")
            
            probe = LiveLspProbe(td)
            diags = probe.get_diagnostics(force_refresh=True)
            
            self.assertTrue(any(d.code == "SyntaxError" for d in diags))
            self.assertIn("broken.py", [d.file for d in diags])
            badge = probe.get_summary_badge()
            self.assertIn("LSP", badge)
            self.assertIn("red", badge)


class TestOpenCodeTypographicIntegrity(unittest.TestCase):
    """Strictly guarantees ZERO raw emojis in cli.py."""

    def test_zero_raw_emojis_in_cli(self):
        cli_path = PROJECT_ROOT / "cli.py"
        content = cli_path.read_text(encoding="utf-8")
        
        emoji_pattern = re.compile(
            r"[\U00010000-\U0010ffff]|[\u2600-\u27bf]|[\u2300-\u23ff]|[\u2b50-\u2b55]|[\u3030\u303d\u3297\u3299]"
        )
        matches = set(emoji_pattern.findall(content))
        noble_terminal_glyphs = {"✓", "✗", "✱", "❯"}
        forbidden_emojis = matches - noble_terminal_glyphs

        self.assertEqual(
            forbidden_emojis,
            set(),
            f"STRICT COMPLIANCE VIOLATION: Found emojis in cli.py: {forbidden_emojis}"
        )


if __name__ == "__main__":
    unittest.main()
