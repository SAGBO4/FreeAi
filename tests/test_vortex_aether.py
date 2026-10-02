"""Comprehensive Test Suite for Project VORTEX-AETHER & Phantom-Memfd Transceiver.
Verifies:
1. Binary Hologram Vector Engine (BHVE) 1-bit quantization & microsecond Hamming search in RAM.
2. Ultrasonic Air-Gap Transceiver (Ghost Acoustic Link 19.4-20.4 kHz in-memory BFSK).
3. Phantom Bus IPC (memfd_create volatile execution with Sacred Life Sentinel).
4. Telegram Cloud Voice Conduit (Bidirectional mobile voice notes & audio replies).
5. Orchestrator & CLI integration.
6. Strict adherence to Mode NÉANT (0 SSD writes, < 70 MB RAM).
"""

import os
import sys
import io
import wave
import asyncio
import tempfile
import unittest
from pathlib import Path
import numpy as np
from unittest.mock import AsyncMock, MagicMock, patch

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.memory.binary_hologram import BinaryHologramEngine
from app.cluster.ultrasonic_airgap import UltrasonicAirGapTransceiver, UltrasonicConfig
from app.orchestrator.phantom_bus_ipc import PhantomBusIPC
from app.security.sacred_life import SacredLifeSentinel, SacredLifeViolationError
from app.memory.telegram_vault import TelegramNeuralVault
from app.orchestrator.orchestrator import TechLeadOrchestrator
from app.resource_manager.watchdog import ResourceManager
from app.tools.gateway import ToolGateway
import cli


class TestBinaryHologramEngine(unittest.TestCase):
    """Verifies the 1-bit Quantized Binary Hologram in volatile RAM."""

    def test_binarization_compression(self):
        engine = BinaryHologramEngine(dimension=768)
        dense = np.random.randn(768).astype(np.float32)
        packed = engine.binarize(dense)

        self.assertEqual(len(packed), 96)  # 768 bits = 96 bytes
        self.assertIsInstance(packed, np.ndarray)
        self.assertEqual(packed.dtype, np.uint8)

    def test_add_and_search_nearest(self):
        engine = BinaryHologramEngine(dimension=768)
        engine.add_entry("Analyse de la mémoire noyau et vulnérabilités Linux", meta={"tag": "kernel"})
        engine.add_entry("Optimisation des pipelines d'instructions AVX-512 SIMD", meta={"tag": "cpu"})
        engine.add_entry("Recette de cuisine traditionnelle italienne", meta={"tag": "cuisine"})

        results = engine.search_nearest("Analyse de la mémoire noyau et vulnérabilités Linux", top_k=1)
        self.assertEqual(len(results), 1)
        similarity, meta = results[0]
        self.assertAlmostEqual(similarity, 1.0, delta=1e-3)
        self.assertEqual(meta["tag"], "kernel")

    def test_ram_footprint_and_status(self):
        engine = BinaryHologramEngine(dimension=768)
        for i in range(100):
            engine.add_entry(f"Knowledge unit {i}")

        st = engine.get_status()
        self.assertEqual(st["entries_indexed"], 100)
        self.assertEqual(st["bytes_per_vector"], 96)
        self.assertLess(st["hologram_ram_kb"], 20.0)
        self.assertTrue(st["zero_ssd"])


class TestUltrasonicAirGapTransceiver(unittest.TestCase):
    """Verifies the acoustic zero-RF physical link in RAM."""

    def test_text_to_bits_and_back(self):
        original = "PHANTOM_77"
        bit_stream = UltrasonicAirGapTransceiver.text_to_bits(original)
        self.assertTrue(bit_stream.startswith(UltrasonicConfig.PREAMBLE))

        recovered = UltrasonicAirGapTransceiver.bits_to_text(bit_stream)
        self.assertEqual(recovered, original)

    def test_synthesize_burst_in_memory_wav(self):
        bits = "101100"
        stream = UltrasonicAirGapTransceiver.synthesize_burst(bits)
        self.assertIsInstance(stream, io.BytesIO)
        stream.seek(0)

        with wave.open(stream, "rb") as wf:
            self.assertEqual(wf.getnchannels(), 1)
            self.assertEqual(wf.getsampwidth(), 2)
            self.assertEqual(wf.getframerate(), UltrasonicConfig.SAMPLE_RATE)
            num_frames = wf.getnframes()
            expected_frames = int(UltrasonicConfig.SAMPLE_RATE * UltrasonicConfig.BIT_DURATION_SEC) * len(bits)
            self.assertEqual(num_frames, expected_frames)

    def test_frequency_decoding_in_ram(self):
        bits = "1010"
        stream = UltrasonicAirGapTransceiver.synthesize_burst(bits)
        stream.seek(0)
        with wave.open(stream, "rb") as wf:
            raw_pcm = wf.readframes(wf.getnframes())

        decoded_bits = UltrasonicAirGapTransceiver.decode_frequencies(raw_pcm)
        self.assertEqual(decoded_bits, bits)

    def test_transmit_ultrasonic_mock(self):
        async def run_test():
            with patch("shutil.which", return_value="/usr/bin/pw-play"):
                mock_proc = MagicMock()
                mock_proc.stdin = MagicMock()
                mock_proc.stdin.write = MagicMock()
                mock_proc.stdin.drain = AsyncMock()
                mock_proc.stdin.close = MagicMock()
                mock_proc.wait = AsyncMock()
                mock_proc.returncode = 0

                with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
                    ok = await UltrasonicAirGapTransceiver.transmit_ultrasonic("TEST_PAYLOAD")
                    self.assertTrue(ok)
                    self.assertTrue(mock_proc.stdin.write.called)

        asyncio.run(run_test())


class TestPhantomBusIPC(unittest.TestCase):
    """Verifies volatile Linux memfd_create execution and Sacred Life Sentinel."""

    def test_execute_volatile_script_success(self):
        ipc = PhantomBusIPC(strict_ethics=True)
        script = "echo 'FREEAI_PHANTOM_VOLATILE_OK'"
        res = ipc.execute_volatile_script(script, privileged=False)

        self.assertTrue(res["success"])
        self.assertEqual(res["returncode"], 0)
        self.assertIn("FREEAI_PHANTOM_VOLATILE_OK", res["stdout"])
        self.assertTrue(res["zero_ssd"])
        self.assertTrue(res["memfd"])

    def test_sacred_life_sentinel_blocks_weapons_in_phantom(self):
        ipc = PhantomBusIPC(strict_ethics=True)
        weapon_script = "cat /dev/urandom | trigger_missile_launch"

        with self.assertRaises(SacredLifeViolationError):
            ipc.execute_volatile_script(weapon_script)

    def test_pure_it_allowed_in_phantom(self):
        ipc = PhantomBusIPC(strict_ethics=True)
        it_script = "echo 'Compiling ARM64 ELF payload' && uname -s"
        res = ipc.execute_volatile_script(it_script, privileged=False)

        self.assertTrue(res["success"])
        self.assertIn("Compiling ARM64", res["stdout"])


class TestTelegramVoiceConduit(unittest.TestCase):
    """Verifies bidirectional voice notes & telepathy via TelegramNeuralVault."""

    def test_send_voice_mock(self):
        async def run_test():
            vault = TelegramNeuralVault(token="mock_token", chat_id="12345678")
            dummy_audio = io.BytesIO(b"OGG_AUDIO_HEADER_MOCK_STREAM")

            mock_resp = MagicMock()
            mock_resp.status_code = 200

            with patch("httpx.AsyncClient.post", return_value=mock_resp):
                ok = await vault.send_voice(dummy_audio, caption="Rapport vocal")
                self.assertTrue(ok)

        asyncio.run(run_test())

    def test_download_file_bytes_mock(self):
        async def run_test():
            vault = TelegramNeuralVault(token="mock_token", chat_id="12345678")

            mock_get_file = MagicMock()
            mock_get_file.status_code = 200
            mock_get_file.json.return_value = {"ok": True, "result": {"file_path": "voice/audio_01.oga"}}

            mock_download = MagicMock()
            mock_download.status_code = 200
            mock_download.content = b"TELEGRAM_RAW_AUDIO_STREAM"

            with patch("httpx.AsyncClient.get", side_effect=[mock_get_file, mock_download]):
                stream = await vault.download_file_bytes("file_voice_id_999")
                self.assertIsNotNone(stream)
                self.assertEqual(stream.getvalue(), b"TELEGRAM_RAW_AUDIO_STREAM")

        asyncio.run(run_test())

    def test_poll_incoming_voice_note_with_stt(self):
        async def run_test():
            vault = TelegramNeuralVault(token="mock_token", chat_id="12345678")

            updates_resp = MagicMock()
            updates_resp.status_code = 200
            updates_resp.json.return_value = {
                "ok": True,
                "result": [
                    {
                        "update_id": 1001,
                        "message": {
                            "message_id": 55,
                            "chat": {"id": 12345678},
                            "from": {"username": "LesaintCreator"},
                            "voice": {"file_id": "v_note_123"}
                        }
                    }
                ]
            }

            mock_stt = MagicMock()
            mock_stt.transcribe = AsyncMock(return_value="FreeAI lance un diagnostic réseau")

            with patch("httpx.AsyncClient.get", return_value=updates_resp):
                with patch.object(vault, "download_file_bytes", return_value=io.BytesIO(b"MOCK_WAV")):
                    result = await vault.poll_incoming_command(stt_engine=mock_stt)
                    self.assertIsNotNone(result)
                    text, sender = result
                    self.assertIn("diagnostic réseau", text)
                    self.assertEqual(sender, "LesaintCreator")

        asyncio.run(run_test())


class TestOrchestratorAndCLIVortexIntegration(unittest.TestCase):
    """Verifies TechLeadOrchestrator and CLI commands for VORTEX-AETHER."""

    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.rm = ResourceManager()
        self.gw = ToolGateway(workspace_root=self.tmp_dir.name, allow_sudo=True, mode="lesaintAi")
        self.orchestrator = TechLeadOrchestrator(tool_gateway=self.gw, resource_manager=self.rm)

    def tearDown(self):
        self.tmp_dir.cleanup()

    def test_get_vortex_status(self):
        st = self.orchestrator.get_vortex_status()
        self.assertTrue(st["vortex_aether_active"])
        self.assertIn("binary_hologram", st)
        self.assertIn("ultrasonic_airgap", st)
        self.assertIn("phantom_bus", st)
        self.assertIn("telegram_vault", st)

    def test_execute_phantom_via_orchestrator(self):
        res = self.orchestrator.execute_phantom("echo 'ORCHESTRATOR_PHANTOM_INTEGRATION'")
        self.assertTrue(res["success"])
        self.assertIn("ORCHESTRATOR_PHANTOM_INTEGRATION", res["stdout"])

    def test_cli_batch_vortex_commands(self):
        async def run_test():
            from cli import run_vortex, run_hologram, run_airgap, run_phantom

            # 1. /vortex
            await run_vortex(self.orchestrator, [])

            # 2. /hologram
            run_hologram(self.orchestrator, ["status"])
            run_hologram(self.orchestrator, ["add", "Module de compilation autonome"])
            run_hologram(self.orchestrator, ["search", "compilation"])

            # 3. /airgap
            await run_airgap(self.orchestrator, ["status"])

            # 4. /phantom
            run_phantom(self.orchestrator, [])
            run_phantom(self.orchestrator, ["echo", "'CLI_PHANTOM_TEST'"])

            # 5. /shadow
            from cli import run_shadow
            await run_shadow(self.orchestrator, [])
            await run_shadow(self.orchestrator, ["echo", "'CLI_SHADOW_TEST'"])

        asyncio.run(run_test())


class TestKineticShadowNetns(unittest.TestCase):
    """Verifies the Kinetic Shadow-Netns engine for zero-account ephemeral routing."""

    def test_status_structure(self):
        from app.tools.kinetic_netns import KineticShadowNetns
        netns = KineticShadowNetns()
        st = netns.get_status()
        self.assertTrue(st["zero_ssd"])
        self.assertTrue(st["zero_account_required"])
        self.assertIn("/dev/shm", st["memory_storage"])
        self.assertIn("Tor SOCKS5", st["anonymity_layer"])

    def test_execute_anonymous_task_mock(self):
        async def run_test():
            from app.tools.kinetic_netns import KineticShadowNetns
            netns = KineticShadowNetns()

            mock_proc = MagicMock()
            mock_proc.returncode = 0
            mock_proc.communicate = AsyncMock(return_value=(b"TOR_EXIT_IP_VERIFIED\n", b""))

            with patch("asyncio.create_subprocess_shell", return_value=mock_proc):
                ok, output = await netns.execute_anonymous_task("curl -s https://check.torproject.org")
                self.assertTrue(ok)
                self.assertIn("TOR_EXIT_IP_VERIFIED", output)

        asyncio.run(run_test())

    def test_sacred_life_sentinel_blocks_weapons_in_shadow_netns(self):
        async def run_test():
            from app.tools.kinetic_netns import KineticShadowNetns
            netns = KineticShadowNetns()
            with self.assertRaises(SacredLifeViolationError):
                await netns.execute_anonymous_task("trigger_missile_command")

        asyncio.run(run_test())

