"""Unit and Integration Tests for OurFreeModel Sovereign Bridge (Feature F-34).
Tests:
- AC1: OpenCode descending session minting, canonicalization, and timestamp bitwise structure.
- AC2: OpenCode v2 client fingerprint, headers, tool injection (read & shell), and tool_choice sanitization.
- AC3: Kilo AI keyless free model filtering and request formatting.
- AC4: Local Standalone Forward Gateway auto-discovery and key discovery.
- AC5: OnlineModelFederation integration with zero-cost models.
"""

import os
import re
import json
import asyncio
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock

from app.llm.our_free_model import (
    mint_session_id,
    canonicalize_session,
    is_canonical_session,
    build_opencode_headers,
    apply_opencode_fingerprint,
    FINGERPRINT_TOOL_DEFINITIONS,
    CLIENT_UA,
    filter_kilo_free_models,
    build_kilo_chat_payload,
    detect_local_forward_gateway,
    _probe_http_port,
    OurFreeModelBridge,
    OPENCODE_FREE_MODELS,
)
from app.llm.federation import OnlineModelFederation


class TestOurFreeModelSession(unittest.TestCase):
    """Tests AC1: OpenCode Session ID generation & bitwise validation."""

    def test_mint_session_id_format_and_bitwise_descending(self):
        session_re = re.compile(r"^ses_[0-9a-f]{12}[0-9A-Za-z]{14}$")
        descending_re = re.compile(r"^[0-9a-f]{9}f[c-f][0-9a-f]$")

        for _ in range(20):
            sid = mint_session_id()
            self.assertTrue(session_re.match(sid), f"Invalid session format: {sid}")
            time_part = sid[4:16]
            self.assertTrue(
                descending_re.match(time_part),
                f"Time part does not match descending gate pattern: {time_part}",
            )
            self.assertTrue(is_canonical_session(sid))

    def test_canonicalize_session_deterministic(self):
        seed_1 = "conversation_alpha_42"
        sid_1a = canonicalize_session(seed_1)
        sid_1b = canonicalize_session(seed_1)
        self.assertEqual(sid_1a, sid_1b)
        self.assertTrue(is_canonical_session(sid_1a))

        seed_2 = "conversation_beta_99"
        sid_2 = canonicalize_session(seed_2)
        self.assertNotEqual(sid_1a, sid_2)
        self.assertTrue(is_canonical_session(sid_2))


class TestOurFreeModelFingerprint(unittest.TestCase):
    """Tests AC2: OpenCode v2 client fingerprint and tool injection."""

    def test_build_opencode_headers(self):
        sid = mint_session_id()
        headers = build_opencode_headers(session_id=sid, stream=True)

        self.assertEqual(headers["content-type"], "application/json")
        self.assertEqual(headers["authorization"], "Bearer public")
        self.assertEqual(headers["user-agent"], CLIENT_UA)
        self.assertEqual(headers["x-opencode-client"], "cli")
        self.assertEqual(headers["x-opencode-session"], sid)
        self.assertEqual(headers["x-opencode-session-id"], sid)
        self.assertEqual(headers["x-session-affinity"], sid)
        self.assertEqual(headers["x-session-id"], sid)
        self.assertEqual(headers["x-opencode-project"], "global")
        self.assertEqual(headers["accept"], "text/event-stream")
        self.assertNotIn("x-opencode-request", headers)

    def test_apply_opencode_fingerprint_injects_read_and_shell(self):
        body = {
            "model": "deepseek-v4.1-flash-free",
            "messages": [{"role": "user", "content": "What is 42?"}],
            "tools": [],
            "tool_choice": "none",
        }

        alias_map = apply_opencode_fingerprint(body)
        self.assertEqual(len(alias_map), 0)

        tool_names = [t["function"]["name"] for t in body["tools"]]
        self.assertIn("read", tool_names)
        self.assertIn("shell", tool_names)

        # tool_choice: "none" must be deleted
        self.assertNotIn("tool_choice", body)

        # read & shell descriptions and schemas must match verbatim
        read_tool = next(t for t in body["tools"] if t["function"]["name"] == "read")
        self.assertEqual(
            read_tool["function"]["description"],
            FINGERPRINT_TOOL_DEFINITIONS["read"]["function"]["description"],
        )
        self.assertEqual(
            read_tool["function"]["parameters"],
            FINGERPRINT_TOOL_DEFINITIONS["read"]["function"]["parameters"],
        )

        # Check placeholder note injection into messages
        sys_msg = body["messages"][0]
        self.assertEqual(sys_msg["role"], "system")
        self.assertIn("Do not call the `read` or `shell` tools", sys_msg["content"])

    def test_apply_opencode_fingerprint_aliases_conflicting_tools(self):
        custom_read = {
            "type": "function",
            "function": {
                "name": "read",
                "description": "Custom user read tool",
                "parameters": {"type": "object", "properties": {"target": {"type": "string"}}},
            },
        }
        body = {
            "model": "deepseek-v4.1-flash-free",
            "messages": [{"role": "user", "content": "Read target"}],
            "tools": [custom_read],
        }

        alias_map = apply_opencode_fingerprint(body)
        self.assertIn("read_client", alias_map)
        self.assertEqual(alias_map["read_client"], "read")

        tool_names = [t["function"]["name"] for t in body["tools"]]
        self.assertIn("read_client", tool_names)
        self.assertIn("read", tool_names)
        self.assertIn("shell", tool_names)


class TestKiloAIGateway(unittest.TestCase):
    """Tests AC3: Kilo AI keyless free models."""

    def test_filter_kilo_free_models(self):
        raw_models = {
            "data": [
                {"id": "paid/gpt-5", "isFree": False},
                {"id": "kilo-auto/free", "isFree": True, "name": "Kilo Auto Free"},
                {"id": "z-ai/glm-4.5-air:free", "isFree": True},
                {"id": "anthropic/claude-3-haiku", "isFree": False},
            ]
        }
        free_list = filter_kilo_free_models(raw_models)
        self.assertEqual(len(free_list), 2)
        ids = [m["id"] for m in free_list]
        self.assertIn("kilo-auto/free", ids)
        self.assertIn("z-ai/glm-4.5-air:free", ids)

    def test_build_kilo_chat_payload(self):
        payload = build_kilo_chat_payload(
            model="kilo-auto/free",
            messages=[{"role": "user", "content": "Hello"}],
            reasoning_effort="high",
        )
        self.assertEqual(payload["model"], "kilo-auto/free")
        self.assertEqual(payload["reasoning"], {"effort": "high"})


class TestLocalForwardDetection(unittest.TestCase):
    """Tests AC4: Local Standalone Forward detection."""

    def test_probe_http_port_against_real_listening_socket(self):
        """No mocking: exercises the real asyncio code path end to end.
        Would have caught the missing `import asyncio` (NameError silently
        swallowed by a bare `except Exception` and reported as 'port closed')."""

        async def run():
            server = await asyncio.start_server(lambda r, w: None, "127.0.0.1", 0)
            port = server.sockets[0].getsockname()[1]
            try:
                found = await _probe_http_port("127.0.0.1", port)
                self.assertTrue(found, "real listening port must be detected as open")

                not_listening_port = port + 1 if port < 65535 else port - 1
                not_found = await _probe_http_port("127.0.0.1", not_listening_port)
                self.assertFalse(not_found)
            finally:
                server.close()
                await server.wait_closed()

        asyncio.run(run())

    def test_detect_local_forward_with_mock_port(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            ofm_home = Path(tmp_dir)
            settings_path = ofm_home / "settings.json"
            settings_path.write_text(json.dumps({"forwardKey": "ofm-testkey12345"}), encoding="utf-8")

            # Mock socket or connection check
            mock_probe = AsyncMock(return_value=True)
            with patch("app.llm.our_free_model._probe_http_port", mock_probe):
                res = asyncio.run(
                    detect_local_forward_gateway(
                        ports=[18900],
                        settings_search_paths=[settings_path],
                    )
                )
                self.assertIsNotNone(res)
                self.assertEqual(res["port"], 18900)
                self.assertEqual(res["api_key"], "ofm-testkey12345")
                self.assertEqual(res["base_url"], "http://127.0.0.1:18900")


class TestFederationIntegration(unittest.TestCase):
    """Tests AC5: OnlineModelFederation integration."""

    def test_catalog_contains_free_providers(self):
        fed = OnlineModelFederation(memory_mode="neant")
        catalog = fed.list_supported_online_models()

        self.assertIn("opencode_free", catalog)
        self.assertIn("kilo_free", catalog)
        self.assertIn("our_free_model_local", catalog)

        self.assertEqual(catalog["opencode_free"]["default_model"], "deepseek-v4.1-flash-free")
        self.assertEqual(catalog["kilo_free"]["default_model"], "kilo-auto/free")

    def test_query_opencode_free_mock(self):
        fed = OnlineModelFederation(memory_mode="neant")

        mock_answer = "DeepSeek V4.1 Flash via OpenCode Free Lane"
        mock_bridge = AsyncMock()
        mock_bridge.query_opencode = AsyncMock(return_value={"content": mock_answer})

        with patch("app.llm.our_free_model.OurFreeModelBridge.get_instance", return_value=mock_bridge):
            res = asyncio.run(
                fed.query_specific_provider(
                    provider="opencode_free",
                    prompt="Test prompt",
                    model="deepseek-v4.1-flash-free",
                )
            )
            self.assertIsNotNone(res)
            self.assertEqual(res["provider"], "opencode_free")
            self.assertEqual(res["content"], mock_answer)

    def test_consult_free_online_model_fallback_to_opencode(self):
        fed = OnlineModelFederation(
            memory_mode="neant",
            openrouter_api_key="",
            deepseek_api_key="",
            grok_api_key="",
            groq_api_key="",
            gemini_api_key="",
            remote_ollama_url="http://127.0.0.1:99999",
            remote_gpu_url=""
        )
        fed.current_provider = "auto"
        fed.current_model = "auto"
        fed.gemini_api_key = None
        fed.openrouter_api_key = None
        fed.deepseek_api_key = None
        fed.grok_api_key = None
        fed.groq_api_key = None

        mock_answer = "DeepSeek V4.1 Flash Sovereign Response"
        mock_bridge = AsyncMock()
        mock_bridge.query_opencode = AsyncMock(return_value={"content": mock_answer})

        with patch("app.llm.our_free_model.detect_local_forward_gateway", AsyncMock(return_value=None)):
            with patch("app.llm.our_free_model.OurFreeModelBridge.get_instance", return_value=mock_bridge):
                res = asyncio.run(
                    fed.consult_free_online_model("Quelle est la vitesse de la lumière ?")
                )
                self.assertTrue(res["success"])
                self.assertEqual(res["provider"], "OpenCode_Zen_Gateway")
                self.assertEqual(res["response"], mock_answer)

    def test_set_online_target_opencode_free(self):
        fed = OnlineModelFederation(memory_mode="neant")
        fed.set_online_target("opencode_free", "deepseek-v4.1-flash-free")
        self.assertEqual(fed.current_provider, "opencode_free")
        self.assertEqual(fed.current_model, "deepseek-v4.1-flash-free")

        mock_answer = "DeepSeek V4.1 targeted response"
        mock_bridge = AsyncMock()
        mock_bridge.query_opencode = AsyncMock(return_value={"content": mock_answer})

        with patch("app.llm.our_free_model.OurFreeModelBridge.get_instance", return_value=mock_bridge):
            res = asyncio.run(
                fed.consult_free_online_model("Explique la théorie de la relativité")
            )
            self.assertTrue(res["success"])
            self.assertEqual(res["provider"], "opencode_free")
            self.assertEqual(res["model"], "deepseek-v4.1-flash-free")
            self.assertEqual(res["response"], mock_answer)

    def test_adversarial_server_error_and_timeout(self):
        bridge = OurFreeModelBridge.get_instance()
        with patch("httpx.AsyncClient.stream", side_effect=Exception("Connection reset by peer")):
            res = asyncio.run(bridge.query_opencode("Prompt that fails", model="deepseek-v4.1-flash-free"))
            self.assertIsNone(res)

    def test_unicode_and_multiline_prompt(self):
        body = {
            "model": "deepseek-v4.1-flash-free",
            "messages": [{"role": "user", "content": "Analyse：你好，monde 🚀\nLigne 2: 1234\nLigne 3: \t\r"}],
            "tools": [],
        }
        apply_opencode_fingerprint(body)
        self.assertIn("read", [t["function"]["name"] for t in body["tools"]])
        self.assertIn("shell", [t["function"]["name"] for t in body["tools"]])


if __name__ == "__main__":
    unittest.main()
