"""Test Suite for Protocol OMNI-CHIMERA (Self-Mutating Autonomous Ghost-Fabric).
Verifies:
1. Ghost Coder: autonomous code generation, sandboxed test execution, and Git branch packaging.
2. Self-Healing Sentinel: system health diagnostics, memory pressure relief, and proactive mitigation.
3. Offline Resilient Conduit: zero-network fallback and localized inference continuity.
4. Epigenetic Hot Mutator (Ultra-Innovation): runtime dynamic skill synthesis, safety verification, and zero-reboot hot module injection in volatile RAM (Mode NÉANT).
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock

from app.evolution.omni_chimera import (
    OmniChimeraOrchestrator,
    GhostCoderSubsystem,
    SelfHealingSentinel,
    OfflineResilientConduit,
    EpigeneticHotMutator
)


class TestOmniChimera(unittest.TestCase):
    def setUp(self):
        self.chimera = OmniChimeraOrchestrator()

    def test_epigenetic_hot_mutation_in_ram(self):
        """Verifies FreeAI can synthesize, verify, and graft a new skill into memory at runtime without rebooting."""
        mutator = self.chimera.hot_mutator
        skill_name = "quantum_hash_validator"
        code = '''
def execute_skill(payload: str) -> str:
    return f"Validated:{payload.upper()}"
'''
        res = mutator.synthesize_and_graft_skill(skill_name, code)
        self.assertTrue(res["success"])
        self.assertIn("grafted_in_ram", res)
        self.assertTrue(res["grafted_in_ram"])
        
        # Test executing the newly grafted skill directly from memory
        output = mutator.invoke_grafted_skill(skill_name, "sovereign_token_2026")
        self.assertEqual(output, "Validated:SOVEREIGN_TOKEN_2026")

    def test_epigenetic_hot_mutation_blocked_by_sentinel(self):
        """Verifies malicious or destructive skills are vetoed before grafting."""
        mutator = self.chimera.hot_mutator
        evil_skill = "trojan_wipe"
        evil_code = '''
import os
def execute_skill(payload: str):
    os.system("rm -rf /")
'''
        res = mutator.synthesize_and_graft_skill(evil_skill, evil_code)
        self.assertFalse(res["success"])
        self.assertIn("veto", res["error"].lower())

    def test_self_healing_diagnosis_and_remediation(self):
        """Verifies self-healing sentinel detects high memory and triggers remediation."""
        sentinel = self.chimera.self_healing
        with patch("psutil.virtual_memory") as mock_vm:
            mock_vm.return_value = MagicMock(percent=88.5, available=500 * 1024 * 1024)
            diag = sentinel.diagnose_system_health()
            self.assertFalse(diag["healthy"])
            self.assertIn("RAM critique", diag["issues"][0])

            # Apply remediation
            rem = sentinel.apply_remediation()
            self.assertTrue(rem["remediated"])
            self.assertIn("Purge des caches mémoire", rem["actions"][0])

    def test_offline_resilient_conduit_switch(self):
        """Verifies instant seamless switch to offline localized cognition when WAN drops."""
        conduit = self.chimera.offline_conduit
        with patch.object(conduit, "_ping_wan", return_value=False):
            status = conduit.evaluate_connectivity()
            self.assertEqual(status["mode"], "airgap_offline")
            self.assertTrue(status["local_fallback_engaged"])

    def test_ghost_coder_pipeline(self):
        """Verifies autonomous code synthesis, testing, and branch packaging."""
        async def _test():
            coder = self.chimera.ghost_coder
            mock_federation = MagicMock()
            mock_federation.consult_free_online_model = AsyncMock(return_value={
                "response": "def calculate_entropy(data): return len(set(data))"
            })
            coder.federation = mock_federation

            res = await coder.synthesize_feature_request(
                prompt="Calculateur d'entropie cryptographique",
                target_module="app/tools/entropy.py"
            )
            self.assertTrue(res["success"])
            self.assertIn("feat/ghost-", res["git_branch"])
            self.assertEqual(res["author"], "SAGBO MICHAEL (@SAGBO4)")
            self.assertIn("FreeAI", res["co_author"])
        import asyncio
        asyncio.run(_test())
