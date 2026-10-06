"""Unit & Integration Tests for Satellite Mesh and 24/7 Continuous Cognition (F-27).
Author: SAGBO MICHAEL (Lead Full-Stack & Sovereign Backend)
"""

import os
import re
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from app.network.satellite_mesh import SovereignSatelliteMesh
from app.cognition.continuous_cognition import PerpetualLearner24x7


@pytest.fixture
def mesh_instance(tmp_path):
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
    # Create fake git repos
    for s in mock_satellites.values():
        (s["local_path"] / ".git").mkdir(parents=True)

    mesh = SovereignSatelliteMesh(satellites=mock_satellites)
    mesh.LEDGER_FILE = tmp_path / ".test_satellite_mesh_ledger.json"
    return mesh


class TestSatelliteMesh:
    """Validates multi-repo satellite mesh, pull operations, and P2P gateway."""

    def test_mesh_status_detection(self, mesh_instance):
        status = mesh_instance.get_mesh_status()
        assert status["mesh_active"] is True
        assert status["total_satellites"] == 2
        assert "forge" in status["satellites"]
        assert "laurince_jarvis" in status["satellites"]
        assert status["satellites"]["laurince_jarvis"]["owner"] == "LaurinceG4N0"

    def test_sync_satellite_and_pull(self, mesh_instance):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="Already up to date.")
            res = mesh_instance.sync_satellite("laurince_jarvis")
            assert res["success"] is True
            assert res["satellite"] == "laurince_jarvis"

    def test_apply_freeai_resultant_touch(self, mesh_instance):
        raw_code = "def peer_func():\n    print('🚀 Hello from peer! 🔥')\n"
        result = mesh_instance.apply_freeai_resultant_touch("peer_feature", raw_code)
        
        assert result["status"] == "TRANSMUTED"
        assert "🚀" not in result["resultant_code"]
        assert "🔥" not in result["resultant_code"]
        assert "Michael SAGBO" in result["resultant_code"]
        assert "Mode NÉANT" in result["resultant_code"]
        assert result["capability_id"].startswith("CAP-")

    def test_probe_peer_machine_socket(self, mesh_instance):
        # Local probe test
        probe_res = mesh_instance.probe_peer_machine(peer_host="127.0.0.1", peer_port=65432)
        assert "reachable" in probe_res
        assert probe_res["protocol"] == "SOVEREIGN_TCP_P2P"

    def test_generate_peer_handshake(self, mesh_instance):
        handshake = mesh_instance.generate_peer_handshake("Laurince_Node_01")
        assert handshake["sender"] == "FreeAI_Core_Michael_SAGBO"
        assert handshake["peer_target"] == "Laurince_Node_01"
        assert len(handshake["handshake_token"]) == 64
        assert handshake["status"] == "EMITTED"


class TestContinuousCognition24x7:
    """Validates 24/7 perpetual learning engine and growth summaries."""

    def test_learning_cycle_execution(self, mesh_instance, tmp_path):
        learner = PerpetualLearner24x7(mesh=mesh_instance)
        learner.LEDGER_FILE = tmp_path / ".test_growth_ledger.json"

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="up to date")
            cycle_result = learner.run_learning_cycle()

            assert cycle_result["status"] == "COMPLETED"
            assert "cycle" in cycle_result
            assert cycle_result["cycle"]["phase"] == "24/7 Perpetual Ingestion"
            assert "growth_token" in cycle_result["cycle"]

    def test_growth_summary_noble_typography(self, mesh_instance, tmp_path):
        learner = PerpetualLearner24x7(mesh=mesh_instance)
        learner.LEDGER_FILE = tmp_path / ".test_growth_ledger.json"
        
        summary = learner.generate_growth_summary()
        assert "FREEAI CONTINUOUS COGNITION (24/7 PERPETUAL SATELLITE ENGINE)" in summary
        assert "Laurince MyJarvis" in summary
        assert "Forge Pipeline" in summary

        # Strict noble typography check: Zero raw emojis allowed in summary
        raw_emojis = re.findall(r"[\U0001F300-\U0001FAFF]", summary)
        assert len(raw_emojis) == 0, f"Raw emojis found in growth summary: {raw_emojis}"
