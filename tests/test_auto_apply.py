"""Unit tests for AutoApplyEngine with presence gating and human camouflage."""

import pytest
import time
from unittest.mock import MagicMock, AsyncMock
from app.tools.auto_apply import AutoApplyEngine


def test_auto_apply_package_generation():
    engine = AutoApplyEngine()
    job = {
        "title": "Senior Backend Developer (Nest.js)",
        "company": "Fintech Solutions",
        "url": "https://weworkremotely.com/jobs/999",
        "location": "Anywhere in the World",
        "source": "weworkremotely",
        "salary": "$120,000 / an",
        "matched_skills": ["Nest.js", "Node.js", "Docker", "PostgreSQL"],
        "description": "Building high scalability distributed services with NestJS."
    }

    package = engine.generate_full_application_package(job)

    assert package["job_title"] == "Senior Backend Developer (Nest.js)"
    assert package["company"] == "Fintech Solutions"
    assert "michaelsagbo.tech" in package["cover_letter"]
    assert "Coding Academy by Epitech" in package["cover_letter"]
    assert "Michael SAGBO" in package["cold_email"]["subject"]
    assert "https://michaelsagbo.tech" in package["cold_email"]["body"]
    assert package["human_camouflage_verified"] is True
    assert package["status"] == "READY_TO_DISPATCH"


def test_human_camouflage_anti_ai():
    engine = AutoApplyEngine()
    ai_cliche_text = "As an AI, I am thrilled to delve into this tapestry of opportunities."
    assert engine.verify_human_camouflage(ai_cliche_text) is False

    human_text = "I am a Full Stack & Backend Lead specialized in Nest.js and Python. Check my portfolio at michaelsagbo.tech."
    assert engine.verify_human_camouflage(human_text) is True


def test_auto_apply_presence_gating_when_online():
    import asyncio
    async def _test():
        mock_vault = MagicMock()
        mock_vault.is_master_online.return_value = True  # Michael is ONLINE

        engine = AutoApplyEngine(telegram_vault=mock_vault)
        res = await engine.run_offline_autonomous_cycle()

        assert res["applied"] is False
        assert res["status"] == "MASTER_ONLINE_INHIBITED"
    asyncio.run(_test())


def test_auto_apply_presence_gating_when_offline():
    import asyncio
    async def _test():
        mock_vault = MagicMock()
        mock_vault.is_master_online.return_value = False  # Michael is OFFLINE
        mock_vault.is_configured = True
        mock_vault.group_chat_id = "-1003920092778"
        mock_vault.topic_map = {"career": 97}
        mock_vault.send_message = AsyncMock(return_value=True)

        mock_career = MagicMock()
        mock_career.get_rich_offers.return_value = [
            {
                "title": "Full Stack Lead Engineer",
                "company": "NextGen SaaS",
                "url": f"https://weworkremotely.com/jobs/offline_test_{int(time.time())}",
                "location": "Global Remote",
                "score": 10,
                "source": "weworkremotely",
                "salary": "$110k"
            }
        ]

        engine = AutoApplyEngine(telegram_vault=mock_vault, career_bridge=mock_career)
        res = await engine.run_offline_autonomous_cycle()

        assert res["applied"] is True
        assert res["status"] == "OFFLINE_APPLICATION_SUCCESSFUL"
        assert res["package"]["company"] == "NextGen SaaS"
        assert mock_vault.send_message.called
    asyncio.run(_test())
