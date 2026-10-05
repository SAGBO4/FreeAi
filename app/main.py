"""Main application entry point (TDR §32 & §33)."""

import os
import sys
import logging
from pathlib import Path
from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from pydantic import BaseModel
from config.settings import settings
from app.resource_manager.watchdog import ResourceManager
from app.tools.gateway import ToolGateway
from app.orchestrator.orchestrator import TechLeadOrchestrator
from app.api.session_routes import router as session_router

# Setup logging (zero disk writing if LOG_TO_FILE is False)
handlers = [logging.StreamHandler(sys.stdout)]
if settings.LOG_TO_FILE:
    os.makedirs(settings.LOG_DIR, exist_ok=True)
    handlers.append(logging.FileHandler(os.path.join(settings.LOG_DIR, "orchestrator.log"), encoding="utf-8"))
else:
    # Purge old log file if existing to save disk
    old_log = Path(settings.LOG_DIR) / "orchestrator.log"
    if old_log.exists():
        try:
            old_log.unlink()
        except Exception:
            pass

logging.basicConfig(
    level=settings.LOG_LEVEL,
    format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
    handlers=handlers
)

logger = logging.getLogger("main")

# Initialize core services
resource_manager = ResourceManager(
    target_mb=settings.RAM_TARGET_MB,
    hard_limit_mb=settings.RAM_HARD_LIMIT_MB
)

tool_gateway = ToolGateway(
    workspace_root=settings.WORKSPACE_ROOT,
    allow_network=settings.ALLOW_NETWORK,
    allow_sudo=settings.ALLOW_SUDO
)

tech_lead = TechLeadOrchestrator(
    tool_gateway=tool_gateway,
    resource_manager=resource_manager
)

app = FastAPI(
    title="Local AI Assistant - Tech Lead Core",
    version="1.0.0",
    description="Offline-first autonomous multi-agent AI assistant for HP EliteBook / Kali Linux"
)

# Attach singletons to app.state
app.state.tech_lead = tech_lead
app.state.tool_gateway = tool_gateway
app.state.resource_manager = resource_manager

# Include OpenCode Real-Time Session & Streaming Router
app.include_router(session_router)

# Mount OpenCode static files
WEB_DIR = Path(__file__).resolve().parent / "web"
if WEB_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(WEB_DIR)), name="static")


class ObjectiveRequest(BaseModel):
    objective: str
    autonomous: bool = False


@app.get("/ui", response_class=HTMLResponse)
@app.get("/")
def get_status(request: Request):
    accept = request.headers.get("accept", "")
    if "text/html" in accept or request.url.path == "/ui":
        index_file = WEB_DIR / "index.html"
        if index_file.exists():
            return FileResponse(index_file)
    return JSONResponse(content={
        "status": "online",
        "mode": settings.APP_MODE,
        "workspace": str(tool_gateway.workspace_root),
        "resources": resource_manager.get_system_stats()
    })


@app.get("/resources")
def get_resources():
    return resource_manager.get_system_stats()


@app.post("/execute")
async def execute_task(req: ObjectiveRequest):
    result = await tech_lead.handle_objective(req.objective, autonomous=req.autonomous)
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error"))
    return result


if __name__ == "__main__":
    import uvicorn
    logger.info(f"Starting Local AI Assistant on {settings.SERVER_HOST}:{settings.SERVER_PORT}...")
    uvicorn.run(app, host=settings.SERVER_HOST, port=settings.SERVER_PORT)
