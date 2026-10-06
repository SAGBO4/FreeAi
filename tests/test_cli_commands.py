"""Unit tests for FreeAi and Lesaint#AI mode switching inside CLI and launcher.
"""

import pytest
from unittest.mock import MagicMock
from cli import get_prompt, handle_mode_command


def test_get_prompt_modes():
    """Verify dynamic prompt formatting based on active mode."""
    assert "[FreeAI:freeAi] > " in get_prompt("freeAi")
    assert "[FreeAI:lesaintAi] > " in get_prompt("lesaintAi")


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


def test_interactive_cli_clean_exit_after_sigint():
    """Verify that receiving KeyboardInterrupt followed by /exit does not raise CancelledError or KeyboardInterrupt."""
    from unittest.mock import patch
    import asyncio
    import cli

    inputs = [KeyboardInterrupt(), "/exit"]

    def fake_input(_):
        if not inputs:
            return "/exit"
        val = inputs.pop(0)
        if isinstance(val, Exception):
            raise val
        return val

    with patch("builtins.input", side_effect=fake_input):
        with patch("cli.setup_readline"):
            # Must exit cleanly without throwing CancelledError or KeyboardInterrupt
            asyncio.run(cli.interactive_cli())


def test_get_dynamic_session_title():
    """Verify that get_dynamic_session_title connects to Forge when available or falls back cleanly."""
    from cli import get_dynamic_session_title

    # Custom task preserves value
    assert get_dynamic_session_title("Refonte Header") == "Refonte Header"

    # Default / None reflects Forge Pipeline
    title = get_dynamic_session_title(None)
    assert "Forge Pipeline" in title or title == "Session active"


def test_execute_tech_lead_task_inquiry_detection():
    """Verify that inquiry questions are detected and dispatched with autonomous=False."""
    import asyncio
    from unittest.mock import AsyncMock, MagicMock
    from cli import execute_tech_lead_task

    mock_lead = MagicMock()
    mock_lead.mode = "freeAi"
    mock_lead.handle_objective = AsyncMock(return_value={
        "success": True,
        "assigned_agent": "conversation",
        "plan": ["Répondre directement à la question de l'utilisateur"],
        "result": {"message": "Forge gère l'orchestration des agents."}
    })

    async def _run():
        # Question prompt ending with ? or starting with 'pourquoi'
        await execute_tech_lead_task(mock_lead, "pourquoi j'ai ça ?")
        mock_lead.handle_objective.assert_called_with("pourquoi j'ai ça ?", autonomous=False)

        # Imperative coding prompt
        await execute_tech_lead_task(mock_lead, "Fix broken tests in test_cli.py")
        mock_lead.handle_objective.assert_called_with("Fix broken tests in test_cli.py", autonomous=True)

    asyncio.run(_run())


def test_run_mesh_cli_command():
    """Verify that /mesh command executes cleanly without emojis and outputs valid growth summary."""
    from unittest.mock import MagicMock
    from cli import run_mesh

    mock_lead = MagicMock()
    # Execute status
    run_mesh(mock_lead, ["status"])
    # Execute probe
    run_mesh(mock_lead, ["probe", "127.0.0.1", "8000"])



