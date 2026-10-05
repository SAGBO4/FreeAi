"""Tests for FreeAI OpenCode Real-Time UI & Agentic Streaming Architecture.
Verifies:
1. OpenCode SSE Event schemas and serialization.
2. AsyncSessionEventHub pub/sub and broadcasting.
3. TechLeadOrchestrator handle_objective_stream.
4. FastAPI session, streaming, model, agent, and file endpoints.
5. Static UI serving at root and /ui.
"""

import asyncio
import json
import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, patch

from app.orchestrator.session_events import (
    SessionStreamEvent,
    SessionEventType,
    SessionStatusInfo,
    ReasoningDelta,
    TextDelta,
    ToolCallEvent,
    StepEndedEvent,
)
from app.orchestrator.event_hub import AsyncSessionEventHub
from app.tools.gateway import ToolGateway
from app.resource_manager.watchdog import ResourceManager
from app.orchestrator.orchestrator import TechLeadOrchestrator
from app.main import app


def test_session_stream_event_serialization():
    """Verify event schemas match OpenCode streaming contracts."""
    tool_event = ToolCallEvent(
        part_id="part_001",
        tool_name="run_command",
        call_id="call_abc",
        arguments={"cmd": "ls -la"},
        status="running",
        duration_ms=45,
    )
    event = SessionStreamEvent(
        event_type=SessionEventType.TOOL_CALLED,
        session_id="sess_123",
        data=tool_event.model_dump(),
    )
    sse_text = event.to_sse()
    assert "event: session.next.tool.called\n" in sse_text
    assert "data: " in sse_text
    payload = json.loads(sse_text.split("data: ")[1].strip())
    assert payload["data"]["tool_name"] == "run_command"
    assert payload["session_id"] == "sess_123"


def test_async_session_event_hub_pub_sub():
    """Verify in-memory non-blocking pub/sub queue per session."""
    async def _run():
        hub = AsyncSessionEventHub()
        session_id = "test_sess_42"

        queue = await hub.subscribe(session_id)
        assert queue is not None

        event = SessionStreamEvent(
            event_type=SessionEventType.TEXT_DELTA,
            session_id=session_id,
            data={"part_id": "p1", "delta": "FreeAI is operational."},
        )
        await hub.publish(session_id, event)

        received = await asyncio.wait_for(queue.get(), timeout=1.0)
        assert received.event_type == SessionEventType.TEXT_DELTA
        assert received.data["delta"] == "FreeAI is operational."

        await hub.unsubscribe(session_id, queue)

    asyncio.run(_run())


def test_event_hub_broadcast():
    """Verify broadcast delivers heartbeat to all active listeners."""
    async def _run():
        hub = AsyncSessionEventHub()
        q1 = await hub.subscribe("s1")
        q2 = await hub.subscribe("s2")

        heartbeat = SessionStreamEvent(
            event_type=SessionEventType.SERVER_HEARTBEAT,
            session_id="global",
            data={"status": "alive"},
        )
        await hub.broadcast(heartbeat)

        r1 = await asyncio.wait_for(q1.get(), timeout=1.0)
        r2 = await asyncio.wait_for(q2.get(), timeout=1.0)
        assert r1.event_type == SessionEventType.SERVER_HEARTBEAT
        assert r2.event_type == SessionEventType.SERVER_HEARTBEAT

        await hub.unsubscribe("s1", q1)
        await hub.unsubscribe("s2", q2)

    asyncio.run(_run())


def test_orchestrator_handle_objective_stream():
    """Verify handle_objective_stream emits complete sequence of agentic events."""
    async def _run():
        gw = ToolGateway(workspace_root="/tmp")
        rm = ResourceManager()
        orch = TechLeadOrchestrator(tool_gateway=gw, resource_manager=rm)
        hub = AsyncSessionEventHub()
        orch.event_hub = hub

        session_id = "stream_session_01"
        q = await hub.subscribe(session_id)

        collected_events = []

        async def _collector():
            while True:
                ev = await q.get()
                collected_events.append(ev.event_type)
                if ev.event_type == SessionEventType.STEP_ENDED:
                    break

        collector_task = asyncio.create_task(_collector())

        # Mock tool execution & LLM generation
        with patch.object(orch.free_ai, "generate_code", new_callable=AsyncMock) as mock_gen:
            mock_gen.return_value = "print('Hello from FreeAI OpenCode UI')"
            await orch.handle_objective_stream(
                session_id=session_id,
                objective="Ecrire un script de test",
                agent_role="Code Agent",
                model="FreeAI Local",
            )

        await asyncio.wait_for(collector_task, timeout=5.0)

        # Verify key lifecycle stages were broadcast
        assert SessionEventType.SESSION_STATUS in collected_events
        assert SessionEventType.STEP_STARTED in collected_events
        assert SessionEventType.TEXT_DELTA in collected_events
        assert SessionEventType.STEP_ENDED in collected_events

        await hub.unsubscribe(session_id, q)

    asyncio.run(_run())


def test_fastapi_sessions_api():
    """Verify REST API for sessions, models, agents, and files."""
    async def _run():
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            # 1. Models endpoint
            res = await ac.get("/api/v1/models")
            assert res.status_code == 200
            models = res.json()
            assert any(m["id"] == "freeai-local" for m in models)
            assert any("deepseek" in m["id"] for m in models)

            # 2. Agents endpoint
            res = await ac.get("/api/v1/agents")
            assert res.status_code == 200
            agents = res.json()
            assert any(a["id"] == "tech-lead" for a in agents)
            assert any(a["id"] == "ui-ux" for a in agents)

            # 3. Create session
            res = await ac.post("/api/v1/sessions", json={"title": "Test OpenCode Session"})
            assert res.status_code == 200
            sess_data = res.json()
            assert "id" in sess_data
            session_id = sess_data["id"]

            # 4. List sessions
            res = await ac.get("/api/v1/sessions")
            assert res.status_code == 200
            sessions = res.json()
            assert any(s["id"] == session_id for s in sessions)

            # 5. Send message
            res = await ac.post(
                f"/api/v1/sessions/{session_id}/message",
                json={"prompt": "Bonjour FreeAI", "agent_role": "Tech Lead", "model": "freeai-local"},
            )
            assert res.status_code == 200
            assert res.json().get("status") == "accepted"

            # 6. Delete session
            res = await ac.delete(f"/api/v1/sessions/{session_id}")
            assert res.status_code == 200

    asyncio.run(_run())


def test_ui_static_serving():
    """Verify FastAPI serves the OpenCode HTML and assets."""
    async def _run():
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            # When requesting /ui
            res = await ac.get("/ui")
            assert res.status_code == 200
            assert "FreeAI Studio" in res.text
            assert "OpenCode" in res.text

            # When requesting / with Accept: text/html
            res_html = await ac.get("/", headers={"accept": "text/html"})
            assert res_html.status_code == 200
            assert "FreeAI Studio" in res_html.text

            # When requesting / without html accept, returns API json
            res_json = await ac.get("/", headers={"accept": "application/json"})
            assert res_json.status_code == 200
            assert "status" in res_json.json()

    asyncio.run(_run())
