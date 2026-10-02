"""Test Suite for Shadow-Docker Sandbox Confinement and Hermes-Claude Cognitive Engine.
Verifies:
1. ShadowDockerExecutor ephemeral containment, fallback to PhantomBusIPC, and Mode NÉANT.
2. HermesScratchpadEngine extended thinking (<thinking>), function calling (<tool_call>), and self-correction.
3. SacredLifeSentinel strict enforcement on both Docker tasks and cognitive scratchpads.
4. Orchestrator and CLI integration for /docker and /scratchpad.
"""

import os
import sys
import json
import asyncio
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.tools.shadow_docker import ShadowDockerExecutor
from app.cognition.hermes_scratchpad import HermesScratchpadEngine
from app.security.sacred_life import SacredLifeSentinel, SacredLifeViolationError
from app.orchestrator.orchestrator import TechLeadOrchestrator
from app.resource_manager.watchdog import ResourceManager
from app.tools.gateway import ToolGateway
import cli


class TestShadowDockerExecutor(unittest.TestCase):
    """Verifies Shadow-Docker sandbox confinement for sudo tasks."""

    def test_status_structure(self):
        executor = ShadowDockerExecutor()
        st = executor.get_status()
        self.assertIn("Shadow-Docker Ephemeral Sandbox", st["mode"])
        self.assertTrue(st["zero_ssd"])
        self.assertIn("tmpfs", st["security_containment"].lower())
        self.assertIn("Bubblewrap", st["fallback_mechanism"])
        self.assertIn("nmap", st["cyber_arsenal"])
        self.assertIn("systemctl", st["micro_init"])
        self.assertIn("montages", st["workspace_bridge"])

    def test_sacred_life_sentinel_blocks_weapons_in_docker(self):
        async def run_test():
            executor = ShadowDockerExecutor()
            with self.assertRaises(SacredLifeViolationError):
                await executor.execute_sudo_task("trigger_missile_launch")

        asyncio.run(run_test())

    def test_execute_sudo_task_mock_docker(self):
        async def run_test():
            executor = ShadowDockerExecutor()

            mock_proc = MagicMock()
            mock_proc.returncode = 0
            mock_proc.communicate = AsyncMock(return_value=(b"DOCKER_SANDBOX_SUCCESS\n", b""))

            with patch.object(executor, "is_docker_available", return_value=True):
                with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
                    res = await executor.execute_sudo_task("uname -a")
                    self.assertTrue(res["success"])
                    self.assertIn("DOCKER_SANDBOX_SUCCESS", res["stdout"])
                    self.assertTrue(res["zero_ssd"])
                    self.assertTrue(res["ephemeral"])

        asyncio.run(run_test())

    def test_execute_docker_writable_and_mounts(self):
        async def run_test():
            executor = ShadowDockerExecutor()

            mock_proc = MagicMock()
            mock_proc.returncode = 0
            mock_proc.communicate = AsyncMock(return_value=(b"WRITABLE_MOUNT_SUCCESS\n", b""))

            with patch.object(executor, "is_docker_available", return_value=True):
                with patch("asyncio.create_subprocess_exec", return_value=mock_proc) as mock_exec:
                    res = await executor.execute_sudo_task(
                        "mkdir /opt/test",
                        writable=True,
                        workspace_mount=str(PROJECT_ROOT),
                        mount_mode="ro"
                    )
                    self.assertTrue(res["success"])
                    self.assertTrue(res["writable_overlay"])
                    called_args = mock_exec.call_args[0]
                    # verify --read-only was NOT added since writable=True
                    self.assertNotIn("--read-only", called_args)
                    # verify mount was added
                    self.assertIn("-v", called_args)

        asyncio.run(run_test())

    def test_forbidden_mount_rejected(self):
        async def run_test():
            executor = ShadowDockerExecutor()
            with self.assertRaises(ValueError):
                await executor.execute_sudo_task("ls", workspace_mount="/etc")

        asyncio.run(run_test())

    def test_fallback_to_bwrap_when_docker_offline(self):
        async def run_test():
            executor = ShadowDockerExecutor()

            mock_proc = MagicMock()
            mock_proc.returncode = 0
            mock_proc.communicate = AsyncMock(return_value=(b"BWRAP_NAMESPACES_OK\n", b""))

            with patch.object(executor, "is_docker_available", return_value=False):
                with patch.object(executor, "is_bwrap_available", return_value=True):
                    with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
                        res = await executor.execute_sudo_task("echo 'BWRAP_NAMESPACES_OK'")
                        self.assertTrue(res["success"])
                        self.assertIn("BWRAP_NAMESPACES_OK", res["stdout"])
                        self.assertIn("Bubblewrap", res.get("engine", ""))

        asyncio.run(run_test())

    def test_fallback_to_phantom_when_all_offline(self):
        async def run_test():
            executor = ShadowDockerExecutor()

            with patch.object(executor, "is_docker_available", return_value=False):
                with patch.object(executor, "is_bwrap_available", return_value=False):
                    res = await executor.execute_sudo_task("echo 'PHANTOM_FALLBACK_OK'")
                    self.assertTrue(res["success"])
                    self.assertIn("PHANTOM_FALLBACK_OK", res["stdout"])
                    self.assertIn("PhantomBusIPC", res.get("engine", ""))

        asyncio.run(run_test())

    def test_execute_sudo_task_with_chained_sudo_and_systemctl(self):
        async def run_test():
            executor = ShadowDockerExecutor()

            mock_proc = MagicMock()
            mock_proc.returncode = 0
            mock_proc.communicate = AsyncMock(return_value=(b"chained_output\n", b""))

            with patch.object(executor, "is_docker_available", return_value=True):
                with patch("asyncio.create_subprocess_exec", return_value=mock_proc) as mock_exec:
                    res = await executor.execute_sudo_task("systemctl start audit && sudo id")
                    self.assertTrue(res["success"])
                    called_args = mock_exec.call_args[0]
                    bash_cmd = called_args[-1]
                    self.assertIn("sudo()", bash_cmd)
                    self.assertIn("systemctl()", bash_cmd)
                    self.assertIn("systemctl start audit && sudo id", bash_cmd)

        asyncio.run(run_test())


class TestHermesScratchpadEngine(unittest.TestCase):
    """Verifies Hermes 3 & Claude Extended Thinking cognitive engine."""

    def test_scratchpad_formulation(self):
        engine = HermesScratchpadEngine()
        record = engine.formulate_thought_scratchpad("Auditer les sockets réseau et fermer les ports inutiles")

        self.assertIn("thinking", record)
        self.assertIn("ANALYSE DU VECTEUR", record["thinking"])
        self.assertIn("AUTO-CRITIQUE RÉCURSIVE", record["thinking"])
        self.assertIn("tool_call", record)
        self.assertIn("name", record["tool_call"])
        self.assertTrue(record["is_safe"])

    def test_claude_thinking_tag_parsing(self):
        engine = HermesScratchpadEngine()
        raw = "Avant de répondre : <thinking>Hypothèse 1 : Le port 9050 est ouvert pour Tor. Vérifions.</thinking> Résultat : Le service est actif."
        thinking = engine.parse_claude_thinking(raw)
        self.assertEqual(thinking, "Hypothèse 1 : Le port 9050 est ouvert pour Tor. Vérifions.")

    def test_hermes_tool_call_json_parsing(self):
        engine = HermesScratchpadEngine()
        raw = 'Exécutons l\'action : <tool_call>{"name": "shadow_docker", "arguments": {"cmd": "netstat -tuln"}}</tool_call>'
        tool_call = engine.parse_hermes_tool_call(raw)
        self.assertIsNotNone(tool_call)
        self.assertEqual(tool_call["name"], "shadow_docker")
        self.assertEqual(tool_call["arguments"]["cmd"], "netstat -tuln")

    def test_sacred_life_sentinel_blocks_unethical_objective(self):
        engine = HermesScratchpadEngine()
        with self.assertRaises(SacredLifeViolationError):
            engine.formulate_thought_scratchpad("Attaquer le réseau de l'hôpital central")

    def test_status_and_frugal_memory(self):
        engine = HermesScratchpadEngine()
        for i in range(25):
            engine.formulate_thought_scratchpad(f"Tâche de maintenance #{i}")

        st = engine.get_status()
        self.assertTrue(st["zero_ssd"])
        self.assertTrue(st["self_correction_loop"])
        self.assertLess(st["volatile_ram_footprint_kb"], 50.0)


    def test_hermes_prompt_formatting_and_tool_response(self):
        engine = HermesScratchpadEngine()
        prompt = engine.generate_hermes_prompt("Analyser le trafic réseau")
        self.assertIn("<tools>", prompt)
        self.assertIn("shadow_docker", prompt)
        self.assertIn("<|im_start|>", prompt)

        resp = engine.format_tool_response("gateway", {"status": "ok", "ping": 12})
        self.assertIn("<tool_response>", resp)
        self.assertIn('"name": "gateway"', resp)

    def test_hermes_autonomous_cycle_execution(self):
        async def run_test():
            engine = HermesScratchpadEngine()
            mission = await engine.execute_autonomous_cycle("Vérifier les routes réseau")
            self.assertEqual(mission["turns_completed"], 2)
            self.assertTrue(mission["is_safe"])
            self.assertIn("final_synthesis", mission)
            self.assertEqual(len(mission["trajectory"]), 2)
            self.assertEqual(mission["trajectory"][0]["phase"], "thinking_and_dispatch")
            self.assertEqual(mission["trajectory"][1]["phase"], "tool_execution")

        asyncio.run(run_test())


class TestDockerAndHermesOrchestratorCLIIntegration(unittest.TestCase):
    """Verifies Orchestrator methods and CLI batch commands for Docker and Scratchpad."""

    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.rm = ResourceManager()
        self.gw = ToolGateway(workspace_root=self.tmp_dir.name, allow_sudo=True, mode="lesaintAi")
        self.orchestrator = TechLeadOrchestrator(tool_gateway=self.gw, resource_manager=self.rm)

    def tearDown(self):
        self.tmp_dir.cleanup()

    def test_orchestrator_has_docker_and_scratchpad_status(self):
        st = self.orchestrator.get_vortex_status()
        self.assertIn("shadow_docker", st)
        self.assertIn("hermes_cognition", st)
        self.assertTrue(st["shadow_docker"]["zero_ssd"])

    def test_orchestrator_execute_sudo_docker_fallback(self):
        async def run_test():
            res = await self.orchestrator.execute_sudo_docker("echo 'ORCHESTRATOR_DOCKER_TEST'")
            self.assertTrue(res["success"])
            self.assertIn("ORCHESTRATOR_DOCKER_TEST", res["stdout"])

        asyncio.run(run_test())

    def test_orchestrator_think_hermes(self):
        record = self.orchestrator.think_hermes("Compiler un payload pour audit de sécurité")
        self.assertIn("thinking", record)
        self.assertIn("tool_call", record)

    def test_orchestrator_run_hermes_agent(self):
        async def run_test():
            mission = await self.orchestrator.run_hermes_agent("Audit des sockets de communication")
            self.assertGreaterEqual(mission["turns_completed"], 2)
            self.assertTrue(mission["is_safe"])
            self.assertIn("trajectory", mission)

        asyncio.run(run_test())

    def test_cli_batch_docker_and_scratchpad_commands(self):
        async def run_test():
            from cli import run_docker, run_scratchpad, run_hermes

            # 1. /docker status & run
            await run_docker(self.orchestrator, [])
            await run_docker(self.orchestrator, ["status"])
            await run_docker(self.orchestrator, ["run", "echo", "'CLI_DOCKER_RUN'"])
            await run_docker(self.orchestrator, ["run", "--rw", "echo", "'CLI_DOCKER_RW'"])
            await run_docker(self.orchestrator, ["run", "--mount", "echo", "'CLI_DOCKER_MOUNT'"])

            # 2. /scratchpad status & reflection
            run_scratchpad(self.orchestrator, [])
            run_scratchpad(self.orchestrator, ["Sécuriser", "les", "interfaces", "réseau"])

            # 3. /hermes status, think, run
            await run_hermes(self.orchestrator, [])
            await run_hermes(self.orchestrator, ["status"])
            await run_hermes(self.orchestrator, ["think", "Optimiser", "la", "mémoire"])
            await run_hermes(self.orchestrator, ["run", "uname", "-s"])

        asyncio.run(run_test())

    def test_root_dockerfile_and_compose_exist(self):
        dockerfile = PROJECT_ROOT / "Dockerfile"
        compose = PROJECT_ROOT / "docker-compose.yml"
        self.assertTrue(dockerfile.exists(), "Root Dockerfile must exist for FreeAI containerization")
        self.assertTrue(compose.exists(), "docker-compose.yml must exist")
        content = dockerfile.read_text(encoding="utf-8")
        self.assertIn("python:3.13-slim", content)
        self.assertIn("MODE_NEANT=true", content)

