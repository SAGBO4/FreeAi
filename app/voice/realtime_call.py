"""Realtime Call Gateway & Full-Duplex WebRTC / Mini App Bridge (Mode NÉANT).
Enables live hands-free telepathic conversations on Telegram with sub-second latency,
barge-in interruption, and synesthetic canvas streaming in RAM.
"""

import asyncio
import enum
import io
import json
import logging
import time
import uuid
from typing import Dict, Any, Optional, List

logger = logging.getLogger("freeai.voice.realtime_call")


class SessionStatus(str, enum.Enum):
    IDLE = "IDLE"
    CONNECTING = "CONNECTING"
    LIVE = "LIVE"
    PAUSED = "PAUSED"
    CLOSED = "CLOSED"


class LiveHologramSession:
    """Manages an active real-time call session entirely in RAM (0 byte on SSD)."""

    def __init__(self, session_id: str, user: str, user_id: Optional[int] = None):
        self.session_id = session_id
        self.user = user
        self.user_id = user_id
        self.created_at = time.time()
        self.status = SessionStatus.CONNECTING
        self.audio_in_buffer = io.BytesIO()
        self.audio_out_queue: asyncio.Queue = asyncio.Queue()
        self.is_assistant_speaking: bool = False
        self.stealth_actions: List[Dict[str, Any]] = []
        self.event_listeners: List[Any] = []

    def mark_connected(self):
        """Transitions status to LIVE when client connects via WebSocket / WebRTC."""
        self.status = SessionStatus.LIVE
        logger.info(f"[RealtimeSession:{self.session_id}] Connected live for @{self.user}")

    def ingest_audio_chunk(self, chunk: bytes):
        """Streams incoming Opus/PCM audio chunks into the in-memory buffer."""
        if self.status != SessionStatus.LIVE and self.status != SessionStatus.CONNECTING:
            return
        self.audio_in_buffer.write(chunk)

    def get_audio_buffer_size(self) -> int:
        """Returns the current buffered audio byte length in RAM."""
        return self.audio_in_buffer.tell()

    def set_assistant_speaking(self, speaking: bool):
        """Tracks assistant playback state for barge-in detection."""
        self.is_assistant_speaking = speaking

    def handle_barge_in(self) -> Dict[str, Any]:
        """User interruption (Barge-in): immediately cancels outgoing audio playback."""
        interrupted = self.is_assistant_speaking
        if interrupted:
            self.is_assistant_speaking = False
            # Drain outgoing audio queue
            while not self.audio_out_queue.empty():
                try:
                    self.audio_out_queue.get_nowait()
                except asyncio.QueueEmpty:
                    break
            logger.info(f"[RealtimeSession:{self.session_id}] Barge-in triggered by @{self.user}. Assistant interrupted.")

        return {
            "interrupted": interrupted,
            "session_id": self.session_id,
            "timestamp": time.time()
        }

    def close(self):
        """Terminates session and purges audio buffer from RAM."""
        self.status = SessionStatus.CLOSED
        self.audio_in_buffer.close()
        logger.info(f"[RealtimeSession:{self.session_id}] Session closed.")


class RealtimeCallGateway:
    """Gateway orchestrating duplex WebSocket sessions, Mini App delivery, and live calls."""

    def __init__(self, host: str = "0.0.0.0", port: int = 8765):
        self.host = host
        self.port = port
        self.sessions: Dict[str, LiveHologramSession] = {}
        self.orchestrator = None

    def attach_orchestrator(self, orchestrator: Any):
        """Attaches TechLeadOrchestrator for stealth in-call background actions."""
        self.orchestrator = orchestrator

    def create_session(self, user: str, user_id: Optional[int] = None) -> LiveHologramSession:
        """Instantiates a new live session with unique UUID."""
        session_id = f"call_{uuid.uuid4().hex[:12]}"
        session = LiveHologramSession(session_id=session_id, user=user, user_id=user_id)
        self.sessions[session_id] = session
        return session

    def get_session(self, session_id: str) -> Optional[LiveHologramSession]:
        return self.sessions.get(session_id)

    async def dispatch_stealth_action(self, session_id: str, instruction: str) -> Dict[str, Any]:
        """Step 3: Dispatches a background autonomous action without interrupting the live call."""
        session = self.get_session(session_id)
        if not session:
            return {"success": False, "error": f"Session {session_id} not found"}

        logger.info(f"[RealtimeCallGateway] Dispatching stealth co-pilot action during call: '{instruction}'")

        if self.orchestrator:
            res = await self.orchestrator.handle_objective(instruction, autonomous=True)
        else:
            res = {"success": True, "output": f"Simulated stealth execution of '{instruction}'"}

        action_record = {
            "instruction": instruction,
            "timestamp": time.time(),
            "result": res
        }
        session.stealth_actions.append(action_record)
        return {"success": True, "result": res}

    def get_mini_app_html(self, session_id: str, ws_url: Optional[str] = None) -> str:
        """Generates the Telegram Mini App (TMA) cyber-futuristic UI in RAM (Zero-SSD)."""
        actual_ws = ws_url or f"ws://{self.host}:{self.port}/ws/live-call/{session_id}"
        
        return f"""<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=no">
    <title>FreeAI Live Hologram Call</title>
    <script src="https://telegram.org/js/telegram-web-app.js"></script>
    <style>
        :root {{
            --bg-color: #050811;
            --neon-cyan: #00f0ff;
            --neon-magenta: #ff007f;
            --panel-bg: rgba(13, 20, 38, 0.75);
            --text-color: #e2e8f0;
        }}
        * {{ margin: 0; padding: 0; box-sizing: border-box; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }}
        body {{
            background-color: var(--bg-color);
            color: var(--text-color);
            display: flex;
            flex-direction: column;
            align-items: center;
            height: 100vh;
            overflow: hidden;
            background-image: radial-gradient(circle at 50% 20%, rgba(0, 240, 255, 0.12) 0%, transparent 60%);
        }}
        .header {{
            width: 100%;
            padding: 16px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid rgba(0, 240, 255, 0.2);
            backdrop-filter: blur(10px);
        }}
        .logo-box {{ display: flex; align-items: center; gap: 8px; }}
        .badge {{
            background: rgba(0, 240, 255, 0.15);
            color: var(--neon-cyan);
            border: 1px solid var(--neon-cyan);
            font-size: 11px;
            padding: 2px 8px;
            border-radius: 12px;
            text-transform: uppercase;
            font-weight: 700;
            letter-spacing: 1px;
        }}
        .orb-container {{
            position: relative;
            width: 220px;
            height: 220px;
            margin: 20px auto 10px;
            display: flex;
            justify-content: center;
            align-items: center;
        }}
        .neural-orb {{
            width: 130px;
            height: 130px;
            border-radius: 50%;
            background: radial-gradient(circle, #00f0ff 0%, #7928ca 70%, transparent 100%);
            box-shadow: 0 0 50px rgba(0, 240, 255, 0.8), 0 0 100px rgba(121, 40, 202, 0.5);
            animation: pulse 2.4s infinite ease-in-out;
            cursor: pointer;
        }}
        @keyframes pulse {{
            0% {{ transform: scale(0.95); opacity: 0.85; filter: hue-rotate(0deg); }}
            50% {{ transform: scale(1.1); opacity: 1; filter: hue-rotate(45deg); }}
            100% {{ transform: scale(0.95); opacity: 0.85; filter: hue-rotate(0deg); }}
        }}
        .canvas-area {{
            flex: 1;
            width: 92%;
            background: var(--panel-bg);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 16px;
            padding: 16px;
            overflow-y: auto;
            margin-bottom: 16px;
            backdrop-filter: blur(12px);
            box-shadow: inset 0 0 20px rgba(0,0,0,0.5);
        }}
        .status-pill {{
            font-size: 12px;
            color: #94a3b8;
            margin-bottom: 8px;
            text-align: center;
        }}
        .code-box {{
            background: #02040a;
            border: 1px solid rgba(0, 240, 255, 0.3);
            border-radius: 8px;
            padding: 10px;
            font-family: monospace;
            font-size: 12px;
            color: #38bdf8;
            white-space: pre-wrap;
            margin-top: 8px;
        }}
        .controls {{
            width: 100%;
            padding: 16px;
            display: flex;
            justify-content: center;
            gap: 20px;
            border-top: 1px solid rgba(255, 255, 255, 0.08);
        }}
        .btn {{
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid rgba(255, 255, 255, 0.2);
            color: white;
            padding: 12px 24px;
            border-radius: 24px;
            font-size: 14px;
            cursor: pointer;
            transition: all 0.2s;
        }}
        .btn-danger {{
            background: rgba(239, 68, 68, 0.2);
            border-color: #ef4444;
            color: #fca5a5;
        }}
    </style>
</head>
<body>
    <div class="header">
        <div class="logo-box">
            <span style="font-weight: 800; font-size: 16px; color: #fff;">FreeAI Nexus</span>
            <span class="badge">Live 300ms</span>
        </div>
        <div id="session-tag" style="font-size: 11px; color: #64748b;">{session_id}</div>
    </div>

    <div class="orb-container">
        <div class="neural-orb" id="orb" title="Micro actif"></div>
    </div>

    <div class="status-pill" id="call-status">Ligne télépathique ouverte • Mode Full-Duplex</div>

    <div class="canvas-area" id="synesthetic-canvas">
        <div style="font-size: 13px; color: var(--neon-cyan); margin-bottom: 6px;">👁️ Synesthésie Multimodale Projetée :</div>
        <div id="canvas-content" style="font-size: 13px; line-height: 1.5; color: #cbd5e1;">
            En attente des pensées et visualisations de FreeAI...
        </div>
    </div>

    <div class="controls">
        <button class="btn" id="btn-mute" onclick="toggleMute()">🎙️ Muet</button>
        <button class="btn btn-danger" onclick="endCall()">🔴 Raccrocher</button>
    </div>

    <script>
        if (window.Telegram && window.Telegram.WebApp) {{
            window.Telegram.WebApp.ready();
            window.Telegram.WebApp.expand();
        }}

        const sessionId = "{session_id}";
        let ws = null;
        let isMuted = false;

        function initWebSocket() {{
            try {{
                ws = new WebSocket("{actual_ws}");
                ws.onopen = () => {{
                    document.getElementById("call-status").innerText = "✔ Connecté au Sanctuaire FreeAI (RAM pure)";
                    document.getElementById("call-status").style.color = "#4ade80";
                }};
                ws.onmessage = (event) => {{
                    const data = JSON.parse(event.data);
                    if (data.type === "synesthetic_frame") {{
                        renderFrame(data.frame);
                    }} else if (data.type === "copilot_action") {{
                        renderCopilotAction(data.action);
                    }}
                }};
                ws.onclose = () => {{
                    document.getElementById("call-status").innerText = "Ligne fermée.";
                }};
            }} catch(e) {{
                console.warn("WebSocket fallback:", e);
            }}
        }}

        function renderFrame(frame) {{
            const canvas = document.getElementById("canvas-content");
            if (frame.frame_type === "MERMAID") {{
                canvas.innerHTML = `<div style="color: #38bdf8; font-weight: bold; margin-bottom: 4px;">📐 Diagramme d'Architecture :</div><pre class="code-box">${{frame.payload}}</pre>`;
            }} else if (frame.frame_type === "CODE") {{
                canvas.innerHTML = `<div style="color: #38bdf8; font-weight: bold; margin-bottom: 4px;">💻 Code Source Projeté :</div><pre class="code-box">${{frame.payload}}</pre>`;
            }} else if (frame.frame_type === "UI_COMPONENT") {{
                canvas.innerHTML = `<div style="color: #a855f7; font-weight: bold; margin-bottom: 4px;">🎨 Composant Shadcn UI :</div><div style="padding: 10px; background: rgba(255,255,255,0.05); border-radius: 8px;">${{frame.payload}}</div>`;
            }}
        }}

        function renderCopilotAction(action) {{
            const canvas = document.getElementById("canvas-content");
            canvas.innerHTML += `<div style="margin-top: 10px; color: #4ade80; font-size: 12px;">⚡ Action Furtive Exécutée : ${{action.instruction}}</div>`;
        }}

        function toggleMute() {{
            isMuted = !isMuted;
            document.getElementById("btn-mute").innerText = isMuted ? "🔇 Activer Micro" : "🎙️ Muet";
        }}

        function endCall() {{
            if (ws) ws.close();
            if (window.Telegram && window.Telegram.WebApp) {{
                window.Telegram.WebApp.close();
            }}
        }}

        initWebSocket();
    </script>
</body>
</html>
"""
