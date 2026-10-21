"""Tests for Sovereign Kimi Interactive Playwright Authenticator (F-36)."""

import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.llm.kimi_authenticator import KimiPlaywrightAuthenticator


class TestKimiPlaywrightAuthenticator:

    def test_stealth_args_and_default_url(self):
        auth = KimiPlaywrightAuthenticator()
        assert auth.KIMI_LOGIN_URL in ("https://www.kimi.ai", "https://kimi.moonshot.cn")
        assert "--disable-blink-features=AutomationControlled" in auth.STEALTH_ARGS

    def test_extract_refresh_token_from_cookies(self):
        auth = KimiPlaywrightAuthenticator()
        cookies = [
            {"name": "session_id", "value": "12345", "domain": "kimi.moonshot.cn"},
            {"name": "refresh_token", "value": "test_refresh_token_abc_xyz", "domain": "kimi.moonshot.cn"},
            {"name": "theme", "value": "dark", "domain": "kimi.moonshot.cn"},
        ]
        token = auth.extract_refresh_token_from_cookies(cookies)
        assert token == "test_refresh_token_abc_xyz"

    def test_extract_refresh_token_missing(self):
        auth = KimiPlaywrightAuthenticator()
        cookies = [
            {"name": "session_id", "value": "12345", "domain": "kimi.moonshot.cn"},
        ]
        assert auth.extract_refresh_token_from_cookies(cookies) is None

    def test_update_env_content_appends_when_missing(self):
        auth = KimiPlaywrightAuthenticator()
        original_env = "GEMINI_API_KEY=xyz\nGROQ_API_KEY=abc\n"
        new_env = auth._render_updated_env_content(original_env, "test_token_123")
        assert "KIMI_REFRESH_TOKEN=test_token_123" in new_env
        assert "GEMINI_API_KEY=xyz" in new_env

    def test_update_env_content_replaces_existing(self):
        auth = KimiPlaywrightAuthenticator()
        original_env = "GEMINI_API_KEY=xyz\nKIMI_REFRESH_TOKEN=old_value\nGROQ_API_KEY=abc\n"
        new_env = auth._render_updated_env_content(original_env, "new_value_456")
        assert "KIMI_REFRESH_TOKEN=new_value_456" in new_env
        assert "old_value" not in new_env
        assert "GEMINI_API_KEY=xyz" in new_env

    @pytest.mark.anyio
    async def test_launch_interactive_login_success_mock(self):
        auth = KimiPlaywrightAuthenticator()

        mock_context = MagicMock()
        mock_context.cookies = AsyncMock(return_value=[
            {"name": "refresh_token", "value": "captured_token_999", "domain": "kimi.moonshot.cn"}
        ])
        mock_context.close = AsyncMock()

        mock_page = MagicMock()
        mock_page.goto = AsyncMock()
        mock_page.add_init_script = AsyncMock()
        mock_page.is_closed = MagicMock(return_value=False)
        mock_context.new_page = AsyncMock(return_value=mock_page)

        mock_browser = MagicMock()
        mock_browser.new_context = AsyncMock(return_value=mock_context)
        mock_browser.close = AsyncMock()

        mock_playwright = MagicMock()
        mock_playwright.chromium.launch = AsyncMock(return_value=mock_browser)
        mock_playwright.stop = AsyncMock()

        with patch("playwright.async_api.async_playwright") as mock_pw_init:
            mock_pw_context = MagicMock()
            mock_pw_context.__aenter__ = AsyncMock(return_value=mock_playwright)
            mock_pw_context.__aexit__ = AsyncMock()
            mock_pw_init.return_value = mock_pw_context

            with patch.object(auth, "persist_refresh_token") as mock_persist:
                res = await auth.launch_interactive_login(headless=True, timeout_sec=5, poll_interval_sec=0.05)
                assert res["success"] is True
                assert res["token"] == "captured_token_999"
                mock_persist.assert_called_once_with("captured_token_999")

    @pytest.mark.anyio
    async def test_launch_interactive_login_timeout(self):
        auth = KimiPlaywrightAuthenticator()

        mock_context = MagicMock()
        mock_context.cookies = AsyncMock(return_value=[])
        mock_context.close = AsyncMock()

        mock_page = MagicMock()
        mock_page.goto = AsyncMock()
        mock_page.add_init_script = AsyncMock()
        mock_page.is_closed = MagicMock(return_value=False)
        mock_context.new_page = AsyncMock(return_value=mock_page)

        mock_browser = MagicMock()
        mock_browser.new_context = AsyncMock(return_value=mock_context)
        mock_browser.close = AsyncMock()

        mock_playwright = MagicMock()
        mock_playwright.chromium.launch = AsyncMock(return_value=mock_browser)
        mock_playwright.stop = AsyncMock()

        with patch("playwright.async_api.async_playwright") as mock_pw_init:
            mock_pw_context = MagicMock()
            mock_pw_context.__aenter__ = AsyncMock(return_value=mock_playwright)
            mock_pw_context.__aexit__ = AsyncMock()
            mock_pw_init.return_value = mock_pw_context

            res = await auth.launch_interactive_login(headless=True, timeout_sec=0.1, poll_interval_sec=0.05)
            assert res["success"] is False
            assert "timed out" in res["error"].lower() or "timeout" in res["error"].lower()

    @pytest.mark.anyio
    async def test_orchestrator_kimi_login_delegation(self):
        from app.orchestrator.orchestrator import TechLeadOrchestrator
        orch = MagicMock(spec=TechLeadOrchestrator)
        orch.kimi_login = TechLeadOrchestrator.kimi_login.__get__(orch)

        with patch("app.llm.kimi_authenticator.KimiPlaywrightAuthenticator.launch_interactive_login", new_callable=AsyncMock) as mock_launch:
            mock_launch.return_value = {"success": True, "token": "tok_123"}
            res = await orch.kimi_login(headless=True, timeout_sec=10)
            assert res["success"] is True
            assert res["token"] == "tok_123"
            mock_launch.assert_called_once_with(headless=True, timeout_sec=10)

    def test_persist_refresh_token_updates_ram_and_env(self, tmp_path):
        env_file = tmp_path / ".env"
        env_file.write_text("PORT=8000\n", encoding="utf-8")

        auth = KimiPlaywrightAuthenticator()
        auth.persist_refresh_token("my_fresh_token", env_path=str(env_file))

        assert os.environ.get("KIMI_REFRESH_TOKEN") == "my_fresh_token"
        content = env_file.read_text(encoding="utf-8")
        assert "KIMI_REFRESH_TOKEN=my_fresh_token" in content
        assert "PORT=8000" in content
