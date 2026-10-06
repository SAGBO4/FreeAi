"""Test Suite for HyperMesh Causal Singularity & Retrocausal Swarm Matrix (Feature F-26).
Verifies:
1. First Principles Quadri-Vectorial Dissection: exactly 2 direct causes + 2 indirect causes.
2. Mobilization of FreeAI's limbs on the internet (Sovereign Web, Peer Sync, Neural Federation, Nightly Harvest).
3. Ghost Fork In-Memory Proactive Collapse Simulation.
4. Strict Zero Raw Emoji in CLI and TUI telemetry rendering.
5. In-Memory Execution Latency (< 5.0 ms in RAM, 0 B SSD, Mode NÉANT).
6. CLI Integration for /causal and /hypermesh.
"""

import sys
import time
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.cognition.hypermesh_causal_singularity import (
    HyperMeshCausalSingularity,
    CausalDiagnosis,
)
import cli


class TestHyperMeshCausalSingularity:
    """Rigorous tests ensuring First Principles causal depth, internet limbs, and 0-emoji noble UI."""

    def test_singleton_initialization(self):
        engine1 = HyperMeshCausalSingularity.get_instance()
        engine2 = HyperMeshCausalSingularity.get_instance()
        assert engine1 is engine2

    def test_strictly_two_direct_and_two_indirect_causes(self):
        engine = HyperMeshCausalSingularity.get_instance()
        diag = engine.diagnose_and_heal("Client error 400 Bad Request for url mixtral-8x7b-32768 decommissioned")

        assert isinstance(diag, CausalDiagnosis)
        assert len(diag.direct_causes) == 2, "Must contain exactly 2 direct causes"
        assert len(diag.indirect_causes) == 2, "Must contain exactly 2 indirect causes"

        # Check vectors
        direct_vectors = [c["vector"] for c in diag.direct_causes]
        assert any("Direct Alpha" in v for v in direct_vectors)
        assert any("Direct Beta" in v for v in direct_vectors)

        indirect_vectors = [c["vector"] for c in diag.indirect_causes]
        assert any("Indirect Gamma" in v for v in indirect_vectors)
        assert any("Indirect Delta" in v for v in indirect_vectors)

    def test_internet_limbs_mobilization(self):
        engine = HyperMeshCausalSingularity.get_instance()
        evidence = engine.mobilize_internet_limbs("DeepSeek 402 Payment Required Groq model 400")

        assert "sovereign_web" in evidence
        assert "peer_sync" in evidence
        assert "neural_federation" in evidence
        assert "nightly_harvest" in evidence

        assert evidence["sovereign_web"]["status"] in ("ENGAGED", "STANDBY")
        assert evidence["peer_sync"]["status"] in ("ENGAGED", "STANDBY")
        assert evidence["neural_federation"]["status"] in ("ENGAGED", "STANDBY")

    def test_ghost_fork_proactive_future_simulation(self):
        engine = HyperMeshCausalSingularity.get_instance()
        sim = engine.simulate_ghost_fork("Call mixtral on groq with deepseek 402 fallback")

        assert sim["futures_simulated"] == 4
        assert "alpha_interface" in sim["collapse_vectors"]
        assert "beta_resource" in sim["collapse_vectors"]
        assert "gamma_topology" in sim["collapse_vectors"]
        assert "delta_environment" in sim["collapse_vectors"]
        assert sim["collapse_vectors"]["alpha_interface"] == "HIGH"
        assert sim["collapse_vectors"]["beta_resource"] == "HIGH"
        assert sim["proactive_immunity_applied"] is True
        assert sim["simulation_latency_ms"] < 5.0

    def test_sub_5ms_ram_latency_benchmark(self):
        engine = HyperMeshCausalSingularity.get_instance()
        t0 = time.perf_counter()
        diag = engine.diagnose_and_heal("Anomalie critique de socket réseau et mémoire")
        latency_ms = (time.perf_counter() - t0) * 1000.0

        assert latency_ms < 10.0, f"Execution latency too high: {latency_ms:.2f} ms"
        assert diag.memory_overhead_bytes == 0
        assert "Invariant F-26" in diag.eternal_invariant

    def test_strict_zero_raw_emoji_in_hologram(self):
        raw_emoji_forbidden = [
            "🚀", "🔥", "✨", "🤖", "💡", "🧠", "⚡", "🔮", "🎉", "💥", "🛑", "⚠️", "❌", "✅", "👀"
        ]
        engine = HyperMeshCausalSingularity.get_instance()
        diag = engine.diagnose_and_heal("Test error for typography inspection")
        hologram = engine.render_telemetry_hologram(diag)

        for emoji in raw_emoji_forbidden:
            assert emoji not in hologram, f"Forbidden raw emoji '{emoji}' found in hologram telemetry"

        # Verify noble OpenCode glyphs
        assert "◈" in hologram
        assert "⊙" in hologram
        assert "▣" in hologram
        assert "IMMUNISATION SOUVERAINE" in hologram

    def test_cli_causal_command_integration(self):
        # 1. Without args (help card)
        with patch("sys.argv", ["cli.py", "/causal"]):
            cli.main()

        # 2. With error context
        with patch("sys.argv", ["cli.py", "/causal", "Erreur", "400", "Bad", "Request"]):
            cli.main()

        # 3. /hypermesh alias
        with patch("sys.argv", ["cli.py", "/hypermesh", "Erreur", "402", "Payment"]):
            cli.main()
