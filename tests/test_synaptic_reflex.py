"""Tests for Feature F-25: Synaptic Reflex Radar & Thought Hologram Matrix.
Validates:
1. Pure in-memory RAM execution (< 5ms latency).
2. Spectral intent decomposition (density, autonomy vector, criticality level).
3. Thought hologram matrix terminal rendering (Noble OpenCode typography).
4. Mode NÉANT compliance (0 B SSD write).
5. STRICTLY ZERO RAW EMOJIS in code and terminal output.
6. CLI integration (/reflex and /synapse handlers).
"""

import os
import sys
import re
import time
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.cognition.synaptic_reflex import (
    SynapticReflexEngine,
    CriticalityLevel,
    QuantumCognitiveState,
    IntentCategory,
)


class TestSynapticReflexEngine(unittest.TestCase):
    """Rigorous test suite for SynapticReflexEngine."""

    def setUp(self):
        self.engine = SynapticReflexEngine()

    def test_engine_initialization_and_telemetry(self):
        """Validates proper instantiation and initial zero-cost state."""
        telemetry = self.engine.get_telemetry()
        self.assertEqual(telemetry["total_analyses"], 0)
        self.assertEqual(telemetry["average_latency_ms"], 0.0)
        self.assertEqual(telemetry["disk_writes_bytes"], 0)
        self.assertTrue(telemetry["mode_neant_active"])
        self.assertEqual(telemetry["ram_history_count"], 0)

    def test_idle_and_empty_prompt(self):
        """Validates graceful fallback for empty or whitespace prompts."""
        for empty_val in ["", "   ", "\n\t  "]:
            data = self.engine.analyze_synaptic_intent(empty_val)
            self.assertEqual(data["algorithmic_density"], 0.0)
            self.assertEqual(data["system_criticality"], CriticalityLevel.LOW.value)
            self.assertEqual(data["criticality_score"], 0.0)
            self.assertEqual(data["intent_category"], IntentCategory.IDLE_RESONANCE.value)
            self.assertEqual(data["quantum_state"], QuantumCognitiveState.RESTING_POTENTIAL.value)
            self.assertIn("SacredLifeSentinel", data["architecture_prerequisites"])
            self.assertLess(data["latency_ms"], 5.0)

    def test_high_algorithmic_density_analysis(self):
        """Validates detection of dense syntax and algorithmic code structures."""
        prompt = (
            "async def process_matrix(items: List[int]) -> Dict[str, Any]:\n"
            "    for x in items:\n"
            "        yield eval(x) + (lambda y: y * 2)(x)\n"
            "    return {'status': 200, 'res': select * from cache}\n"
        )
        data = self.engine.analyze_synaptic_intent(prompt)
        self.assertGreater(data["algorithmic_density"], 0.35)
        self.assertIn("ToolGateway.fs", data["architecture_prerequisites"])
        self.assertIn("LSP.pyright", data["anticipated_toolchains"])
        self.assertLess(data["latency_ms"], 5.0)

    def test_cognitive_autonomy_vector(self):
        """Validates dynamic scaling of the autonomy vector between imperative and passive queries."""
        # Highly imperative proactive objective
        imperative_prompt = (
            "Construis, implémente et orchestre de bout en bout l'architecture distribuée "
            "complète du cluster Raft avec auto-guérison et tests de charge"
        )
        data_imp = self.engine.analyze_synaptic_intent(imperative_prompt)
        self.assertGreaterEqual(data_imp["cognitive_autonomy"], 0.65)
        self.assertEqual(data_imp["intent_category"], IntentCategory.ARCHITECTURAL_ENGINEERING.value)
        self.assertIn("AetherSwarmOrchestrator", data_imp["anticipated_toolchains"])

        # Passive informational inquiry
        passive_prompt = "Bonjour, qu'est-ce que le protocole TCP ? Peux-tu m'expliquer son fonctionnement ?"
        data_pass = self.engine.analyze_synaptic_intent(passive_prompt)
        self.assertLessEqual(data_pass["cognitive_autonomy"], 0.40)
        self.assertEqual(data_pass["intent_category"], IntentCategory.KNOWLEDGE_SYNTHESIS.value)

    def test_system_criticality_classification(self):
        """Validates identification of critical commands and destructive security risks."""
        # Critical security & root trigger
        critical_prompt = "sudo rm -rf /etc/shadow && dd if=/dev/zero of=/dev/sda wipe"
        data_crit = self.engine.analyze_synaptic_intent(critical_prompt)
        self.assertEqual(data_crit["system_criticality"], CriticalityLevel.CRITICAL.value)
        self.assertGreaterEqual(data_crit["criticality_score"], 0.85)
        self.assertEqual(data_crit["intent_category"], IntentCategory.ADVERSARIAL_DEFENSE.value)
        self.assertEqual(data_crit["quantum_state"], QuantumCognitiveState.ADVERSARIAL_ALERT.value)
        self.assertIn("ShadowDockerExecutor", data_crit["architecture_prerequisites"])
        self.assertIn("PhantomBusIPC", data_crit["architecture_prerequisites"])

        # High operational impact
        high_prompt = "git push --force origin main && docker rm -f redis_node"
        data_high = self.engine.analyze_synaptic_intent(high_prompt)
        self.assertIn(data_high["system_criticality"], [CriticalityLevel.HIGH.value, CriticalityLevel.CRITICAL.value])

        # Low impact read-only
        low_prompt = "Affiche la météo et donne-moi l'heure courante"
        data_low = self.engine.analyze_synaptic_intent(low_prompt)
        self.assertEqual(data_low["system_criticality"], CriticalityLevel.LOW.value)
        self.assertLess(data_low["criticality_score"], 0.35)

    def test_spectral_harmonics_structure(self):
        """Validates spectral harmonics metrics completeness."""
        prompt = "Vérifie les branches git et compare le diff avec l'arbre distant"
        data = self.engine.analyze_synaptic_intent(prompt)
        harmonics = data["spectral_harmonics"]
        self.assertIn("syntactic_depth", harmonics)
        self.assertIn("entropy_flux", harmonics)
        self.assertIn("toolchain_entropy", harmonics)
        self.assertIn("epistemic_certainty", harmonics)
        for k, v in harmonics.items():
            self.assertIsInstance(v, float)
            self.assertGreaterEqual(v, 0.0)
            self.assertLessEqual(v, 1.0)

    def test_sub_5ms_latency_benchmark_in_ram(self):
        """Benchmarks 100 consecutive runs to ensure sub-5ms pure RAM execution."""
        prompts = [
            "Refactorise le module d'arbitrage consensus avec lock sans attente",
            "sudo chmod 777 /var/run/docker.sock",
            "Explique la différence entre Coroutine et Thread en Python",
            "git status et rollback des commits non testés",
            "Indexe les vecteurs dans l'hologramme binaire 1-bit AVX-512",
            "",
            "npm test -- --coverage",
        ]

        latencies = []
        for i in range(100):
            p = prompts[i % len(prompts)]
            data = self.engine.analyze_synaptic_intent(p)
            latencies.append(data["latency_ms"])
            self.assertLess(
                data["latency_ms"], 5.0,
                f"Latency exceeded 5ms limit: {data['latency_ms']} ms on prompt: '{p}'"
            )

        avg_latency = sum(latencies) / len(latencies)
        self.assertLess(avg_latency, 2.0, f"Average latency too high: {avg_latency} ms")

        # Telemetry should reflect 100 analyses
        telemetry = self.engine.get_telemetry()
        self.assertEqual(telemetry["total_analyses"], 100)
        self.assertGreater(telemetry["average_latency_ms"], 0.0)

    def test_thought_hologram_matrix_rendering(self):
        """Validates generation of noble telemetric thought hologram matrix."""
        prompt = "Développe une boucle de consensus Raft p2p avec transport mémoire"
        data = self.engine.analyze_synaptic_intent(prompt)
        hologram = self.engine.render_thought_hologram(data)

        self.assertIsInstance(hologram, str)
        self.assertIn("SYNAPTIC REFLEX RADAR // THOUGHT HOLOGRAM MATRIX (F-25)", hologram)
        self.assertIn("COGNITIVE PROACTIVITY ENGINE · ZERO SSD · SUB-5MS RAM", hologram)
        self.assertIn("Densité Algorithmique", hologram)
        self.assertIn("Autonomie Cognitive", hologram)
        self.assertIn("Criticité Système", hologram)
        self.assertIn("0 B (Volatile RAM Pur)", hologram)
        self.assertIn("SACRED_LIFE_PASS", hologram)

        # Check noble geometric glyphs
        self.assertIn("◈", hologram)
        self.assertIn("⊙", hologram)
        self.assertIn("▣", hologram)
        self.assertIn("►", hologram)
        self.assertIn("■", hologram)
        self.assertIn("□", hologram)

    def test_strict_zero_raw_emoji_enforcement(self):
        """Strictly validates ZERO raw emojis exist in output or source code."""
        # Comprehensive regex covering Unicode Emoji ranges
        emoji_pattern = re.compile(
            r"[\U0001F600-\U0001F64F"  # Emoticons
            r"\U0001F300-\U0001F5FF"  # Misc Symbols & Pictographs
            r"\U0001F680-\U0001F6FF"  # Transport & Map
            r"\U0001F700-\U0001F77F"  # Alchemical
            r"\U0001F780-\U0001F7FF"  # Geometric Extended
            r"\U0001F800-\U0001F8FF"  # Supplemental Arrows-C
            r"\U0001F900-\U0001F9FF"  # Supplemental Symbols & Pictographs
            r"\U0001FA00-\U0001FA6F"  # Chess
            r"\U0001FA70-\U0001FAFF"  # Symbols & Pictographs Ext-A
            r"\U00002600-\U000026FF"  # Misc Symbols (lightning, coffee, warn...)
            r"\U00002700-\U000027BF]"  # Dingbats
        )

        # 1. Test source file purity
        source_path = Path(__file__).parent.parent / "app" / "cognition" / "synaptic_reflex.py"
        with open(source_path, "r", encoding="utf-8") as f:
            source_content = f.read()

        source_emojis = emoji_pattern.findall(source_content)
        self.assertEqual(
            source_emojis, [],
            f"Found forbidden raw emojis in source code: {source_emojis}"
        )

        # 2. Test hologram renderings across diverse test prompts
        test_prompts = [
            "Prompt ordinaire",
            "sudo rm -rf /",
            "def test(): pass",
            "Construis l'architecture complète",
            "",
            "Qu'est-ce que le mode NÉANT ?",
        ]
        for p in test_prompts:
            data = self.engine.analyze_synaptic_intent(p)
            rendered = self.engine.render_thought_hologram(data)
            output_emojis = emoji_pattern.findall(rendered)
            self.assertEqual(
                output_emojis, [],
                f"Found forbidden raw emojis in rendered hologram for '{p}': {output_emojis}"
            )

    def test_reset_ephemeral_state(self):
        """Validates ephemeral state reset in RAM."""
        self.engine.analyze_synaptic_intent("test 1")
        self.engine.analyze_synaptic_intent("test 2")
        self.assertEqual(self.engine.get_telemetry()["total_analyses"], 2)

        self.engine.reset_ephemeral_state()
        telemetry = self.engine.get_telemetry()
        self.assertEqual(telemetry["total_analyses"], 0)
        self.assertEqual(telemetry["ram_history_count"], 0)
        self.assertEqual(telemetry["average_latency_ms"], 0.0)

    def test_cli_run_reflex_handler(self):
        """Validates cli.py run_reflex function execution without errors or emojis."""
        from cli import run_reflex

        mock_tech_lead = MagicMock()
        mock_tech_lead.synaptic_reflex = self.engine

        # Test telemetry mode (no args)
        with patch("cli.console.print") as mock_print:
            run_reflex(mock_tech_lead, [])
            self.assertTrue(mock_print.called)

        # Test intent radar analysis with prompt args
        with patch("cli.console.print") as mock_print:
            run_reflex(mock_tech_lead, ["Architecte", "le", "cluster", "mesh", "P2P"])
            self.assertTrue(mock_print.called)
            # Verify the printed argument is the rendered hologram string
            args_called = mock_print.call_args[0]
            printed_output = args_called[0]
            self.assertIn("SYNAPTIC REFLEX RADAR // THOUGHT HOLOGRAM MATRIX", str(printed_output))


if __name__ == "__main__":
    unittest.main()
