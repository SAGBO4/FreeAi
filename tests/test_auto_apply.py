"""Unit tests for AutoApplyEngine with presence gating and human camouflage."""

import pytest
import time
import asyncio
import re
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock
from app.tools.auto_apply import AutoApplyEngine

SAMPLE_FORM_URL = f"file://{Path(__file__).parent / 'fixtures' / 'sample_job_application_form.html'}"


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


def test_live_review_application_fills_real_form_and_never_submits():
    """End-to-end: opens a REAL headful browser against a local sample application
    form (never a real job site, to avoid any live side effect), verifies the fields
    were genuinely written into the DOM (not just claimed), that a real resume PDF
    file was generated and attached to the file input, that a working noVNC review
    URL was produced, and that closing the session leaves no process behind."""
    async def _test():
        mock_career = MagicMock()
        mock_career.get_rich_offers.return_value = [
            {
                "title": "Senior Backend Engineer",
                "company": "Test Co",
                "url": SAMPLE_FORM_URL,
                "location": "Remote",
                "score": 10,
                "source": "test_fixture",
                "salary": "N/A"
            }
        ]

        engine = AutoApplyEngine(career_bridge=mock_career)
        res = await engine.prepare_live_review_application(job_index=1)

        assert res["success"] is True, res.get("error")
        assert re.match(r"^http://[\d\.]+:\d+/vnc\.html\?.*password=", res["review_url"])

        report = res["autofill_report"]
        assert "email" in report["filled_fields"]
        assert "phone" in report["filled_fields"]
        assert "city" in report["filled_fields"]
        assert "cover_letter" in report["filled_fields"]
        assert report["file_uploaded"] is not None
        assert Path(report["file_uploaded"]).exists()
        assert report["fully_automatic_success"] is False  # never claims full autonomy

        # Verify the real DOM of the real browser page actually holds the values -
        # not just that we *tried* to fill them.
        session = engine._live_review_sessions[res["session_id"]]
        dom_values = await session._page.evaluate(
            """() => ({
                email: document.getElementById('em').value,
                phone: document.getElementById('ph').value,
                city: document.getElementById('ct').value,
                cover_letter: document.getElementById('cl').value,
                resume_filename: document.getElementById('cv').files.length ? document.getElementById('cv').files[0].name : null
            })"""
        )
        assert dom_values["email"] == "contact@michaelsagbo.tech"
        assert dom_values["phone"] == "+2290152617561"
        assert dom_values["city"] == "Cotonou"
        assert len(dom_values["cover_letter"]) > 0
        assert dom_values["resume_filename"] is not None

        closed = await engine.close_live_review_session(res["session_id"])
        assert closed is True
        assert res["session_id"] not in engine._live_review_sessions

    asyncio.run(_test())
