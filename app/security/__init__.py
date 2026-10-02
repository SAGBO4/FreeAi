"""FreeAI Security & Ethical Governance Package."""

from app.security.sacred_life import SacredLifeSentinel, SacredLifeViolationError

__all__ = ["SacredLifeSentinel", "SacredLifeViolationError"]
