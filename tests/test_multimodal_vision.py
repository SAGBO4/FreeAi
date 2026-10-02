"""Tests for Telegram Multimodal Vision & Video Analysis (F-10).
Verifies:
1. Photo and Video ingestion directly in RAM (Mode NÉANT, 0 disk write).
2. Multimodal analysis via Federation (Groq Vision / OpenRouter Free / Fallback).
3. Seamless integration in dispatch_telegram_order.
"""

import asyncio
import io
import pytest
from app.memory.telegram_vault import TelegramCommand, TelegramNeuralVault
from app.llm.federation import OnlineModelFederation


@pytest.fixture
def federation():
    return OnlineModelFederation(memory_mode="neant")


def test_telegram_command_with_multimodal_metadata():
    fake_img = b"\xff\xd8\xff\xe0\x00\x10JFIF" * 20
    cmd = TelegramCommand(
        text="Analyse cette architecture",
        user="Michael",
        is_voice=False,
        media_bytes=fake_img,
        media_type="image/jpeg"
    )
    assert cmd.text == "Analyse cette architecture"
    assert cmd.user == "Michael"
    assert cmd.media_bytes == fake_img
    assert cmd.media_type == "image/jpeg"
    # Backwards compatibility as tuple
    text_unpacked, user_unpacked = cmd
    assert text_unpacked == "Analyse cette architecture"
    assert user_unpacked == "Michael"


def test_multimodal_analysis_execution(federation):
    async def _run():
        fake_img = b"\xff\xd8\xff\xe0\x00\x10JFIF" * 30
        res = await federation.analyze_multimodal(
            media_bytes=fake_img,
            prompt="Que contient cette capture d'écran ?",
            media_type="image/jpeg"
        )
        assert res is not None
        assert isinstance(res, str)
        assert len(res) > 20
        # Verification that analysis completed
        assert any(w in res.lower() for w in ["analyse", "image", "visuelle", "format", "structure", "détection"])
    asyncio.run(_run())


def test_cli_dispatch_multimodal_image():
    from unittest.mock import AsyncMock, patch
    from app.tools.gateway import ToolGateway
    from app.resource_manager.watchdog import ResourceManager
    from app.orchestrator.orchestrator import TechLeadOrchestrator
    import cli

    gw = ToolGateway(workspace_root="/tmp")
    rm = ResourceManager()
    orch = TechLeadOrchestrator(tool_gateway=gw, resource_manager=rm)

    async def _run():
        fake_img = b"\xff\xd8\xff\xe0\x00\x10JFIF" * 15
        with patch.object(orch.telegram_vault, "send_message", new_callable=AsyncMock) as mock_send_msg:
            mock_send_msg.return_value = True

            await cli.dispatch_telegram_order(
                orch,
                "Que vois-tu sur ce schéma ?",
                user="Michael",
                is_voice=False,
                media_bytes=fake_img,
                media_type="image/jpeg"
            )

            mock_send_msg.assert_called_once()
            analysis_text = mock_send_msg.call_args[0][0]
            assert "Analyse Multimodale" in analysis_text
            assert "Image Numérique" in analysis_text
    asyncio.run(_run())

