"""Code Integrity Guardian & Anti-Truncation Sentinel.

Alias and re-export to app.security.code_integrity_guardian for single source of truth.
"""
from app.security.code_integrity_guardian import (
    CodeHealthReport,
    CodeIntegrityGuardian,
    CodeIntegrityFinding,
    code_sentinel,
    code_integrity_guardian,
    PLACEHOLDER_REGEX,
    FORBIDDEN_EMOJI_REGEX,
    EM_DASH,
)

__all__ = [
    "CodeHealthReport",
    "CodeIntegrityGuardian",
    "CodeIntegrityFinding",
    "code_sentinel",
    "code_integrity_guardian",
    "PLACEHOLDER_REGEX",
    "FORBIDDEN_EMOJI_REGEX",
    "EM_DASH",
]
