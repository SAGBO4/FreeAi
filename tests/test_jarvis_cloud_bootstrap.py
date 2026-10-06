"""Tests for Jarvis Cloud Evolution & Sovereign Neural Swarm Bootstrap (scripts/jarvis_cloud_bootstrap.py).
Validates:
1. STRICT ZERO hardcoded keys in scripts and workflows.
2. Resilience against 402 Payment Required (DeepSeek 0$ balance).
3. Automatic cascade fallback when a model returns 400 (decommissioned model).
4. Multi-agent consensus distillation even with a single provider answering.
5. Telegram notification formatting and graceful error handling.
"""

import os
import sys
import re
import json
import pytest
import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.jarvis_cloud_bootstrap import (
    MODEL_CASCADES,
    SovereignSwarmClient,
    run_swarm_bootstrap,
    send_telegram_message,
)


class TestJarvisCloudBootstrap:
    """Rigorous tests ensuring 0-key leak and extreme resilience."""

    def test_strict_zero_hardcoded_keys(self):
        """Verifies no API keys are hardcoded in scripts or workflows."""
        key_patterns = [
            re.compile(r"gsk_[A-Za-z0-9_-]{20,}"),     # Groq
            re.compile(r"sk-[A-Za-z0-9_-]{20,}"),      # OpenAI / DeepSeek / OpenRouter
            re.compile(r"AIza[A-Za-z0-9_-]{20,}"),     # Google
        ]

        files_to_check = [
            Path(__file__).parent.parent / "scripts" / "jarvis_cloud_bootstrap.py",
            Path(__file__).parent.parent / ".github" / "workflows" / "jarvis_cloud_evolution.yml",
        ]

        for file_path in files_to_check:
            assert file_path.exists(), f"File {file_path} missing"
            content = file_path.read_text(encoding="utf-8")
            for pat in key_patterns:
                matches = pat.findall(content)
                assert len(matches) == 0, f"Hardcoded key detected in {file_path.name}: {matches}"

    def test_model_cascades_do_not_contain_decommissioned_models(self):
        """Verifies that decommissioned mixtral-8x7b-32768 is removed and modern models are used."""
        groq_models = MODEL_CASCADES["groq"]["models"]
        assert "mixtral-8x7b-32768" not in groq_models
        assert "llama-3.3-70b-versatile" in groq_models
        assert "llama-3.1-8b-instant" in groq_models

    def test_swarm_client_init_reads_env_only(self, monkeypatch):
        """Ensures SovereignSwarmClient only activates providers with non-empty env keys."""
        monkeypatch.setenv("GROQ_API_KEY", "test-groq-key")
        monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
        monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)

        client = SovereignSwarmClient()
        assert client.provider_status["groq"] == "READY"
        assert client.provider_status["deepseek"] == "NO_KEY"
        assert client.provider_status["openrouter_free"] == "NO_KEY"
        assert client.provider_status["gemini"] == "NO_KEY"

    def test_deepseek_402_graceful_handling(self, monkeypatch):
        """Validates that a 402 Payment Required does not crash but deactivates DeepSeek gracefully."""
        async def _run():
            monkeypatch.setenv("DEEPSEEK_API_KEY", "mock-deepseek-key")
            swarm = SovereignSwarmClient()

            mock_response = MagicMock()
            mock_response.status_code = 402

            mock_http_client = AsyncMock()
            mock_http_client.post.return_value = mock_response

            model_used, content = await swarm.query_provider_cascade(
                mock_http_client, "deepseek", "Test prompt"
            )

            assert model_used is None
            assert content is None
            assert swarm.provider_status["deepseek"] == "PAYMENT_REQUIRED_402"

        asyncio.run(_run())

    def test_model_decommissioned_400_fallback(self, monkeypatch):
        """Validates that a 400 Bad Request on the first model triggers fallback to the next model in cascade."""
        async def _run():
            monkeypatch.setenv("GROQ_API_KEY", "mock-groq-key")
            swarm = SovereignSwarmClient()

            # First model returns 400 (e.g. deprecated), second succeeds
            res_fail = MagicMock()
            res_fail.status_code = 400

            res_ok = MagicMock()
            res_ok.status_code = 200
            res_ok.raise_for_status = MagicMock()
            res_ok.json.return_value = {
                "choices": [{"message": {"content": "Explication de pointe Groq LPU."}}]
            }

            mock_http_client = AsyncMock()
            mock_http_client.post.side_effect = [res_fail, res_ok]

            model_used, content = await swarm.query_provider_cascade(
                mock_http_client, "groq", "Test prompt"
            )

            assert model_used == "llama-3.1-8b-instant"
            assert content == "Explication de pointe Groq LPU."

        asyncio.run(_run())

    def test_run_swarm_bootstrap_single_provider_success(self, monkeypatch, tmp_path):
        """Validates that if only Groq answers (DeepSeek 402 or offline), bootstrap still distills knowledge."""
        async def _run():
            monkeypatch.setenv("GROQ_API_KEY", "mock-groq-key")
            monkeypatch.setenv("DEEPSEEK_API_KEY", "mock-deepseek-key")

            # Mock Swarm client queries
            async def mock_query(client, provider_id, prompt, **kwargs):
                if provider_id == "groq":
                    return "llama-3.3-70b-versatile", "Conseil souverain de performance mémoire."
                elif provider_id == "deepseek":
                    return None, None
                return None, None

            with patch.object(SovereignSwarmClient, "query_provider_cascade", side_effect=mock_query):
                with patch("scripts.jarvis_cloud_bootstrap.send_telegram_message", new_callable=AsyncMock) as mock_tg:
                    results = await run_swarm_bootstrap(num_topics=2, notify_telegram=True)

                    assert len(results) == 2
                    for r in results:
                        assert any("llama-3.3-70b-versatile" in c for c in r["contributors"])
                        assert "Conseil souverain" in r["consensus"]

                    assert mock_tg.called

        asyncio.run(_run())

    def test_send_telegram_message(self, monkeypatch):
        """Validates telegram sending and graceful missing key handling."""
        async def _run():
            # 1. Missing keys
            monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
            monkeypatch.delenv("TELEGRAM_CHAT_ID", raising=False)
            assert await send_telegram_message("Test") is False

            # 2. Configured keys with HTTP mock
            monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123456:ABC-DEF")
            monkeypatch.setenv("TELEGRAM_CHAT_ID", "987654321")

            mock_res = MagicMock()
            mock_res.raise_for_status = MagicMock()

            with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
                mock_post.return_value = mock_res
                assert await send_telegram_message("Hello from Jarvis") is True

        asyncio.run(_run())

