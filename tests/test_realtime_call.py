"""Tests for Realtime Call Gateway, Live Synesthetic Canvas, and Stealth Co-pilot.
Verifies Step 1 (Audio Duplex / Mini App), Step 2 (Synesthetic Canvas), and Step 3 (Stealth Co-pilot).
"""

import asyncio
import io
import json
import pytest
from app.voice.realtime_call import RealtimeCallGateway, LiveHologramSession, SessionStatus
from app.cognition.synesthetic_canvas import SynestheticCanvasStreamer, SynestheticFrameType
from app.orchestrator.orchestrator import TechLeadOrchestrator
from app.tools.gateway import ToolGateway
from app.resource_manager.watchdog import ResourceManager


@pytest.fixture
def call_gateway():
    return RealtimeCallGateway(port=8765)


@pytest.fixture
def canvas_streamer():
    return SynestheticCanvasStreamer()


@pytest.fixture
def orchestrator(tmp_path):
    gateway = ToolGateway(workspace_root=str(tmp_path))
    res_mgr = ResourceManager(target_mb=3500, hard_limit_mb=4000)
    return TechLeadOrchestrator(tool_gateway=gateway, resource_manager=res_mgr)


def test_session_creation_and_lifecycle(call_gateway):
    session = call_gateway.create_session(user="Michael SAGBO", user_id=12345678)
    assert session.session_id is not None
    assert session.user == "Michael SAGBO"
    assert session.status == SessionStatus.CONNECTING

    # Transition to live
    session.mark_connected()
    assert session.status == SessionStatus.LIVE

    # Ingest audio chunk in RAM (Zero-SSD, Zero-Disk)
    chunk = b"\x01\x02\x03\x04" * 64
    session.ingest_audio_chunk(chunk)
    assert session.get_audio_buffer_size() > 0

    # Close session
    session.close()
    assert session.status == SessionStatus.CLOSED


def test_synesthetic_canvas_mermaid_and_code_projection(canvas_streamer):
    # Test Mermaid diagram extraction from architectural spoken prompt
    frame_mermaid = canvas_streamer.generate_frame_from_speech(
        speech_text="On va concevoir une architecture cyber avec un Reverse Proxy et une passerelle API chiffrée."
    )
    assert frame_mermaid.frame_type == SynestheticFrameType.MERMAID
    assert "graph" in frame_mermaid.payload or "flowchart" in frame_mermaid.payload or "classDiagram" in frame_mermaid.payload

    # Test Code projection from python spoken prompt
    frame_code = canvas_streamer.generate_frame_from_speech(
        speech_text="Voici la fonction Python def sanitize_input(val): return val.strip() pour sécuriser l'entrée."
    )
    assert frame_code.frame_type == SynestheticFrameType.CODE
    assert "def " in frame_code.payload

    # Test UI component projection from Shadcn UI prompt
    frame_ui = canvas_streamer.generate_frame_from_speech(
        speech_text="On affiche un dashboard card avec un bouton Shadcn UI pour valider la transaction."
    )
    assert frame_ui.frame_type == SynestheticFrameType.UI_COMPONENT
    assert "card" in frame_ui.payload.lower() or "button" in frame_ui.payload.lower()


def test_barge_in_interruption(call_gateway):
    session = call_gateway.create_session(user="Michael")
    session.mark_connected()

    # Simulate FreeAI speaking
    session.set_assistant_speaking(True)
    assert session.is_assistant_speaking is True

    # User speaks -> Barge-in event triggered
    event = session.handle_barge_in()
    assert event["interrupted"] is True
    assert session.is_assistant_speaking is False


def test_mini_app_asset_generation_in_ram(call_gateway):
    # Ensure Mini App HTML/JS is served directly from RAM without touching SSD
    html_content = call_gateway.get_mini_app_html(session_id="test_session_123")
    assert "<!DOCTYPE html>" in html_content
    assert "Telegram.WebApp" in html_content
    assert "canvas" in html_content.lower() or "orb" in html_content.lower()
    assert "test_session_123" in html_content


def test_stealth_copilot_live_execution(call_gateway, orchestrator):
    async def _run():
        session = call_gateway.create_session(user="Michael")
        session.mark_connected()

        # Attach orchestrator to gateway
        call_gateway.attach_orchestrator(orchestrator)

        # Launch a stealth co-pilot action while in call
        task = await call_gateway.dispatch_stealth_action(
            session_id=session.session_id,
            instruction="Vérifie le statut système"
        )
        assert task["success"] is True
        assert "result" in task

        # Verify that session recorded the stealth action without closing call
        assert session.status == SessionStatus.LIVE
        assert len(session.stealth_actions) == 1
    asyncio.run(_run())


def test_cli_dispatch_call_command(orchestrator):
    from unittest.mock import AsyncMock, patch
    import cli

    async def _run():
        with patch.object(orchestrator.telegram_vault, "send_message", new_callable=AsyncMock) as mock_send_msg, \
             patch.object(orchestrator.voice, "synthesize_speech", new_callable=AsyncMock) as mock_synth:
            mock_send_msg.return_value = True
            mock_synth.return_value = io.BytesIO(b"fake_audio")

            await cli.dispatch_telegram_order(orchestrator, "/call", user="Michael")

            mock_send_msg.assert_called_once()
            call_text = mock_send_msg.call_args[0][0]
            assert "Ligne Télépathique Live Active" in call_text
            assert "call_" in call_text
            assert len(orchestrator.realtime_call_gateway.sessions) >= 1
    asyncio.run(_run())

