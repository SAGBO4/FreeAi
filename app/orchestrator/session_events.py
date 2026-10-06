"""OpenCode Real-Time Event Contracts & Schemas for FreeAI.
Implements the exact streaming events and lifecycle payloads used by OpenCode UI:
- Server handshakes and heartbeats
- Session status and step transitions
- Deep reasoning / thinking deltas with headings
- Text streaming deltas (paced)
- Tool call lifecycle: called, progress, success, failed, with duration & diffs
- Step ended summary with token telemetry & file patches
"""

import time
import json
from enum import Enum
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field


class SessionEventType(str, Enum):
    # Server lifecycle
    SERVER_CONNECTED = "server.connected"
    SERVER_HEARTBEAT = "server.heartbeat"

    # Session lifecycle & status
    SESSION_STATUS = "session.status"
    STEP_STARTED = "session.next.step.started"
    STEP_ENDED = "session.next.step.ended"

    # Stream of consciousness / Reasoning
    REASONING_STARTED = "session.next.reasoning.started"
    REASONING_DELTA = "session.next.reasoning.delta"
    REASONING_ENDED = "session.next.reasoning.ended"

    # Streaming Assistant text
    TEXT_STARTED = "session.next.text.started"
    TEXT_DELTA = "session.next.text.delta"
    TEXT_ENDED = "session.next.text.ended"

    # Tool execution lifecycle
    TOOL_CALLED = "session.next.tool.called"
    TOOL_PROGRESS = "session.next.tool.progress"
    TOOL_SUCCESS = "session.next.tool.success"
    TOOL_FAILED = "session.next.tool.failed"

    # Terminal / PTY
    TERMINAL_OUTPUT = "terminal.output"


class SessionStatusInfo(BaseModel):
    status: str = Field(..., description="Status: 'idle' | 'busy' | 'retry' | 'error'")
    model: Optional[str] = None
    agent: Optional[str] = None
    active_tool: Optional[str] = None
    timestamp: float = Field(default_factory=time.time)


class ReasoningDelta(BaseModel):
    part_id: str
    delta: str
    heading: Optional[str] = None
    timestamp: float = Field(default_factory=time.time)


class TextDelta(BaseModel):
    part_id: str
    delta: str
    timestamp: float = Field(default_factory=time.time)


class ToolCallEvent(BaseModel):
    part_id: str
    tool_name: str
    call_id: str
    arguments: Dict[str, Any] = Field(default_factory=dict)
    status: str = Field("running", description="'running' | 'completed' | 'failed'")
    duration_ms: Optional[int] = None
    output: Optional[str] = None
    error: Optional[str] = None
    diff: Optional[str] = None
    timestamp: float = Field(default_factory=time.time)


class StepEndedEvent(BaseModel):
    step_index: int = 1
    tokens_used: int = 0
    duration_ms: int = 0
    files_modified: List[str] = Field(default_factory=list)
    diff: Optional[str] = None
    timestamp: float = Field(default_factory=time.time)


class SessionStreamEvent(BaseModel):
    event_type: SessionEventType
    session_id: str
    data: Dict[str, Any] = Field(default_factory=dict)
    timestamp: float = Field(default_factory=time.time)

    def to_sse(self) -> str:
        """Serializes event to standard Server-Sent Events (SSE) format."""
        payload = json.dumps({
            "event": self.event_type.value,
            "session_id": self.session_id,
            "timestamp": self.timestamp,
            "data": self.data
        }, ensure_ascii=False)
        return f"event: {self.event_type.value}\ndata: {payload}\n\n"
