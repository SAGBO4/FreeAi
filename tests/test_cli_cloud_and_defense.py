"""Tests for /defense and /cloud CLI commands and integration."""

import asyncio
import unittest
from unittest.mock import MagicMock, AsyncMock, patch

import cli
from app.orchestrator.orchestrator import TechLeadOrchestrator


class TestCLICloudAndDefense(unittest.TestCase):
    def setUp(self):
        self.mock_gateway = MagicMock()
        self.mock_gateway.mode = "freeAi"
        self.mock_gateway.allow_sudo = False
        self.mock_gateway.allow_network = True
        self.mock_gateway.fortress = MagicMock()
        self.mock_gateway.fortress.audit_prompt_injection.return_value = (True, "OK")
        self.mock_gateway.fortress.audit_command.return_value = (True, "OK")

        self.mock_vault = MagicMock()
        self.mock_vault.send_message = AsyncMock(return_value=True)

        self.mock_res = MagicMock()
        self.mock_res.register_degraded_callback = MagicMock()
        self.mock_res.register_shutdown_callback = MagicMock()
        self.mock_res.check_memory_budget.return_value = "normal"
        self.mock_res.get_system_stats.return_value = {}

        self.tech_lead = MagicMock()
        self.tech_lead.mode = "freeAi"
        self.tech_lead.tool_gateway = self.mock_gateway
        self.tech_lead.telegram_vault = self.mock_vault

        from app.cluster.free_cloud_pool import FreeCloudPool
        from app.security.active_defense import ActiveDefenseSentinel
        self.tech_lead.free_cloud_pool = FreeCloudPool(mode="freeAi")
        self.tech_lead.active_defense = ActiveDefenseSentinel(
            sovereign_fortress=self.mock_gateway.fortress,
            telegram_vault=self.mock_vault,
            cloud_pool=self.tech_lead.free_cloud_pool
        )

    def test_slash_commands_contain_defense_and_cloud(self):
        self.assertIn("/defense", cli.SLASH_COMMANDS)
        self.assertIn("/defense status", cli.SLASH_COMMANDS)
        self.assertIn("/cloud", cli.SLASH_COMMANDS)
        self.assertIn("/cloud list", cli.SLASH_COMMANDS)

    def test_run_defense_status(self):
        async def _run():
            with patch("cli.console.print") as mock_print:
                await cli.run_defense(self.tech_lead, ["status"])
                self.assertTrue(mock_print.called)
        asyncio.run(_run())

    def test_run_defense_ban_and_unban(self):
        async def _run():
            await cli.run_defense(self.tech_lead, ["ban", "10.0.0.99", "600"])
            self.assertTrue(self.tech_lead.active_defense.is_ip_banned("10.0.0.99"))

            await cli.run_defense(self.tech_lead, ["unban", "10.0.0.99"])
            self.assertFalse(self.tech_lead.active_defense.is_ip_banned("10.0.0.99"))
        asyncio.run(_run())

    def test_run_defense_test_simulation(self):
        async def _run():
            with patch("cli.console.print") as mock_print:
                await cli.run_defense(self.tech_lead, ["test", "198.51.100.77"])
                self.assertTrue(mock_print.called)
                self.assertTrue(self.tech_lead.active_defense.is_ip_banned("198.51.100.77"))
                self.assertTrue(self.mock_vault.send_message.called)
        asyncio.run(_run())

    def test_run_defense_incidents(self):
        async def _run():
            with patch("cli.console.print") as mock_print:
                await cli.run_defense(self.tech_lead, ["incidents"])
                self.assertTrue(mock_print.called)
        asyncio.run(_run())

    def test_run_defense_mirage(self):
        async def _run():
            with patch("cli.console.print") as mock_print:
                # 1. When empty
                await cli.run_defense(self.tech_lead, ["mirage"])
                self.assertTrue(mock_print.called)

                # 2. When trap engaged
                from app.security.active_defense import AttackVector
                await self.tech_lead.active_defense.defend_against_attack(
                    source_ip="198.51.100.222",
                    attack_vector=AttackVector.BRUTE_FORCE,
                    details="Simulated attack"
                )
                await cli.run_defense(self.tech_lead, ["mirage"])
                self.assertTrue(mock_print.called)
        asyncio.run(_run())


    def test_run_cloud_list(self):
        async def _run():
            with patch("cli.console.print") as mock_print:
                await cli.run_cloud(self.tech_lead, ["list"])
                self.assertTrue(mock_print.called)
        asyncio.run(_run())

    def test_run_cloud_ping(self):
        async def _run():
            with patch("cli.console.print") as mock_print:
                await cli.run_cloud(self.tech_lead, ["ping"])
                self.assertTrue(mock_print.called)
        asyncio.run(_run())

    def test_run_cloud_add_and_dispatch(self):
        async def _run():
            with patch("cli.console.print") as mock_print:
                await cli.run_cloud(self.tech_lead, ["add", "NodeOracle1", "oracle_cloud", "10.10.10.1"])
                self.assertTrue(mock_print.called)

                await cli.run_cloud(self.tech_lead, ["dispatch", "neural_train"])
                self.assertTrue(mock_print.called)
        asyncio.run(_run())
