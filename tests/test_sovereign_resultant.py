#!/usr/bin/env python3
"""
Test Suite for Feature F-31: The Sovereign Resultant Engine (SRE).
Spec: docs/SPEC.md (Section 4, AC1 to AC5).

Forge Stage: Tests First (RED before GREEN).
Verifies:
- AC1: Threat Sentinel (IP/ASN inspection, Tor exit node classification, E.164 phone numbering).
- AC2: Stealth Conduit (SOCKS5/Tor auto-detection, seamless fallback to direct egress).
- AC3: Hermes Multi-Target Security Auditor (Local, Staging, and Remote APIs, header audit, CORS, remediation).
- AC4: Sovereign Resultant Synthesis (Unified orchestrator coordination in volatile RAM).
- AC5: Zero-Simulation & Resilience under breakage (Socket checks, HTTP 5xx failover, clean telemetry).
"""

import os
import unittest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock

from app.tools.threat_sentinel import ThreatSentinel, IPReputationReport
from app.network.stealth_conduit import StealthConduit, ConduitStatus
from app.cognition.hermes_auditor import HermesAuditor, AuditReport, RemediationPatch
from app.orchestrator.sovereign_resultant import SovereignResultantEngine, ResultantReport


class TestThreatSentinel(unittest.TestCase):
    def setUp(self):
        self.sentinel = ThreatSentinel()

    def test_ac1_ip_and_tor_exit_classification(self):
        """AC1: ThreatSentinel parses IP, classifies Tor exit nodes vs standard IPs."""
        # Simulated Tor exit node IP and clean IP
        tor_exit_ip = "185.220.101.5"
        clean_ip = "8.8.8.8"

        mock_tor_list = "185.220.101.5\n185.220.101.6\n185.220.101.7"
        with patch.object(self.sentinel, "_fetch_tor_exit_nodes", return_value=mock_tor_list.splitlines()):
            rep_tor = self.sentinel.inspect_ip(tor_exit_ip)
            self.assertTrue(rep_tor.is_tor_exit_node)
            self.assertIn("Tor Exit Node", rep_tor.tags)

            rep_clean = self.sentinel.inspect_ip(clean_ip)
            self.assertFalse(rep_clean.is_tor_exit_node)
            self.assertNotIn("Tor Exit Node", rep_clean.tags)

    def test_ac1_phone_e164_validation(self):
        """AC1: ThreatSentinel validates international phone numbering syntax under E.164."""
        valid_res = self.sentinel.validate_phone_e164("+33612345678")
        self.assertTrue(valid_res["valid"])
        self.assertEqual(valid_res["country_code"], "FR")

        invalid_res = self.sentinel.validate_phone_e164("not-a-number")
        self.assertFalse(invalid_res["valid"])

    def test_ac1_malformed_and_private_ip_handling(self):
        """AC1: ThreatSentinel handles malformed IP syntax and private RFC1918 addresses."""
        malformed = self.sentinel.inspect_ip("999.999.999.999")
        self.assertEqual(malformed.reputation_score, 0.0)
        self.assertIn("Malformed-IP", malformed.tags)
        self.assertIn("Invalid IP address syntax", malformed.details.get("error", ""))

        private_v4 = self.sentinel.inspect_ip("192.168.1.1")
        self.assertTrue(private_v4.is_private)
        self.assertEqual(private_v4.reputation_score, 1.0)
        self.assertIn("Local/Private", private_v4.tags)

        loopback_v6 = self.sentinel.inspect_ip("::1")
        self.assertTrue(loopback_v6.is_private)
        self.assertIn("Local/Private", loopback_v6.tags)

    def test_ac1_tor_fetch_failure_resilience(self):
        """AC1: ThreatSentinel handles live Tor bulk exit node fetch failure gracefully."""
        with patch.object(self.sentinel, "_fetch_tor_exit_nodes", return_value=[]):
            self.sentinel._cached_tor_exits = None
            rep = self.sentinel.inspect_ip("8.8.8.8")
            self.assertFalse(rep.is_tor_exit_node)
            self.assertEqual(len(self.sentinel.get_tor_exit_nodes()), 0)



class TestStealthConduit(unittest.TestCase):
    def setUp(self):
        self.conduit = StealthConduit(tor_host="127.0.0.1", tor_port=9050)

    def test_ac2_tor_status_detection_and_fallback(self):
        """AC2: StealthConduit probes SOCKS5 port; falls back cleanly if inactive."""
        # Scenario A: Inactive Tor port -> fallback to direct
        with patch.object(self.conduit, "_probe_socks5_port", return_value=False):
            status = self.conduit.get_conduit_status()
            self.assertFalse(status.tor_available)
            self.assertEqual(status.active_mode, "direct")

        # Scenario B: Active Tor port -> uses SOCKS5
        with patch.object(self.conduit, "_probe_socks5_port", return_value=True):
            status_tor = self.conduit.get_conduit_status()
            self.assertTrue(status_tor.tor_available)
            self.assertEqual(status_tor.active_mode, "socks5_tor")

    def test_ac2_request_execution_with_fallback(self):
        """AC2: StealthConduit executes async HTTP request via direct fallback without crash."""
        async def _test():
            with patch.object(self.conduit, "_probe_socks5_port", return_value=False), \
                 patch("httpx.AsyncClient.request", new_callable=AsyncMock) as mock_req:
                mock_resp = MagicMock(status_code=200, text="OK", is_success=True)
                mock_req.return_value = mock_resp

                res = await self.conduit.fetch_url("https://example.com/api/test")
                self.assertTrue(res["success"])
                self.assertEqual(res["mode_used"], "direct")
                self.assertEqual(res["status_code"], 200)

        asyncio.run(_test())

    def test_ac2_direct_connection_error_resilience(self):
        """AC2: StealthConduit catches transport exceptions cleanly without unhandled crash."""
        async def _test():
            with patch.object(self.conduit, "_probe_socks5_port", return_value=False), \
                 patch("httpx.AsyncClient.request", side_effect=Exception("Network is unreachable")):
                res = await self.conduit.fetch_url("http://192.0.2.1:8080")
                self.assertFalse(res["success"])
                self.assertEqual(res["mode_used"], "direct_error")
                self.assertIn("Network is unreachable", res["error"])

        asyncio.run(_test())


class TestHermesMultiTargetAuditor(unittest.TestCase):
    def setUp(self):
        self.auditor = HermesAuditor()

    def test_ac3_audit_security_headers_and_cors(self):
        """AC3: HermesAuditor checks headers (HSTS, CSP, X-Frame-Options) and permissive CORS."""
        # Mock HTTP response with missing headers and CORS wildcard
        mock_headers = {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Server": "Uvicorn/0.30.0"
        }

        async def _test():
            with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
                mock_resp = MagicMock(
                    status_code=200,
                    headers=mock_headers,
                    text='{"status": "ok"}',
                    is_success=True
                )
                mock_get.return_value = mock_resp

                report = await self.auditor.audit_target("https://api.staging.example.com")
                self.assertIsInstance(report, AuditReport)
                self.assertEqual(report.target_url, "https://api.staging.example.com")
                self.assertFalse(report.has_hsts)
                self.assertFalse(report.has_csp)
                self.assertTrue(report.permissive_cors)
                self.assertGreater(len(report.remediations), 0)

        asyncio.run(_test())

    def test_ac3_remote_and_local_url_support(self):
        """AC3: HermesAuditor accepts both local URLs and remote/staging/bug-bounty URLs."""
        valid_local = self.auditor.validate_target_url("http://localhost:8000/v1/health")
        valid_docker = self.auditor.validate_target_url("http://coordinator:8000")
        valid_remote = self.auditor.validate_target_url("https://api.production-domain.org/api")
        invalid_url = self.auditor.validate_target_url("ftp://unsupported-scheme.com")

        self.assertTrue(valid_local)
        self.assertTrue(valid_docker)
        self.assertTrue(valid_remote)
        self.assertFalse(invalid_url)


class TestSovereignResultantEngine(unittest.TestCase):
    def setUp(self):
        self.engine = SovereignResultantEngine()

    def test_ac4_full_resultant_pipeline_synthesis(self):
        """AC4: Unified pipeline executes ThreatSentinel, StealthConduit & HermesAuditor in RAM."""
        async def _test():
            with patch.object(self.engine.threat_sentinel, "inspect_ip") as mock_inspect_ip, \
                 patch.object(self.engine.hermes_auditor, "audit_target") as mock_audit:

                mock_inspect_ip.return_value = IPReputationReport(
                    ip="192.168.1.50",
                    is_tor_exit_node=False,
                    reputation_score=1.0,
                    tags=["Local/Private"]
                )
                mock_audit.return_value = AuditReport(
                    target_url="http://127.0.0.1:8000",
                    status_code=200,
                    has_hsts=True,
                    has_csp=True,
                    permissive_cors=False,
                    remediations=[]
                )

                result = await self.engine.execute_resultant_mission(
                    target_url="http://127.0.0.1:8000",
                    target_ip="192.168.1.50"
                )

                self.assertIsInstance(result, ResultantReport)
                self.assertTrue(result.success)
                self.assertIn("threat_intel", result.to_dict())
                self.assertIn("security_audit", result.to_dict())
                self.assertIn("stealth_conduit", result.to_dict())

        asyncio.run(_test())

    def test_ac5_resilience_under_target_timeout(self):
        """AC5: Remote target timeout or connection failure returns clean structured report."""
        async def _test():
            with patch("httpx.AsyncClient.get", side_effect=Exception("Connection timed out")):
                report = await self.engine.hermes_auditor.audit_target("https://unreachable-staging.corp")
                self.assertIsInstance(report, AuditReport)
                self.assertFalse(report.reachable)
                self.assertIn("Connection timed out", report.error_message)

        asyncio.run(_test())

    def test_ac5_empty_mission_resilience(self):
        """AC5: Executing mission with all None targets returns clean report without exceptions."""
        async def _test():
            report = await self.engine.execute_resultant_mission()
            self.assertIsInstance(report, ResultantReport)
            self.assertTrue(report.success)
            self.assertIn("Egress routing mode", report.summary)

        asyncio.run(_test())

    def test_ac5_invalid_url_scheme_resilience(self):
        """AC5: Reject unsupported URL schemes (ftp, smb, file) cleanly without crash."""
        async def _test():
            report = await self.engine.hermes_auditor.audit_target("ftp://unsupported.domain.org")
            self.assertIsInstance(report, AuditReport)
            self.assertFalse(report.reachable)
            self.assertIn("Invalid URL", report.error_message)

        asyncio.run(_test())

    def test_ac6_tech_lead_orchestrator_integration(self):
        """AC6: TechLeadOrchestrator routes 'la resultante' to SovereignResultantEngine."""
        from app.orchestrator.orchestrator import TechLeadOrchestrator
        from app.tools.gateway import ToolGateway
        from app.resource_manager.watchdog import ResourceManager

        async def _test():
            gw = ToolGateway(workspace_root="/tmp")
            rm = ResourceManager()
            orch = TechLeadOrchestrator(tool_gateway=gw, resource_manager=rm)

            with patch.object(orch.sovereign_resultant, "execute_resultant_mission", new_callable=AsyncMock) as mock_mission:
                mock_mission.return_value = ResultantReport(
                    mission_id="sre-test-123",
                    success=True,
                    summary="Threat intelligence analyzed; Security audit completed"
                )

                res = await orch.handle_objective("Exécute la resultante sur le projet")
                self.assertTrue(res["success"])
                self.assertEqual(res["assigned_agent"], "sovereign_resultant")
                self.assertIn("Threat intelligence analyzed", res["output"])
                mock_mission.assert_called_once()

        asyncio.run(_test())


if __name__ == "__main__":
    unittest.main()
