"""Unit and integration tests for FreeAI CLI and Dynamic Mode Switching (TDR §13, §17, §31, §32)."""

import os
import sys
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
        self.temp_dir = tempfile.TemporaryDirectory()
        self.gw = ToolGateway(
            workspace_root=self.temp_dir.name,
            allow_sudo=False,
            allow_full_fs_access=False,
            allow_global_read=True,
            mode="freeAi"
        )
        self.rm = ResourceManager()
        self.orch = TechLeadOrchestrator(tool_gateway=self.gw, resource_manager=self.rm)

    def tearDown(self):
        self.temp_dir.cleanup()

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

        # 2. lesaintAi mode: sudo command allowed (reaches execution)
        self.orch.set_mode("lesaintAi")
        # In test environment, sudo might prompt or fail with exit code, but gateway should NOT reject it upfront
        res = self.gw.execute_command("sudo -V || true")
        self.assertTrue(res["success"] or "exit_code" in res)
        self.assertNotIn("Sudo is disabled", res.get("error", ""))


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
    """Verifies CLI prompts, helpers, and status output."""

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


if __name__ == "__main__":
    unittest.main()
