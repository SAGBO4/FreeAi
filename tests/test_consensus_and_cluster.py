"""Unit and Integration Tests for Consensus Clash, Free Online GPUs, and LAN Cluster Swarm."""

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

from app.cluster.swarm import LANClusterManager, ComputeNode
from app.llm.federation import OnlineModelFederation
from app.tools.gateway import ToolGateway
from app.resource_manager.watchdog import ResourceManager
from app.orchestrator.orchestrator import TechLeadOrchestrator
import cli


class TestLANClusterManager(unittest.TestCase):
    def setUp(self):
        self.cluster = LANClusterManager(mode="freeAi", allow_sudo=False, allow_network=True)

    def test_local_ip_and_subnet_discovery(self):
        ip = self.cluster.get_local_lan_ip()
        subnet = self.cluster.get_subnet()
        self.assertTrue(len(ip.split(".")) == 4)
        self.assertTrue(len(subnet.split(".")) == 3)

    def test_register_and_remove_node(self):
        node = self.cluster.register_node("192.168.1.100:11434")
        self.assertIn("192.168.1.100:11434", self.cluster.nodes)
        self.assertEqual(node.port, 11434)
        self.assertEqual(node.node_type, "ollama")

        # Remote GPU URL detection
        gpu_node = self.cluster.register_node("https://colab-worker.bore.pub")
        self.assertTrue(gpu_node.is_gpu)
        self.assertEqual(gpu_node.source, "online_gpu")

        # Removal
        ok = self.cluster.remove_node("192.168.1.100:11434")
        self.assertTrue(ok)
        self.assertNotIn("192.168.1.100:11434", self.cluster.nodes)

    def test_ssh_permission_enforcement(self):
        # In freeAi mode: SSH is denied
        self.cluster.update_permissions(mode="freeAi", allow_sudo=False)
        res = self.cluster.deploy_or_check_ssh_node("192.168.1.50")
        self.assertFalse(res["success"])
        self.assertIn("Accès refusé", res["error"])

        # In lesaintAi mode: SSH is permitted
        self.cluster.update_permissions(mode="lesaintAi", allow_sudo=True)
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="Linux kali 6.12\nNVIDIA GeForce RTX 3060 12GB")
            res_admin = self.cluster.deploy_or_check_ssh_node("192.168.1.50")
            self.assertTrue(res_admin["success"])
            self.assertTrue(res_admin["has_gpu"])
            self.assertIn("RTX 3060", res_admin["hardware_specs"])

    def test_probe_node_ollama(self):
        node = self.cluster.register_node("192.168.1.42:11434")
        mock_response = MagicMock(status_code=200)
        mock_response.json.return_value = {"models": [{"name": "qwen2.5-coder:7b"}]}

        async def _test():
            with patch("httpx.AsyncClient.get", return_value=mock_response):
                await self.cluster.probe_node(node)
                self.assertEqual(node.status, "online")
                self.assertEqual(node.model_name, "qwen2.5-coder:7b")
        asyncio.run(_test())

    def test_dispatch_inference_to_cluster(self):
        node = self.cluster.register_node("192.168.1.42:11434")
        node.status = "online"
        node.model_name = "llama3"

        mock_post = MagicMock(status_code=200)
        mock_post.json.return_value = {"response": "Distributed code from LAN node"}

        async def _test():
            with patch("httpx.AsyncClient.post", return_value=mock_post):
                res = await self.cluster.dispatch_inference("Write quicksort in C")
                self.assertIsNotNone(res)
                self.assertTrue(res["success"])
                self.assertEqual(res["source"], "lan_cluster_node")
                self.assertEqual(res["response"], "Distributed code from LAN node")
        asyncio.run(_test())


class TestConsensusClashAndGroq(unittest.TestCase):
    def setUp(self):
        self.fed = OnlineModelFederation(memory_mode="neant", persist_to_disk=False)

    def test_catalog_has_groq_and_free(self):
        cat = self.fed.list_supported_online_models()
        self.assertIn("groq", cat)
        self.assertIn("openrouter_free", cat)
        self.assertTrue(cat["groq"]["endpoint"].startswith("https://api.groq.com"))

    def test_groq_lpu_call_mock(self):
        self.fed.groq_api_key = "gsk_test_mock_groq_key"
        self.fed.set_online_target("groq", "llama-3.3-70b-versatile")

        mock_res = MagicMock(status_code=200)
        mock_res.json.return_value = {
            "choices": [{"message": {"content": "Fast LPU solution from Groq"}}]
        }

        async def _test():
            with patch("httpx.AsyncClient.post", return_value=mock_res):
                res = await self.fed.consult_free_online_model("Fast code optimization")
                self.assertTrue(res["success"])
                self.assertTrue("Groq_LPU" in res["provider"])
                self.assertEqual(res["response"], "Fast LPU solution from Groq")
        asyncio.run(_test())

    def test_consensus_clash_execution(self):
        """Verifies the multi-AI contradictory debate and synthesis."""
        async def _test():
            # Mock responses for round 1 and round 2
            mock_res_a = {"success": True, "response": "DeepSeek: Use memory-safe Rust with zero allocations"}
            mock_res_b = {"success": True, "response": "Grok: Use async epoll C kernel module for raw speed"}

            with patch.object(self.fed, "consult_free_online_model", side_effect=[
                mock_res_a, mock_res_b,  # Round 1
                {"success": True, "response": "Critique DeepSeek: C kernel module has risk of segfaults"},  # Round 2
                {"success": True, "response": "Critique Grok: Rust has compile time overhead"}              # Round 2
            ]):
                res = await self.fed.consensus_clash("Build maximum performance network proxy")
                self.assertTrue(res["success"])
                self.assertIn("round1", res)
                self.assertIn("round2", res)
                self.assertIn("synthesis", res)
                self.assertIn("ARBITRAGE DU CONSENSUS CLASH", res["synthesis"])

        asyncio.run(_test())


class TestCLIClusterAndClashCommands(unittest.TestCase):
    def setUp(self):
        self.gw = ToolGateway(workspace_root=tempfile.gettempdir(), mode="freeAi")
        self.rm = ResourceManager()
        self.tl = TechLeadOrchestrator(tool_gateway=self.gw, resource_manager=self.rm)

    def test_slash_commands_list_contains_clash_gpu_cluster(self):
        self.assertIn("/clash", cli.SLASH_COMMANDS)
        self.assertIn("/gpu", cli.SLASH_COMMANDS)
        self.assertIn("/cluster", cli.SLASH_COMMANDS)

    def test_cli_gpu_guide(self):
        # Should execute without error
        cli.run_gpu_guide(self.tl, [])

    def test_cli_cluster_management(self):
        async def _test():
            # /cluster list
            await cli.run_cluster(self.tl, ["list"])

            # /cluster add
            await cli.run_cluster(self.tl, ["add", "192.168.1.88:11434"])
            self.assertIn("192.168.1.88:11434", self.tl.cluster_manager.nodes)

            # /cluster rm
            await cli.run_cluster(self.tl, ["rm", "192.168.1.88:11434"])
            self.assertNotIn("192.168.1.88:11434", self.tl.cluster_manager.nodes)

            # /cluster ssh in freeAi mode
            await cli.run_cluster(self.tl, ["ssh", "192.168.1.88"])

        asyncio.run(_test())

    def test_cli_clash_command(self):
        async def _test():
            mock_clash = {
                "success": True,
                "model_a": "deepseek",
                "model_b": "grok",
                "round1": {"deepseek": "Sol A", "grok": "Sol B"},
                "round2": {"deepseek_attacks_grok": "Crit A", "grok_attacks_deepseek": "Crit B"},
                "synthesis": "Unified Solution"
            }
            with patch.object(self.tl, "consensus_clash", return_value=mock_clash):
                await cli.run_clash(self.tl, ["Test", "challenge"])

        asyncio.run(_test())

    def test_batch_mode_clash_and_cluster(self):
        with patch("sys.argv", ["cli.py", "/gpu"]):
            cli.main()

        with patch("sys.argv", ["cli.py", "/cluster", "list"]):
            cli.main()


if __name__ == "__main__":
    unittest.main()
