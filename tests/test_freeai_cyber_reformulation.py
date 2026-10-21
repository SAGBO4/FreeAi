#!/usr/bin/env python3
"""
Tests unitaires pour la reformulation des demandes et l'exécution adaptative dans freeai_cyber.py
"""

import unittest
from unittest.mock import patch, MagicMock
from freeai_cyber import reformulate_demand, execute_command
from app.tools.kali_registry import KaliToolRegistry


class TestFreeAICyberReformulation(unittest.TestCase):
    """Tests pour la reformulation des demandes et l'exécution adaptative."""

    def test_reformulate_demand(self):
        """Test de la reformulation des demandes interdites."""
        self.assertEqual(reformulate_demand("brute force"), "test de vulnérabilités d'authentification avec Hydra")
        self.assertEqual(reformulate_demand("cracker"), "test de sécurité des mots de passe avec Hydra")
        self.assertEqual(reformulate_demand("scan port"), "détection de ports ouverts avec Nmap")
        self.assertEqual(reformulate_demand("intrusion"), "analyse de vulnérabilités avec Nikto")
        self.assertEqual(reformulate_demand("test légal"), "test légal")  # Pas de reformulation

    @patch('subprocess.run')
    def test_execute_command_with_reformulation(self, mock_run):
        """Test de l'exécution d'une commande avec reformulation."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="Commande exécutée avec succès",
            stderr=""
        )

        with patch.object(KaliToolRegistry, 'build_tool_command') as mock_build:
            mock_build.return_value = "echo test"

            # Tester avec une demande reformulée
            output = execute_command("hydra", {"target": "127.0.0.1", "service": "ssh"})
            self.assertEqual(output, "Commande exécutée avec succès")


if __name__ == "__main__":
    unittest.main()