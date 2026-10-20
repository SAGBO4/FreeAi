"""OurFreeModel Sovereign Bridge for FreeAi (Feature F-34).
Faithfully reproduces and integrates the reverse-engineered zero-cost LLM conduits
from dsh-our-free-model:
1. OpenCode Zen Gateway (/inference/v1/chat/completions) with v2 fingerprint,
   descending timestamp session IDs, verbatim read/shell tools, and tool_choice sanitization.
2. Kilo AI Public Gateway (/api/gateway/chat/completions) keyless free pool.
3. Local Standalone Forward Gateway auto-discovery (ports 18900, 18899, 18923).
Supports MEMORY_MODE="neant" (100% ephemeral in-RAM execution, zero disk writes).
"""

import os
import re
import time
import json
import socket
import asyncio
import hashlib
import secrets
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List, AsyncGenerator, Tuple
import httpx

logger = logging.getLogger("our_free_model_bridge")

BASE62 = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
CLIENT_UA = "opencode/latest/2.0.26/cli"
OPENCODE_BASE = os.getenv("OUR_FREE_MODEL_BASE", "https://opencode.ai").rstrip("/")
KILO_BASE = os.getenv("OUR_FREE_MODEL_KILO_BASE", "https://api.kilo.ai/api/gateway").rstrip("/")

SESSION_RE = re.compile(r"^ses_[0-9a-f]{12}[0-9A-Za-z]{14}$")
SESSION_DESCENDING_RE = re.compile(r"^[0-9a-f]{9}f[c-f][0-9a-f]$")

_last_stamp = 0
_seq = 0

FINGERPRINT_TOOL_DEFINITIONS = {
    "read": {
        "type": "function",
        "function": {
            "name": "read",
            "description": (
                "Read the contents of a file or directory. Supports text files, images, and PDFs. "
                "Images and PDFs are presented directly to the model. Each text line is prefixed by "
                "its 1-based line number as <line>: <content>. The prefix is for reference and is not "
                "part of the file content. Directory entries are returned one per line. Use offset and "
                "limit to read large files or directories in sections. Prefer one larger read over many "
                "small slices, and use grep to find specific content in large files."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File or directory to read"},
                    "offset": {
                        "type": "integer",
                        "minimum": 0,
                        "description": "The line or directory entry to start reading from (1-based)",
                    },
                    "limit": {
                        "type": "integer",
                        "minimum": 0,
                        "description": "The maximum number of lines or directory entries to read (defaults to and capped at 2000)",
                    },
                },
                "required": ["path"],
                "additionalProperties": False,
            },
        },
    },
    "shell": {
        "type": "function",
        "function": {
            "name": "shell",
            "description": (
                "Execute a shell command and return its output. Commands run on Linux using bash. "
                "Quote file paths containing spaces or special characters. Prefer dedicated tools over "
                "shell commands when possible. When output is large, the full result is saved to a file "
                "and a truncated preview is returned. Rely on automatic truncation unless filtering the "
                "output is more useful. Commands accept an optional timeout, background commands have no "
                "timeout by default. Background commands return immediately, and you will be notified "
                "when they complete."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "Shell command string to execute"},
                    "workdir": {
                        "type": "string",
                        "description": "Working directory to execute the command in. Defaults to the current working directory. When possible, avoid changing directories in the command and set the working directory here instead.",
                    },
                    "timeout": {
                        "type": "integer",
                        "minimum": 0,
                        "description": "Timeout in milliseconds. Set to 0 to disable the timeout. Defaults to 120000 for foreground commands. Background commands have no timeout by default.",
                    },
                    "background": {
                        "type": "boolean",
                        "description": "Run the command in the background and return immediately (useful for dev servers and long-running builds). You do not need to use '&' at the end of the command when using this parameter. You will be notified when it completes. DO NOT poll for completion.",
                    },
                },
                "required": ["command"],
                "additionalProperties": False,
            },
        },
    },
}

INJECTED_TOOL_NOTE = (
    "Do not call the `read` or `shell` tools; they are placeholders that do nothing. "
    "Use the other tools you have been given instead."
)

OPENCODE_FREE_MODELS = {
    "deepseek-v4.1-flash-free": {
        "name": "DeepSeek V4.1 Flash (Gratuit & Illimité)",
        "context_window": 1048576,
        "max_output": 384000,
        "vision": True,
        "reasoning": True,
        "efforts": ["disabled", "low", "high", "max"],
    },
    "glm-5.3-flash-free": {
        "name": "GLM 5.3 Flash (Gratuit & Illimité)",
        "context_window": 1048576,
        "max_output": 131072,
        "vision": True,
        "reasoning": True,
        "efforts": ["low", "high", "max"],
    },
    "nemotron-3.5-super-vl-free": {
        "name": "Nemotron 3.5 Super VL (Gratuit & Illimité)",
        "context_window": 1048576,
        "max_output": 131072,
        "vision": True,
        "reasoning": True,
        "efforts": ["disabled", "minimal", "low", "medium", "high", "xhigh"],
    },
    "space-bunny-free": {
        "name": "Space Bunny (Gratuit & Illimité)",
        "context_window": 1048576,
        "max_output": 524288,
        "vision": True,
        "reasoning": True,
        "efforts": ["low", "medium", "high", "xhigh", "max"],
    },
    "mimo-v2.6-flash-free": {
        "name": "MiMo V2.6 Flash (Gratuit & Illimité)",
        "context_window": 1048576,
        "max_output": 131072,
        "vision": True,
        "reasoning": True,
    },
    "longcat-2.5-preview-free": {
        "name": "Longcat 2.5 Preview (Gratuit & Illimité)",
        "context_window": 1048576,
        "max_output": 131072,
        "vision": False,
        "reasoning": True,
    },
    "big-pickle": {
        "name": "Big Pickle (Gratuit & Illimité)",
        "context_window": 262144,
        "max_output": 131072,
        "vision": True,
        "reasoning": False,
    },
}


def is_canonical_session(session_id: str) -> bool:
    """Checks if session_id satisfies the gate's length and descending bitwise format."""
    if not isinstance(session_id, str):
        return False
    clean = session_id.strip()
    return bool(SESSION_RE.match(clean) and SESSION_DESCENDING_RE.match(clean[4:16]))


def _base62_fixed(data: bytes, width: int = 14) -> str:
    """Renders bytes as width big-endian Base62 characters."""
    n = int.from_bytes(data, byteorder="big")
    chars = []
    base = 62
    for _ in range(width):
        chars.append(BASE62[n % base])
        n //= base
    return "".join(reversed(chars))


def mint_session_id(timestamp_ms: Optional[int] = None) -> str:
    """Mints a v2 OpenCode session ID with descending 48-bit timestamp and counter 1-63."""
    global _last_stamp, _seq
    if timestamp_ms is None:
        timestamp_ms = int(time.time() * 1000)

    if timestamp_ms != _last_stamp:
        _last_stamp = timestamp_ms
        _seq = 0
    _seq = (_seq + 1) % 63
    if _seq == 0:
        _seq = 1

    current = (timestamp_ms * 0x1000) + _seq
    inverted = (~current) & 0xFFFFFFFFFFFF
    time_hex = f"{inverted:012x}"
    random_part = "".join(secrets.choice(BASE62) for _ in range(14))
    return f"ses_{time_hex}{random_part}"


def canonicalize_session(conversation_key: str) -> str:
    """Maps a conversation key deterministically to a valid descending session ID."""
    digest = hashlib.sha256(f"ses\0{conversation_key}".encode("utf-8")).digest()
    d0, d1, d2, d3, d4 = digest[0], digest[1], digest[2], digest[3], digest[4]
    val = (d0 << 28) | (d1 << 20) | (d2 << 12) | (d3 << 4) | (d4 >> 4)
    current = (val << 12) | 1
    inverted = (~current) & 0xFFFFFFFFFFFF
    time_hex = f"{inverted:012x}"
    random_part = _base62_fixed(digest[6:16], 14)
    return f"ses_{time_hex}{random_part}"


def build_opencode_headers(session_id: str, stream: bool = True) -> Dict[str, str]:
    """Generates the exact v2 client headers required by OpenCode."""
    return {
        "content-type": "application/json",
        "authorization": "Bearer public",
        "user-agent": CLIENT_UA,
        "x-opencode-client": "cli",
        "x-opencode-session": session_id,
        "x-opencode-session-id": session_id,
        "x-session-affinity": session_id,
        "x-session-id": session_id,
        "x-opencode-project": "global",
        "accept": "text/event-stream" if stream else "*/*",
    }


def _tool_name(tool: Any) -> str:
    if not isinstance(tool, dict):
        return ""
    if "name" in tool and isinstance(tool["name"], str):
        return tool["name"].strip()
    fn = tool.get("function")
    if isinstance(fn, dict) and isinstance(fn.get("name"), str):
        return fn["name"].strip()
    return ""


def apply_opencode_fingerprint(body: Dict[str, Any]) -> Dict[str, str]:
    """Applies the v2 tool gate requirements to body in-place.
    Returns alias map (sent alias -> original caller tool name)."""
    tools = list(body.get("tools") or [])
    taken = { _tool_name(t) for t in tools if _tool_name(t) }
    alias_map: Dict[str, str] = {}
    out_tools: List[Dict[str, Any]] = []

    seen = set()
    present = set()

    for tool in tools:
        name = _tool_name(tool)
        if name not in ("read", "shell"):
            out_tools.append(tool)
            continue
        if name in seen:
            continue
        seen.add(name)

        # Check if it carries the exact fingerprint definition
        fn = tool.get("function", {}) if "function" in tool else tool
        desc = fn.get("description", "")
        params = fn.get("parameters", {})
        want = FINGERPRINT_TOOL_DEFINITIONS[name]["function"]

        if desc == want["description"] and params == want["parameters"]:
            out_tools.append(tool)
            present.add(name)
        else:
            # Rename conflicting caller tool
            alias = f"{name}_client"
            idx = 2
            while alias in taken:
                alias = f"{name}_client{idx}"
                idx += 1
            taken.add(alias)
            alias_map[alias] = name

            renamed = json.loads(json.dumps(tool))
            if "function" in renamed:
                renamed["function"]["name"] = alias
            else:
                renamed["name"] = alias
            out_tools.append(renamed)

    injected = []
    for required in ("read", "shell"):
        if required not in present:
            out_tools.append(json.loads(json.dumps(FINGERPRINT_TOOL_DEFINITIONS[required])))
            injected.append(required)

    body["tools"] = out_tools

    # tool_choice: "none" is rejected by v2 gate
    tc = body.get("tool_choice")
    if tc == "none" or (isinstance(tc, dict) and tc.get("type") == "none"):
        body.pop("tool_choice", None)

    # Note injected tools
    if injected:
        messages = list(body.get("messages") or [])
        if messages and messages[0].get("role") == "system":
            first = messages[0]
            existing = first.get("content", "")
            messages[0] = {"role": "system", "content": f"{existing}\n\n{INJECTED_TOOL_NOTE}".strip()}
        else:
            messages.insert(0, {"role": "system", "content": INJECTED_TOOL_NOTE})
        body["messages"] = messages

    return alias_map


def filter_kilo_free_models(raw_payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Filters models where isFree is True from Kilo listing."""
    data = raw_payload.get("data") or []
    return [m for m in data if m.get("isFree") is True and m.get("id")]


def build_kilo_chat_payload(
    model: str,
    messages: List[Dict[str, Any]],
    reasoning_effort: str = "high",
    stream: bool = True,
) -> Dict[str, Any]:
    """Builds chat payload for Kilo AI keyless gateway."""
    payload: Dict[str, Any] = {
        "model": model,
        "messages": messages,
        "stream": stream,
    }
    if reasoning_effort:
        payload["reasoning"] = {"effort": reasoning_effort}
    return payload


async def _probe_http_port(host: str, port: int, timeout_sec: float = 1.0) -> bool:
    """Non-blocking TCP probe to check if a local port is listening."""
    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(host, port), timeout=timeout_sec
        )
        writer.close()
        await writer.wait_closed()
        return True
    except (OSError, asyncio.TimeoutError):
        return False


_LOCAL_GATEWAY_CACHE_TTL_SEC = 30.0
_local_gateway_cache: Dict[str, Any] = {"value": None, "checked_at": -1.0}


async def detect_local_forward_gateway(
    ports: Optional[List[int]] = None,
    settings_search_paths: Optional[List[Path]] = None,
) -> Optional[Dict[str, Any]]:
    """Detects if dsh-our-free-model or standalone forward gateway is active on loopback.

    The default (no explicit ports/paths) call is cached for _LOCAL_GATEWAY_CACHE_TTL_SEC:
    federation.py's fallback cascade calls this on every query that falls through to it,
    and re-probing 3 loopback ports on each such call added needless latency to the common
    case where no local gateway is running. Explicit args (used by tests) bypass the cache."""
    use_cache = ports is None and settings_search_paths is None
    if use_cache:
        now = time.time()
        if now - _local_gateway_cache["checked_at"] < _LOCAL_GATEWAY_CACHE_TTL_SEC:
            return _local_gateway_cache["value"]

    if ports is None:
        ports = [18900, 18899, 18923]

    if settings_search_paths is None:
        home = Path.home()
        settings_search_paths = [
            home / ".our-free-model" / "settings.json",
            home / ".config" / "dsh" / "our-free-model" / "settings.json",
            home / ".dsh" / "our-free-model" / "settings.json",
        ]

    forward_key = ""
    for path in settings_search_paths:
        try:
            if path.exists():
                data = json.loads(path.read_text(encoding="utf-8"))
                key = data.get("forwardKey") or data.get("standaloneLanKey")
                if key:
                    forward_key = key
                    break
        except Exception:
            pass

    result = None
    for port in ports:
        if await _probe_http_port("127.0.0.1", port):
            result = {
                "port": port,
                "base_url": f"http://127.0.0.1:{port}",
                "api_key": forward_key or "ofm-local",
            }
            break

    if use_cache:
        _local_gateway_cache["value"] = result
        _local_gateway_cache["checked_at"] = time.time()
    return result


class OurFreeModelBridge:
    """Core sovereign bridge uniting OpenCode, Kilo AI, and Local Forward Proxy."""

    _instance: Optional["OurFreeModelBridge"] = None
    _SESSION_CACHE_MAX_ENTRIES = 256

    def __init__(self):
        self._session_cache: Dict[str, str] = {}

    @classmethod
    def get_instance(cls) -> "OurFreeModelBridge":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def get_session(self, conversation_id: Optional[str] = None) -> str:
        """Returns stable descending session ID for conversation.

        _session_cache lives on the process-wide singleton, so it is bounded with
        FIFO eviction instead of growing forever (Mode NÉANT is supposed to be
        ephemeral, not an unbounded in-RAM leak over a long-running process)."""
        cid = conversation_id or "global"
        if cid not in self._session_cache:
            if len(self._session_cache) >= self._SESSION_CACHE_MAX_ENTRIES:
                oldest_cid = next(iter(self._session_cache))
                del self._session_cache[oldest_cid]
            self._session_cache[cid] = canonicalize_session(cid)
        return self._session_cache[cid]

    async def query_opencode(
        self,
        prompt: str,
        model: str = "deepseek-v4.1-flash-free",
        system_prompt: Optional[str] = None,
        conversation_id: Optional[str] = None,
        reasoning_effort: Optional[str] = None,
        timeout_sec: int = 40,
    ) -> Optional[Dict[str, Any]]:
        """Queries OpenCode Zen Gateway (/inference/v1/chat/completions) without any API key.
        OpenCode free-tier requires stream=True; tokens are streamed and aggregated in RAM."""
        sid = self.get_session(conversation_id)
        headers = build_opencode_headers(sid, stream=True)

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        body: Dict[str, Any] = {
            "model": model,
            "messages": messages,
            "stream": True,
        }

        # Reasoning effort handling
        if reasoning_effort and model in OPENCODE_FREE_MODELS:
            model_caps = OPENCODE_FREE_MODELS[model]
            if "efforts" in model_caps and reasoning_effort in model_caps["efforts"]:
                body["reasoning_effort"] = (
                    "none" if reasoning_effort == "disabled" else reasoning_effort
                )

        apply_opencode_fingerprint(body)

        url = f"{OPENCODE_BASE}/inference/v1/chat/completions"
        collected_tokens = []
        try:
            async with httpx.AsyncClient(timeout=timeout_sec) as client:
                async with client.stream("POST", url, headers=headers, json=body) as resp:
                    if resp.status_code != 200:
                        err_text = await resp.aread()
                        logger.warning(
                            f"[OPENCODE] HTTP {resp.status_code}: {err_text[:200].decode('utf-8', errors='ignore')}"
                        )
                        return None
                    async for line in resp.aiter_lines():
                        line_str = line.strip()
                        if line_str.startswith("data: ") and line_str != "data: [DONE]":
                            try:
                                chunk = json.loads(line_str[6:])
                                delta = chunk.get("choices", [{}])[0].get("delta", {}).get("content", "")
                                if delta:
                                    collected_tokens.append(delta)
                            except Exception:
                                pass
            if collected_tokens:
                return {"content": "".join(collected_tokens), "provider": "opencode_free", "model": model}
        except Exception as e:
            logger.error(f"[OPENCODE] Failed to query {model}: {e}")
            return None
        return None

    async def stream_opencode(
        self,
        prompt: str,
        model: str = "deepseek-v4.1-flash-free",
        system_prompt: Optional[str] = None,
        conversation_id: Optional[str] = None,
        reasoning_effort: Optional[str] = None,
        timeout_sec: int = 40,
    ) -> AsyncGenerator[str, None]:
        """Streams tokens in real time directly from OpenCode Zen Gateway."""
        sid = self.get_session(conversation_id)
        headers = build_opencode_headers(sid, stream=True)

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        body: Dict[str, Any] = {
            "model": model,
            "messages": messages,
            "stream": True,
        }

        if reasoning_effort and model in OPENCODE_FREE_MODELS:
            model_caps = OPENCODE_FREE_MODELS[model]
            if "efforts" in model_caps and reasoning_effort in model_caps["efforts"]:
                body["reasoning_effort"] = (
                    "none" if reasoning_effort == "disabled" else reasoning_effort
                )

        apply_opencode_fingerprint(body)
        url = f"{OPENCODE_BASE}/inference/v1/chat/completions"

        try:
            async with httpx.AsyncClient(timeout=timeout_sec) as client:
                async with client.stream("POST", url, headers=headers, json=body) as resp:
                    if resp.status_code != 200:
                        return
                    async for line in resp.aiter_lines():
                        line_str = line.strip()
                        if line_str.startswith("data: ") and line_str != "data: [DONE]":
                            try:
                                chunk = json.loads(line_str[6:])
                                delta = chunk.get("choices", [{}])[0].get("delta", {}).get("content", "")
                                if delta:
                                    yield delta
                            except Exception:
                                pass
        except Exception as e:
            logger.error(f"[OPENCODE] Stream error {model}: {e}")

    async def query_kilo(
        self,
        prompt: str,
        model: str = "kilo-auto/free",
        system_prompt: Optional[str] = None,
        reasoning_effort: str = "high",
        timeout_sec: int = 40,
    ) -> Optional[Dict[str, Any]]:
        """Queries Kilo AI keyless public gateway without any credentials."""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        body = build_kilo_chat_payload(
            model=model,
            messages=messages,
            reasoning_effort=reasoning_effort,
            stream=False,
        )

        headers = {
            "content-type": "application/json",
            "accept": "application/json",
            "user-agent": "FreeAi-Sovereign-Conduit",
        }

        url = f"{KILO_BASE}/chat/completions"
        try:
            async with httpx.AsyncClient(timeout=timeout_sec) as client:
                resp = await client.post(url, headers=headers, json=body)
                if resp.status_code != 200:
                    logger.warning(f"[KILO] HTTP {resp.status_code}: {resp.text[:200]}")
                    return None
                data = resp.json()
                choices = data.get("choices") or []
                if choices and "message" in choices[0]:
                    content = choices[0]["message"].get("content") or ""
                    return {"content": content, "raw": data}
        except Exception as e:
            logger.error(f"[KILO] Failed to query {model}: {e}")
            return None
        return None
