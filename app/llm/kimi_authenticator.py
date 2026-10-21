"""Sovereign Kimi Interactive Playwright Authenticator (F-36).

Provides an interactive, one-time assisted login using Playwright Chromium to intercept
and persist Kimi's refresh_token cookie without requiring manual DevTools extraction.
Once captured, FreeAi operates 100% autonomously in RAM (Mode NÉANT) without needing a browser.
"""

import asyncio
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("freeai.llm.kimi_authenticator")


class KimiPlaywrightAuthenticator:
    """Automates interactive login on kimi.ai / kimi.moonshot.cn to extract refresh_token."""

    KIMI_LOGIN_URL = os.getenv("KIMI_LOGIN_URL", "https://www.kimi.ai")
    USER_AGENT = (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/133.0.0.0 Safari/537.36"
    )
    STEALTH_ARGS = [
        "--disable-blink-features=AutomationControlled",
        "--no-sandbox",
        "--disable-infobars",
        "--window-size=1280,800",
    ]

    _STEALTH_INIT_SCRIPT = """
    Object.defineProperty(navigator, 'webdriver', {
        get: () => undefined
    });
    """

    def extract_refresh_token_from_cookies(self, cookies: List[Dict[str, Any]]) -> Optional[str]:
        """Scans a list of cookie dictionaries for the Kimi refresh_token."""
        for cookie in cookies:
            name = cookie.get("name", "")
            if name == "refresh_token":
                val = cookie.get("value")
                if val:
                    return str(val)
        return None

    def _render_updated_env_content(self, current_content: str, token: str) -> str:
        """Pure helper: updates or appends KIMI_REFRESH_TOKEN in .env content string."""
        lines = current_content.splitlines(keepends=True)
        replaced = False
        new_lines = []
        for line in lines:
            if line.strip().startswith("KIMI_REFRESH_TOKEN="):
                new_lines.append(f"KIMI_REFRESH_TOKEN={token}\n")
                replaced = True
            else:
                new_lines.append(line)
        if not replaced:
            if new_lines and not new_lines[-1].endswith("\n"):
                new_lines.append("\n")
            new_lines.append(f"KIMI_REFRESH_TOKEN={token}\n")
        return "".join(new_lines)

    def persist_refresh_token(self, token: str, env_path: Optional[str] = None) -> None:
        """Stores the token in memory and persists to .env file if available."""
        # 1. Update in-memory runtime environment (Mode NÉANT)
        os.environ["KIMI_REFRESH_TOKEN"] = token

        try:
            from app.llm.kimi_web_bridge import KimiWebBridge
            bridge = KimiWebBridge.get_instance()
            bridge.set_refresh_token(token)
        except Exception as e:
            logger.debug(f"[KIMI_AUTH] Bridge RAM update notice: {e}")

        # 2. Persist to .env file if present
        target_path = Path(env_path) if env_path else Path(".env")
        try:
            if target_path.exists():
                content = target_path.read_text(encoding="utf-8")
                updated = self._render_updated_env_content(content, token)
                target_path.write_text(updated, encoding="utf-8")
                logger.info(f"[KIMI_AUTH] Persisted KIMI_REFRESH_TOKEN into {target_path}")
            else:
                target_path.write_text(f"KIMI_REFRESH_TOKEN={token}\n", encoding="utf-8")
                logger.info(f"[KIMI_AUTH] Created {target_path} with KIMI_REFRESH_TOKEN")
        except Exception as e:
            logger.warning(f"[KIMI_AUTH] Failed writing .env file: {e}")

    async def launch_interactive_login(
        self,
        headless: bool = False,
        timeout_sec: float = 120.0,
        poll_interval_sec: float = 1.0,
        display: Optional[str] = None
    ) -> Dict[str, Any]:
        """Launches Playwright Chromium, prompts user to log in, and sniffs refresh_token."""
        try:
            from playwright.async_api import async_playwright
        except ImportError:
            return {
                "success": False,
                "error": "Playwright is not installed. Install with: pip install playwright && playwright install chromium"
            }

        start_time = asyncio.get_event_loop().time()
        captured_token: Optional[str] = None

        launch_env = os.environ.copy()
        if display:
            launch_env["DISPLAY"] = display

        try:
            async with async_playwright() as pw:
                browser = await pw.chromium.launch(
                    headless=headless,
                    args=self.STEALTH_ARGS,
                    env=launch_env
                )
                try:
                    context = await browser.new_context(
                        user_agent=self.USER_AGENT,
                        viewport={"width": 1280, "height": 800}
                    )
                    page = await context.new_page()
                    await page.add_init_script(self._STEALTH_INIT_SCRIPT)

                    async def _handle_response(resp):
                        nonlocal captured_token
                        try:
                            url = resp.url
                            if any(k in url for k in ("token", "auth", "login")):
                                ct = resp.headers.get("content-type", "")
                                if "json" in ct:
                                    data = await resp.json()
                                    if isinstance(data, dict):
                                        tok = data.get("refresh_token") or data.get("data", {}).get("refresh_token")
                                        if tok:
                                            captured_token = str(tok)
                                            logger.info("[KIMI_AUTH] Intercepted refresh_token from network response JSON")
                        except Exception:
                            pass

                    page.on("response", _handle_response)

                    logger.info(f"[KIMI_AUTH] Navigating to {self.KIMI_LOGIN_URL}")
                    try:
                        await page.goto(self.KIMI_LOGIN_URL, wait_until="domcontentloaded", timeout=30000)
                    except Exception as e:
                        logger.warning(f"[KIMI_AUTH] page.goto notice (continuing): {e}")

                    # Poll cookies and localStorage until refresh_token appears or timeout
                    while (asyncio.get_event_loop().time() - start_time) < timeout_sec:
                        if page.is_closed():
                            return {"success": False, "error": "Browser window closed by user"}

                        if captured_token:
                            break

                        cookies = await context.cookies()
                        token = self.extract_refresh_token_from_cookies(cookies)
                        if token:
                            captured_token = token
                            logger.info("[KIMI_AUTH] Successfully intercepted refresh_token cookie!")
                            break

                        try:
                            ls_token = await page.evaluate(
                                "() => localStorage.getItem('refresh_token') || localStorage.getItem('kimi_refresh_token')"
                            )
                            if ls_token:
                                captured_token = str(ls_token)
                                logger.info("[KIMI_AUTH] Intercepted refresh_token from localStorage")
                                break
                        except Exception:
                            pass

                        await asyncio.sleep(poll_interval_sec)

                    if not captured_token:
                        return {"success": False, "error": f"Login timed out after {timeout_sec} seconds"}

                    # Persist token
                    self.persist_refresh_token(captured_token)
                    return {
                        "success": True,
                        "token": captured_token,
                        "message": "Kimi authentication token captured and configured successfully."
                    }

                finally:
                    await browser.close()

        except Exception as e:
            logger.error(f"[KIMI_AUTH] Error during interactive login: {e}")
            return {"success": False, "error": str(e)}
