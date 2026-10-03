"""Tests for Sudo Execution inside Docker Containers and Root Environments."""

import os
import unittest
from unittest.mock import patch, MagicMock

from app.tools.gateway import ToolGateway


class TestDockerSudoExecution(unittest.TestCase):
    def setUp(self):
        self.gateway = ToolGateway(
            workspace_root="/tmp",
            allow_network=True,
            allow_sudo=True,
            allow_global_read=True,
            allow_full_fs_access=True
        )

    def test_root_environment_with_sudo_binary(self):
        """Simulates container running as root with sudo installed."""
        with patch("os.geteuid", return_value=0), \
             patch("shutil.which", return_value="/usr/bin/sudo"), \
             patch("subprocess.run") as mock_run:

            mock_run.return_value = MagicMock(returncode=0, stdout="root\n", stderr="")
            res = self.gateway.execute_command("sudo whoami")

            self.assertTrue(res["success"])
            # Command should be executed with sudo -n
            called_cmd = mock_run.call_args[0][0]
            self.assertIn("sudo -n whoami", called_cmd)

    def test_root_environment_without_sudo_binary(self):
        """Simulates minimal container running as root without sudo binary installed."""
        with patch("os.geteuid", return_value=0), \
             patch("shutil.which", return_value=None), \
             patch("subprocess.run") as mock_run:

            mock_run.return_value = MagicMock(returncode=0, stdout="eth0\n", stderr="")
            res = self.gateway.execute_command("sudo ip link show")

            self.assertTrue(res["success"])
            # 'sudo ' should be stripped automatically so command runs natively as root
            called_cmd = mock_run.call_args[0][0]
            self.assertEqual(called_cmd, "ip link show")

    def test_dockerfile_and_compose_sudo_specifications(self):
        """Validates that Dockerfile and docker-compose.yml specify sudo and Linux capabilities."""
        with open("Dockerfile", "r", encoding="utf-8") as f:
            df_content = f.read()
        self.assertIn("sudo", df_content)
        self.assertIn("NOPASSWD: ALL", df_content)

        with open("docker-compose.yml", "r", encoding="utf-8") as f:
            dc_content = f.read()
        self.assertIn("SYS_ADMIN", dc_content)
        self.assertIn("NET_ADMIN", dc_content)
