"""Dedicated isolated FastAPI server for Inngest Cloud webhooks (Port 8005).

Contains ONLY /api/inngest (protected by Inngest cryptographic signing key).
Strictly excludes any local execution or administrative endpoints (/execute, /ui, etc.).
"""

import uvicorn
from fastapi import FastAPI
from app.orchestrator.inngest_conduit import register_inngest_routes

app = FastAPI(title="FreeAI Inngest Sovereign Webhook Bridge")
register_inngest_routes(app)

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8005, log_level="info")
