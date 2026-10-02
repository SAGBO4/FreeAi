"""Configuration module using pure Pydantic BaseModel and os.environ."""

import os
from pathlib import Path
from pydantic import BaseModel, Field


def _get_bool(key: str, default: bool) -> bool:
    val = os.getenv(key)
    if val is None:
        return default
    return val.strip().lower() in ("true", "1", "yes", "t")


def _get_int(key: str, default: int) -> int:
    val = os.getenv(key)
    if val is None:
        return default
    try:
        return int(val)
    except ValueError:
        return default


def _load_env_file():
    env_path = Path(".env")
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, val = line.split("=", 1)
            key = key.strip()
            val = val.strip().strip("\"'")
            if key not in os.environ:
                os.environ[key] = val


_load_env_file()


class Settings(BaseModel):
    # Hardware & CPU LLM settings
    LLM_MODEL_PATH: str = Field(default_factory=lambda: os.getenv("LLM_MODEL_PATH", "./models/qwen2.5-coder-1.5b-instruct-q4_k_m.gguf"))
    LLM_CONTEXT_SIZE: int = Field(default_factory=lambda: _get_int("LLM_CONTEXT_SIZE", 4096))
    LLM_THREADS: int = Field(default_factory=lambda: _get_int("LLM_THREADS", 4))

    # Strict RAM limits (TDR §3 & §9)
    RAM_TARGET_MB: int = Field(default_factory=lambda: _get_int("RAM_TARGET_MB", 3500))
    RAM_HARD_LIMIT_MB: int = Field(default_factory=lambda: _get_int("RAM_HARD_LIMIT_MB", 4000))
    WATCHDOG_INTERVAL_SEC: float = Field(default=1.0)

    # Local Network Security
    SERVER_HOST: str = Field(default_factory=lambda: os.getenv("SERVER_HOST", "127.0.0.1"))
    SERVER_PORT: int = Field(default_factory=lambda: _get_int("SERVER_PORT", 8000))
    ALLOW_NETWORK: bool = Field(default_factory=lambda: _get_bool("ALLOW_NETWORK", False))
    ALLOW_SUDO: bool = Field(default_factory=lambda: _get_bool("ALLOW_SUDO", False))

    # Modes: normal, autonomous, lab
    APP_MODE: str = Field(default_factory=lambda: os.getenv("APP_MODE", "normal"))

    # Workspace & Directories
    WORKSPACE_ROOT: str = Field(default_factory=lambda: os.getenv("WORKSPACE_ROOT", str(Path.home() / "Projects")))
    LOG_DIR: str = Field(default_factory=lambda: os.getenv("LOG_DIR", "./logs"))
    MEMORY_DIR: str = Field(default_factory=lambda: os.getenv("MEMORY_DIR", "./memory"))
    LOG_LEVEL: str = Field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"))

    # Memory Configuration (Neon Cloud PostgreSQL & Zero Local Disk)
    MEMORY_MODE: str = Field(default_factory=lambda: os.getenv("MEMORY_MODE", "neant"))
    PERSIST_TO_DISK: bool = Field(default_factory=lambda: _get_bool("PERSIST_TO_DISK", False))
    LOG_TO_FILE: bool = Field(default_factory=lambda: _get_bool("LOG_TO_FILE", False))
    NEON_DATABASE_URL: str = Field(default_factory=lambda: os.getenv("NEON_DATABASE_URL", ""))


settings = Settings()
