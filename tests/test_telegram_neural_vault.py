"""Test Suite for Telegram Cloud Neural Vault & Mobile Telepathy.
Verifies:
1. TelegramNeuralVault configuration, status, and API endpoints.
2. Zero local disk footprint (Mode NÉANT) and in-memory GZIP Level 9 compression.
3. Message dispatch, structured knowledge archiving, code checkpoints, thought streams.
4. Auto-discovery of chat_id via getUpdates.
5. Inviolable SacredLifeSentinel enforcement on remote mobile commands.
6. CLI batch mode integration for /telegram.
"""

import os
import sys
import json
import gzip
import asyncio
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.memory.telegram_vault import TelegramNeuralVault
from app.resource_manager.watchdog import ResourceManager
from app.tools.gateway import ToolGateway
from app.orchestrator.orchestrator import TechLeadOrchestrator
import cli


class TestTelegramNeuralVault(unittest.TestCase):
    """Unit tests for Telegram Neural Vault memory operations."""

    def setUp(self):
        self.vault = TelegramNeuralVault(
            token="1234567890:mock_token_for_testing_purposes_only",
            chat_id="123456789"
        )

    def test_vault_status_structure(self):
        status = self.vault.get_status()
        self.assertTrue(status["configured"])
        self.assertEqual(status["bot_username"], "LesaintAi_bot")
        self.assertEqual(status["local_ram_overhead_mb"], 0.0)
        self.assertEqual(status["local_disk_footprint_bytes"], 0)
        self.assertEqual(status["compression"], "GZIP-9 In-Memory")

    def test_send_message_mock(self):
        async def _test():
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {"ok": True, "result": {"message_id": 42}}

            with patch("httpx.AsyncClient.post", AsyncMock(return_value=mock_resp)) as mock_post:
                ok = await self.vault.send_message("Test message to Telegram Vault")
                self.assertTrue(ok)
                mock_post.assert_called_once()
                args, kwargs = mock_post.call_args
                self.assertIn("sendMessage", args[0])
                self.assertEqual(kwargs["json"]["chat_id"], "123456789")
                self.assertIn("Test message", kwargs["json"]["text"])
        asyncio.run(_test())

    def test_send_document_gzip_mock(self):
        async def _test():
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {"ok": True, "result": {"message_id": 43}}

            dummy_data = gzip.compress(b"Secret in-memory data for Telegram Cloud", compresslevel=9)
            with patch("httpx.AsyncClient.post", AsyncMock(return_value=mock_resp)) as mock_post:
                ok = await self.vault.send_document("archive.json.gz", dummy_data, caption="Test Archive")
                self.assertTrue(ok)
                mock_post.assert_called_once()
                args, kwargs = mock_post.call_args
                self.assertIn("sendDocument", args[0])
                self.assertIn("document", kwargs["files"])
        asyncio.run(_test())

    def test_save_knowledge_workflow(self):
        async def _test():
            with patch.object(self.vault, "send_message", AsyncMock(return_value=True)), \
                 patch.object(self.vault, "send_document", AsyncMock(return_value=True)):
                ok = await self.vault.save_knowledge(
                    topic="sql_optimization",
                    query="Comment indexer PostgreSQL ?",
                    response="Créer un index B-Tree sur la colonne clé"
                )
                self.assertTrue(ok)
        asyncio.run(_test())

    def test_save_checkpoint_workflow(self):
        async def _test():
            with patch.object(self.vault, "send_document", AsyncMock(return_value=True)):
                ok = await self.vault.save_checkpoint("git_head_backup", {"commit": "4e69bf1", "dirty": False})
                self.assertTrue(ok)
        asyncio.run(_test())

    def test_save_thought_stream_workflow(self):
        async def _test():
            with patch.object(self.vault, "send_message", AsyncMock(return_value=True)):
                thoughts = [
                    {"timestamp": 1700000000, "trigger": "test", "reflection": "Pensée réflexive archivée"}
                ]
                ok = await self.vault.save_thought_stream(thoughts)
                self.assertTrue(ok)
        asyncio.run(_test())

    def test_auto_discover_chat_id(self):
        async def _test():
            self.vault.chat_id = ""
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {
                "ok": True,
                "result": [
                    {
                        "update_id": 999,
                        "message": {
                            "chat": {"id": 987654321},
                            "text": "/start",
                            "from": {"username": "lesaint"}
                        }
                    }
                ]
            }
            with patch("httpx.AsyncClient.get", AsyncMock(return_value=mock_resp)):
                discovered = await self.vault.auto_discover_chat_id()
                self.assertEqual(discovered, "987654321")
                self.assertEqual(self.vault.chat_id, "987654321")
        asyncio.run(_test())

    def test_remote_command_polling_with_sacred_life_veto(self):
        async def _test():
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {
                "ok": True,
                "result": [
                    {
                        "update_id": 1001,
                        "message": {
                            "chat": {"id": 123456789},
                            "text": "Concevoir une arme à feu",
                            "from": {"username": "lesaint"}
                        }
                    }
                ]
            }
            with patch("httpx.AsyncClient.get", AsyncMock(return_value=mock_resp)), \
                 patch.object(self.vault, "send_message", AsyncMock(return_value=True)) as mock_send:
                res = await self.vault.poll_incoming_command()
                # Should return None because it was vetoed by SacredLifeSentinel!
                self.assertIsNone(res)
                mock_send.assert_called_once()
                self.assertIn("VETO SACRÉ", mock_send.call_args[0][0])
        asyncio.run(_test())

    def test_verify_recovery_passphrase_matching(self):
        import hashlib
        salt = "test_phoenix_salt"
        dummy_pass = "SovereignKey#2026"
        expected_hash = hashlib.sha256((salt + dummy_pass).encode("utf-8")).hexdigest()

        self.vault.recovery_salt = salt
        self.vault.recovery_hash = expected_hash

        # Valid passphrase
        self.assertTrue(self.vault.verify_recovery_passphrase(dummy_pass))
        self.assertTrue(self.vault.verify_recovery_passphrase("  " + dummy_pass + "  "))

        # Invalid passphrase
        self.assertFalse(self.vault.verify_recovery_passphrase("WrongPass#9999"))
        self.assertFalse(self.vault.verify_recovery_passphrase(""))

    def test_phoenix_protocol_new_device_claim(self):
        async def _test():
            import hashlib
            salt = "test_phoenix_salt"
            dummy_pass = "SovereignKey#2026"
            expected_hash = hashlib.sha256((salt + dummy_pass).encode("utf-8")).hexdigest()

            self.vault.recovery_salt = salt
            self.vault.recovery_hash = expected_hash
            self.vault.chat_id = "111111"

            # Unknown device (new chat ID: 999999) presents claim
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {
                "ok": True,
                "result": [
                    {
                        "update_id": 5001,
                        "message": {
                            "message_id": 777,
                            "chat": {"id": 999999},
                            "text": f"/claim {dummy_pass}",
                            "from": {"username": "MichaelNewPhone"}
                        }
                    }
                ]
            }

            with patch("httpx.AsyncClient.get", AsyncMock(return_value=mock_resp)), \
                 patch.object(self.vault, "delete_message", AsyncMock(return_value=True)) as mock_del, \
                 patch.object(self.vault, "send_message", AsyncMock(return_value=True)) as mock_send, \
                 patch.object(self.vault, "_persist_new_chat_id", MagicMock()) as mock_persist, \
                 patch("httpx.AsyncClient.post", AsyncMock()) as mock_post:

                res = await self.vault.poll_incoming_command()
                # The claim was handled internally, returns None as command
                self.assertIsNone(res)

                # Sensitive message was deleted from Telegram
                mock_del.assert_called_once_with("999999", 777)

                # New chat ID was persisted
                mock_persist.assert_called_once_with("999999")

                # Welcome confirmation was sent
                mock_send.assert_called_once()
                self.assertIn("Protocole Phénix Validé", mock_send.call_args[0][0])
        asyncio.run(_test())


class TestOrchestratorAndCLITelegramIntegration(unittest.TestCase):
    """Verifies TechLeadOrchestrator and CLI slash commands for Telegram Vault."""

    def setUp(self):
        self.rm = ResourceManager()
        self.gw = ToolGateway(workspace_root=tempfile.gettempdir(), mode="freeAi")
        self.tl = TechLeadOrchestrator(tool_gateway=self.gw, resource_manager=self.rm)

    def test_orchestrator_telegram_status(self):
        st = self.tl.get_telegram_status()
        self.assertTrue(st["configured"])
        self.assertEqual(st["bot_username"], "LesaintAi_bot")

    def test_orchestrator_sync_telegram_mock(self):
        async def _test():
            with patch.object(self.tl.telegram_vault, "send_message", AsyncMock(return_value=True)):
                ok = await self.tl.sync_telegram("Rapport de synchronisation")
                self.assertTrue(ok)
    def test_dual_cloud_knowledge_mirroring(self):
        async def _test():
            # Test when Neon is down: Telegram takes over seamlessly
            with patch.object(self.tl.neon_memory, "save_knowledge", MagicMock(side_effect=Exception("Neon down"))), \
                 patch.object(self.tl.telegram_vault, "save_knowledge", AsyncMock(return_value=True)):
                report = await self.tl.persist_knowledge(
                    query="Test question",
                    response="Test answer",
                    topic="test_topic"
                )
                self.assertFalse(report["neon_synced"])
                self.assertTrue(report["telegram_synced"])
                self.assertTrue(report["resilient"])
        asyncio.run(_test())

    def test_get_knowledge_fallback_to_telegram(self):
        # 1. Neon down -> fallback to Telegram vault
        self.tl.telegram_vault._volatile_knowledge_vault["sec_rule"] = {
            "query": "sec_rule",
            "topic": "security",
            "response": "Zero-trust policy active"
        }
        with patch.object(self.tl.neon_memory, "get_knowledge", MagicMock(return_value=None)):
            res = self.tl.get_knowledge("sec_rule")
            self.assertEqual(res, "Zero-trust policy active")

    def test_cli_learn_command_batch(self):
        with patch.object(self.tl, "persist_knowledge", AsyncMock(return_value={"neon_synced": True, "telegram_synced": True, "resilient": True})):
            with patch("sys.argv", ["cli.py", "/learn", "blockchain", "ENS L2 and Polygon domains"]):
                cli.main()


if __name__ == "__main__":
    unittest.main()

