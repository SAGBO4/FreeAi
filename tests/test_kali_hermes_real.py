#!/usr/bin/env python3
"""
Test Suite for Real Kali Cyber-Hermes Agent & Zero-Simulation Engine.
Verifies:
- AC1: KaliToolRegistry dynamic detection of real Kali Linux local binaries.
- AC2: Hermes 3 / Claude function schema generation for detected local tools.
- AC3: HermesScratchpadEngine intelligent dispatch to real Kali tools (sqlmap, ffuf, radare2, etc.).
- AC4: Elimination of simulated status in autonomous execution cycle.
- AC5: BinaryHologramEngine hyperdimensional semantic similarity (proves dead MD5 whole-hash simulation).
- AC6: SecurityAgent integration with real Kali arsenal.
"""

import unittest
import asyncio
import numpy as np
from unittest.mock import MagicMock

from app.tools.kali_registry import KaliToolRegistry, KALI_TOOL_CATALOG
from app.cognition.hermes_scratchpad import HermesScratchpadEngine
from app.agents.security_agent import SecurityAgent
from app.memory.binary_hologram import BinaryHologramEngine


class TestRealKaliCyberHermes(unittest.TestCase):
    """Zero-Simulation Quality Gate for Kali Cyber-Hermes integration."""

    def setUp(self):
        self.registry = KaliToolRegistry()
        self.hermes = HermesScratchpadEngine()

    def test_ac1_kali_tools_detected_on_host(self):
        """AC1: Proves that real local Kali binaries are detected on host without mocks."""
        tools = self.registry.get_installed_tools()
        self.assertIsInstance(tools, dict)
        # On Kali Linux, at least one of the major tools must be found
        self.assertGreater(len(tools), 0, "KaliToolRegistry must detect installed host binaries.")
        for tool_name, bin_path in tools.items():
            self.assertTrue(bin_path.startswith("/"), f"Binary path {bin_path} must be absolute.")

    def test_ac2_hermes_schemas_generation(self):
        """AC2: Validates that local Kali tools are formatted into valid Hermes 3 function schemas."""
        schemas = self.registry.get_hermes_tool_schemas()
        self.assertIsInstance(schemas, list)
        self.assertEqual(len(schemas), len(self.registry.get_installed_tools()))
        if schemas:
            first = schemas[0]
            self.assertIn("name", first)
            self.assertTrue(first["name"].startswith("kali_"))
            self.assertIn("description", first)
            self.assertIn("parameters", first)

    def test_ac3_hermes_intelligent_dispatch_to_kali_tools(self):
        """AC3: Verifies HermesScratchpadEngine selects real Kali tools based on objective."""
        # 1. SQL Injection task -> kali_sqlmap
        if self.registry.is_tool_available("sqlmap"):
            record = self.hermes.formulate_thought_scratchpad("Audit d'injection SQL sur l'endpoint /api/login")
            self.assertEqual(record["tool_call"]["name"], "kali_sqlmap")

        # 2. Web fuzzing task -> kali_ffuf
        if self.registry.is_tool_available("ffuf"):
            record = self.hermes.formulate_thought_scratchpad("Fuzzing d'endpoints et répertoires cachés sur le port 8000")
            self.assertEqual(record["tool_call"]["name"], "kali_ffuf")

        # 3. Reverse engineering -> kali_radare2
        if self.registry.is_tool_available("radare2"):
            record = self.hermes.formulate_thought_scratchpad("Désassemblage et analyse binaire de l'exécutable ./test_bin")
            self.assertEqual(record["tool_call"]["name"], "kali_radare2")

    def test_ac4_zero_simulation_in_autonomous_cycle(self):
        """AC4: Invalidation of fake simulation in autonomous execution cycle."""
        async def run_test():
            # Executing cycle without mock must NOT return 'status': 'simulated'
            result = await self.hermes.execute_autonomous_cycle("echo 'TEST_ZERO_SIMULATION'")
            self.assertTrue(result["is_safe"])
            for turn in result["trajectory"]:
                raw = turn.get("raw_result", {})
                self.assertNotEqual(raw.get("status"), "simulated", "Simulation status is strictly banned.")
        asyncio.run(run_test())

    def test_ac5_hyperdimensional_continuous_semantics(self):
        """AC5: Proves that semantic memory preserves cosine similarity between related concepts (No random MD5)."""
        engine = BinaryHologramEngine(dimension=768)

        v_sec1 = engine._hash_projection("Audit de sécurité nmap et scanner de ports réseau")
        v_sec2 = engine._hash_projection("Analyse de vulnérabilités et scan nmap des services")
        v_cake = engine._hash_projection("Recette de cuisine gâteau au chocolat et crème anglaise")

        cos_related = float(np.dot(v_sec1, v_sec2))
        cos_unrelated = float(np.dot(v_sec1, v_cake))

        # Related concepts must have significantly higher similarity than unrelated concepts
        self.assertGreater(cos_related, cos_unrelated, "Semantically overlapping texts must have higher cosine similarity.")
        self.assertGreater(cos_related, 0.25, "Related texts must share positive projection components.")

        # Test ranking in memory
        engine.add_entry("Audit réseau et scan de ports nmap", meta={"topic": "pentest"})
        engine.add_entry("Recette de cuisine gâteau", meta={"topic": "food"})

        results = engine.search_nearest("scanner les ports avec nmap", top_k=2)
        self.assertGreater(len(results), 0)
        # First ranked result must be the pentest topic
        best_similarity, best_meta = results[0]
        self.assertEqual(best_meta["topic"], "pentest")

    def test_ac6_security_agent_kali_arsenal_exposure(self):
        """AC6: Verifies SecurityAgent exposes real Kali arsenal and handles tool execution."""
        mock_gw = MagicMock()
        mock_gw.list_files.return_value = {"success": True, "items": []}
        mock_gw.execute_command.return_value = {
            "success": True,
            "stdout": "sqlmap 1.8.x - automatic SQL injection tool",
            "stderr": "",
            "returncode": 0
        }

        agent = SecurityAgent(tool_gateway=mock_gw)
        tools = agent.get_available_kali_tools()
        self.assertIsInstance(tools, dict)
        self.assertGreater(len(tools), 0)

        async def run_task():
            res = await agent.execute_task("Vérifier la sécurité globale du projet")
            self.assertEqual(res["status"], "completed")
            self.assertIn("kali_arsenal", res)
            self.assertGreater(res["kali_arsenal"]["detected_tools_count"], 0)

        asyncio.run(run_task())

    def test_ac7_adaptive_self_healing_react_loop(self):
        """AC7: Proves that the ReAct loop executes tools, listens to output, and self-corrects until convergence."""
        async def run_test():
            # Mock executor that fails on turn 1 (simulating unrecognized option) and succeeds on turn 2
            mock_gw = MagicMock()
            mock_gw.execute_command.side_effect = [
                {"success": False, "stderr": "Error: unrecognized option '--broken-flag'", "exit_code": 1},
                {"success": True, "stdout": "PORT_8000_OPEN_SUCCESS", "stderr": "", "exit_code": 0}
            ]

            class AdaptiveExecutor:
                def __init__(self, gw):
                    self.tool_gateway = gw

            result = await self.hermes.execute_adaptive_react_loop(
                objective="Scanner port 8000 --broken-flag",
                executor=AdaptiveExecutor(mock_gw),
                max_turns=3
            )

            # Verification of real-time OODA loop:
            # 1. Mission must have converged
            self.assertTrue(result["converged"], "Adaptive loop must converge after self-correction.")
            # 2. At least 2 turns were executed
            self.assertGreaterEqual(result["turns_completed"], 2)
            # 3. An adaptation was performed
            self.assertGreaterEqual(result["adaptations_performed"], 1)
            # 4. Trajectory contains thinking and adaptation
            phases = [t["phase"] for t in result["trajectory"]]
            self.assertIn("thinking_and_adaptation", phases)
            self.assertIn("tool_execution", phases)

        asyncio.run(run_test())


if __name__ == "__main__":
    unittest.main()
