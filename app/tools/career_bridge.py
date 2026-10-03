"""Career-OS Sovereign Integration Bridge for FreeAI.
Bridges FreeAI with Gilchrist Kanté's personal Career Operating System (~/Rendue/career-os).
Provides programmatic radar scanning, pipeline intelligence,
Telegram alerts for remote opportunities, and Supabase ledger monitoring.
"""

import os
import json
import logging
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional

logger = logging.getLogger("career_bridge")


class CareerBridge:
    """Manages integration with career-os: radar scraping, telemetry,
    and opportunity alerts."""

    DEFAULT_CAREER_DIR = Path("/home/lesaint/Rendue/career-os")

    def __init__(self, career_dir: Optional[str] = None):
        self.career_dir = Path(career_dir or self.DEFAULT_CAREER_DIR).resolve()

    @property
    def is_available(self) -> bool:
        return (self.career_dir / "package.json").exists()

    @property
    def is_configured(self) -> bool:
        env_file = self.career_dir / ".env.local"
        if not env_file.exists():
            return False
        content = env_file.read_text(encoding="utf-8")
        return "SUPABASE_URL=" in content and "SUPABASE_SERVICE_ROLE_KEY=" in content

    def get_status(self) -> Dict[str, Any]:
        """Returns the operational status of career-os."""
        if not self.is_available:
            return {
                "available": False,
                "error": f"Répertoire {self.career_dir} introuvable."
            }

        return {
            "available": True,
            "path": str(self.career_dir),
            "configured": self.is_configured,
            "has_node_modules": (self.career_dir / "node_modules").exists(),
            "has_schema_sql": (self.career_dir / "supabase" / "schema.sql").exists(),
            "has_radar_sql": (self.career_dir / "supabase" / "radar.sql").exists(),
            "modules": [
                "Objectifs (académiques, pro, revenu, compétences, visibilité)",
                "Prospects (pipeline commercial)",
                "Devis (calculateur de facturation local/international)",
                "Projets (suivi des jalons de paiement)",
                "Articles (pipeline de contenu technique)",
                "Radar d'offres (Remotive, RemoteOK, Jobicy, Working Nomads, WWR)",
                "Dashboard (synthèse financière et objectifs en cours)"
            ]
        }

    def run_radar_tests(self) -> Dict[str, Any]:
        """Runs the radar test suite."""
        test_file = self.career_dir / "scripts" / "radar" / "lib.test.mjs"
        if not test_file.exists():
            return {"success": False, "error": "Fichier de test radar introuvable."}

        try:
            res = subprocess.run(
                ["node", "--test", str(test_file)],
                capture_output=True,
                text=True,
                timeout=30
            )
            return {
                "success": res.returncode == 0,
                "stdout": res.stdout,
                "stderr": res.stderr
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def run_radar_dry(self) -> Dict[str, Any]:
        """Runs a dry run of the radar scraper without writing to Supabase."""
        radar_script = self.career_dir / "scripts" / "radar" / "radar.mjs"
        if not radar_script.exists():
            return {"success": False, "error": "Script radar introuvable."}

        try:
            res = subprocess.run(
                ["node", str(radar_script), "dry"],
                cwd=str(self.career_dir),
                capture_output=True,
                text=True,
                timeout=60
            )
            return {
                "success": res.returncode == 0,
                "output": res.stdout,
                "errors": res.stderr
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
