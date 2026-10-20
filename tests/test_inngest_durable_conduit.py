"""Tests for Inngest Sovereign Durable Conduit (Feature F-37).

Covers both engines explicitly:
- Native engine: in-process step memoization, no cross-restart durability.
- Cloud engine: real `inngest` SDK wiring (client, function registration,
  FastAPI route mounting), activated only when INNGEST_EVENT_KEY is set.
"""

import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.orchestrator.inngest_conduit import (
    InngestSovereignConduit,
    WorkflowContext,
    StepExecutionError,
    register_inngest_routes,
)


class TestNativeDurableStepEngine:

    @pytest.mark.anyio
    async def test_step_run_executes_and_memoizes(self):
        conduit = InngestSovereignConduit()
        ctx = WorkflowContext(workflow_id="wf-test-01")

        call_counter = 0

        async def worker_task(val: int) -> int:
            nonlocal call_counter
            call_counter += 1
            return val * 2

        r1 = await conduit.step_run(ctx, "step-multiply", worker_task, 21)
        assert r1 == 42
        assert call_counter == 1
        assert "step-multiply" in ctx.memoized_steps
        assert ctx.memoized_steps["step-multiply"] == 42

        r2 = await conduit.step_run(ctx, "step-multiply", worker_task, 999)
        assert r2 == 42
        assert call_counter == 1  # Not incremented: memoized within this process

    @pytest.mark.anyio
    async def test_step_sleep_records_duration(self):
        conduit = InngestSovereignConduit()
        ctx = WorkflowContext(workflow_id="wf-test-02")

        await conduit.step_sleep(ctx, "step-cooldown", seconds=0.01)
        assert "step-cooldown" in ctx.memoized_steps
        assert ctx.memoized_steps["step-cooldown"]["status"] == "slept"

    @pytest.mark.anyio
    async def test_multi_llm_circuit_breaker_cascade(self):
        conduit = InngestSovereignConduit()
        ctx = WorkflowContext(workflow_id="wf-llm-cascade")

        step1_called = 0
        step2_called = 0

        async def failing_primary_model():
            nonlocal step1_called
            step1_called += 1
            raise RuntimeError("HTTP 429: Too Many Requests on Primary")

        async def successful_fallback_model():
            nonlocal step2_called
            step2_called += 1
            return {"provider": "kimi_web", "response": "Paris"}

        async def run_resilient_swarm():
            ans = None
            try:
                ans = await conduit.step_run(ctx, "primary-groq", failing_primary_model)
            except Exception:
                ans = await conduit.step_run(ctx, "fallback-kimi", successful_fallback_model)
            return ans

        res = await run_resilient_swarm()
        assert res["provider"] == "kimi_web"
        assert res["response"] == "Paris"
        assert step1_called == 1
        assert step2_called == 1
        assert "primary-groq" in ctx.failed_steps
        assert "fallback-kimi" in ctx.memoized_steps

    @pytest.mark.anyio
    async def test_telegram_telemetry_dispatch(self):
        conduit = InngestSovereignConduit()
        ctx = WorkflowContext(workflow_id="wf-telemetry-01")
        ctx.memoized_steps["step-1"] = "Done"

        mock_bot = MagicMock()
        mock_bot.send_message = AsyncMock(return_value={"ok": True})

        with patch.object(conduit, "_get_telegram_dispatcher", return_value=mock_bot):
            res = await conduit.dispatch_telemetry(ctx, status="completed")
            assert res is True
            mock_bot.send_message.assert_called_once()

    def test_cloud_mode_unavailable_without_event_key(self, monkeypatch):
        monkeypatch.delenv("INNGEST_EVENT_KEY", raising=False)
        monkeypatch.delenv("INNGEST_SIGNING_KEY", raising=False)
        conduit = InngestSovereignConduit()
        assert conduit.cloud_mode_available is False
        assert conduit._cloud_client is None

    @pytest.mark.anyio
    async def test_execute_resilient_swarm_native_fallback(self, monkeypatch):
        monkeypatch.delenv("INNGEST_EVENT_KEY", raising=False)
        conduit = InngestSovereignConduit()
        assert conduit.cloud_mode_available is False

        fake_federation = MagicMock()
        fake_federation.query_specific_provider = AsyncMock(
            return_value={"content": "Reykjavik", "provider": "groq"}
        )

        with patch("app.llm.federation.OnlineModelFederation", return_value=fake_federation):
            result = await conduit.execute_resilient_swarm("Quelle est la capitale de l'Islande ?")

        assert result["engine"] == "native"
        assert result["content"] == "Reykjavik"
        fake_federation.query_specific_provider.assert_awaited()


class TestCloudDurableEngine:
    """Exercises the real inngest SDK wiring, not a reimplementation of it.

    `inngest` is a declared dependency in requirements.txt, so this class
    assumes it is installed rather than skipping when it is not.
    """

    def test_cloud_mode_available_with_event_key(self, monkeypatch):
        monkeypatch.setenv("INNGEST_EVENT_KEY", "test-event-key")
        monkeypatch.delenv("INNGEST_SIGNING_KEY", raising=False)
        conduit = InngestSovereignConduit()
        assert conduit.cloud_mode_available is True
        assert conduit._cloud_client is not None
        assert conduit._cloud_function is not None

    def test_register_inngest_routes_mounts_real_inngest_endpoint(self, monkeypatch):
        monkeypatch.setenv("INNGEST_EVENT_KEY", "test-event-key")
        monkeypatch.delenv("INNGEST_SIGNING_KEY", raising=False)
        from fastapi import FastAPI

        InngestSovereignConduit._instance = None
        app = FastAPI()
        register_inngest_routes(app)

        inngest_routes = [r for r in app.routes if getattr(r, "path", "") == "/api/inngest"]
        assert inngest_routes, "real inngest.fast_api.serve must mount /api/inngest"
        methods = set()
        for r in inngest_routes:
            methods |= getattr(r, "methods", set())
        assert {"GET", "POST", "PUT"} <= methods

        InngestSovereignConduit._instance = None

    @pytest.mark.anyio
    async def test_execute_resilient_swarm_delegates_to_cloud(self, monkeypatch):
        monkeypatch.setenv("INNGEST_EVENT_KEY", "test-event-key")
        monkeypatch.delenv("INNGEST_SIGNING_KEY", raising=False)
        conduit = InngestSovereignConduit()
        assert conduit.cloud_mode_available is True

        with patch.object(conduit._cloud_client, "send", return_value=["evt_123"]) as mock_send:
            result = await conduit.execute_resilient_swarm("ping")

        mock_send.assert_called_once()
        assert result["engine"] == "cloud"
        assert result["delegated"] is True
        assert result["event_ids"] == ["evt_123"]


def test_native_stub_route_reports_itself_as_non_functional(monkeypatch):
    monkeypatch.delenv("INNGEST_EVENT_KEY", raising=False)
    monkeypatch.delenv("INNGEST_SIGNING_KEY", raising=False)
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    InngestSovereignConduit._instance = None
    app = FastAPI()
    register_inngest_routes(app)
    client = TestClient(app)

    status = client.get("/api/inngest").json()
    assert status["cloud_mode_available"] is False

    webhook = client.post("/api/inngest", json={"events": []})
    assert webhook.status_code == 503

    InngestSovereignConduit._instance = None
