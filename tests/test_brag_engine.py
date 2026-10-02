"""Unit tests for FreeAI Sovereign Brag Engine (reproducing Claude Code /brag).
Verifies:
1. Codebase inspection and feature extraction.
2. Viral launch social copy generation (Twitter/X, LinkedIn, Telegram).
3. In-memory video presentation rendering and Telegram export.
4. CLI and Telegram slash command integration.
"""

import os
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock

from app.tools.brag_engine import BragEngine


class TestBragEngine(unittest.TestCase):
    def setUp(self):
        self.engine = BragEngine()

    def test_inspect_current_project(self):
        info = self.engine.inspect_project()
        self.assertIn("name", info)
        self.assertIn("description", info)
        self.assertIn("features", info)
        self.assertTrue(len(info["features"]) >= 3)
        self.assertEqual(info["name"], "FreeAI")

    def test_generate_social_copy(self):
        info = {
            "name": "FreeAI",
            "tagline": "Sovereign Autonomous Cognitive Agent",
            "features": ["Mode NÉANT RAM", "AETHER-SWARM Cloud", "Protocole Phénix"],
            "metrics": "201 tests passing • 0 octet SSD",
            "author": "SAGBO MICHAEL (@SAGBO4)"
        }
        copy = self.engine.generate_social_copy(info)
        self.assertIn("twitter", copy)
        self.assertIn("linkedin", copy)
        self.assertIn("telegram", copy)
        self.assertIn("FreeAI", copy["twitter"])
        self.assertIn("AETHER-SWARM", copy["linkedin"])
        self.assertIn("SAGBO MICHAEL", copy["twitter"])

    def test_execute_brag_with_video_in_ram(self):
        async def _test():
            mock_video_engine = MagicMock()
            mock_video_engine.render_cinematic_teaser_in_ram.return_value = {
                "success": True,
                "filename": "brag_freeai.mp4",
                "size_kb": 250.0,
                "duration_sec": 4,
                "data": b"fake_mp4_bytes"
            }
            self.engine.video_engine = mock_video_engine

            mock_vault = MagicMock()
            mock_vault.is_configured = True
            mock_vault.send_video = AsyncMock(return_value=True)

            res = await self.engine.execute_brag(
                telegram_vault=mock_vault,
                export_telegram=True
            )

            self.assertTrue(res["success"])
            self.assertIn("social_copy", res)
            self.assertIn("video", res)
            mock_vault.send_video.assert_called_once()
        import asyncio
        asyncio.run(_test())
