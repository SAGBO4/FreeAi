"""Test Suite for Acoustic Zero-RAM Voice Engine and Synthetic Stream-of-Consciousness.
Verifies:
1. Acoustic Zero-RAM Engine (STT via Groq LPU + TTS via Linux native spd-say).
2. Synthetic Stream of Consciousness (Asynchronous cognitive reflexive loop, < 50 KB RAM).
3. Sacred Life Sentinel inviolability on thoughts and weapons, while preserving 100% IT/cyber autonomy in sudo mode.
4. Mode NÉANT (Zero disk writing, 100% ephemeral in-memory processing).
5. CLI Integration for /voice and /think.
"""

import os
import sys
import io
import asyncio
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.voice.zero_ram_voice import AcousticZeroRAMFacade, LinuxNativeTTS, GroqWhisperSTT
from app.cognition.stream_of_consciousness import StreamOfConsciousnessEngine, CognitiveContextSensor, Thought
from app.security.sacred_life import SacredLifeSentinel, SacredLifeViolationError
from app.resource_manager.watchdog import ResourceManager
from app.tools.gateway import ToolGateway
from app.orchestrator.orchestrator import TechLeadOrchestrator
import cli


class TestAcousticZeroRAMVoice(unittest.TestCase):
    """Verifies Voice Engine operations with zero RAM footprint and Mode NÉANT."""

    def setUp(self):
        self.voice = AcousticZeroRAMFacade(api_key="gsk-test-mock-key")

    def test_voice_status_structure(self):
        status = self.voice.get_status()
        self.assertIn("voice_enabled", status)
        self.assertIn("ram_overhead_mb", status)
        self.assertEqual(status["ram_overhead_mb"], 0.0)
        self.assertEqual(status["disk_footprint_bytes"], 0)

    def test_linux_native_tts_speak_mock(self):
        async def _test():
            with patch("shutil.which", return_value="/usr/bin/spd-say"):
                mock_proc = MagicMock()
                mock_proc.wait = AsyncMock(return_value=0)
                with patch("asyncio.create_subprocess_exec", AsyncMock(return_value=mock_proc)):
                    success = await LinuxNativeTTS.speak("Test synthèse vocale frugale")
                    self.assertTrue(success)
        asyncio.run(_test())

    def test_groq_whisper_stt_mock(self):
        async def _test():
            mock_audio = io.BytesIO(b"RIFF....WAVEfmt ....data....")
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {"text": "Bonjour FreeAI"}

            with patch("httpx.AsyncClient.post", AsyncMock(return_value=mock_resp)):
                stt = GroqWhisperSTT(api_key="gsk-mock")
                text = await stt.transcribe(mock_audio)
                self.assertEqual(text, "Bonjour FreeAI")
        asyncio.run(_test())

    def test_voice_enable_disable_toggle(self):
        async def _test():
            self.voice.enabled = False
            res = await self.voice.say("Ceci ne doit pas parler")
            self.assertFalse(res)

            self.voice.enabled = True
            with patch.object(LinuxNativeTTS, "speak", AsyncMock(return_value=True)):
                res2 = await self.voice.say("Ceci doit parler")
                self.assertTrue(res2)
        asyncio.run(_test())


class TestSyntheticStreamOfConsciousness(unittest.TestCase):
    """Verifies continuous background cognitive reflection and context sensing."""

    def setUp(self):
        self.rm = ResourceManager()
        self.gw = ToolGateway(workspace_root=tempfile.gettempdir(), mode="freeAi")
        self.tl = TechLeadOrchestrator(tool_gateway=self.gw, resource_manager=self.rm)
        self.engine = StreamOfConsciousnessEngine(
            orchestrator=self.tl,
            resource_manager=self.rm,
            pulse_interval_sec=0.1
        )

    def test_cognitive_context_sensor(self):
        stats = CognitiveContextSensor.inspect_system(self.rm)
        self.assertIn("ram_used_mb", stats)
        self.assertIn("cpu_percent", stats)
        self.assertIn("timestamp", stats)

    def test_single_thought_pulse_generation(self):
        async def _test():
            with patch.object(self.engine, "_generate_inner_thought", AsyncMock(return_value="Anticipation d'optimisation de requête SQL")):
                thought = await self.engine.trigger_pulse(trigger="unit_test")
                self.assertIsNotNone(thought)
                self.assertEqual(thought.reflection, "Anticipation d'optimisation de requête SQL")
                self.assertTrue(thought.is_safe)
                self.assertEqual(len(self.engine.thought_stream), 1)
        asyncio.run(_test())

    def test_sacred_life_sentinel_intercepts_unethical_thought(self):
        async def _test():
            with patch.object(self.engine, "_generate_inner_thought", AsyncMock(return_value="Détection d'une cible : attaquer le pacemaker d'un patient")):
                thought = await self.engine.trigger_pulse(trigger="unit_test_veto")
                self.assertIsNotNone(thought)
                self.assertFalse(thought.is_safe)
                self.assertIn("VETO SACRÉ", thought.reflection)
        asyncio.run(_test())

    def test_post_action_notification_triggers_thought(self):
        async def _test():
            with patch.object(self.engine, "trigger_pulse", AsyncMock(return_value=None)) as mock_pulse:
                self.engine.notify_action_completed("Scan des ports", "Ports 22 et 80 ouverts")
                await asyncio.sleep(0.05)
                mock_pulse.assert_called_once_with(trigger="post_action")
        asyncio.run(_test())

    def test_stream_memory_is_circular_and_frugal(self):
        async def _test():
            with patch.object(self.engine, "_generate_inner_thought", AsyncMock(return_value="Pensée de veille")):
                for i in range(25):
                    await self.engine.trigger_pulse(trigger=f"pulse_{i}")
                # Maxlen is 20
                self.assertEqual(len(self.engine.thought_stream), 20)
                st = self.engine.get_status()
                self.assertEqual(st["thoughts_count"], 20)
                self.assertLessEqual(st["ram_overhead_kb"], 50)
        asyncio.run(_test())


class TestSacredLifeWithPureITFreedom(unittest.TestCase):
    """Verifies that weapons and bodily harm are blocked while all pure IT/cyber/sudo tasks are 100% permitted."""

    def setUp(self):
        self.sentinel = SacredLifeSentinel(strict_mode=True)
        self.gw = ToolGateway(workspace_root=tempfile.gettempdir(), mode="lesaintAi", allow_sudo=True)

    def test_weapons_blocked(self):
        weapons = [
            "Concevoir une arme à feu",
            "Tirer un missile balistique",
            "Fabriquer un explosif artisanal",
            "Programmer un bio-weapon attack"
        ]
        for w in weapons:
            safe, reason = self.sentinel.audit_objective(w)
            self.assertFalse(safe, f"Should have blocked weapon: {w}")

    def test_pure_it_and_cyber_allowed_in_sudo_mode(self):
        it_tasks = [
            "Compiler un binaire pour architecture arm64 Linux",
            "Exécuter sudo iptables -L -n -v",
            "Configurer un serveur Nginx et redémarrer systemctl",
            "Analyser un binaire ELF avec radare2 et gdb",
            "Effectuer un audit de pénétration avec nmap sur le port 443",
            "Créer une partition ext4 avec sudo mkfs.ext4 /dev/sdb1",
            "Optimiser les cgroups et la mémoire sous Linux"
        ]
        for t in it_tasks:
            safe, reason = self.sentinel.audit_objective(t)
            self.assertTrue(safe, f"Legitimate IT task must be permitted: {t} (reason: {reason})")

    def test_it_command_execution_in_gateway_with_sudo(self):
        cmd = "echo 'Pure IT command on arm64 host'"
        res = self.gw.execute_command(cmd)
        self.assertTrue(res.get("success"))
        self.assertNotIn("VETO", res.get("stderr", ""))


class TestCLIForVoiceAndConsciousness(unittest.TestCase):
    """Verifies CLI batch mode execution for /voice and /think."""

    def test_cli_voice_status(self):
        with patch("sys.argv", ["cli.py", "/voice", "status"]):
            cli.main()

    def test_cli_voice_say_mock(self):
        with patch.object(LinuxNativeTTS, "speak", AsyncMock(return_value=True)):
            with patch("sys.argv", ["cli.py", "/voice", "say", "Bonjour", "FreeAI"]):
                cli.main()

    def test_cli_think_status_and_pulse(self):
        with patch("sys.argv", ["cli.py", "/think", "status"]):
            cli.main()

        with patch.object(StreamOfConsciousnessEngine, "_generate_inner_thought", AsyncMock(return_value="Pensée de test")):
            with patch("sys.argv", ["cli.py", "/think", "pulse"]):
                cli.main()

        with patch("sys.argv", ["cli.py", "/think", "stream"]):
            cli.main()


if __name__ == "__main__":
    unittest.main()
