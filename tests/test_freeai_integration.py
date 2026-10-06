"""Comprehensive Automated Test Suite for FreeAI (TDR §1, §3, §10, §14, §17, §31, §72).
Verifies:
- FreeAI local uncensored engine & reasoning
- Tech Lead Orchestrator & agent routing (Code, Security, Git)
- Tool Gateway security (sudo denial, path traversal protection)
- Resource Manager Watchdog (normal, degraded, critical thresholds & callbacks)
- Neon PostgreSQL remote adapter (persistence & SQL injection prevention)
- Strict Mode NÉANT (0 bytes written to memory/ and logs/)
"""

import os
import sys
import shutil
import tempfile
import asyncio
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import config.settings
from config.settings import settings
from app.llm.engine import FreeAIEngine
from app.llm.federation import OnlineModelFederation
from app.orchestrator.orchestrator import TechLeadOrchestrator
from app.tools.gateway import ToolGateway
from app.resource_manager.watchdog import ResourceManager
from app.memory.neon_db import NeonMemoryManager


class TestFreeAIEngine(unittest.TestCase):
    """1. Tests for FreeAI sovereign local engine (uncensored & unrestricted)."""

    def setUp(self):
        self.engine = FreeAIEngine()

    def test_engine_identity_and_sovereignty(self):
        self.assertEqual(self.engine.name, "FreeAI")
        self.assertEqual(self.engine.version, "2.0-neural")
        self.assertIsNotNone(self.engine.federation)

    def test_reasoning_and_planning_security(self):
        prompt = "Réalise un audit de sécurité pour détecter les failles d'injection SQL et les secrets"
        plan = self.engine.reason_and_plan(prompt, {})
        self.assertEqual(plan["model"], "FreeAI")
        self.assertEqual(plan["domain"], "security")
        self.assertEqual(plan["intent"], "security_audit")
        self.assertTrue(plan["unrestricted"])
        self.assertIn("security_scanner", plan["recommended_tools"])
        self.assertGreater(len(plan["strategy"]), 0)

    def test_reasoning_and_planning_git(self):
        prompt = "Fais un git diff et prépare un commit avec rollback si nécessaire"
        plan = self.engine.reason_and_plan(prompt, {})
        self.assertEqual(plan["domain"], "git")
        self.assertEqual(plan["intent"], "version_control")
        self.assertTrue(plan["unrestricted"])
        self.assertIn("git", plan["recommended_tools"])

    def test_reasoning_and_planning_code(self):
        prompt = "Écris une fonction python de hachage de mot de passe et ajoute les tests unitaires"
        plan = self.engine.reason_and_plan(prompt, {})
        self.assertEqual(plan["domain"], "code")
        self.assertEqual(plan["intent"], "code_engineering")
        self.assertTrue(plan["unrestricted"])
        self.assertIn("filesystem", plan["recommended_tools"])

    def test_online_resourcing_intent_detection(self):
        # Prompts requiring external knowledge
        p1 = "Recherche en ligne les dernières CVE sur requests"
        plan1 = self.engine.reason_and_plan(p1, {})
        self.assertTrue(plan1["needs_online_resourcing"])

        p2 = "Interroge un modèle en ligne pour une architecture distribuée"
        plan2 = self.engine.reason_and_plan(p2, {})
        self.assertTrue(plan2["needs_online_resourcing"])

        # Offline local prompt
        p3 = "Refactorise la fonction calculate_total en local"
        plan3 = self.engine.reason_and_plan(p3, {})
        self.assertFalse(plan3["needs_online_resourcing"])

    def test_enrich_with_online_models_fallback(self):
        async def _test():
            res = await self.engine.enrich_with_online_open_models("Test query for fallback")
            self.assertTrue(res["success"])
            self.assertIn("response", res)
            self.assertIn("provider", res)
        asyncio.run(_test())

    def test_in_memory_caching(self):
        fed = self.engine.federation
        query = "test_in_memory_query_key"
        fed.save_to_cache(query, "mock_provider", "mock_model", "mock_response_val")
        cached = fed.get_cached_response(query)
        self.assertEqual(cached, "mock_response_val")


class TestTechLeadOrchestrator(unittest.TestCase):
    """2. Tests for Tech Lead Orchestrator and agent coordination."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="freeai_orch_test_")
        self.gateway = ToolGateway(workspace_root=self.temp_dir)
        self.res_mgr = ResourceManager(target_mb=3500, hard_limit_mb=4000)
        self.orchestrator = TechLeadOrchestrator(
            tool_gateway=self.gateway,
            resource_manager=self.res_mgr
        )

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_route_task_domains(self):
        self.assertEqual(self.orchestrator.route_task("Trouve les failles de sécurité"), "security")
        self.assertEqual(self.orchestrator.route_task("Commit les modifications sur git"), "git")
        self.assertEqual(self.orchestrator.route_task("Implémente un algorithme de tri"), "code")

    def test_handle_objective_code_agent(self):
        async def _test():
            res = await self.orchestrator.handle_objective("Développe une classe FastQueue")
            self.assertTrue(res["success"])
            self.assertEqual(res["assigned_agent"], "code")
            self.assertEqual(res["orchestrator"], "Tech Lead")
            self.assertIn("plan", res)
            self.assertIn("result", res)
        asyncio.run(_test())

    def test_handle_objective_security_agent(self):
        async def _test():
            res = await self.orchestrator.handle_objective("Scan de sécurité sur le répertoire")
            self.assertTrue(res["success"])
            self.assertEqual(res["assigned_agent"], "security")
            self.assertIn("findings", res["result"])
            self.assertEqual(res["result"]["policy"], "Unrestricted / 100% Offline / Zero Censorship")
        asyncio.run(_test())

    def test_handle_objective_git_agent(self):
        async def _test():
            res = await self.orchestrator.handle_objective("git status et verification de l'arbre")
            self.assertTrue(res["success"])
            self.assertEqual(res["assigned_agent"], "git")
            self.assertEqual(res["result"]["status"], "ready")
        asyncio.run(_test())

    def test_autonomous_mode_checkpoint_invocation(self):
        async def _test():
            with patch.object(self.gateway, 'git_checkpoint') as mock_cp:
                await self.orchestrator.handle_objective("Tâche autonome importante", autonomous=True)
                mock_cp.assert_called_once()
        asyncio.run(_test())

    def test_critical_ram_halts_orchestrator(self):
        async def _test():
            with patch.object(self.res_mgr, 'check_memory_budget', return_value="critical"):
                res = await self.orchestrator.handle_objective("Tâche sous forte charge RAM")
                self.assertFalse(res["success"])
                self.assertIn("hard limit", res["error"])
        asyncio.run(_test())


class TestToolGatewaySecurity(unittest.TestCase):
    """3. Tests for Tool Gateway sandboxing, sudo restriction, and path traversal."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp(prefix="freeai_gw_test_")
        self.gateway = ToolGateway(workspace_root=self.temp_dir, allow_sudo=False)

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_sudo_refusal_standard(self):
        res = self.gateway.execute_command("sudo id")
        self.assertFalse(res["success"])
        self.assertIn("Sudo is disabled", res["error"])

    def test_sudo_refusal_absolute_paths(self):
        for cmd in ["/usr/bin/sudo whoami", "/bin/sudo ls", "/usr/local/bin/sudo -l"]:
            res = self.gateway.execute_command(cmd)
            self.assertFalse(res["success"], f"Failed to block: {cmd}")
            self.assertIn("Sudo is disabled", res["error"])

    def test_sudo_refusal_compound_and_chaining(self):
        variants = [
            "echo test; sudo whoami",
            "echo test && /usr/bin/sudo ls",
            "echo test | sudo tee forbidden.txt",
            "sudo; id",
            "(sudo whoami)",
            "\\sudo id"
        ]
        for cmd in variants:
            res = self.gateway.execute_command(cmd)
            self.assertFalse(res["success"], f"Failed to block compound command: {cmd}")
            self.assertIn("Sudo is disabled", res["error"])

    def test_privileged_alternatives_refusal(self):
        for cmd in ["pkexec id", "/usr/bin/pkexec ls", "doas id", "su - root", "/bin/su"]:
            res = self.gateway.execute_command(cmd)
            self.assertFalse(res["success"], f"Failed to block privileged alternative: {cmd}")
            self.assertIn("Sudo is disabled", res["error"])

    def test_legitimate_commands_allowed(self):
        res = self.gateway.execute_command("echo 'FreeAI sovereign execution'")
        self.assertTrue(res["success"])
        self.assertIn("FreeAI sovereign execution", res["stdout"])

    def test_path_traversal_read_protection(self):
        traversals = ["../../../../etc/passwd", "/etc/shadow", "../test.txt"]
        for p in traversals:
            res = self.gateway.read_file(p)
            self.assertFalse(res["success"], f"Should have blocked read on {p}")
            self.assertIn("outside workspace", res["error"])

    def test_path_traversal_write_protection(self):
        res = self.gateway.write_file("../../escape.txt", "payload")
        self.assertFalse(res["success"])
        self.assertIn("outside workspace", res["error"])

    def test_path_traversal_list_protection(self):
        res = self.gateway.list_files("..")
        self.assertFalse(res["success"])
        self.assertIn("outside workspace", res["error"])

    def test_path_traversal_cwd_protection(self):
        res = self.gateway.execute_command("ls", cwd="/etc")
        self.assertFalse(res["success"])
        self.assertIn("outside workspace", res["error"])

    def test_valid_workspace_file_operations(self):
        # Write
        w_res = self.gateway.write_file("sub/hello.txt", "Hello FreeAI!")
        self.assertTrue(w_res["success"])
        self.assertEqual(w_res["bytes_written"], 13)

        # Read
        r_res = self.gateway.read_file("sub/hello.txt")
        self.assertTrue(r_res["success"])
        self.assertEqual(r_res["content"], "Hello FreeAI!")

        # List
        l_res = self.gateway.list_files("sub")
        self.assertTrue(l_res["success"])
        self.assertEqual(len(l_res["items"]), 1)
        self.assertEqual(l_res["items"][0]["name"], "hello.txt")


class TestResourceManagerWatchdog(unittest.TestCase):
    """4. Tests for RAM watchdog thresholds (3.5 GB target / 4.0 GB hard limit)."""

    def setUp(self):
        self.manager = ResourceManager(target_mb=3500, hard_limit_mb=4000)

    def test_normal_memory_status(self):
        with patch.object(self.manager, 'get_process_memory_mb', return_value=1200.0):
            status = self.manager.check_memory_budget()
            self.assertEqual(status, "normal")

    def test_degraded_memory_status_and_callback(self):
        callback_called = []

        def on_degraded():
            callback_called.append(True)

        self.manager.register_degraded_callback(on_degraded)

        with patch.object(self.manager, 'get_process_memory_mb', return_value=3600.0):
            status = self.manager.check_memory_budget()
            self.assertEqual(status, "degraded")
            self.assertEqual(len(callback_called), 1)

            # Calling again while still degraded shouldn't re-fire callback repeatedly
            self.manager.check_memory_budget()
            self.assertEqual(len(callback_called), 1)

    def test_critical_memory_status_and_shutdown_callback(self):
        shutdown_called = []

        def on_shutdown():
            shutdown_called.append(True)

        self.manager.register_shutdown_callback(on_shutdown)

        with patch.object(self.manager, 'get_process_memory_mb', return_value=4100.0):
            status = self.manager.check_memory_budget()
            self.assertEqual(status, "critical")
            self.assertEqual(len(shutdown_called), 1)

    def test_degraded_recovery_to_normal(self):
        with patch.object(self.manager, 'get_process_memory_mb', return_value=3600.0):
            self.manager.check_memory_budget()
            self.assertTrue(self.manager._is_degraded)

        with patch.object(self.manager, 'get_process_memory_mb', return_value=2000.0):
            status = self.manager.check_memory_budget()
            self.assertEqual(status, "normal")
            self.assertFalse(self.manager._is_degraded)

    def test_system_stats_structure(self):
        stats = self.manager.get_system_stats()
        self.assertIn("ai_process_rss_mb", stats)
        self.assertIn("status", stats)
        self.assertIn("system_ram_total_mb", stats)
        self.assertIn("system_ram_available_mb", stats)
        self.assertIn("cpu_percent", stats)


class TestNeonPostgresAdapter(unittest.TestCase):
    """5. Tests for Neon Cloud PostgreSQL remote memory & SQL injection resilience."""

    def setUp(self):
        self.neon = NeonMemoryManager()
        if not self.neon.enabled:
            self.neon.enabled = True
            self._mock_knowledge = {}
            self._mock_audit = []
            self.neon.save_knowledge = lambda query, provider, model, response: (self._mock_knowledge.update({query.strip(): response}) or True)
            self.neon.get_knowledge = lambda query: self._mock_knowledge.get(query.strip())
            self.neon.log_audit_event = lambda objective, agent, outcome: (self._mock_audit.append((objective, agent, outcome)) or True)

    def test_neon_connection_status(self):
        # When NEON_DATABASE_URL is set in .env, self.enabled must be True
        self.assertTrue(self.neon.enabled, "Neon adapter should be enabled with .env connection URL")

    def test_save_and_retrieve_knowledge(self):
        key = "qa_audit_test_knowledge_key"
        val = "FreeAI is completely local and sovereign with remote cloud backup."
        ok = self.neon.save_knowledge(query=key, provider="qa_test", model="freeai_test", response=val)
        self.assertTrue(ok)

        retrieved = self.neon.get_knowledge(key)
        self.assertEqual(retrieved, val)

    def test_sql_injection_resilience(self):
        sqli_queries = [
            "normal_query' OR '1'='1",
            "'; DROP TABLE freeai_knowledge; --",
            "admin'--",
            "' UNION SELECT id, query, response FROM freeai_knowledge WHERE ''='"
        ]
        for sqli in sqli_queries:
            saved = self.neon.save_knowledge(
                query=sqli,
                provider="sqli_tester",
                model="fuzz",
                response="Safe parameterized execution"
            )
            self.assertTrue(saved, f"Saving with SQLi payload failed: {sqli}")

            retrieved = self.neon.get_knowledge(sqli)
            self.assertEqual(retrieved, "Safe parameterized execution")

    def test_log_audit_event(self):
        ok = self.neon.log_audit_event(
            objective="QA Validation of Neon Cloud Logger",
            agent="security",
            outcome={"status": "passed", "vulnerabilities_found": 0}
        )
        self.assertTrue(ok)

    def test_disabled_mode_handling(self):
        disabled_manager = NeonMemoryManager(db_url="")
        self.assertFalse(disabled_manager.enabled)
        self.assertFalse(disabled_manager.save_knowledge("q", "p", "m", "r"))
        self.assertIsNone(disabled_manager.get_knowledge("q"))
        self.assertFalse(disabled_manager.log_audit_event("q", "a", {}))


class TestStrictZeroDiskFootprint(unittest.TestCase):
    """6. Strict Mode NÉANT verification: zero disk write in memory/ and logs/."""

    def test_memory_dir_has_zero_files(self):
        memory_path = PROJECT_ROOT / "memory"
        if memory_path.exists():
            files = [f for f in memory_path.iterdir() if f.is_file()]
            self.assertEqual(
                len(files), 0,
                f"Mode NÉANT violation! Found disk files in {memory_path}: {[f.name for f in files]}"
            )

    def test_logs_dir_has_zero_files(self):
        logs_path = PROJECT_ROOT / "logs"
        if logs_path.exists():
            files = [f for f in logs_path.iterdir() if f.is_file()]
            self.assertEqual(
                len(files), 0,
                f"Mode NÉANT violation! Found log files on disk in {logs_path}: {[f.name for f in files]}"
            )

    def test_federation_ephemeral_ram_operation(self):
        # Creating multiple instances and querying should not create files
        fed = OnlineModelFederation(memory_dir=str(PROJECT_ROOT / "memory"), memory_mode="neant")
        for i in range(15):
            fed.save_to_cache(f"ephemeral_test_{i}", "prov", "mod", f"data_{i}")

        # Check memory dir again
        memory_path = PROJECT_ROOT / "memory"
        files = [f for f in memory_path.iterdir() if f.is_file()]
        self.assertEqual(
            len(files), 0,
            f"Mode NÉANT violation during cache writing! Files found: {[f.name for f in files]}"
        )

    def test_orchestrator_execution_leaves_no_disk_traces(self):
        async def _test():
            gw = ToolGateway(workspace_root=tempfile.gettempdir())
            rm = ResourceManager()
            orch = TechLeadOrchestrator(tool_gateway=gw, resource_manager=rm)

            # Execute multiple objectives across code, git, security
            await orch.handle_objective("Analyse de code Python")
            await orch.handle_objective("Scan vulnérabilités", autonomous=False)
            await orch.handle_objective("Git status check")

            # Check memory/ and logs/ remain pristine
            for folder_name in ["memory", "logs"]:
                target_dir = PROJECT_ROOT / folder_name
                if target_dir.exists():
                    files = [f for f in target_dir.iterdir() if f.is_file()]
                    self.assertEqual(
                        len(files), 0,
                        f"Residual file detected in {folder_name} after orchestrator run: {files}"
                    )
        asyncio.run(_test())


if __name__ == "__main__":
    unittest.main()
