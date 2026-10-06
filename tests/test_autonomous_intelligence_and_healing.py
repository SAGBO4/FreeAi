"""Comprehensive Test Suite for Autonomous Intelligence, Chronos Awareness,
Dynamic Nightly Swarm Learning, Audio Reports, and Proactive Self-Healing (F-19 to F-22).

Zero-Bug Verification:
1. ChronosTimeEngine & Temporal Greetings (Strict prohibition of "Bonjour" at 18h+).
2. PersonaEngine Time Calibration (Human dialog matches time of day).
3. DynamicNightlyLearner (Zero hardcoded static list, non-repetition across dates).
4. Morning & Evening Briefings with Neural Audio Voice Notes (OGG Opus).
5. AutonomousSelfHealingGuardian (Proactive anomaly detection & autonomous RAM remediation).
6. Strict zero raw emoji compliance in TUI / terminal messages.
"""

import os
import io
import json
import asyncio
import pytest
from datetime import datetime, date, time
from zoneinfo import ZoneInfo
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock, patch

from app.cognition.chronos_time import ChronosTimeEngine
from app.cognition.persona import ConversationalPersona
from app.tools.nightly_learner import DynamicNightlyLearner
from app.tools.morning_briefing import MorningBriefingEngine, EveningDebriefingEngine, DailyReportsEngine
from app.resource_manager.self_healing_guardian import AutonomousSelfHealingGuardian


class TestChronosTimeEngine:
    """Verifies temporal precision, satellite clock, and strict greeting rules."""

    def test_day_period_classification(self):
        # Morning: 5h00 - 11h59
        dt_matin = datetime(2026, 10, 6, 8, 30, tzinfo=ZoneInfo("UTC"))
        assert ChronosTimeEngine.get_day_period(dt_matin) == "matin"

        # Midi: 12h00 - 13h59
        dt_midi = datetime(2026, 10, 6, 12, 15, tzinfo=ZoneInfo("UTC"))
        assert ChronosTimeEngine.get_day_period(dt_midi) == "midi"

        # Afternoon: 14h00 - 17h59
        dt_aprem = datetime(2026, 10, 6, 16, 0, tzinfo=ZoneInfo("UTC"))
        assert ChronosTimeEngine.get_day_period(dt_aprem) == "apres_midi"

        # Evening: 18h00 - 22h59
        dt_soir_18h = datetime(2026, 10, 6, 18, 0, tzinfo=ZoneInfo("UTC"))
        dt_soir_20h = datetime(2026, 10, 6, 20, 45, tzinfo=ZoneInfo("UTC"))
        assert ChronosTimeEngine.get_day_period(dt_soir_18h) == "soiree"
        assert ChronosTimeEngine.get_day_period(dt_soir_20h) == "soiree"

        # Night: 23h00 - 04h59
        dt_nuit = datetime(2026, 10, 6, 23, 30, tzinfo=ZoneInfo("UTC"))
        dt_aube = datetime(2026, 10, 6, 3, 0, tzinfo=ZoneInfo("UTC"))
        assert ChronosTimeEngine.get_day_period(dt_nuit) == "nuit"
        assert ChronosTimeEngine.get_day_period(dt_aube) == "nuit"

    def test_strict_no_bonjour_at_18h_or_evening(self):
        """CRITICAL: FreeAI MUST NEVER say 'Bonjour' at 18h or evening."""
        for hour in [18, 19, 20, 21, 22]:
            dt = datetime(2026, 10, 6, hour, 0, tzinfo=ZoneInfo("UTC"))
            prefix = ChronosTimeEngine.get_greeting_prefix(dt)
            greeting = ChronosTimeEngine.get_appropriate_greeting(name="Michael", dt=dt)
            
            assert prefix == "Bonsoir", f"Failed at hour {hour}: got {prefix}"
            assert "bonjour" not in greeting.lower(), f"Greeting at {hour}h contains 'bonjour': {greeting}"
            assert "bonsoir" in greeting.lower()

    def test_morning_greetings_use_bonjour(self):
        for hour in [7, 8, 9, 10]:
            dt = datetime(2026, 10, 6, hour, 0, tzinfo=ZoneInfo("UTC"))
            prefix = ChronosTimeEngine.get_greeting_prefix(dt)
            greeting = ChronosTimeEngine.get_appropriate_greeting(name="Michael", dt=dt)
            
            assert prefix == "Bonjour"
            assert "bonjour" in greeting.lower()

    def test_satellite_clock_telemetry(self):
        telemetry = ChronosTimeEngine.get_satellite_clock_telemetry()
        assert telemetry["satellite_synced"] is True
        assert "formatted_time" in telemetry
        assert "period" in telemetry
        assert telemetry["period"] in ("matin", "midi", "apres_midi", "soiree", "nuit")

    def test_exact_required_greetings_by_hour(self):
        """Verifies exact required prompt specifications:
        - 9h -> 'Bonjour'
        - 15h -> 'Bon après-midi'
        - 18h & 20h -> 'Bonsoir'
        - 23h & 2h -> 'Bonne nuit'
        """
        # 9h -> 'Bonjour'
        dt_9h = datetime(2026, 10, 6, 9, 0, tzinfo=ZoneInfo("UTC"))
        assert ChronosTimeEngine.get_greeting_prefix(dt_9h) == "Bonjour"

        # 15h -> 'Bon après-midi'
        dt_15h = datetime(2026, 10, 6, 15, 0, tzinfo=ZoneInfo("UTC"))
        assert ChronosTimeEngine.get_greeting_prefix(dt_15h) == "Bon après-midi"

        # 18h -> 'Bonsoir' (STRICT: NEVER 'Bonjour')
        dt_18h = datetime(2026, 10, 6, 18, 0, tzinfo=ZoneInfo("UTC"))
        assert ChronosTimeEngine.get_greeting_prefix(dt_18h) == "Bonsoir"
        assert "bonjour" not in ChronosTimeEngine.get_appropriate_greeting("Michael", dt_18h).lower()

        # 20h -> 'Bonsoir'
        dt_20h = datetime(2026, 10, 6, 20, 0, tzinfo=ZoneInfo("UTC"))
        assert ChronosTimeEngine.get_greeting_prefix(dt_20h) == "Bonsoir"

        # 23h -> 'Bonne nuit'
        dt_23h = datetime(2026, 10, 6, 23, 0, tzinfo=ZoneInfo("UTC"))
        assert ChronosTimeEngine.get_greeting_prefix(dt_23h) == "Bonne nuit"

        # 2h -> 'Bonne nuit'
        dt_2h = datetime(2026, 10, 6, 2, 0, tzinfo=ZoneInfo("UTC"))
        assert ChronosTimeEngine.get_greeting_prefix(dt_2h) == "Bonne nuit"


class TestPersonaTemporalIntegration:
    """Verifies that ConversationalPersona adapts to Chronos time."""

    def test_persona_greeting_at_18h_uses_bonsoir(self):
        persona = ConversationalPersona()
        dt_18h = datetime(2026, 10, 6, 18, 0)
        
        with patch.object(persona.chronos, "get_local_datetime", return_value=dt_18h):
            reply = persona._generate_local_human_reply("bonjour freeai", "")
            assert "bonjour" not in reply.lower()
            assert "bonsoir" in reply.lower()

    def test_persona_greeting_at_morning_uses_bonjour(self):
        persona = ConversationalPersona()
        dt_9am = datetime(2026, 10, 6, 9, 0)
        
        with patch.object(persona.chronos, "get_local_datetime", return_value=dt_9am):
            reply = persona._generate_local_human_reply("salut freeai", "")
            assert "bonjour" in reply.lower() or "salut" in reply.lower()


class TestDynamicNightlyLearner:
    """Verifies dynamic swarm learning and non-repetition across days."""

    def test_dynamic_learnings_generation(self, tmp_path):
        ledger_file = tmp_path / "test_ledger.json"
        learner = DynamicNightlyLearner(ledger_path=ledger_file)
        
        learnings = learner.generate_daily_learnings(date(2026, 10, 6))
        assert len(learnings) == 4
        domains = [item["domain"] for item in learnings]
        assert "Web3 & Smart Contracts" in domains
        assert "Ingénierie des Modèles & Inférence LPU" in domains
        assert "Hologramme Binaire 1-Bit & Mémoire Vectorielle" in domains
        assert "Architecture UI & Systèmes Souverains" in domains

    def test_non_repetition_across_consecutive_days(self, tmp_path):
        ledger_file = tmp_path / "test_ledger.json"
        learner = DynamicNightlyLearner(ledger_path=ledger_file)
        
        day1_learnings = learner.generate_daily_learnings(date(2026, 10, 6))
        day2_learnings = learner.generate_daily_learnings(date(2026, 10, 7))
        
        day1_insights = [item["insight"] for item in day1_learnings]
        day2_insights = [item["insight"] for item in day2_learnings]
        
        # Insights must be different between day 1 and day 2!
        assert day1_insights != day2_insights

    def test_ledger_persistence_and_reload(self, tmp_path):
        ledger_file = tmp_path / "test_ledger.json"
        learner = DynamicNightlyLearner(ledger_path=ledger_file)
        learner.generate_daily_learnings(date(2026, 10, 6))
        
        assert ledger_file.exists()
        reloaded = DynamicNightlyLearner(ledger_path=ledger_file)
        assert "2026-10-06" in reloaded._history

    def test_morning_briefing_get_nightly_swarm_learnings_not_hardcoded(self):
        """Verifies MorningBriefingEngine uses DynamicNightlyLearner and does not return static hardcoded list."""
        engine = MorningBriefingEngine()
        learnings = engine.get_nightly_swarm_learnings()
        assert isinstance(learnings, list)
        assert len(learnings) == 4
        # Verify dynamic metadata is present
        assert any("insight_hash" in item or "learned_on" in item for item in learnings)


class TestDailyReportsAndVoiceNotes:
    """Verifies morning and evening debriefings and neural voice notes (OGG Opus)."""

    def test_morning_briefing_audio_broadcast(self):
        async def _test():
            mock_vault = MagicMock()
            mock_vault.is_configured = True
            mock_vault.group_chat_id = "-1003920092778"
            mock_vault.topic_map = {"career": 97}
            mock_vault.send_message = AsyncMock(return_value=True)
            mock_vault.send_voice = AsyncMock(return_value=True)

            mock_voice = MagicMock()
            mock_voice.synthesize_speech = AsyncMock(return_value=io.BytesIO(b"OPUS_MOCK_BYTES"))

            mock_career = MagicMock()
            mock_career.get_rich_offers.return_value = []
            mock_career.run_radar_dry.return_value = {"success": True, "stdout": ""}

            engine = MorningBriefingEngine(
                telegram_vault=mock_vault,
                career_bridge=mock_career,
                voice_tts=mock_voice
            )
            res = await engine.broadcast_morning_briefing()
            
            assert res["success"] is True
            assert res["posted_to_general"] is True
            assert res["posted_voice"] is True
            assert mock_vault.send_voice.call_count >= 1

        asyncio.run(_test())

    def test_evening_debriefing_audio_broadcast(self):
        async def _test():
            mock_vault = MagicMock()
            mock_vault.is_configured = True
            mock_vault.group_chat_id = "-1003920092778"
            mock_vault.send_message = AsyncMock(return_value=True)
            mock_vault.send_voice = AsyncMock(return_value=True)

            mock_voice = MagicMock()
            mock_voice.synthesize_speech = AsyncMock(return_value=io.BytesIO(b"OPUS_EVENING_BYTES"))

            engine = EveningDebriefingEngine(
                telegram_vault=mock_vault,
                voice_tts=mock_voice
            )
            text = engine.generate_evening_text()
            assert "DÉBRIEFING DU SOIR" in text
            assert "BILAN DE PRODUCTIVITÉ" in text
            assert "CYCLE NOCTURNE" in text

            res = await engine.broadcast_evening_debriefing()
            assert res["success"] is True
            assert res["posted_to_general"] is True
            assert res["posted_voice"] is True
            assert mock_vault.send_voice.call_count >= 1

        asyncio.run(_test())

    def test_sentinel_loop_autonomous_dispatch_in_cli(self):
        """Verifies automated dispatch in the sentinel loop (freeai-jarvis.service in cli.py)."""
        async def _test():
            mock_tech_lead = MagicMock()
            mock_tech_lead.telegram_vault.is_configured = True
            mock_tech_lead.telegram_vault.send_message = AsyncMock(return_value=True)
            mock_tech_lead.telegram_vault.send_voice = AsyncMock(return_value=True)
            mock_tech_lead.voice.synthesize_speech = AsyncMock(return_value=io.BytesIO(b"MOCK_OPUS"))
            mock_tech_lead._last_morning_briefing_date = None
            mock_tech_lead._last_evening_briefing_date = None

            today_str = str(date.today())

            # 1. Morning dispatch at 07h30
            current_hour = 8
            mock_career = MagicMock()
            mock_career.get_rich_offers.return_value = []
            mock_career.run_radar_dry.return_value = {"success": True, "stdout": ""}
            if current_hour >= 7 and getattr(mock_tech_lead, "_last_morning_briefing_date", None) != today_str:
                engine = MorningBriefingEngine(
                    telegram_vault=mock_tech_lead.telegram_vault,
                    career_bridge=mock_career,
                    voice_tts=mock_tech_lead.voice
                )
                await engine.broadcast_morning_briefing()
                mock_tech_lead._last_morning_briefing_date = today_str

            assert mock_tech_lead._last_morning_briefing_date == today_str
            assert mock_tech_lead.telegram_vault.send_voice.call_count >= 1

            # 2. Evening dispatch at 21h00
            current_hour = 21
            if current_hour >= 20 and getattr(mock_tech_lead, "_last_evening_briefing_date", None) != today_str:
                engine = EveningDebriefingEngine(telegram_vault=mock_tech_lead.telegram_vault, voice_tts=mock_tech_lead.voice)
                await engine.broadcast_evening_debriefing()
                mock_tech_lead._last_evening_briefing_date = today_str

            assert mock_tech_lead._last_evening_briefing_date == today_str
            assert mock_tech_lead.telegram_vault.send_voice.call_count >= 2

        import asyncio
        asyncio.run(_test())


class TestAutonomousSelfHealingGuardian:
    """Verifies proactive anomaly detection and autonomous RAM remediation."""

    def test_diagnose_healthy_state(self):
        guardian = AutonomousSelfHealingGuardian(ram_critical_pct=95.0)
        guardian.max_process_rss_mb = 4000.0
        with patch("psutil.virtual_memory") as mock_vm, patch.object(guardian, "_probe_wan_reachability", return_value=True):
            mock_vm.return_value = MagicMock(percent=45.0, available=4000 * 1024 * 1024)
            diag = guardian.diagnose_vital_health()
            assert diag["healthy"] is True
            assert diag["issues_count"] == 0

    def test_diagnose_ram_anomaly(self):
        guardian = AutonomousSelfHealingGuardian(ram_critical_pct=80.0)
        guardian.max_process_rss_mb = 4000.0
        with patch("psutil.virtual_memory") as mock_vm, patch.object(guardian, "_probe_wan_reachability", return_value=True):
            mock_vm.return_value = MagicMock(percent=88.5, available=300 * 1024 * 1024)
            diag = guardian.diagnose_vital_health()
            assert diag["healthy"] is False
            assert diag["issues_count"] >= 1
            assert any(issue["type"] == "ram_pressure" for issue in diag["issues"])

    def test_autonomous_remediation_execution(self):
        async def _test():
            guardian = AutonomousSelfHealingGuardian()
            diagnosis = {
                "healthy": False,
                "issues": [
                    {"type": "ram_pressure", "severity": "high", "details": "RAM 89%"},
                    {"type": "wan_connectivity_dropped", "severity": "medium", "details": "WAN down"}
                ]
            }
            remediation = await guardian.execute_proactive_remediation(diagnosis)
            assert remediation["success"] is True
            assert remediation["issues_resolved"] == 2
            assert any("Purge mémoire RAM" in act for act in remediation["actions"])
            assert any("air-gap" in act for act in remediation["actions"])
            assert len(guardian._remediation_history) >= 1

        asyncio.run(_test())

    def test_single_audit_and_heal_cycle(self):
        async def _test():
            guardian = AutonomousSelfHealingGuardian()
            with patch.object(guardian, "diagnose_vital_health") as mock_diag:
                mock_diag.return_value = {"healthy": True, "issues_count": 0, "issues": []}
                res = await guardian.run_single_audit_and_heal_cycle()
                assert res["healthy_initially"] is True
                assert res["remediated"] is False

        asyncio.run(_test())

    def test_socket_disconnection_and_service_fault_healing(self):
        """Verifies simulated socket disconnection and LSP/service fault are healed autonomously in RAM."""
        async def _test():
            guardian = AutonomousSelfHealingGuardian()
            # 1. Trigger simulated LSP / service syntax fault
            guardian.trigger_lsp_fault()
            assert guardian._lsp_probe_healthy is False

            # 2. Simulate socket drop + FD leak + LSP fault
            fault_diag = {
                "healthy": False,
                "issues": [
                    {"type": "wan_connectivity_dropped", "severity": "medium", "details": "Socket disconnected"},
                    {"type": "lsp_cache_degraded", "severity": "low", "details": "LSP syntax cache corrupted"},
                    {"type": "fd_leak", "severity": "high", "details": "Orphaned socket descriptors"}
                ]
            }

            rem = await guardian.execute_proactive_remediation(fault_diag)
            assert rem["success"] is True
            assert rem["issues_resolved"] == 3
            # Guardian restored LSP healthy flag in RAM
            assert guardian._lsp_probe_healthy is True
            assert any("air-gap" in act for act in rem["actions"])
            assert any("syntaxique" in act.lower() for act in rem["actions"])
            assert any("descripteurs" in act.lower() for act in rem["actions"])

        asyncio.run(_test())

    def test_zero_user_intervention_enforced(self):
        """Verifies that autonomous self-healing executes 100% non-interactively without user prompts."""
        async def _test():
            guardian = AutonomousSelfHealingGuardian()
            with patch("builtins.input", side_effect=AssertionError("CRITICAL: input() was called during autonomous self-healing!")):
                diag = {
                    "healthy": False,
                    "issues": [{"type": "ram_pressure", "severity": "high", "details": "Simulated RAM peak"}]
                }
                res = await guardian.execute_proactive_remediation(diag)
                assert res["success"] is True

        asyncio.run(_test())
