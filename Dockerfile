# FreeAI Sovereign AI & Autonomous Cyber Intelligence Platform
# Containerized Deployment (Production & Local)
# Mode NÉANT compliant: Supports ephemeral tmpfs execution and 0-SSD disk persistence

FROM python:3.13-slim

ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    WORKSPACE_ROOT=/workspace \
    MODE_NEANT=true

WORKDIR /app

# Install system dependencies, network diagnostic utilities, and Docker CLI (for sibling container orchestration)
RUN apt-get update && apt-get install -y --no-install-recommends \
    bash \
    curl \
    git \
    sudo \
    iproute2 \
    net-tools \
    procps \
    ca-certificates \
    && echo "ALL ALL=(ALL) NOPASSWD: ALL" > /etc/sudoers.d/freeai \
    && chmod 0440 /etc/sudoers.d/freeai \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# Install Python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY . /app

# Create workspace mount point
RUN mkdir -p /workspace

# Healthcheck to verify system integrity
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD python3 -c "import os, tempfile; from app.tools.gateway import ToolGateway; from app.resource_manager.watchdog import ResourceManager; from app.orchestrator.orchestrator import TechLeadOrchestrator; gw=ToolGateway(os.getenv('WORKSPACE_ROOT', tempfile.gettempdir())); rm=ResourceManager(); orch=TechLeadOrchestrator(gw, rm); print('OK')" || exit 1

ENTRYPOINT ["python3", "cli.py"]
CMD ["--help"]
