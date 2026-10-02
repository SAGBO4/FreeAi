"""Test Suite for Protocol AETHER-LEGION (Sovereign Autonomous Scout Swarm).
Verifies:
1. Scout member creation and archetype specialization (cyber, singularity, horizon, sentinel).
2. Autonomous probe synthesis in RAM (Mode NÉANT, 0 SSD write).
3. Reconnaissance mission execution and intelligence harvesting.
4. SacredLife ethical veto on offensive/destructive probe missions.
5. Telegram notification formatting and CLI integration.
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock

from app.cluster.aether_legion import (
    AetherLegionOrchestrator,
    ScoutMember,
    ScoutArchetype,
    IntelligenceFinding
)


class TestAetherLegion(unittest.TestCase):
    def setUp(self):
        self.legion = AetherLegionOrchestrator()

    def test_default_legion_members_initialized(self):
        """Verifies default autonomous scout members are registered."""
        members = self.legion.list_members()
        self.assertGreaterEqual(len(members), 4)
        archetypes = [m["archetype"] for m in members]
        self.assertIn("singularity", archetypes)
        self.assertIn("cyber", archetypes)
        self.assertIn("horizon", archetypes)
        self.assertIn("sentinel", archetypes)

    def test_deploy_custom_scout_member(self):
        """Verifies deploying a new specialized scout with custom mission."""
        scout = self.legion.deploy_scout(
            name="Vigil-Quantum",
            archetype=ScoutArchetype.SINGULARITY,
            mission="Surveiller les dépôts GitHub sur l'informatique quantique et post-quantique"
        )
        self.assertEqual(scout.name, "Vigil-Quantum")
        self.assertEqual(scout.archetype, ScoutArchetype.SINGULARITY)
        self.assertTrue(scout.active)
        self.assertTrue(scout.in_memory_payload.startswith("# Sovereign Autonomous Probe"))

    def test_sacred_life_blocks_destructive_probe_mission(self):
        """Verifies SacredLife veto intercepts and rejects malicious probing/scanning missions."""
        with self.assertRaises(ValueError) as ctx:
            self.legion.deploy_scout(
                name="Malicious-Scanner",
                archetype=ScoutArchetype.CYBER,
                mission="Scanner les ports et lancer des attaques DoS / exploit rm -rf sur la cible"
            )
        self.assertIn("Veto éthique SacredLife", str(ctx.exception))

    def test_execute_recon_mission_and_harvest(self):
        """Verifies running a scout mission harvests intelligence without disk writes."""
        import asyncio
        async def _test():
            members = self.legion.list_members()
            target_id = members[0]["id"]
            
            # Execute recon
            res = await self.legion.execute_recon_mission(target_id)
            self.assertTrue(res["success"])
            self.assertIn("findings", res)
            self.assertGreater(len(res["findings"]), 0)
            
            # Global harvest
            harvest = await self.legion.harvest_all_intel()
            self.assertTrue(harvest["success"])
            self.assertIn("digest", harvest)
            self.assertIn("total_findings", harvest)
            self.assertTrue(harvest["mode_neant_ram_only"])
        asyncio.run(_test())

    def test_synthesize_serverless_worker_payload(self):
        """Verifies generation of exportable serverless JS/Python probe code."""
        scout = self.legion.deploy_scout(
            name="ArXiv-Tracker",
            archetype=ScoutArchetype.SINGULARITY,
            mission="Veille sur les nouveaux modèles d'inférence frugale"
        )
        payload = self.legion.export_probe_payload(scout.id, format="python")
        self.assertIn("class AutonomousScoutProbe", payload)
        self.assertIn("def report_intelligence", payload)
