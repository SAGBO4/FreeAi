"""Unit tests for FreeAi and Lesaint#AI mode switching inside CLI and launcher.
"""

import pytest
from unittest.mock import MagicMock
from cli import get_prompt, handle_mode_command


def test_get_prompt_modes():
    """Verify dynamic prompt formatting based on active mode."""
    assert "[FreeAI:freeAi] > " in get_prompt("freeAi")
    assert "[FreeAI:lesaintAi ⚡] > " in get_prompt("lesaintAi")


def test_handle_mode_command_freeai():
    """Verify switching to FreeAi standard mode."""
    mock_lead = MagicMock()
    mock_lead.set_mode.return_value = {"mode": "freeAi", "allow_sudo": False}

    handle_mode_command(mock_lead, ["freeAi"])
    mock_lead.set_mode.assert_called_with("freeAi")


def test_handle_mode_command_lesaintai():
    """Verify switching to Lesaint#AI super-user mode."""
    mock_lead = MagicMock()
    mock_lead.set_mode.return_value = {"mode": "lesaintAi", "allow_sudo": True}

    handle_mode_command(mock_lead, ["lesaintAi"])
    mock_lead.set_mode.assert_called_with("lesaintAi")


def test_mode_keyword_normalization():
    """Verify keyword mapping for FreeAi and Lesaint#AI."""
    free_variants = ["FreeAi", "freeai", "/FreeAi", "/freeai", "free-ai"]
    lesaint_variants = ["Lesaint#AI", "lesaint#ai", "/Lesaint#AI", "/lesaint#ai", "LesaintAI", "lesaintai", "Lesaint", "lesaint"]

    for v in free_variants:
        norm = v.lstrip("/").lower()
        assert norm in ("freeai", "free-ai", "free_ai", "free")

    for v in lesaint_variants:
        norm = v.lstrip("/").lower()
        assert norm in ("lesaint#ai", "lesaintai", "lesaint-ai", "lesaint_ai", "lesaint")
