"""Unit and Integration Tests for Sovereign Auto-Evolution, P2P Mesh, Shadow Arena & Speculative Decoding."""

import os
import sys
import unittest
import tempfile
import asyncio
from pathlib import Path
from unittest.mock import patch, MagicMock

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.evolution.auto_update import AutoUpdateEngine
from app.cluster.mesh import P2PMeshBeacon
from app.llm.arena import ShadowRedTeamArena
from app.cluster.speculative import SpeculativeAccelerationEngine
from app.tools.gateway import ToolGateway
from app.resource_manager.watchdog import ResourceManager
from app.orchestrator.orchestrator import TechLeadOrchestrator
import cli


class TestAutoEvolutionEngine(unittest.TestCase):
    def setUp(self):
        self.updater = AutoUpdateEngine(workspace_root=str(PROJECT_ROOT))

    def test_check_git_status(self):
        st = self.updater.check_git_status()
        self.assertTrue(st["success"])
        self.assertIn("branch", st)
        self.assertIn("current_commit", st)
        self.assertIsInstance(st["is_dirty"], bool)

    def test_apply_self_patch_rollback_on_test_failure(self):
        """Verifies that an autonomous patch causing test failure is immediately rolled back."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_root = Path(tmpdir)
            test_file = tmp_root / "dummy.py"
            test_file.write_text("def test(): return True", encoding="utf-8")

            updater = AutoUpdateEngine(workspace_root=str(tmp_root))

            # Mock tests failing
            mock_test_fail = {"success": False, "summary": "1 failed in 0.1s"}
            with patch.object(updater, "run_safety_verification_tests", return_value=mock_test_fail):
                res = updater.apply_self_evolution_patch(
                    patch_description="break syntax",
                    file_path="dummy.py",
                    new_content="def test(): syntax error here !!!"
                )

                self.assertFalse(res["success"])
                self.assertTrue(res.get("rolled_back"))
                # Original content restored
                self.assertEqual(test_file.read_text(encoding="utf-8"), "def test(): return True")

    def test_apply_self_patch_success(self):
        """Verifies that a valid autonomous patch is committed cleanly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_root = Path(tmpdir)
            test_file = tmp_root / "dummy_valid.py"
            test_file.write_text("# Initial code", encoding="utf-8")

            updater = AutoUpdateEngine(workspace_root=str(tmp_root))
            mock_test_pass = {"success": True, "summary": "all passed"}

            with patch.object(updater, "run_safety_verification_tests", return_value=mock_test_pass):
                with patch("subprocess.run") as mock_sub:
                    mock_sub.return_value = MagicMock(returncode=0)
                    res = updater.apply_self_evolution_patch(
                        patch_description="add safe helper",
                        file_path="dummy_valid.py",
                        new_content="# Initial code\n# Optimized helper added"
                    )
                    self.assertTrue(res["success"])
                    self.assertEqual(test_file.read_text(encoding="utf-8"), "# Initial code\n# Optimized helper added")


class TestP2PMeshBeacon(unittest.TestCase):
    def setUp(self):
        self.mesh = P2PMeshBeacon(node_id="test_node_42", node_port=8000, allow_network=True)

    def test_beacon_payload_creation(self):
        payload = self.mesh.create_beacon_payload()
        self.assertIn(b"FREEAI_MESH_V1", payload)
        self.assertIn(b"test_node_42", payload)

    def test_handle_incoming_beacon(self):
        raw = b'{"magic": "FREEAI_MESH_V1", "node_id": "remote_peer_99", "hostname": "kali-laptop", "port": 11434, "is_gpu": true}'
        peer = self.mesh.handle_incoming_beacon(raw, ("192.168.1.75", 41234))
        self.assertIsNotNone(peer)
        self.assertEqual(peer["node_id"], "remote_peer_99")
        self.assertEqual(peer["ip"], "192.168.1.75")
        self.assertEqual(peer["port"], 11434)
        self.assertTrue(peer["is_gpu"])

        # Check in status
        st = self.mesh.get_mesh_status()
        self.assertEqual(st["active_peers_count"], 1)


class TestShadowRedTeamArena(unittest.TestCase):
    def test_arena_duel_execution(self):
        mock_fed = MagicMock()

        async def mock_consult(prompt, **kwargs):
            if "RED TEAM OFFENSIVE" in prompt:
                return {"success": True, "response": "Exploit: Race condition on token revoke"}
            elif "BLUE TEAM DEFENSE" in prompt:
                return {"success": True, "response": "Hardening: Mutex lock and atomic revoke in Redis"}
            else:
                return {"success": True, "response": "Retest: Mutex lock fully mitigates race condition"}

        mock_fed.consult_free_online_model = mock_consult
        arena = ShadowRedTeamArena(federation=mock_fed)

        async def _test():
            res = await arena.execute_adversarial_duel("Session token revocation mechanism")
            self.assertTrue(res["success"])
            self.assertIn("red_attack", res)
            self.assertIn("blue_defense", res)
            self.assertIn("hardened_shield", res)
            self.assertIn("INVULNÉRABLE", res["hardened_shield"])

        asyncio.run(_test())


class TestSpeculativeAccelerationEngine(unittest.TestCase):
    def test_accelerated_generation_fallback(self):
        mock_local = MagicMock()
        mock_local.reason_and_plan.return_value = {
            "description": "Create async queue",
            "steps": ["Step 1", "Step 2"]
        }
        mock_cluster = MagicMock()

        async def mock_dispatch(*args, **kwargs):
            return None  # No remote node available

        mock_cluster.dispatch_inference = mock_dispatch

        mock_fed = MagicMock()

        async def mock_online(*args, **kwargs):
            return {"success": True, "provider": "Groq_LPU", "response": "Accelerated full queue implementation"}

        mock_fed.consult_free_online_model = mock_online

        spec = SpeculativeAccelerationEngine(
            local_engine=mock_local,
            cluster_manager=mock_cluster,
            federation=mock_fed
        )

        async def _test():
            res = await spec.accelerated_generate("Implement high performance queue in C")
            self.assertTrue(res["success"])
            self.assertEqual(res["strategy"], "speculative_hybrid_federation")
            self.assertIn("Accelerated full queue", res["response"])

        asyncio.run(_test())


class TestCLIExtremeInnovationCommands(unittest.TestCase):
    def setUp(self):
        self.gw = ToolGateway(workspace_root=tempfile.gettempdir(), mode="freeAi")
        self.rm = ResourceManager()
        self.tl = TechLeadOrchestrator(tool_gateway=self.gw, resource_manager=self.rm)

    def test_slash_commands_contain_new_tools(self):
        self.assertIn("/evolve", cli.SLASH_COMMANDS)
        self.assertIn("/arena", cli.SLASH_COMMANDS)
        self.assertIn("/mesh", cli.SLASH_COMMANDS)
        self.assertIn("/speculate", cli.SLASH_COMMANDS)

    def test_cli_evolve_check(self):
        cli.run_evolve(self.tl, ["check"])

    def test_cli_arena_command(self):
        async def _test():
            mock_duel = {
                "success": True,
                "red_attack": "Exploit payload",
                "blue_defense": "Mitigation patch",
                "bypass_attempt": "Defense holds",
                "hardened_shield": "Shield Approved"
            }
            with patch.object(self.tl, "execute_shadow_arena", return_value=mock_duel):
                await cli.run_arena(self.tl, ["Test", "target"])

        asyncio.run(_test())

    def test_cli_mesh_command(self):
        async def _test():
            await cli.run_mesh(self.tl, ["status"])

        asyncio.run(_test())

    def test_cli_speculate_command(self):
        async def _test():
            mock_spec = {
                "success": True,
                "strategy": "speculative_distributed_gpu",
                "estimated_speed": "100 tok/s",
                "latency_sec": 0.32,
                "response": "Fast generated code"
            }
            with patch.object(self.tl, "speculative_generate", return_value=mock_spec):
                await cli.run_speculate(self.tl, ["Test", "speculation"])

        asyncio.run(_test())

    def test_batch_mode_new_commands(self):
        with patch("sys.argv", ["cli.py", "/evolve", "check"]):
            cli.main()

        with patch("sys.argv", ["cli.py", "/mesh", "status"]):
            cli.main()


if __name__ == "__main__":
    unittest.main()
