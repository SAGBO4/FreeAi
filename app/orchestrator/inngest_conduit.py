"""Inngest Sovereign Durable Conduit (Feature F-37).

Two distinct, honestly-separated execution engines:

1. Native engine (always available, Mode NEANT): step memoization in a plain
   in-process dict. Survives retries within the same process. Does NOT
   survive a process crash or a reboot - there is no persistence beyond the
   Python process's own RAM.
2. Cloud engine (opt-in, requires the `inngest` package and
   INNGEST_EVENT_KEY/INNGEST_SIGNING_KEY): delegates the mission as a signed
   event to Inngest Cloud (or a local Inngest Dev Server) and registers a
   durable function that Inngest calls back into via `/api/inngest`. Inngest
   persists step state on its side, so a mission genuinely resumes at its
   last completed step after this process restarts - but only while this
   FastAPI server is reachable from Inngest (public URL, or a tunnel such as
   ngrok/cloudflared in dev). This is the only path that delivers
   cross-restart durability; the native engine never does.
"""

import asyncio
import inspect
import logging
import os
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("freeai.orchestrator.inngest_conduit")

try:
    import inngest as inngest_sdk
    import inngest.fast_api as inngest_fast_api
    INNGEST_SDK_AVAILABLE = True
except ImportError:
    inngest_sdk = None
    inngest_fast_api = None
    INNGEST_SDK_AVAILABLE = False

RESILIENT_SWARM_EVENT = "freeai/resilient.swarm.requested"


class StepExecutionError(Exception):
    """Raised when a durable step execution fails."""
    pass


@dataclass
class WorkflowContext:
    """Ephemeral in-memory workflow execution state (native engine only)."""
    workflow_id: str
    created_at: float = field(default_factory=time.time)
    memoized_steps: Dict[str, Any] = field(default_factory=dict)
    failed_steps: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


class InngestSovereignConduit:
    """Dual-engine durable execution facade for resilient multi-LLM workflows."""

    _instance: Optional["InngestSovereignConduit"] = None

    def __init__(self):
        self.inngest_signing_key = os.getenv("INNGEST_SIGNING_KEY", "")
        self.inngest_event_key = os.getenv("INNGEST_EVENT_KEY", "")
        self._active_contexts: Dict[str, WorkflowContext] = {}
        self._cloud_client: Optional[Any] = None
        self._cloud_function: Optional[Any] = None
        if self.cloud_mode_available:
            self._cloud_client = inngest_sdk.Inngest(
                app_id="freeai-sovereign-conduit",
                event_key=self.inngest_event_key or None,
                signing_key=self.inngest_signing_key or None,
                is_production=bool(self.inngest_signing_key),
            )
            self._cloud_function = self._build_cloud_function(self._cloud_client)

    @property
    def cloud_mode_available(self) -> bool:
        """True only when the official SDK is installed AND Inngest keys are configured."""
        return INNGEST_SDK_AVAILABLE and bool(self.inngest_event_key)

    @classmethod
    def get_instance(cls) -> "InngestSovereignConduit":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    # ------------------------------------------------------------------
    # Native engine (process-local, non-durable across restarts)
    # ------------------------------------------------------------------

    def create_context(self, workflow_id: Optional[str] = None) -> WorkflowContext:
        """Instantiates an isolated ephemeral workflow context in RAM."""
        wf_id = workflow_id or f"wf_{int(time.time()*1000)}_{os.urandom(3).hex()}"
        ctx = WorkflowContext(workflow_id=wf_id)
        self._active_contexts[wf_id] = ctx
        return ctx

    async def step_run(
        self,
        ctx: WorkflowContext,
        step_id: str,
        func: Callable[..., Any],
        *args: Any,
        **kwargs: Any
    ) -> Any:
        """Executes a step with in-process memoization (native engine, zero re-execution on retry within the same process)."""
        if step_id in ctx.memoized_steps:
            logger.debug(f"[INNGEST-NATIVE] Step '{step_id}' already memoized in workflow '{ctx.workflow_id}'. Skipping.")
            return ctx.memoized_steps[step_id]

        logger.info(f"[INNGEST-NATIVE] Executing step '{step_id}' in workflow '{ctx.workflow_id}'")
        try:
            if inspect.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)

            ctx.memoized_steps[step_id] = result
            return result
        except Exception as e:
            ctx.failed_steps[step_id] = str(e)
            logger.warning(f"[INNGEST-NATIVE] Step '{step_id}' failed: {e}")
            raise

    async def step_sleep(
        self,
        ctx: WorkflowContext,
        step_id: str,
        seconds: float
    ) -> None:
        """Non-blocking delay with native memoization (same-process only)."""
        if step_id in ctx.memoized_steps:
            return

        logger.info(f"[INNGEST-NATIVE] Step '{step_id}' sleeping for {seconds}s")
        await asyncio.sleep(seconds)
        ctx.memoized_steps[step_id] = {"status": "slept", "seconds": seconds}

    def _get_telegram_dispatcher(self) -> Optional[Any]:
        """Resolves active Telegram dispatcher if initialized."""
        try:
            from app.telegram.bot import get_telegram_dispatcher
            return get_telegram_dispatcher()
        except Exception:
            return None

    async def dispatch_telemetry(
        self,
        ctx: WorkflowContext,
        status: str = "completed"
    ) -> bool:
        """Dispatches workflow telemetry to Telegram Neural Vault."""
        dispatcher = self._get_telegram_dispatcher()
        if not dispatcher:
            logger.debug("[INNGEST] No Telegram dispatcher configured. Telemetry recorded in RAM.")
            return False

        report = (
            f"[Inngest] Rapport d'Execution\n"
            f"Workflow ID: {ctx.workflow_id}\n"
            f"Statut: {status.upper()}\n"
            f"Etapes Validees: {len(ctx.memoized_steps)}\n"
            f"Etapes Echouees: {len(ctx.failed_steps)}\n"
            f"Moteur: {'Cloud (Inngest)' if self.cloud_mode_available else 'Natif (RAM locale, non-durable)'}"
        )
        try:
            await dispatcher.send_message(report)
            return True
        except Exception as e:
            logger.warning(f"[INNGEST] Failed sending Telegram telemetry: {e}")
            return False

    async def _run_cascade(
        self,
        step_runner: Callable[[str, Callable[[], Any]], Any],
        prompt: str,
        system_prompt: Optional[str],
    ) -> Dict[str, Any]:
        """Shared cascade logic (Groq -> Kimi Web -> Kilo AI), driven by either engine's step runner."""
        from app.llm.federation import OnlineModelFederation
        fed = OnlineModelFederation()

        async def try_groq():
            return await fed.query_specific_provider("groq", prompt, model="qwen/qwen3.8-27b", system_prompt=system_prompt)

        async def try_kimi():
            return await fed.query_specific_provider("kimi_web", prompt, system_prompt=system_prompt)

        async def try_kilo():
            return await fed.query_specific_provider("kilo_free", prompt, model="kilo-auto/free", system_prompt=system_prompt)

        ans = None
        for step_name, worker in [("step-groq", try_groq), ("step-kimi", try_kimi), ("step-kilo", try_kilo)]:
            try:
                res = await step_runner(step_name, worker)
                if res and res.get("content"):
                    ans = res
                    break
            except Exception as e:
                logger.debug(f"[INNGEST] Cascade step '{step_name}' failed ({e}), escalating to next step.")

        if not ans:
            ans = await fed.consult_free_online_model(prompt, system_prompt=system_prompt)

        return ans or {"success": False, "error": "All cascade steps exhausted"}

    async def execute_resilient_swarm(
        self,
        prompt: str,
        system_prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """Runs the resilient multi-model cascade (Groq -> Kimi Web -> Kilo AI).

        If cloud mode is configured, the mission is delegated to Inngest as a
        signed event: Inngest durably executes the registered function and
        this call returns immediately with a "delegated" status, the final
        result reaching Telegram once the function completes server-side.
        Otherwise, the cascade runs synchronously in this process using the
        native (non-durable) engine.
        """
        if self.cloud_mode_available:
            ids = await self._cloud_client.send(
                inngest_sdk.Event(
                    name=RESILIENT_SWARM_EVENT,
                    data={"prompt": prompt, "system_prompt": system_prompt},
                )
            )
            logger.info(f"[INNGEST-CLOUD] Mission delegated to Inngest Cloud: {ids}")
            return {
                "success": True,
                "engine": "cloud",
                "delegated": True,
                "event_ids": ids,
                "message": "Mission deleguee au Neuro-Conduit Inngest. Resultat livre via Telegram.",
            }

        ctx = self.create_context()

        async def native_step_runner(step_name: str, worker: Callable[[], Any]) -> Any:
            return await self.step_run(ctx, step_name, worker)

        ans = await self._run_cascade(native_step_runner, prompt, system_prompt)
        await self.dispatch_telemetry(ctx, status="success" if ans.get("content") or ans.get("success") else "failed")
        ans.setdefault("engine", "native")
        return ans

    def _build_cloud_function(self, client: Any) -> Any:
        """Registers the durable Inngest function backing the resilient swarm event."""
        conduit = self

        @client.create_function(
            fn_id="resilient-swarm-cascade",
            trigger=inngest_sdk.TriggerEvent(event=RESILIENT_SWARM_EVENT),
            retries=2,
        )
        async def resilient_swarm_fn(ctx: Any) -> Dict[str, Any]:
            prompt = ctx.event.data.get("prompt", "")
            system_prompt = ctx.event.data.get("system_prompt")

            async def cloud_step_runner(step_name: str, worker: Callable[[], Any]) -> Any:
                return await ctx.step.run(step_name, worker)

            ans = await conduit._run_cascade(cloud_step_runner, prompt, system_prompt)

            wf_ctx = WorkflowContext(workflow_id=ctx.run_id)
            wf_ctx.memoized_steps["cascade"] = ans
            await conduit.dispatch_telemetry(wf_ctx, status="success" if ans.get("content") or ans.get("success") else "failed")
            return ans

        return resilient_swarm_fn


def register_inngest_routes(app: Any) -> None:
    """Mounts the Inngest endpoint on the FastAPI application.

    When the official SDK is installed and INNGEST_EVENT_KEY is configured,
    this mounts the real Inngest protocol handler (signature verification,
    function registration/sync, durable step callbacks). Otherwise it mounts
    a minimal introspection-only stub that clearly reports itself as
    non-functional, so the project's own docs cannot overstate it.
    """
    conduit = InngestSovereignConduit.get_instance()

    if conduit.cloud_mode_available and conduit._cloud_function is not None:
        inngest_fast_api.serve(app, conduit._cloud_client, [conduit._cloud_function])
        logger.info("[INNGEST] Real Inngest Cloud protocol endpoint mounted on /api/inngest")
        return

    from fastapi import APIRouter, Request
    from fastapi.responses import JSONResponse

    router = APIRouter(prefix="/api/inngest", tags=["inngest"])

    @router.get("")
    async def inngest_introspection():
        return {
            "status": "native_only",
            "conduit": "InngestSovereignConduit",
            "cloud_mode_available": False,
            "reason": "inngest package not installed or INNGEST_EVENT_KEY not set",
            "note": "This endpoint does not implement the real Inngest protocol (no signature verification, no function sync). Set INNGEST_EVENT_KEY and install the `inngest` package for genuine cross-restart durability.",
        }

    @router.post("")
    async def inngest_webhook_stub(request: Request):
        return JSONResponse(
            status_code=503,
            content={
                "received": False,
                "error": "cloud_mode_unavailable",
                "message": "Inngest SDK not configured on this instance; this stub does not process real Inngest webhooks.",
            }
        )

    app.include_router(router)
    logger.warning("[INNGEST] Native-only stub mounted on /api/inngest (no real Inngest protocol support)")
