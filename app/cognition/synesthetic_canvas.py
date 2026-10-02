"""Live Synesthetic Canvas & Multimodal Real-Time Projector.
Synchronizes spoken words with real-time visual frames (Mermaid diagrams, code snippets,
Shadcn UI components) projected directly into the Telegram Mini App (TMA).
"""

import enum
import logging
import re
import time
import uuid
from typing import Dict, Any, Optional

logger = logging.getLogger("freeai.cognition.synesthetic_canvas")


class SynestheticFrameType(str, enum.Enum):
    MERMAID = "MERMAID"
    CODE = "CODE"
    UI_COMPONENT = "UI_COMPONENT"
    THOUGHT_PULSE = "THOUGHT_PULSE"
    METRIC = "METRIC"


class SynestheticFrame:
    """Represents an atomic visual frame projected to the user's screen in real time."""

    def __init__(
        self,
        frame_type: SynestheticFrameType,
        payload: str,
        speech_transcript: str = "",
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.frame_id = f"frame_{uuid.uuid4().hex[:8]}"
        self.frame_type = frame_type
        self.payload = payload
        self.speech_transcript = speech_transcript
        self.metadata = metadata or {}
        self.timestamp = time.time()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "frame_id": self.frame_id,
            "frame_type": self.frame_type.value,
            "payload": self.payload,
            "speech_transcript": self.speech_transcript,
            "metadata": self.metadata,
            "timestamp": self.timestamp
        }


class SynestheticCanvasStreamer:
    """Extracts concepts from live speech & consciousness and projects synchronized visual frames."""

    def __init__(self):
        self.frame_history = []

    def generate_frame_from_speech(self, speech_text: str) -> SynestheticFrame:
        """Analyzes incoming speech transcript and generates the matching multimodal visual frame."""
        text_lower = speech_text.lower()

        # 1. Architecture & Flowchart detection -> Mermaid diagram
        arch_triggers = ["architecture", "schéma", "schema", "flux", "diagram", "diagramme", "reverse proxy", "passerelle", "pipeline", "topologie"]
        if any(w in text_lower for w in arch_triggers):
            mermaid_diagram = (
                "graph TD\n"
                "    User([📱 Smartphone Telegram]) -->|WebRTC / TMA| Gateway[⚡ Realtime Call Gateway]\n"
                "    Gateway -->|RAM Audio Stream| Voice[🎙️ Zero-RAM Whisper LPU]\n"
                "    Gateway -->|Live Synesthesia| Canvas[👁️ Synesthetic Canvas]\n"
                "    Gateway -->|Stealth Actions| TechLead[🧠 Tech Lead Fortress]\n"
                "    TechLead -->|Sub-second Output| Canvas"
            )
            frame = SynestheticFrame(
                frame_type=SynestheticFrameType.MERMAID,
                payload=mermaid_diagram,
                speech_transcript=speech_text,
                metadata={"title": "Architecture Temps Réel FreeAI"}
            )
            self.frame_history.append(frame)
            return frame

        # 2. Code & Programming detection -> Syntax-highlighted code snippet
        code_triggers = ["code", "fonction", "def ", "python", "script", "endpoint", "classe", "algorithme", "sanitize"]
        if any(w in text_lower for w in code_triggers):
            # Extract code if present or format sample
            extracted = self._extract_code_or_template(speech_text)
            frame = SynestheticFrame(
                frame_type=SynestheticFrameType.CODE,
                payload=extracted,
                speech_transcript=speech_text,
                metadata={"language": "python"}
            )
            self.frame_history.append(frame)
            return frame

        # 3. UI & Design System detection -> Shadcn UI Component spec
        ui_triggers = ["ui", "composant", "interface", "bouton", "button", "card", "carte", "dashboard", "shadcn", "modal", "orbe"]
        if any(w in text_lower for w in ui_triggers):
            component_spec = (
                "<div class='rounded-xl border border-cyan-500/30 bg-slate-900/80 p-4 shadow-xl backdrop-blur'>\n"
                "  <div class='flex items-center justify-between pb-2'>\n"
                "    <h3 class='text-sm font-semibold text-cyan-400'>FreeAI Live Neural Dashboard</h3>\n"
                "    <span class='rounded-full bg-emerald-500/20 px-2 py-0.5 text-xs text-emerald-300'>Active</span>\n"
                "  </div>\n"
                "  <p class='text-xs text-slate-300'>Flux audio WebRTC streaming à 300 ms en RAM pure.</p>\n"
                "  <div class='mt-3 flex gap-2'>\n"
                "    <button class='rounded-lg bg-cyan-500 px-3 py-1.5 text-xs font-medium text-black hover:bg-cyan-400'>Action Rapide</button>\n"
                "  </div>\n"
                "</div>"
            )
            frame = SynestheticFrame(
                frame_type=SynestheticFrameType.UI_COMPONENT,
                payload=component_spec,
                speech_transcript=speech_text,
                metadata={"framework": "shadcn/ui", "variant": "cyberpunk"}
            )
            self.frame_history.append(frame)
            return frame

        # Default: Thought pulse
        frame = SynestheticFrame(
            frame_type=SynestheticFrameType.THOUGHT_PULSE,
            payload=f"💡 Pensée synchronisée : {speech_text[:120]}...",
            speech_transcript=speech_text
        )
        self.frame_history.append(frame)
        return frame

    def _extract_code_or_template(self, speech_text: str) -> str:
        """Extracts code block or creates clean python template from speech."""
        match = re.search(r"(def\s+[a-zA-Z_][a-zA-Z0-9_]*\s*\(.*?\):.*)", speech_text)
        if match:
            return match.group(1)
        return (
            "def secure_stream_handler(audio_chunk: bytes) -> bytes:\n"
            "    # Zero-SSD buffer processing\n"
            "    sanitized = audio_chunk.strip()\n"
            "    return sanitized\n"
        )
