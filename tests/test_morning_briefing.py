"""Unit tests for MorningBriefingEngine."""

import pytest
from unittest.mock import MagicMock, AsyncMock
from app.tools.morning_briefing import MorningBriefingEngine


def test_morning_briefing_rich_career_highlights():
    mock_career = MagicMock()
    mock_career.get_rich_offers.return_value = [
        {
            "title": "Senior Backend Developer (NestJS / Node)",
            "company": "Fintech Global",
            "url": "https://weworkremotely.com/jobs/123",
            "location": "Anywhere in the World",
            "salary": "$90k - $120k",
            "score": 9,
            "source": "weworkremotely",
            "description": "Looking for expert in Nest.js, TypeScript and Docker."
        }
    ]
    engine = MorningBriefingEngine(career_bridge=mock_career)
    highlights = engine.get_todays_career_highlights()
    assert len(highlights) == 1
    assert highlights[0]["company"] == "Fintech Global"
    assert "https://" in highlights[0]["url"]
    assert "michaelsagbo.tech" in highlights[0]["pitch"]


def test_morning_briefing_career_highlights_regex_fallback():
    mock_career = MagicMock()
    mock_career.get_rich_offers.return_value = []
    mock_career.run_radar_dry.return_value = {
        "success": True,
        "stdout": (
            " 10 en weworkremotely FULL TIME: Software Engineer - React | Anywhere in the World\n"
            "  7 en workingnomads Backend Architect | Global\n"
        )
    }
    engine = MorningBriefingEngine(career_bridge=mock_career)
    highlights = engine.get_todays_career_highlights()
    assert len(highlights) == 2
    assert highlights[0]["score"] == 10
    assert "React" in highlights[0]["title"]


def test_morning_briefing_text_generation():
    mock_career = MagicMock()
    mock_career.get_rich_offers.return_value = []
    mock_career.run_radar_dry.return_value = {"success": True, "stdout": ""}
    engine = MorningBriefingEngine(career_bridge=mock_career)
    text = engine.generate_briefing_text()
    assert "RAPPORT DU MATIN" in text
    assert "RADAR CAREER-OS" in text
    assert "AETHER-SWARM" in text
    assert "500$" in text
    assert "Mode NÉANT" in text


def test_career_actionable_report():
    mock_career = MagicMock()
    mock_career.get_rich_offers.return_value = [
        {
            "title": "Full Stack Lead Engineer",
            "company": "TechCorp",
            "url": "https://weworkremotely.com/jobs/456",
            "location": "100% Remote",
            "salary": "$100k",
            "score": 10,
            "source": "weworkremotely",
            "description": "Nest.js Next.js Python"
        }
    ]
    engine = MorningBriefingEngine(career_bridge=mock_career)
    report = engine.generate_career_actionable_report()
    assert "TechCorp" in report
    assert "https://weworkremotely.com/jobs/456" in report
    assert "michaelsagbo.tech" in report
    assert "Message d'Accroche Prêt à Envoyer" in report


def test_morning_briefing_broadcast():
    import asyncio
    async def _test():
        mock_vault = MagicMock()
        mock_vault.is_configured = True
        mock_vault.group_chat_id = "-1003920092778"
        mock_vault.topic_map = {"career": 97}
        mock_vault.send_message = AsyncMock(return_value=True)

        mock_career = MagicMock()
        mock_career.get_rich_offers.return_value = []
        mock_career.run_radar_dry.return_value = {"success": True, "stdout": ""}

        engine = MorningBriefingEngine(telegram_vault=mock_vault, career_bridge=mock_career)
        res = await engine.broadcast_morning_briefing()

        assert res["success"] is True
        assert res["posted_to_general"] is True
        assert res["posted_to_career"] is True
        assert mock_vault.send_message.call_count >= 2
    asyncio.run(_test())
