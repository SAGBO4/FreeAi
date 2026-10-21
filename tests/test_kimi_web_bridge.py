"""Unit and Integration Tests for Sovereign Kimi Web Bridge (Feature F-35).
Tests:
- AC1: Automated Token Refresh & In-RAM Caching.
- AC2: Ephemeral Chat Lifecycle Management.
- AC3: SSE Stream Ingestion & Parsing.
- AC4: Dual-Channel Fallback (Web Protocol & Official Platform API).
- AC5: OnlineModelFederation Integration & Zero Disk Footprint (Mode NÉANT).
"""

import os
import json
import asyncio
import unittest
from unittest.mock import patch, MagicMock, AsyncMock

from app.llm.kimi_web_bridge import (
    KimiWebBridge,
    KIMI_WEB_BASE,
    KIMI_API_BASE,
)
from app.llm.federation import OnlineModelFederation


class TestKimiWebBridgeAuth(unittest.TestCase):
    """Tests AC1: Token exchange & RAM caching."""

    def setUp(self):
        self.bridge = KimiWebBridge(refresh_token="mock_refresh_token_xyz")

    def test_get_access_token_success(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "access_token": "mock_access_token_123",
            "refresh_token": "mock_new_refresh_token",
        }

        with patch("httpx.AsyncClient.get", AsyncMock(return_value=mock_resp)) as mock_get:
            token = asyncio.run(self.bridge.get_access_token())
            self.assertEqual(token, "mock_access_token_123")
            mock_get.assert_called_once()

            # Second call must hit the RAM cache, not the network
            cached_token = asyncio.run(self.bridge.get_access_token())
            self.assertEqual(cached_token, "mock_access_token_123")
            self.assertEqual(mock_get.call_count, 1)

    def test_multi_token_pool_rotation(self):
        pool_tokens = "token_alpha,token_beta,token_gamma"
        bridge = KimiWebBridge(refresh_token=pool_tokens)
        self.assertEqual(len(bridge.token_pool), 3)
        self.assertIn(bridge.get_active_refresh_token(), ["token_alpha", "token_beta", "token_gamma"])


class TestKimiWebLifecycleAndStream(unittest.TestCase):
    """Tests AC2 & AC3: Chat creation and SSE streaming."""

    def setUp(self):
        self.bridge = KimiWebBridge(refresh_token="mock_refresh")
        self.bridge._cached_access_token = "mock_access_valid"
        self.bridge._token_expires_at = 9999999999

    def test_create_chat_session(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"id": "chat_session_888"}

        with patch("httpx.AsyncClient.post", AsyncMock(return_value=mock_resp)):
            chat_id = asyncio.run(self.bridge.create_chat_session())
            self.assertEqual(chat_id, "chat_session_888")

    def test_query_kimi_web_sse_parsing(self):
        # Mock create_chat
        self.bridge.create_chat_session = AsyncMock(return_value="chat_session_888")

        # Mock stream lines
        sse_lines = [
            'data: {"event": "cmpl", "text": "Kimi "}',
            'data: {"event": "cmpl", "text": "K3 "}',
            'data: {"event": "cmpl", "text": "Sovereign"}',
            "data: [DONE]",
        ]

        class FakeStreamResponse:
            status_code = 200

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb):
                pass

            async def aiter_lines(self):
                for line in sse_lines:
                    yield line

        with patch("httpx.AsyncClient.stream", return_value=FakeStreamResponse()):
            res = asyncio.run(
                self.bridge.query_kimi_web("Explique le principe de Kimi K3")
            )
            self.assertIsNotNone(res)
            self.assertEqual(res["provider"], "kimi_web")
            self.assertEqual(res["content"], "Kimi K3 Sovereign")


class TestKimiOfficialFallback(unittest.TestCase):
    """Tests AC4: Official Platform API fallback."""

    def test_query_kimi_official_api(self):
        bridge = KimiWebBridge(api_key="sk-mock-moonshot-api-key")

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "choices": [{"message": {"content": "Moonshot Official API Answer"}}]
        }

        with patch("httpx.AsyncClient.post", AsyncMock(return_value=mock_resp)):
            res = asyncio.run(bridge.query_kimi_official("Question test"))
            self.assertIsNotNone(res)
            self.assertEqual(res["provider"], "kimi")
            self.assertEqual(res["content"], "Moonshot Official API Answer")


class TestFederationIntegrationKimi(unittest.TestCase):
    """Tests AC5: OnlineModelFederation integration."""

    def test_catalog_contains_kimi(self):
        fed = OnlineModelFederation(memory_mode="neant")
        catalog = fed.list_supported_online_models()

        self.assertIn("kimi", catalog)
        self.assertIn("kimi_web", catalog)
        self.assertEqual(catalog["kimi_web"]["default_model"], "kimi-k3-web")

    def test_query_specific_provider_kimi_web(self):
        fed = OnlineModelFederation(memory_mode="neant")

        mock_bridge = AsyncMock()
        mock_bridge.query_kimi_web = AsyncMock(
            return_value={"provider": "kimi_web", "content": "Kimi Web Response via FreeAi"}
        )

        with patch("app.llm.kimi_web_bridge.KimiWebBridge.get_instance", return_value=mock_bridge):
            res = asyncio.run(
                fed.query_specific_provider(
                    provider="kimi_web",
                    prompt="Quelle est la structure atomique du diamant ?",
                )
            )
            self.assertIsNotNone(res)
            self.assertEqual(res["provider"], "kimi_web")
            self.assertEqual(res["content"], "Kimi Web Response via FreeAi")


if __name__ == "__main__":
    unittest.main()
