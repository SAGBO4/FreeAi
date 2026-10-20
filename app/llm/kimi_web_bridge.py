"""Sovereign Kimi Web Bridge for FreeAi (Feature F-35).
Provides serverless, cloud-native access to Moonshot AI's Kimi models (Kimi K2.5 / K3)
by speaking the reverse-engineered Kimi Web authentication and streaming protocol (https://kimi.moonshot.cn),
with fallback to the official Moonshot developer API (https://api.moonshot.cn/v1).
Supports MEMORY_MODE="neant" (100% ephemeral in-RAM execution, zero disk footprint).
"""

import os
import time
import json
import random
import logging
from typing import Dict, Any, Optional, List, AsyncGenerator
import httpx

logger = logging.getLogger("kimi_web_bridge")

KIMI_WEB_BASE = os.getenv("KIMI_WEB_BASE", "https://www.kimi.ai").rstrip("/")
KIMI_API_BASE = os.getenv("KIMI_API_BASE", "https://api.moonshot.cn/v1").rstrip("/")

DEFAULT_KIMI_USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/133.0.0.0 Safari/537.36 FreeAI-Sovereign-Conduit/1.0"
)


class KimiWebBridge:
    """Core sovereign bridge for Kimi Web (https://kimi.moonshot.cn) & Moonshot API."""

    _instance: Optional["KimiWebBridge"] = None

    def __init__(
        self,
        refresh_token: Optional[str] = None,
        api_key: Optional[str] = None,
        token_ttl_sec: int = 900,
    ):
        raw_refresh = refresh_token or os.getenv("KIMI_REFRESH_TOKEN") or os.getenv("MOONSHOT_REFRESH_TOKEN") or ""
        self.token_pool = [t.strip() for t in raw_refresh.split(",") if t.strip()]
        self.api_key = api_key or os.getenv("KIMI_API_KEY") or os.getenv("MOONSHOT_API_KEY")

        self.token_ttl_sec = token_ttl_sec
        self._cached_access_token: Optional[str] = None
        self._token_expires_at: float = 0.0
        self._active_token_idx: int = 0
        self._active_chat_id: Optional[str] = None

    @classmethod
    def get_instance(cls) -> "KimiWebBridge":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def get_active_refresh_token(self) -> Optional[str]:
        """Returns the current refresh token from the pool, rotating round-robin."""
        if not self.token_pool:
            return None
        token = self.token_pool[self._active_token_idx % len(self.token_pool)]
        self._active_token_idx += 1
        return token

    async def get_access_token(self, force_refresh: bool = False) -> Optional[str]:
        """Exchanges refresh_token for ephemeral access_token and caches it in RAM."""
        now = time.time()
        if not force_refresh and self._cached_access_token and now < self._token_expires_at:
            return self._cached_access_token

        refresh_token = self.get_active_refresh_token()
        if not refresh_token:
            logger.debug("[KIMI_WEB] No refresh_token configured in environment or pool.")
            return None

        url = f"{KIMI_WEB_BASE}/api/auth/token/refresh"
        headers = {
            "Authorization": f"Bearer {refresh_token}",
            "User-Agent": DEFAULT_KIMI_USER_AGENT,
            "Accept": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(url, headers=headers)
                if resp.status_code == 200:
                    data = resp.json()
                    access_token = data.get("access_token")
                    if access_token:
                        self._cached_access_token = access_token
                        self._token_expires_at = now + self.token_ttl_sec
                        logger.info("[KIMI_WEB] Ephemeral access_token renewed successfully in RAM.")
                        return access_token
                else:
                    logger.warning(f"[KIMI_WEB] Token refresh failed: HTTP {resp.status_code} - {resp.text[:200]}")
        except Exception as e:
            logger.error(f"[KIMI_WEB] Token refresh network error: {e}")

        return None

    async def create_chat_session(self, name: str = "FreeAi Sovereign Session") -> Optional[str]:
        """Creates an ephemeral chat session on Kimi Web."""
        token = await self.get_access_token()
        if not token:
            return None

        url = f"{KIMI_WEB_BASE}/api/chat"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": DEFAULT_KIMI_USER_AGENT,
        }
        payload = {"name": name, "is_example": False}

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(url, headers=headers, json=payload)
                if resp.status_code == 200:
                    data = resp.json()
                    chat_id = data.get("id")
                    if chat_id:
                        self._active_chat_id = chat_id
                        return chat_id
                else:
                    logger.warning(f"[KIMI_WEB] Failed to create chat session: HTTP {resp.status_code}")
        except Exception as e:
            logger.error(f"[KIMI_WEB] Create chat network error: {e}")

        return None

    async def query_kimi_web(
        self,
        prompt: str,
        chat_id: Optional[str] = None,
        system_prompt: Optional[str] = None,
        use_search: bool = True,
        timeout_sec: int = 45,
    ) -> Optional[Dict[str, Any]]:
        """Queries Kimi Web completion stream and aggregates delta tokens into text."""
        collected: List[str] = []
        async for token in self.stream_kimi_web(
            prompt=prompt,
            chat_id=chat_id,
            system_prompt=system_prompt,
            use_search=use_search,
            timeout_sec=timeout_sec,
        ):
            collected.append(token)

        if collected:
            return {
                "provider": "kimi_web",
                "model": "kimi-k3-web",
                "content": "".join(collected),
            }
        return None

    async def stream_kimi_web(
        self,
        prompt: str,
        chat_id: Optional[str] = None,
        system_prompt: Optional[str] = None,
        use_search: bool = True,
        timeout_sec: int = 45,
    ) -> AsyncGenerator[str, None]:
        """Streams typewriter tokens directly from Kimi Web completion/stream."""
        token = await self.get_access_token()
        if not token:
            return

        cid = chat_id or self._active_chat_id or await self.create_chat_session()
        if not cid:
            return

        url = f"{KIMI_WEB_BASE}/api/chat/{cid}/completion/stream"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "text/event-stream",
            "User-Agent": DEFAULT_KIMI_USER_AGENT,
        }

        full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
        payload = {
            "messages": [{"role": "user", "content": full_prompt}],
            "refs": [],
            "use_search": use_search,
        }

        try:
            async with httpx.AsyncClient(timeout=timeout_sec) as client:
                async with client.stream("POST", url, headers=headers, json=payload) as resp:
                    if resp.status_code == 401:
                        # Access token might have expired early, renew once
                        token = await self.get_access_token(force_refresh=True)
                        return
                    if resp.status_code != 200:
                        logger.warning(f"[KIMI_WEB] Completion stream HTTP {resp.status_code}")
                        return

                    async for line in resp.aiter_lines():
                        line_str = line.strip()
                        if not line_str or line_str == "data: [DONE]":
                            continue
                        if line_str.startswith("data: "):
                            raw_json = line_str[6:].strip()
                            try:
                                chunk = json.loads(raw_json)
                                # Kimi web event formats: {"event": "cmpl", "text": "..."}
                                event = chunk.get("event")
                                if event == "cmpl" or (not event and "text" in chunk):
                                    text = chunk.get("text", "")
                                    if text:
                                        yield text
                            except Exception:
                                pass
        except Exception as e:
            logger.error(f"[KIMI_WEB] Stream error: {e}")

    async def query_kimi_official(
        self,
        prompt: str,
        model: str = "moonshot-v1-auto",
        system_prompt: Optional[str] = None,
        timeout_sec: int = 40,
    ) -> Optional[Dict[str, Any]]:
        """Queries official Moonshot Developer API (https://api.moonshot.cn/v1)."""
        api_key = self.api_key or os.getenv("KIMI_API_KEY") or os.getenv("MOONSHOT_API_KEY")
        if not api_key:
            return None

        url = f"{KIMI_API_BASE}/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "FreeAI-Kimi-Official/1.0",
        }

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": model,
            "messages": messages,
            "temperature": 0.3,
        }

        try:
            async with httpx.AsyncClient(timeout=timeout_sec) as client:
                resp = await client.post(url, headers=headers, json=payload)
                if resp.status_code == 200:
                    data = resp.json()
                    choices = data.get("choices") or []
                    if choices and "message" in choices[0]:
                        content = choices[0]["message"].get("content") or ""
                        return {"provider": "kimi", "model": model, "content": content}
        except Exception as e:
            logger.error(f"[KIMI_OFFICIAL] API query error: {e}")
        return None
