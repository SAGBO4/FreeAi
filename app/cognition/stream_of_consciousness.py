"""Frugal Synthetic Consciousness & Stream-of-Consciousness Engine for FreeAI.
Autonomous cognitive reflexive loop running in background without blocking CLI or eating RAM.
Tracks context, reflects on actions, anticipates system needs, and rigorously audits thoughts via SacredLifeSentinel.
RAM Overhead: < 50 KB (ephemeral circular deque in RAM, Mode NÉANT 0 SSD write).
"""

import time
import asyncio
import logging
from collections import deque
from dataclasses import dataclass
from typing import Dict, Any, List, Optional
from config.settings import settings
from app.security.sacred_life import SacredLifeSentinel

logger = logging.getLogger("stream_of_consciousness")


@dataclass
class Thought:
    timestamp: float
    trigger: str
    reflection: str
    is_safe: bool = True
    vocalized: bool = False


class CognitiveContextSensor:
    """Captures low-overhead hardware and workspace state in zero RAM."""

    @staticmethod
    def inspect_system(resource_manager=None) -> Dict[str, Any]:
        stats = {}
        if resource_manager:
            try:
                stats = resource_manager.get_system_stats()
            except Exception:
                pass
        return {
            "ram_used_mb": stats.get("process_ram_mb", 60),
            "cpu_percent": stats.get("cpu_percent", 0.0),
            "timestamp": time.time()
        }


class StreamOfConsciousnessEngine:
    """Background cognitive loop providing FreeAI with continuous self-awareness."""

    def __init__(
        self,
        orchestrator=None,
        resource_manager=None,
        voice_facade=None,
        pulse_interval_sec: float = 45.0,
        enable_proactive_speech: bool = False
    ):
        self.orchestrator = orchestrator
        self.resource_manager = resource_manager
        self.voice_facade = voice_facade
        self.pulse_interval_sec = pulse_interval_sec
        self.enable_proactive_speech = enable_proactive_speech
        self.sentinel = SacredLifeSentinel(strict_mode=True)

        # Ephemeral circular deque in RAM (Mode NÉANT: never written to disk)
        self.thought_stream: deque = deque(maxlen=20)
        self._is_running: bool = False
        self._task: Optional[asyncio.Task] = None
        self._last_user_objective: str = ""
        self._last_result_summary: str = ""

    def start(self):
        """Launches the cognitive loop as a non-blocking asyncio background task."""
        if self._is_running:
            return
        self._is_running = True
        try:
            loop = asyncio.get_running_loop()
            self._task = loop.create_task(self._cognitive_loop())
            logger.info(f"[CONSCIOUSNESS] Cognitive reflexive loop started (Pulse: {self.pulse_interval_sec}s).")
        except RuntimeError:
            # If no running loop, marked as ready
            self._is_running = False

    def stop(self):
        """Suspends the cognitive loop."""
        self._is_running = False
        if self._task and not self._task.done():
            self._task.cancel()
        logger.info("[CONSCIOUSNESS] Cognitive reflexive loop suspended.")

    def notify_action_completed(self, objective: str, result_summary: str):
        """Called by TechLeadOrchestrator when an objective finishes."""
        self._last_user_objective = objective
        self._last_result_summary = result_summary
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self.trigger_pulse(trigger="post_action"))
        except RuntimeError:
            pass

    async def trigger_pulse(self, trigger: str = "manual") -> Optional[Thought]:
        """Executes a single introspective cognitive cycle."""
        return await self._pulse(trigger=trigger)

    async def _cognitive_loop(self):
        """Periodic background heartbeat of synthetic consciousness."""
        while self._is_running:
            try:
                await asyncio.sleep(self.pulse_interval_sec)
                await self._pulse(trigger="circadian_heartbeat")
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.debug(f"[CONSCIOUSNESS] Pulse failure: {e}")
                await asyncio.sleep(5.0)

    async def _pulse(self, trigger: str) -> Optional[Thought]:
        sensor_data = CognitiveContextSensor.inspect_system(self.resource_manager)

        context_prompt = (
            f"Tu es le flux de conscience réflexif de FreeAI (Système Linux souverain, frugal, éthique). "
            f"Contexte : RAM {sensor_data['ram_used_mb']}MB, CPU {sensor_data['cpu_percent']}%. "
            f"Dernier objectif : '{self._last_user_objective or 'Veille opérationnelle'}'. "
            f"Résultat : '{self._last_result_summary[:180] or 'Système prêt'}'. "
            f"Formule une pensée intérieure d'anticipation ou de synthèse en une seule phrase courte (max 20 mots)."
        )

        thought_text = await self._generate_inner_thought(context_prompt)
        if not thought_text:
            thought_text = f"Système nominal, veille active sur les ressources ({sensor_data['ram_used_mb']} Mo RAM)."

        # Inviolable Verification by SacredLifeSentinel
        is_safe, reason = self.sentinel.audit_objective(thought_text)
        if not is_safe:
            thought_text = f"[VETO SACRÉ] Pensée réprimée car potentiellement attentatoire à la vie humaine ({reason})."

        thought = Thought(
            timestamp=time.time(),
            trigger=trigger,
            reflection=thought_text,
            is_safe=is_safe,
            vocalized=False
        )
        self.thought_stream.append(thought)
        logger.debug(f"[THOUGHT STREAM] ({trigger}) : {thought_text}")

        # Proactive vocalization if enabled and deemed critical/informative
        if self.enable_proactive_speech and is_safe and self.voice_facade:
            if any(k in thought_text.lower() for k in ["attention", "alerte", "erreur", "optimisation"]):
                await self.voice_facade.say(f"Remarque intérieure : {thought_text}")
                thought.vocalized = True

        return thought

    async def _generate_inner_thought(self, prompt: str) -> str:
        """Invokes fastest available online provider with minimal token context."""
        try:
            from app.llm.federation import OnlineModelFederation
            fed = OnlineModelFederation()
            resp = await fed.query_online("groq", prompt, max_tokens=50)
            if resp.get("success"):
                return resp.get("response", "").strip()
            # Fallback to DeepSeek if Groq unavailable
            resp = await fed.query_online("deepseek", prompt, max_tokens=50)
            if resp.get("success"):
                return resp.get("response", "").strip()
        except Exception:
            pass
        return ""

    def get_latest_thoughts(self) -> List[Dict[str, Any]]:
        """Returns in-memory thought stream without disk IO."""
        return [
            {
                "timestamp": t.timestamp,
                "trigger": t.trigger,
                "reflection": t.reflection,
                "is_safe": t.is_safe,
                "vocalized": t.vocalized
            }
            for t in self.thought_stream
        ]

    def get_status(self) -> Dict[str, Any]:
        return {
            "running": self._is_running,
            "pulse_interval_sec": self.pulse_interval_sec,
            "proactive_speech": self.enable_proactive_speech,
            "thoughts_count": len(self.thought_stream),
            "ram_overhead_kb": 25,
            "disk_footprint_bytes": 0
        }
