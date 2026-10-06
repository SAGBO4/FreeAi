"""Tests pour les 4 composants de rupture FreeAI :
1. DynamicNightlyLearner (Apprentissage nocturne & déduplication sémantique)
2. DailyReportsEngine (Double rapport matin/soir & audio vocal)
3. SatelliteChronos & greffe PersonaEngine (Conscience temporelle & salutations strictes)
4. AutonomousSelfHealingGuardian (Auto-guérison proactive en arrière-plan)
"""

import io
import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from app.satellite.satellite_chronos import SatelliteChronos, DayPhase
from app.cognition.persona import ConversationalPersona
from app.evolution.dynamic_nightly_learner import DynamicNightlyLearner
from app.tools.daily_briefing_engine import DailyReportsEngine
from app.resource_manager.self_healing_guardian import AutonomousSelfHealingGuardian


class TestSatelliteChronosAndPersona:
    """Tests de l'horloge satellitaire et de l'éradication du 'bonjour' à 18h."""

    def test_chronos_phase_classification(self):
        chronos = SatelliteChronos()

        # 06h30 -> Aube
        dt_dawn = datetime(2026, 10, 6, 6, 30)
        assert chronos.classify_phase(dt_dawn) == DayPhase.AUBE
        assert chronos.get_salutation(dt_dawn) == "Bonjour"

        # 09h00 -> Matin
        dt_morning = datetime(2026, 10, 6, 9, 0)
        assert chronos.classify_phase(dt_morning) == DayPhase.MATIN
        assert chronos.get_salutation(dt_morning) == "Bonjour"

        # 12h30 -> Midi
        dt_noon = datetime(2026, 10, 6, 12, 30)
        assert chronos.classify_phase(dt_noon) == DayPhase.MIDI
        assert chronos.get_salutation(dt_noon) == "Bonjour"

        # 15h30 -> Après-midi
        dt_afternoon = datetime(2026, 10, 6, 15, 30)
        assert chronos.classify_phase(dt_afternoon) == DayPhase.APRES_MIDI
        assert chronos.get_salutation(dt_afternoon) == "Bonjour"

        # 18h00 pile -> Soirée (RÈGLE ABSOLUE)
        dt_evening = datetime(2026, 10, 6, 18, 0)
        assert chronos.classify_phase(dt_evening) == DayPhase.SOIREE
        assert chronos.get_salutation(dt_evening) == "Bonsoir"

        # 21h45 -> Soirée
        dt_late_evening = datetime(2026, 10, 6, 21, 45)
        assert chronos.classify_phase(dt_late_evening) == DayPhase.SOIREE
        assert chronos.get_salutation(dt_late_evening) == "Bonsoir"

        # 02h00 -> Nuit
        dt_night = datetime(2026, 10, 6, 2, 0)
        assert chronos.classify_phase(dt_night) == DayPhase.NUIT
        assert chronos.get_salutation(dt_night) == "Bonsoir"

    def test_chronos_ephemeris(self):
        chronos = SatelliteChronos(lat=48.8566, lon=2.3522)
        ephem = chronos.get_solar_ephemeris(datetime(2026, 6, 21, 12, 0))
        assert "solar_elevation_deg" in ephem
        assert ephem["is_daylight"] is True
        assert ephem["phase"] == "midi"

    def test_persona_greeting_at_evening_never_says_bonjour(self):
        persona = ConversationalPersona()
        # Mock chronos to simulate 19h15 (Soirée)
        mock_dt = datetime(2026, 10, 6, 19, 15)
        with patch.object(persona.chronos, "get_local_datetime", return_value=mock_dt):
            reply = persona._generate_local_human_reply("bonsoir freeai", "")
            assert "bonjour" not in reply.lower()
            assert "bonsoir" in reply.lower() or "soir" in reply.lower()

            reply_hello = persona._generate_local_human_reply("salut jarvis", "")
            assert "bonjour" not in reply_hello.lower()
            assert "bonsoir" in reply_hello.lower() or "soir" in reply_hello.lower()


class TestDynamicNightlyLearner:
    """Tests de l'apprentissage nocturne dynamique et de la déduplication."""

    def test_deduplication_and_ledger(self, tmp_path):
        async def _run():
            ledger_file = tmp_path / "test_ledger.json"
            with patch.object(DynamicNightlyLearner, "LEDGER_FILE", ledger_file):
                learner = DynamicNightlyLearner()
                title = "Zero-Knowledge Rollup Flash Swaps Optimization"
                domain = "🛡️ Web3"

                assert learner.is_already_learned(title, domain) is False

                entry = {"title": title, "domain": domain, "date": "2026-10-06"}
                learner.mark_as_learned(entry)

                # Une innovation identique ou quasi-identique doit être refusée
                assert learner.is_already_learned(title, domain) is True
                assert learner.is_already_learned(title.lower(), domain) is True
        asyncio.run(_run())

    def test_run_nightly_learning_cycle_offline_fallback(self, tmp_path):
        async def _run():
            ledger_file = tmp_path / "test_ledger2.json"
            with patch.object(DynamicNightlyLearner, "LEDGER_FILE", ledger_file), \
                 patch.object(DynamicNightlyLearner, "fetch_arxiv_ai_papers", new=AsyncMock(return_value=[])), \
                 patch.object(DynamicNightlyLearner, "fetch_huggingface_models", new=AsyncMock(return_value=[])), \
                 patch.object(DynamicNightlyLearner, "fetch_github_trending", new=AsyncMock(return_value=[])), \
                 patch.object(DynamicNightlyLearner, "fetch_recent_cves", new=AsyncMock(return_value=[])):
                learner = DynamicNightlyLearner()
                learnings = await learner.run_nightly_learning_cycle(max_total_insights=3)
                assert len(learnings) > 0
                for item in learnings:
                    assert "domain" in item
                    assert "insight" in item
        asyncio.run(_run())


class TestDailyReportsEngine:
    """Tests du double rapport (matin et soir) et de l'intégration vocale."""

    def test_generate_enhanced_evening_report(self):
        engine = DailyReportsEngine()
        report = engine.generate_enhanced_evening_report()
        assert "DÉBRIEFING DU SOIR" in report
        assert "INTÉGRITÉ DU CODE" in report
        assert "Mode NÉANT" in report
        assert "5 Février" in report

    def test_broadcast_morning_and_evening_telegram_flow(self):
        async def _run():
            mock_vault = MagicMock()
            mock_vault.is_configured = True
            mock_vault.chat_id = "12345"
            mock_vault.group_chat_id = "-1003920092778"
            mock_vault.topic_map = {"career": 97}
            mock_vault.send_message = AsyncMock(return_value=True)
            mock_vault.send_voice = AsyncMock(return_value=True)

            engine = DailyReportsEngine(telegram_vault=mock_vault)

            # Mock voice synthesis and scraping to avoid external network calls
            with patch("app.voice.zero_ram_voice.NeuralAudioSynthesizer.synthesize_ogg_opus", new=AsyncMock(return_value=io.BytesIO(b"OPUS_MOCK_DATA"))), \
                 patch.object(engine.morning_engine, "generate_briefing_text", return_value="BRIEFING MOCK"), \
                 patch.object(engine.morning_engine, "generate_career_actionable_cards", return_value=["CARD1"]):
                res_morning = await engine.broadcast_morning_briefing()
                assert res_morning["success"] is True
                assert res_morning["posted_to_general"] is True
                assert res_morning["posted_voice"] is True
                assert mock_vault.send_voice.called

                res_evening = await engine.broadcast_evening_debriefing()
                assert res_evening["success"] is True
                assert res_evening["posted_to_general"] is True
                assert res_evening["posted_voice"] is True
        asyncio.run(_run())


class TestAutonomousSelfHealingGuardian:
    """Tests de la détection d'anomalies et auto-réparation proactive."""

    def test_diagnose_and_remediate_lsp_fault(self):
        guardian = AutonomousSelfHealingGuardian()
        # Diagnostic normal
        diag1 = guardian.diagnose_vital_health()
        assert "healthy" in diag1

        # Déclenchement anomalie LSP
        guardian.trigger_lsp_fault()
        diag2 = guardian.diagnose_vital_health()
        assert diag2["healthy"] is False
        assert any(i["type"] == "lsp_cache_degraded" for i in diag2["issues"])

    def test_proactive_remediation_cycle(self):
        async def _run():
            guardian = AutonomousSelfHealingGuardian()
            fake_diagnosis = {
                "healthy": False,
                "issues": [
                    {"type": "ram_pressure", "severity": "high"},
                    {"type": "telegram_poller_stalled", "severity": "medium"},
                    {"type": "lsp_cache_degraded", "severity": "low"}
                ]
            }
            remediation = await guardian.execute_proactive_remediation(fake_diagnosis)
            assert remediation["success"] is True
            assert len(remediation["actions"]) == 3
            assert any("RAM" in a for a in remediation["actions"])
            assert any("Telegram" in a for a in remediation["actions"])
            assert any("LSP" in a for a in remediation["actions"])
        asyncio.run(_run())
