"""Asynchronous In-Memory Event Hub for FreeAI & OpenCode UI (Zero Disk Write).
Manages reactive subscriptions, real-time message broadcasting, and SSE queue lifecycle.
"""

import asyncio
import logging
from typing import Dict, Set, Optional, List
from .session_events import SessionStreamEvent, SessionEventType

logger = logging.getLogger("event_hub")


class AsyncSessionEventHub:
    """Zero-overhead in-memory event bus managing real-time listeners for sessions."""

    _instance: Optional["AsyncSessionEventHub"] = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if getattr(self, "_initialized", False):
            return
        self._listeners: Dict[str, Set[asyncio.Queue]] = {}
        self._global_listeners: Set[asyncio.Queue] = set()
        self._lock = asyncio.Lock()
        self._initialized = True
        logger.info("[AsyncSessionEventHub] Initialized in-memory pub/sub engine.")

    async def subscribe(self, session_id: str) -> asyncio.Queue:
        """Subscribe to events for a specific session."""
        async with self._lock:
            if session_id not in self._listeners:
                self._listeners[session_id] = set()
            queue: asyncio.Queue = asyncio.Queue(maxsize=1000)
            self._listeners[session_id].add(queue)
            return queue

    async def unsubscribe(self, session_id: str, queue: asyncio.Queue):
        """Remove a subscriber queue when client disconnects."""
        async with self._lock:
            if session_id in self._listeners:
                self._listeners[session_id].discard(queue)
                if not self._listeners[session_id]:
                    del self._listeners[session_id]

    async def publish(self, session_id: str, event: SessionStreamEvent):
        """Publish an event to all subscribers of a session."""
        async with self._lock:
            queues = list(self._listeners.get(session_id, set()))
            globals_ = list(self._global_listeners)

        for q in queues + globals_:
            try:
                q.put_nowait(event)
            except asyncio.QueueFull:
                logger.warning(f"[EventHub] Dropping slow subscriber frame on session {session_id}")
            except Exception as e:
                logger.error(f"[EventHub] Delivery failure: {e}")

    async def broadcast(self, event: SessionStreamEvent):
        """Broadcast an event to all active sessions (e.g. heartbeat, resource updates)."""
        async with self._lock:
            all_queues = []
            for qs in self._listeners.values():
                all_queues.extend(qs)
            all_queues.extend(self._global_listeners)

        for q in all_queues:
            try:
                q.put_nowait(event)
            except Exception:
                pass


# Global singleton
event_hub = AsyncSessionEventHub()
