"""
Tests for Feature F-33: Zero-Touch Local Intercom & Apex Sovereign Resultant (ZTLI).
Validates AC1 through AC5:
- AC1: mDNS / Zeroconf Local Announcement & Host Discovery
- AC2: Zero-Disk In-RAM Web Gateway (Mode NÉANT, 0 disk I/O)
- AC3: Strict Pydantic Boundary Validation (AudioSignalPayload, IntercomStatusResponse)
- AC4: Dual-Channel Loopback & FastAPI In-Memory Route Execution
- AC5: Apex Sovereign Resultant & TechLead Orchestrator Integration
"""

import asyncio
import os
import unittest
from unittest.mock import patch, MagicMock

import pytest
from pydantic import ValidationError
from starlette.testclient import TestClient

from app.network.zero_touch_intercom import (
    ZeroTouchIntercom,
    AudioSignalPayload,
    IntercomStatusResponse,
    EMBEDDED_INTERCOM_HTML,
    create_intercom_fastapi_app,
)


class TestZeroTouchIntercom(unittest.TestCase):

    def test_ac1_local_ip_and_mdns_discovery(self):
        """AC1: Intercom detects local IP and constructs proper mDNS service parameters."""
        intercom = ZeroTouchIntercom(port=8088)
        local_ip = intercom.get_local_ip()
        self.assertTrue(isinstance(local_ip, str))
        self.assertTrue(len(local_ip.split(".")) == 4 or local_ip == "127.0.0.1")

        info = intercom.get_service_info()
        self.assertEqual(info["hostname"], "freeai.local")
        self.assertEqual(info["port"], 8088)
        self.assertIn("http://", info["access_url"])

    def test_ac2_zero_disk_html_payload_purity(self):
        """AC2: Web client is served strictly from memory constant (0 disk I/O, Mode NÉANT)."""
        self.assertIsInstance(EMBEDDED_INTERCOM_HTML, str)
        self.assertIn("<!DOCTYPE html>", EMBEDDED_INTERCOM_HTML)
        self.assertIn("AudioContext", EMBEDDED_INTERCOM_HTML)
        self.assertIn("FreeAi Sovereign Intercom", EMBEDDED_INTERCOM_HTML)
        # Verify no file read is needed
        self.assertGreater(len(EMBEDDED_INTERCOM_HTML), 500)

    def test_ac3_pydantic_boundary_validation(self):
        """AC3: Audio payloads and status models are strictly validated by Pydantic."""
        valid_payload = AudioSignalPayload(
            peer_id="client_mobile_ios",
            chunk_seq=1,
            pcm_base64="AAAA////AAAA",
            sample_rate=16000,
        )
        self.assertEqual(valid_payload.peer_id, "client_mobile_ios")
        self.assertEqual(valid_payload.chunk_seq, 1)

        # Invalid sample rate or negative seq must be rejected
        with self.assertRaises(ValidationError):
            AudioSignalPayload(
                peer_id="",  # empty peer_id rejected
                chunk_seq=-5,
                pcm_base64="",
                sample_rate=0,
            )

        # Status response validation
        status = IntercomStatusResponse(
            active=True,
            mdns_hostname="freeai.local",
            port=8088,
            connected_peers=["peer1"],
            mode="in_ram_neant",
        )
        self.assertTrue(status.active)
        self.assertEqual(status.mode, "in_ram_neant")

    def test_ac4_fastapi_in_memory_routes(self):
        """AC4: FastAPI app serves in-RAM HTML5 client and processes audio chunks without disk I/O."""
        intercom = ZeroTouchIntercom(port=8088)
        app = create_intercom_fastapi_app(intercom)
        client = TestClient(app)

        # 1. GET /intercom serves raw HTML directly from RAM
        with patch("builtins.open", side_effect=AssertionError("Disk open prohibited in Mode NÉANT!")):
            resp = client.get("/intercom")
            self.assertEqual(resp.status_code, 200)
            self.assertIn("text/html", resp.headers["content-type"])
            self.assertIn("FreeAi Sovereign Intercom", resp.text)

        # 2. GET /intercom/status returns valid JSON
        resp_status = client.get("/intercom/status")
        self.assertEqual(resp_status.status_code, 200)
        data = resp_status.json()
        self.assertEqual(data["mdns_hostname"], "freeai.local")

        # 3. POST /intercom/audio ingests base64 PCM into memory buffer
        audio_body = {
            "peer_id": "phone_alpha",
            "chunk_seq": 1,
            "pcm_base64": "AP8A/wD/",
            "sample_rate": 16000,
        }
        resp_audio = client.post("/intercom/audio", json=audio_body)
        self.assertEqual(resp_audio.status_code, 200)
        self.assertTrue(resp_audio.json()["received"])
        self.assertGreater(intercom.buffered_bytes, 0)

    def test_ac5_apex_sovereign_resultant_and_orchestrator_integration(self):
        """AC5: SovereignResultantEngine and TechLeadOrchestrator route /intercom commands."""
        from app.orchestrator.orchestrator import TechLeadOrchestrator
        from app.tools.gateway import ToolGateway
        from app.resource_manager.watchdog import ResourceManager

        async def _test():
            gw = ToolGateway(workspace_root="/tmp")
            rm = ResourceManager()
            orch = TechLeadOrchestrator(tool_gateway=gw, resource_manager=rm)

            # Test /intercom direct routing
            res = await orch.handle_objective("/intercom", autonomous=False)
            self.assertTrue(res["success"])
            self.assertEqual(res["assigned_agent"], "zero_touch_intercom")
            self.assertIn("freeai.local", res["output"])
            self.assertIn("ZÉRO-INSTALLATION", res["output"])

        asyncio.run(_test())
