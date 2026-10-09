"""Stealth Conduit & Resilient Tor / Direct Proxy Router.
Detects local SOCKS5 proxy (Tor on 127.0.0.1:9050) and routes async traffic
with automatic fallback to direct egress if Tor is offline.
"""

import time
import socket
import logging
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, Optional

import httpx

logger = logging.getLogger("freeai.network.stealth_conduit")


@dataclass
class ConduitStatus:
    tor_available: bool = False
    active_mode: str = "direct"  # "socks5_tor" or "direct"
    proxy_url: Optional[str] = None
    telemetry: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class StealthConduit:
    """Manages anonymous or direct egress for FreeAi agents."""

    def __init__(self, tor_host: str = "127.0.0.1", tor_port: int = 9050):
        self.tor_host = tor_host
        self.tor_port = tor_port
        self.socks5_url = f"socks5://{self.tor_host}:{self.tor_port}"

    def _probe_socks5_port(self) -> bool:
        """Probes whether a SOCKS5 listener is actively accepting connections."""
        try:
            with socket.create_connection((self.tor_host, self.tor_port), timeout=0.3):
                return True
        except (socket.timeout, ConnectionRefusedError, OSError):
            return False

    def get_conduit_status(self) -> ConduitStatus:
        """Determines active egress routing mode dynamically."""
        is_tor = self._probe_socks5_port()
        if is_tor:
            return ConduitStatus(
                tor_available=True,
                active_mode="socks5_tor",
                proxy_url=self.socks5_url,
                telemetry={"listener": f"{self.tor_host}:{self.tor_port}"}
            )
        return ConduitStatus(
            tor_available=False,
            active_mode="direct",
            proxy_url=None,
            telemetry={"fallback_reason": "No active SOCKS5 listener detected"}
        )

    async def fetch_url(
        self,
        url: str,
        method: str = "GET",
        headers: Optional[Dict[str, str]] = None,
        timeout_sec: float = 8.0
    ) -> Dict[str, Any]:
        """Fetches URL using Tor if available, with transparent direct fallback."""
        status = self.get_conduit_status()
        start = time.time()

        req_headers = headers or {
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) FreeAi-StealthConduit/1.0"
        }

        # Try SOCKS5 if Tor is active
        if status.tor_available:
            try:
                # httpx supports SOCKS proxies via socksio
                async with httpx.AsyncClient(proxy=self.socks5_url, timeout=timeout_sec) as client:
                    resp = await client.request(method, url, headers=req_headers)
                    return {
                        "success": True,
                        "status_code": resp.status_code,
                        "text": resp.text,
                        "mode_used": "socks5_tor",
                        "latency_sec": round(time.time() - start, 3)
                    }
            except Exception as e:
                logger.warning(f"SOCKS5 routing failed ({e}), falling back to direct egress.")

        # Fallback to direct connection
        try:
            async with httpx.AsyncClient(timeout=timeout_sec) as client:
                resp = await client.request(method, url, headers=req_headers)
                return {
                    "success": True,
                    "status_code": resp.status_code,
                    "text": resp.text,
                    "mode_used": "direct",
                    "latency_sec": round(time.time() - start, 3)
                }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "mode_used": "direct_error",
                "latency_sec": round(time.time() - start, 3)
            }
