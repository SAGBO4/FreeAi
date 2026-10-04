"""Unit tests for BountyRadar, GhostProtocol, MissionSolver, and WarChestLedger.
Test-first design according to Forge Pipeline standards.
"""

import pytest
import os
import json
import time
from unittest.mock import AsyncMock, patch, MagicMock
from pathlib import Path

from app.tools.bounty_radar import (
    GhostProtocolGuard,
    BountyRadarEngine,
    BountyItem,
    WarChestLedger
)


def test_ghost_protocol_headers():
    """Verify that GhostProtocol produces realistic desktop headers and rotating user-agents."""
    guard = GhostProtocolGuard()
    h1 = guard.get_stealth_headers()
    assert "User-Agent" in h1
    assert "Mozilla/5.0" in h1["User-Agent"]
    assert "Accept-Language" in h1
    assert "Accept" in h1


def test_ghost_protocol_circuit_breaker():
    """Verify that GhostProtocol trips circuit breaker on 429/403 and prevents blacklisting."""
    guard = GhostProtocolGuard()
    test_domain = "api.suspicious-domain.org"

    assert guard.is_domain_healthy(test_domain) is True

    # Record 429 Too Many Requests
    guard.record_failure(test_domain, status_code=429)
    assert guard.is_domain_healthy(test_domain) is False

    # Check that query raises or is blocked
    delay = guard.get_cooldown_remaining(test_domain)
    assert delay > 0


def test_war_chest_ledger_progress(tmp_path):
    """Verify that WarChest tracks cash goals for VPS and GPU."""
    ledger_file = tmp_path / "test_war_chest.json"
    wc = WarChestLedger(ledger_path=ledger_file)

    # Initial state
    assert wc.get_balance()["ready_to_claim_usd"] == 0.0

    # Add a solved bounty
    wc.record_bounty_solution(
        bounty_id="GH-62",
        title="Fix vista deployment",
        reward_usd=150.0,
        platform="github",
        issue_url="https://github.com/Mantitup-Org/vista/issues/62"
    )

    bal = wc.get_balance()
    assert bal["ready_to_claim_usd"] == 150.0

    # VPS progress (target 10$/mo): 150$ = 100% of 1st month + 15 months covered
    assert bal["vps_months_covered"] >= 15
    assert bal["vps_progress_pct"] >= 100.0

    # GPU progress (target 100$/mo): 150$ = 150% of 1st month
    assert bal["gpu_progress_pct"] >= 100.0


@pytest.mark.anyio
async def test_bounty_harvester_parsing():
    """Verify that BountyRadar parses GitHub bounty items cleanly."""
    radar = BountyRadarEngine()

    mock_raw_items = [
        {
            "id": 12345,
            "title": "Bug: fix memory leak in worker [$250 bounty]",
            "html_url": "https://github.com/example/repo/issues/10",
            "body": "There is a leak in the background worker. Reward: $250 for PR fixing it.",
            "labels": [{"name": "bug"}, {"name": "bounty"}],
            "repository_url": "https://api.github.com/repos/example/repo"
        }
    ]

    with patch.object(radar, "_fetch_github_bounties", new_callable=AsyncMock) as mock_fetch:
        mock_fetch.return_value = mock_raw_items
        bounties = await radar.scan_bounties(limit=5)
        assert len(bounties) >= 1
        b0 = bounties[0]
        assert b0.reward_usd == 250.0
        assert "Bug: fix memory leak" in b0.title
        assert b0.bounty_id == "GH-12345"


@pytest.mark.anyio
async def test_mission_solver_package():
    """Verify that MissionSolver prepares a complete human-camouflaged PR package."""
    radar = BountyRadarEngine()

    sample_bounty = BountyItem(
        bounty_id="GH-62",
        title="Bug: vista deploy still breaks static hosts",
        issue_url="https://github.com/Mantitup-Org/vista/issues/62",
        repo_url="https://github.com/Mantitup-Org/vista",
        reward_usd=100.0,
        platform="github",
        labels=["bug", "bounty"],
        description="Fix double redirects in static cloudflare pages adapter."
    )

    with patch.object(radar.federation, "consult_free_online_model", new_callable=AsyncMock) as mock_ai:
        mock_ai.return_value = {
            "success": True,
            "response": "```patch\n--- a/deploy.js\n+++ b/deploy.js\n@@ -10,3 +10,4 @@\n- old\n+ new\n```\nExplication technique: correction de la redirection Cloudflare Pages."
        }

        sol = await radar.solve_bounty(sample_bounty)
        assert sol["success"] is True
        assert "package" in sol
        pkg = sol["package"]
        assert pkg["bounty_id"] == "GH-62"
        assert pkg["estimated_reward_usd"] == 100.0
        assert "michaelsagbo.tech" in pkg["pr_body"]
        assert "patch" in pkg["solution_code"]
