#!/usr/bin/env python3
"""
Tests unitaires pour les fonctionnalités liées à KaliToolRegistry et HermesScratchpadEngine.
"""

import sys
import os
import shutil
import unittest
from unittest.mock import patch
from app.tools.kali_registry import KaliToolRegistry
from app.cognition.hermes_scratchpad import HermesScratchpadEngine

# Ajout du répertoire parent au sys.path pour importer correctement les modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestFreeAICyber(unittest.TestCase):
    """Tests pour les fonctionnalités liées à KaliToolRegistry et HermesScratchpadEngine"""

    def setUp(self):
        self.registry = KaliToolRegistry()
        self.hermes_engine = HermesScratchpadEngine()

    def test_get_installed_tools(self):
        """Test de la détection des outils installés."""
        installed_tools = self.registry.get_installed_tools()
        self.assertTrue(len(installed_tools) > 0, "Aucun outil Kali détecté.")

    def test_get_hermes_tool_schemas(self):
        """Test de la génération des schémas d'outils (sqlmap forcé présent : sa détection
        réelle dépend du binaire installé sur l'hôte, absent sur un runner CI propre)."""
        real_which = shutil.which

        def fake_which(cmd, *args, **kwargs):
            if cmd == "sqlmap":
                return "/usr/bin/sqlmap"
            return real_which(cmd, *args, **kwargs)

        with patch("app.tools.kali_registry.shutil.which", side_effect=fake_which):
            schemas = self.registry.get_hermes_tool_schemas()

        self.assertTrue(len(schemas) > 0, "Aucun schéma d'outil généré.")
        self.assertTrue(any(schema["name"] == "kali_sqlmap" for schema in schemas), "Le schéma pour kali_sqlmap n'est pas trouvé.")

    def test_hermes_thinking_scratchpad(self):
        """Test de la génération de réflexion dans le scratchpad."""
        scratchpad = self.hermes_engine.formulate_thought_scratchpad("Test audit de sécurité")
        self.assertIsNotNone(scratchpad, "Le scratchpad de réflexion est vide.")
        self.assertIn("thinking", scratchpad, "Le champ 'thinking' est manquant.")
        self.assertIn("tool_call", scratchpad, "Le champ 'tool_call' est manquant.")

    def test_kali_tool_command_building(self):
        """Test de la construction de commandes pour les outils Kali."""
        with patch.object(self.registry, "get_installed_tools", return_value={"sqlmap": "/usr/bin/sqlmap"}):
            command = self.registry.build_tool_command("sqlmap", {"target_url": "http://example.com"})
            self.assertIsNotNone(command, "La commande pour sqlmap n'a pas été construite.")
            self.assertIn("sqlmap", command, "La commande ne contient pas sqlmap.")

    def test_kali_tool_availability(self):
        """Test de la disponibilité des outils (sqlmap forcé présent : sa détection réelle
        dépend du binaire installé sur l'hôte, absent sur un runner CI propre)."""
        self.assertFalse(self.registry.is_tool_available("nonexistent_tool"), "L'outil inexistant est considéré comme disponible.")

        real_which = shutil.which

        def fake_which(cmd, *args, **kwargs):
            if cmd == "sqlmap":
                return "/usr/bin/sqlmap"
            return real_which(cmd, *args, **kwargs)

        with patch("app.tools.kali_registry.shutil.which", side_effect=fake_which):
            self.assertTrue(self.registry.is_tool_available("sqlmap") or self.registry.is_tool_available("ffuf"), "Aucun outil Kali standard n'est disponible.")

    def test_kali_tool_availability_reflects_real_detection_not_hardcoded_list(self):
        """is_tool_available doit suivre la détection réelle (shutil.which), pas une liste figée.
        Régression ciblée : l'ancien code renvoyait True pour 'hydra' sans jamais vérifier le
        binaire. En simulant un hôte où 'hydra' est absent et 'sqlmap' présent, on vérifie que
        le résultat suit bien la simulation et non une liste codée en dur."""
        import app.tools.kali_registry as kr

        def fake_which(bin_name):
            return "/usr/bin/sqlmap" if bin_name == "sqlmap" else None

        with patch.object(kr.shutil, "which", side_effect=fake_which):
            registry = kr.KaliToolRegistry()
            self.assertTrue(registry.is_tool_available("sqlmap"))
            self.assertFalse(registry.is_tool_available("hydra"))
            self.assertFalse(registry.is_tool_available("nonexistent_tool"))


if __name__ == "__main__":
    unittest.main()