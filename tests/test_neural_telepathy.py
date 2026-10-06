"""Unit & Integration Tests for Omni-Satellite Neural Telepathy & Cryptographic Thought Sync.
Author: SAGBO MICHAEL (Lead Full-Stack & Sovereign Backend)
Specialized AI Agent: ai-extreme-innovator
"""

import re
import pytest
import time
from unittest.mock import patch, MagicMock

from app.network.neural_telepathy import (
    VectorThoughtBeam,
    CredoSentinelMembrane,
    NeuralTelepathyMatrix
)
from app.network.satellite_mesh import SovereignSatelliteMesh


class TestNeuralTelepathy:
    """Validates the supreme personal touch: Neural Telepathy and Thought Sync."""

    def test_vector_thought_beam_creation_and_normalization(self):
        matrix = NeuralTelepathyMatrix.get_instance()
        vec = matrix.compute_thought_vector("AST_OPTIMIZATION_PASS")
        assert len(vec) == 64
        # L2 norm must be approximately 1.0
        norm = sum(x * x for x in vec) ** 0.5
        assert pytest.approx(norm, 0.001) == 1.0

    def test_credo_sentinel_membrane_signature_and_security(self):
        matrix = NeuralTelepathyMatrix.get_instance()
        beam = matrix.project_thought_beam(
            source_node="FreeAI_Core",
            target_node="Laurince_MyJarvis",
            concept="REFLEX_CACHE_LOOKUP",
            reflex_code="def lookup(k): return cache.get(k)"
        )

        # 1. Valid beam passes membrane check
        valid, reason = CredoSentinelMembrane.verify_membrane(beam)
        assert valid is True
        assert reason == "ACCEPTED_SOVEREIGN_PURITY"

        # 2. Tampered signature fails
        beam.credo_signature = "TAMPERED_HASH_00000000"
        valid, reason = CredoSentinelMembrane.verify_membrane(beam)
        assert valid is False
        assert "REJECTED_INVALID_CREDO_SIGNATURE" in reason

        # 3. Raw emoji injection is rejected
        beam_emoji = matrix.project_thought_beam(
            source_node="FreeAI_Core",
            target_node="Laurince_MyJarvis",
            concept="EMOJI_CONCEPT",
            reflex_code="print('Rocket 🚀')"
        )
        # Note: project_thought_beam auto-sanitizes raw emojis defensively, so let's test direct membrane injection
        beam_emoji.reflex_code = "print('Danger 🔥')"
        # Re-sign with emoji to test membrane rejection
        beam_emoji.credo_signature = CredoSentinelMembrane.sign_thought(
            beam_emoji.thought_id, beam_emoji.source_node, beam_emoji.concept, beam_emoji.reflex_code
        )
        valid, reason = CredoSentinelMembrane.verify_membrane(beam_emoji)
        assert valid is False
        assert "REJECTED_RAW_EMOJI_DETECTED" in reason

        # 4. Hostile payload is rejected
        beam_hostile = matrix.project_thought_beam(
            source_node="Peer_Hostile",
            target_node="FreeAI_Core",
            concept="HOSTILE_INJECTION",
            reflex_code="rm -rf / --no-preserve-root"
        )
        valid, reason = CredoSentinelMembrane.verify_membrane(beam_hostile)
        assert valid is False
        assert "REJECTED_HOSTILE_PAYLOAD" in reason

    def test_in_memory_mode_neant_and_resonance(self):
        matrix = NeuralTelepathyMatrix(max_ram_buffer=10)
        
        beam1 = matrix.project_thought_beam(
            source_node="FreeAI_Core",
            target_node="Laurince_MyJarvis",
            concept="LPU_STREAM_PARSER",
            reflex_code="def parse_lpu(chunk): return chunk.strip()"
        )
        beam2 = matrix.project_thought_beam(
            source_node="Forge_Engine",
            target_node="FreeAI_Core",
            concept="BUILD_PIPELINE_STABILITY",
            reflex_code="def build_check(): return True"
        )

        matches = matrix.resonate_query("LPU_STREAM_PARSER", top_k=2)
        assert len(matches) >= 1
        top_beam, score = matches[0]
        assert top_beam.concept == "LPU_STREAM_PARSER"
        assert score > 0.25  # Meaningful token overlap resonance
        if len(matches) > 1:
            # Second beam is unrelated and must have significantly lower resonance
            assert matches[1][1] < score

        # Check Mode NÉANT metrics: 0 SSD write
        telem = matrix.get_telemetry_report()
        assert telem["ssd_write_bytes"] == 0
        assert telem["mode_neant_certified"] is True
        assert telem["average_latency_ms"] < 10.0

    def test_satellite_mesh_neural_telepathy_integration(self, tmp_path):
        mock_satellites = {
            "forge": {
                "name": "Forge Pipeline Engine",
                "local_path": tmp_path / "forge",
                "remote_url": "git@github.com:misterkante/forge.git",
                "primary_branch": "main",
                "owner": "misterkante"
            },
            "laurince_jarvis": {
                "name": "Laurince MyJarvis Local Engine",
                "local_path": tmp_path / "my_jarvis",
                "remote_url": "git@github.com:LaurinceG4N0/my_jarvis.git",
                "primary_branch": "main",
                "owner": "LaurinceG4N0"
            }
        }
        mesh = SovereignSatelliteMesh(satellites=mock_satellites)
        mesh.LEDGER_FILE = tmp_path / ".test_ledger.json"

        # Project thought beam via mesh
        res = mesh.project_thought_beam(
            target_satellite="laurince_jarvis",
            concept="SHARED_MEMORY_REFLEX",
            reflex_code="def shared_reflex(): return True"
        )
        assert res["success"] is True
        assert res["mode_neant"] is True
        assert res["target"] == "laurince_jarvis"

        # Trigger omni-satellite telepathic pulse
        pulse_res = mesh.trigger_telepathic_mesh_pulse()
        assert pulse_res["pulse_success"] is True
        assert len(pulse_res["beams_propagated"]) == 3
        assert pulse_res["ssd_write_bytes"] == 0

    def test_noble_display_zero_raw_emojis(self):
        matrix = NeuralTelepathyMatrix.get_instance()
        display = matrix.format_noble_display()
        assert "FREEAI NEURAL TELEPATHY & CRYPTOGRAPHIC THOUGHT SYNC" in display
        assert "Mode NEANT 100% RAM Volatile" in display

        # Absolute noble typography assertion: zero raw emojis permitted
        raw_emojis = re.findall(r"[\U0001F300-\U0001FAFF]", display)
        assert len(raw_emojis) == 0, f"Raw emojis forbidden in noble display: {raw_emojis}"
