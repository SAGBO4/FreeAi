"""Unit and integration tests for FreeAI CLI and Dynamic Mode Switching (TDR §13, §17, §31, §32)."""

import os
import sys
import asyncio
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.tools.gateway import ToolGateway
from app.resource_manager.watchdog import ResourceManager
from app.orchestrator.orchestrator import TechLeadOrchestrator
from app.memory.neon_db import NeonMemoryManager
import cli


class TestDynamicModeSwitching(unittest.TestCase):
    """Verifies dynamic permission switching between freeAi and lesaintAi."""

    def setUp(self):
        self.temp_ws = tempfile.TemporaryDirectory()
        self.temp_outside = tempfile.TemporaryDirectory()
        self.gw = ToolGateway(
            workspace_root=self.temp_ws.name,
            allow_sudo=False,
            allow_full_fs_access=False,
            allow_global_read=True,
            mode="freeAi"
        )
        self.rm = ResourceManager()
        self.orch = TechLeadOrchestrator(tool_gateway=self.gw, resource_manager=self.rm)

    def tearDown(self):
        self.temp_ws.cleanup()
        self.temp_outside.cleanup()

    def test_default_mode_is_freeai(self):
        self.assertEqual(self.gw.mode, "freeAi")
        self.assertEqual(self.orch.mode, "freeAi")
        self.assertFalse(self.gw.allow_sudo)
        self.assertFalse(self.gw.allow_full_fs_access)
        self.assertTrue(self.gw.allow_global_read)

    def test_switch_to_lesaintai_mode(self):
        res = self.orch.set_mode("lesaintAi")
        self.assertEqual(res["mode"], "lesaintAi")
        self.assertTrue(self.gw.allow_sudo)
        self.assertTrue(self.gw.allow_full_fs_access)
        self.assertTrue(self.gw.allow_global_read)
        self.assertEqual(self.orch.mode, "lesaintAi")

    def test_switch_back_to_freeai_mode(self):
        self.orch.set_mode("lesaintAi")
        self.assertTrue(self.gw.allow_sudo)

        res = self.orch.set_mode("freeAi")
        self.assertEqual(res["mode"], "freeAi")
        self.assertFalse(self.gw.allow_sudo)
        self.assertFalse(self.gw.allow_full_fs_access)
        self.assertTrue(self.gw.allow_global_read)
        self.assertEqual(self.orch.mode, "freeAi")

    def test_sudo_enforcement_by_mode(self):
        # 1. freeAi mode: sudo command rejected
        self.orch.set_mode("freeAi")
        res = self.gw.execute_command("sudo whoami")
        self.assertFalse(res["success"])
        self.assertIn("Sudo is disabled", res["error"])

        # Also test alternative privileged commands
        for cmd in ["/usr/bin/sudo id", "pkexec id", "doas id", "su -"]:
            res = self.gw.execute_command(cmd)
            self.assertFalse(res["success"], f"Failed to block: {cmd}")
            self.assertIn("Sudo is disabled", res["error"])

        # 2. lesaintAi mode: sudo command allowed (reaches execution)
        self.orch.set_mode("lesaintAi")
        # In test environment, sudo might prompt or fail with exit code, but gateway should NOT reject it upfront
        res = self.gw.execute_command("sudo -V || true")
        self.assertTrue(res["success"] or "exit_code" in res)
        self.assertNotIn("Sudo is disabled", res.get("error", ""))

    def test_filesystem_confinement_by_mode(self):
        outside_target = str(Path(self.temp_outside.name) / "outside_test.txt")

        # 1. In freeAi mode: writing outside workspace is forbidden
        self.orch.set_mode("freeAi")
        w_res_free = self.gw.write_file(outside_target, "forbidden write")
        self.assertFalse(w_res_free["success"])
        self.assertIn("outside workspace", w_res_free["error"])

        # In freeAi mode: writing inside workspace is allowed
        inside_target = "inside_test.txt"
        w_res_inside = self.gw.write_file(inside_target, "allowed write")
        self.assertTrue(w_res_inside["success"])

        # In freeAi mode: reading outside workspace is permitted (global read)
        # Prepare a file outside workspace
        outside_file = Path(self.temp_outside.name) / "readable_outside.txt"
        outside_file.write_text("global read content", encoding="utf-8")
        r_res_free = self.gw.read_file(str(outside_file))
        self.assertTrue(r_res_free["success"])
        self.assertEqual(r_res_free["content"], "global read content")

        # 2. In lesaintAi mode: writing outside workspace is unlocked (computer-wide)
        self.orch.set_mode("lesaintAi")
        w_res_lesaint = self.gw.write_file(outside_target, "unlocked computer-wide write")
        self.assertTrue(w_res_lesaint["success"])
        self.assertEqual(Path(outside_target).read_text(encoding="utf-8"), "unlocked computer-wide write")


class TestSearchAndRollback(unittest.TestCase):
    """Verifies file search, code search, and Git rollback operations."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.ws = Path(self.temp_dir.name)
        # Create sample files
        (self.ws / "sample_service.py").write_text("def run_service():\n    return 'ACTIVE_SERVICE'\n", encoding="utf-8")
        (self.ws / "config.json").write_text('{"env": "production"}', encoding="utf-8")
        sub = self.ws / "subdir"
        sub.mkdir()
        (sub / "nested_helper.py").write_text("# helper code\ndef calculate_rate(): pass\n", encoding="utf-8")

        self.gw = ToolGateway(workspace_root=str(self.ws), allow_global_read=True, allow_full_fs_access=True)
        self.rm = ResourceManager()
        self.orch = TechLeadOrchestrator(tool_gateway=self.gw, resource_manager=self.rm)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_search_files(self):
        res = self.orch.search_files(pattern="*.py", search_dir=str(self.ws))
        self.assertTrue(res["success"])
        self.assertEqual(res["count"], 2)
        filenames = [Path(p).name for p in res["matches"]]
        self.assertIn("sample_service.py", filenames)
        self.assertIn("nested_helper.py", filenames)

    def test_search_code(self):
        res = self.orch.search_code(query="ACTIVE_SERVICE", search_dir=str(self.ws), file_pattern="*.py")
        self.assertTrue(res["success"])
        self.assertEqual(res["count"], 1)
        self.assertIn("ACTIVE_SERVICE", res["matches"][0]["content"])
        self.assertEqual(res["matches"][0]["line"], 2)


class TestCLIFunctionality(unittest.TestCase):
    """Verifies CLI prompts, helpers, slash commands, quote resilience, and clean EOF termination."""

    def test_dynamic_prompt_formatting(self):
        prompt_standard = cli.get_prompt("freeAi")
        self.assertEqual(prompt_standard, "[FreeAI:freeAi] > ")

        prompt_super = cli.get_prompt("lesaintAi")
        self.assertEqual(prompt_super, "[FreeAI:lesaintAi ⚡] > ")

    def test_orchestrator_get_status_structure(self):
        rm = ResourceManager()
        gw = ToolGateway(workspace_root=tempfile.gettempdir(), mode="freeAi")
        orch = TechLeadOrchestrator(tool_gateway=gw, resource_manager=rm)

        status = orch.get_status()
        self.assertIn("mode", status)
        self.assertEqual(status["mode"], "freeAi")
        self.assertIn("resources", status)
        self.assertIn("neon", status)
        self.assertIn("ai_process_rss_mb", status["resources"])
        self.assertIn("system_ram_total_mb", status["resources"])

    def test_neon_sync_method(self):
        manager = NeonMemoryManager(db_url="")
        res = manager.sync_memory({"test": "sync"})
        self.assertFalse(res["success"])
        self.assertIn("not enabled", res["message"])

    def test_cli_handles_clean_eof_exit(self):
        """Verifies that interactive_cli breaks immediately on EOF without infinite looping."""
        with patch("builtins.input", side_effect=EOFError):
            async def _run():
                await cli.interactive_cli(initial_mode="freeAi")
            # Must finish without hanging or raising exception
            asyncio.run(_run())

    def test_cli_handles_exit_command(self):
        """Verifies that /exit terminates interactive_cli cleanly."""
        inputs = iter(["/exit"])
        with patch("builtins.input", side_effect=lambda _: next(inputs)):
            async def _run():
                await cli.interactive_cli(initial_mode="freeAi")
            asyncio.run(_run())

    def test_cli_handles_french_apostrophes_and_quotes(self):
        """Verifies that natural language with apostrophes does not crash with ValueError."""
        executed = []

        async def mock_execute(tl, text):
            executed.append(text)

        inputs = iter(["J'ai un bug d'exécution dans mon script", "/exit"])
        with patch("builtins.input", side_effect=lambda _: next(inputs)):
            with patch("cli.execute_tech_lead_task", side_effect=mock_execute):
                async def _run():
                    await cli.interactive_cli(initial_mode="freeAi")
                asyncio.run(_run())

        self.assertEqual(len(executed), 1)
        self.assertEqual(executed[0], "J'ai un bug d'exécution dans mon script")

    def test_cli_slash_commands_execution(self):
        """Verifies execution of all slash command handlers."""
        gw = ToolGateway(workspace_root=tempfile.gettempdir(), mode="freeAi")
        rm = ResourceManager()
        tl = TechLeadOrchestrator(tool_gateway=gw, resource_manager=rm)

        # /help
        cli.print_help()

        # /status
        cli.print_status(tl)

        # /mode
        cli.handle_mode_command(tl, ["lesaintAi"])
        self.assertEqual(tl.mode, "lesaintAi")
        cli.handle_mode_command(tl, ["freeAi"])
        self.assertEqual(tl.mode, "freeAi")

        # /search
        cli.run_search_files(tl, ["*.py", tempfile.gettempdir()])

        # /code
        cli.run_search_code(tl, ["test", "*.py", tempfile.gettempdir()])

        # /sync
        cli.run_sync(tl)

        # /online (display and switch)
        cli.run_online_config(tl, [])
        cli.run_online_config(tl, ["deepseek"])
        self.assertEqual(tl.free_ai.federation.current_provider, "deepseek")
        cli.run_online_config(tl, ["grok"])
        self.assertEqual(tl.free_ai.federation.current_provider, "grok")
        cli.run_online_config(tl, ["qwen"])
        self.assertEqual(tl.free_ai.federation.current_provider, "qwen")

        # /ask
        async def _test_ask():
            await cli.run_ask_online(tl, ["Explique", "un", "concept"])
        asyncio.run(_test_ask())


class TestRemoteOnlineModels(unittest.TestCase):
    """Verifies that Grok, DeepSeek, Qwen and OpenRouter operate strictly as remote REST APIs with zero local footprint."""

    def setUp(self):
        self.rm = ResourceManager()
        self.gw = ToolGateway(workspace_root=tempfile.gettempdir(), mode="freeAi")
        self.tl = TechLeadOrchestrator(tool_gateway=self.gw, resource_manager=self.rm)

    def test_catalog_structure(self):
        catalog = self.tl.list_online_models()
        self.assertIn("deepseek", catalog)
        self.assertIn("grok", catalog)
        self.assertIn("qwen", catalog)
        self.assertIn("openrouter", catalog)
        self.assertTrue(catalog["deepseek"]["endpoint"].startswith("https://"))
        self.assertTrue(catalog["grok"]["endpoint"].startswith("https://"))

    def test_remote_rest_api_invocation_zero_disk(self):
        """Verifies remote REST API invocation via mock without downloading model weights."""
        fed = self.tl.free_ai.federation
        fed.deepseek_api_key = "sk-test-deepseek-mock-key"
        fed.set_online_target("deepseek", "deepseek-chat")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Solution from remote DeepSeek V3 online API"}}]
        }

        async def _test():
            with patch("httpx.AsyncClient.post", return_value=mock_response) as mock_post:
                res = await self.tl.ask_online_model("Optimise cette requête SQL")
                self.assertTrue(res["success"])
                self.assertEqual(res["provider"], "DeepSeek")
                self.assertEqual(res["response"], "Solution from remote DeepSeek V3 online API")

                # Verify REST request payload & endpoint
                mock_post.assert_called_once()
                args, kwargs = mock_post.call_args
                self.assertEqual(args[0], "https://api.deepseek.com/chat/completions")
                self.assertEqual(kwargs["headers"]["Authorization"], "Bearer sk-test-deepseek-mock-key")
                self.assertEqual(kwargs["json"]["model"], "deepseek-chat")

        asyncio.run(_test())

    def test_batch_mode_cli_online_commands(self):
        """Verifies CLI batch mode execution for /online and /ask."""
        with patch("sys.argv", ["cli.py", "/online"]):
            cli.main()

        with patch("sys.argv", ["cli.py", "/online", "grok"]):
            cli.main()

        mock_ask_res = {"success": True, "provider": "DeepSeek", "response": "Batch answer"}
        with patch.object(TechLeadOrchestrator, "ask_online_model", return_value=mock_ask_res):
            with patch("sys.argv", ["cli.py", "/ask", "Test", "question"]):
                cli.main()


if __name__ == "__main__":
    unittest.main()
