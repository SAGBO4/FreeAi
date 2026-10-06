"""FastAPI Session & OpenCode Real-Time API for FreeAI.
Implements:
- Session management (create, list, get, delete)
- OpenCode SSE event streaming with heartbeats
- Message prompt dispatch with background task execution
- Models & Agents catalogs
- Workspace file indexing for @ mentions
- Real-time Git diff endpoint for review panel
- Terminal execution endpoint for interactive drawer
"""

import os
import time
import json
import uuid
import asyncio
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request, BackgroundTasks
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.orchestrator.session_events import (
    SessionStreamEvent,
    SessionEventType,
    SessionStatusInfo,
)
from app.orchestrator.event_hub import event_hub
from config.settings import settings

logger = logging.getLogger("session_routes")

router = APIRouter(prefix="/api/v1", tags=["OpenCode Sessions"])

# In-memory session store (zero disk write required)
SESSIONS: Dict[str, Dict[str, Any]] = {}
ACTIVE_TASKS: Dict[str, asyncio.Task] = {}


class CreateSessionRequest(BaseModel):
    title: Optional[str] = "Nouvelle Session FreeAI"
    workspace: Optional[str] = None


class MessagePromptRequest(BaseModel):
    prompt: str
    agent_role: Optional[str] = "Tech Lead"
    model: Optional[str] = "freeai-local"
    context: Optional[Dict[str, Any]] = Field(default_factory=dict)


class TerminalCommandRequest(BaseModel):
    command: str


@router.get("/sessions")
def list_sessions():
    """Lists all active sessions with metadata."""
    sorted_sessions = sorted(
        SESSIONS.values(),
        key=lambda s: s.get("updated_at", 0),
        reverse=True
    )
    return sorted_sessions


@router.post("/sessions")
def create_session(req: CreateSessionRequest):
    """Creates a new session for FreeAI OpenCode UI."""
    session_id = f"sess_{uuid.uuid4().hex[:12]}"
    now = time.time()
    session_obj = {
        "id": session_id,
        "title": req.title or "Nouvelle Session FreeAI",
        "created_at": now,
        "updated_at": now,
        "workspace": req.workspace or str(settings.WORKSPACE_ROOT),
        "messages": [],
        "diff": "",
        "status": "idle"
    }
    SESSIONS[session_id] = session_obj
    return session_obj


@router.get("/sessions/{session_id}")
def get_session(session_id: str):
    """Retrieves session details and message history."""
    if session_id not in SESSIONS:
        raise HTTPException(status_code=404, detail="Session introuvable")
    return SESSIONS[session_id]


@router.delete("/sessions/{session_id}")
def delete_session(session_id: str):
    """Deletes a session and cancels any running tasks."""
    if session_id in ACTIVE_TASKS:
        ACTIVE_TASKS[session_id].cancel()
        del ACTIVE_TASKS[session_id]
    if session_id in SESSIONS:
        del SESSIONS[session_id]
    return {"success": True, "deleted_id": session_id}


@router.post("/sessions/{session_id}/abort")
async def abort_session(session_id: str):
    """Aborts the currently active agent execution in a session."""
    if session_id in ACTIVE_TASKS:
        ACTIVE_TASKS[session_id].cancel()
        del ACTIVE_TASKS[session_id]
    
    if session_id in SESSIONS:
        SESSIONS[session_id]["status"] = "idle"

    await event_hub.publish(session_id, SessionStreamEvent(
        event_type=SessionEventType.SESSION_STATUS,
        session_id=session_id,
        data={"status": "idle", "interrupted": True}
    ))
    return {"success": True, "aborted": True}


@router.post("/sessions/{session_id}/message")
async def send_message(session_id: str, req: MessagePromptRequest, request: Request):
    """Receives a user prompt and triggers asynchronous agentic execution."""
    if session_id not in SESSIONS:
        # Create on the fly if not exists
        SESSIONS[session_id] = {
            "id": session_id,
            "title": req.prompt[:30] + ("..." if len(req.prompt) > 30 else ""),
            "created_at": time.time(),
            "updated_at": time.time(),
            "workspace": str(settings.WORKSPACE_ROOT),
            "messages": [],
            "status": "idle"
        }

    session = SESSIONS[session_id]
    session["updated_at"] = time.time()
    
    # Auto-title session if it's the first message
    if not session.get("messages"):
        session["title"] = req.prompt[:35] + ("..." if len(req.prompt) > 35 else "")

    # Append user turn
    user_turn = {
        "id": f"msg_{uuid.uuid4().hex[:8]}",
        "role": "user",
        "content": req.prompt,
        "timestamp": time.time()
    }
    session["messages"].append(user_turn)

    # Get orchestrator instance from app state
    orchestrator = getattr(request.app.state, "tech_lead", None)

    async def _run_stream():
        try:
            session["status"] = "busy"
            if orchestrator:
                result = await orchestrator.handle_objective_stream(
                    session_id=session_id,
                    objective=req.prompt,
                    agent_role=req.agent_role or "Tech Lead",
                    model=req.model or "freeai-local",
                    context=req.context,
                    event_hub=event_hub
                )
                # Append assistant turn to history
                assistant_turn = {
                    "id": f"msg_{uuid.uuid4().hex[:8]}",
                    "role": "assistant",
                    "content": result.get("response", ""),
                    "timestamp": time.time()
                }
                session["messages"].append(assistant_turn)
            session["status"] = "idle"
        except asyncio.CancelledError:
            session["status"] = "idle"
            logger.info(f"[Session {session_id}] Execution cancelled by user.")
        except Exception as e:
            session["status"] = "error"
            logger.error(f"[Session {session_id}] Error in execution: {e}")
            await event_hub.publish(session_id, SessionStreamEvent(
                event_type=SessionEventType.SESSION_STATUS,
                session_id=session_id,
                data={"status": "error", "error": str(e)}
            ))

    task = asyncio.create_task(_run_stream())
    ACTIVE_TASKS[session_id] = task

    return {"status": "accepted", "session_id": session_id}


@router.get("/sessions/{session_id}/stream")
async def stream_session_events(session_id: str, request: Request):
    """Server-Sent Events (SSE) endpoint providing 60fps real-time updates & 10s heartbeats."""
    queue = await event_hub.subscribe(session_id)

    async def _sse_generator():
        # 1. Handshake
        handshake = SessionStreamEvent(
            event_type=SessionEventType.SERVER_CONNECTED,
            session_id=session_id,
            data={"session_id": session_id, "timestamp": time.time()}
        )
        yield handshake.to_sse()

        last_heartbeat = time.time()
        try:
            while True:
                # Check client disconnected
                if await request.is_disconnected():
                    break

                try:
                    event: SessionStreamEvent = await asyncio.wait_for(queue.get(), timeout=1.0)
                    yield event.to_sse()
                except asyncio.TimeoutError:
                    pass

                # 10s keepalive heartbeat
                now = time.time()
                if now - last_heartbeat >= 10.0:
                    heartbeat = SessionStreamEvent(
                        event_type=SessionEventType.SERVER_HEARTBEAT,
                        session_id=session_id,
                        data={"time": now}
                    )
                    yield heartbeat.to_sse()
                    last_heartbeat = now
        finally:
            await event_hub.unsubscribe(session_id, queue)

    return StreamingResponse(
        _sse_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.get("/models")
def list_models():
    """Returns available local, cloud, and federated models for the prompt composer."""
    return [
        {
            "id": "freeai-local",
            "name": "FreeAI Sovereign Core (Qwen2.5 / DeepSeek)",
            "provider": "local",
            "speed": "Ultra-Fast (Offline)",
            "description": "Modèle local sans latence, 100% privé, optimisé RAM HP EliteBook",
            "is_default": True
        },
        {
            "id": "deepseek-r1",
            "name": "DeepSeek R1 (Ghost Cloud)",
            "provider": "openrouter",
            "speed": "Reasoning Engine",
            "description": "Raisonnement profond mathématique et cyber avec chain-of-thought",
            "is_default": False
        },
        {
            "id": "claude-3-7-sonnet",
            "name": "Claude 3.7 Sonnet (Anthropic)",
            "provider": "anthropic",
            "speed": "Smart Coding",
            "description": "Capacités de codage avancées, refactoring et vision",
            "is_default": False
        },
        {
            "id": "gpt-4o",
            "name": "GPT-4o (OpenAI)",
            "provider": "openai",
            "speed": "Multimodal",
            "description": "Génération de code polyvalente et synthèse rapide",
            "is_default": False
        },
        {
            "id": "gemini-2-5-flash",
            "name": "Gemini 2.5 Flash (Google)",
            "provider": "google",
            "speed": "Instant (1M Context)",
            "description": "Fenêtre de contexte géante pour analyser tout le codebase",
            "is_default": False
        },
        {
            "id": "llama-3-3-70b",
            "name": "Llama 3.3 70B (Groq LPU)",
            "provider": "groq",
            "speed": "500+ tokens/s",
            "description": "Inférence ultra-rapide sur matériel LPU",
            "is_default": False
        }
    ]


@router.get("/agents")
def list_agents():
    """Returns available specialized agents for the prompt composer."""
    return [
        {
            "id": "tech-lead",
            "name": "Tech Lead Orchestrator",
            "role": "Coordinateur Autonome Multi-Agents",
            "color": "#3b82f6",
            "glyph": "👑",
            "description": "Décompose les objectifs, assigne les agents spécialisés et orchestre la livraison."
        },
        {
            "id": "code-agent",
            "name": "Code Agent",
            "role": "Ingénieur Logiciel & Refactoring",
            "color": "#10b981",
            "glyph": "💻",
            "description": "Écrit du code propre, applique les patchs et résout les bugs."
        },
        {
            "id": "security-agent",
            "name": "Security Sentinel",
            "role": "Auditeur de Sécurité & Défense Active",
            "color": "#f43f5e",
            "glyph": "🛡️",
            "description": "Audit les vulnérabilités OWASP, le chiffrement et la défense active."
        },
        {
            "id": "ui-ux",
            "name": "UI/UX & Extreme Innovation",
            "role": "Architecte Design System & Expérience",
            "color": "#a855f7",
            "glyph": "✨",
            "description": "Conçoit des interfaces modernes basées sur OpenCode & shadcn/ui."
        },
        {
            "id": "git-agent",
            "name": "Git Agent",
            "role": "Gestionnaire de Versions & Rollback",
            "color": "#f59e0b",
            "glyph": "🌿",
            "description": "Gère les branches, les commits, les diffs et les rollbacks instantanés."
        },
        {
            "id": "sovereign",
            "name": "LesaintAI Sovereign",
            "role": "Super-Utilisateur Autonome",
            "color": "#ec4899",
            "glyph": "⚡",
            "description": "Mode super-administrateur avec autorisations élevées et auto-évolution."
        }
    ]


@router.get("/files")
def search_files(query: Optional[str] = None):
    """Searches workspace files for @ context mentions."""
    root = Path(settings.WORKSPACE_ROOT)
    results = []
    query_lower = query.lower() if query else ""

    ignored_dirs = {".git", ".pytest_cache", "__pycache__", "node_modules", ".venv", "venv"}

    for p in root.rglob("*"):
        if any(ignored in p.parts for ignored in ignored_dirs):
            continue
        if p.is_file():
            rel = str(p.relative_to(root))
            if not query_lower or query_lower in rel.lower():
                results.append({
                    "path": rel,
                    "name": p.name,
                    "size": p.stat().st_size
                })
                if len(results) >= 50:
                    break
    return results


@router.get("/diff")
def get_diff():
    """Returns the current Git diff for the review panel."""
    import subprocess
    try:
        res = subprocess.run(
            ["git", "diff", "HEAD"],
            cwd=str(settings.WORKSPACE_ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=5
        )
        return {
            "diff": res.stdout,
            "has_changes": bool(res.stdout.strip())
        }
    except Exception as e:
        return {"diff": "", "error": str(e), "has_changes": False}


@router.post("/terminal/execute")
def execute_terminal(req: TerminalCommandRequest, request: Request):
    """Executes a command for the bottom drawer terminal."""
    tool_gateway = getattr(request.app.state, "tool_gateway", None)
    if tool_gateway and hasattr(tool_gateway, "execute_bash"):
        res = tool_gateway.execute_bash(req.command)
        return res
    
    # Fallback safe runner
    import subprocess
    try:
        proc = subprocess.run(
            req.command,
            shell=True,
            cwd=str(settings.WORKSPACE_ROOT),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=15
        )
        return {
            "stdout": proc.stdout,
            "stderr": proc.stderr,
            "exit_code": proc.returncode,
            "command": req.command
        }
    except subprocess.TimeoutExpired:
        return {"stdout": "", "stderr": "Command timed out after 15s", "exit_code": 124}
    except Exception as e:
        return {"stdout": "", "stderr": str(e), "exit_code": 1}
