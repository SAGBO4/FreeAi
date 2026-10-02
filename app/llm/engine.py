"""FreeAI — Moteur d'Intelligence Artificielle Locale & Fédérée.
Nom du modèle : FreeAI
Architecture : 100% Local par défaut, avec capacité de ressourcement auprès de modèles libres en ligne.
Libre, sans restriction ni censure.
"""

import os
import re
import json
import logging
from typing import Dict, Any, List, Optional
from .federation import OnlineModelFederation

logger = logging.getLogger("freeai_engine")


class FreeAIEngine:
    """FreeAI: Local, sovereign, and unrestricted AI model.

    - Default: Fast, local CPU-based execution (zero latency, zero network requirement).
    - Dynamic Resourcing: If knowledge is missing or external research is needed,
      FreeAI consults free open-source models online and saves the knowledge in its local SQLite cache.
    """

    def __init__(self, model_path: Optional[str] = None, memory_dir: str = "./memory"):
        self.name = "FreeAI"
        self.version = "1.0-alpha"
        self.model_path = model_path
        self.federation = OnlineModelFederation(memory_dir=memory_dir)
        logger.info(f"[{self.name}] Initialized FreeAI Core Engine (Local & Unrestricted).")

    def reason_and_plan(self, prompt: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Analyzes an objective, determines the intent, and crafts an actionable plan."""
        p_lower = prompt.lower()

        # Check if external resourcing is required
        needs_online_resourcing = any(
            w in p_lower for w in [
                "cherche en ligne", "interroge", "nouvelle doc", "dernier", "cve",
                "ressource", "info externe", "modèle en ligne", "recherche web", "externe", "cherche"
            ]
        )

        # 0. Conversational, Greetings, Personality & Social Intent
        conversational_triggers = [
            "comment vas-tu", "comment tu vas", "ça va", "ca va", "comment ca va",
            "salut", "bonjour", "hello", "coucou", "hey", "bonsoir", "qui es-tu",
            "tu fais quoi", "merci", "raconte", "dis-moi", "tu penses quoi",
            "blague", "avis", "discussion", "parle-moi", "bonjour jarvis", "salut freeai", "vas tu"
        ]
        is_greeting_or_chit_chat = any(t in p_lower for t in conversational_triggers) or (
            len(prompt.split()) <= 7 and any(p in p_lower for p in ["tu", "toi", "vas", "bien", "ami", "potes", "frère"])
        )
        if is_greeting_or_chit_chat and not any(k in p_lower for k in ["code", "fichier", "fonction", "git", "secu", "test", "docker", "script"]):
            return {
                "model": self.name,
                "domain": "conversation",
                "intent": "human_dialogue",
                "unrestricted": True,
                "needs_online_resourcing": False,
                "strategy": [
                    "1. Analyse de l'état d'esprit et du contexte relationnel.",
                    "2. Consultation de la mémoire vectorielle épisodique.",
                    "3. Synthèse d'une réponse humaine, chaleureuse et complice."
                ],
                "recommended_tools": ["vector_memory", "persona"]
            }

        # 1. Security / Audit Task
        if any(k in p_lower for k in ["secu", "audit", "vuln", "faille", "cwe", "inject", "pentest", "scan", "secret"]):
            return {
                "model": self.name,
                "domain": "security",
                "intent": "security_audit",
                "unrestricted": True,
                "needs_online_resourcing": needs_online_resourcing,
                "strategy": [
                    "1. Scan de surface et cartographie des fichiers cibles.",
                    "2. Analyse SAST sans restriction (injections SQL, XSS, SSRF, chemins non assainis).",
                    "3. Recherche de secrets codés en dur (.env, clés privées, tokens).",
                    "4. Génération de tests de charge / payloads de validation dans l'environnement autorisé.",
                    "5. Production d'un rapport structuré avec remédiation technique."
                ],
                "recommended_tools": ["filesystem", "terminal", "security_scanner"]
            }

        # 2. Git & Version Control
        elif any(k in p_lower for k in ["git", "commit", "branch", "diff", "tag", "rollback", "revert"]):
            return {
                "model": self.name,
                "domain": "git",
                "intent": "version_control",
                "unrestricted": True,
                "needs_online_resourcing": needs_online_resourcing,
                "strategy": [
                    "1. Inspection du statut du dépôt (`git status`).",
                    "2. Examen des différences (`git diff`).",
                    "3. Création d'un checkpoint / snapshot préventif.",
                    "4. Exécution de l'opération demandée."
                ],
                "recommended_tools": ["git", "terminal"]
            }

        # 3. Code Generation / Project Engineering
        else:
            return {
                "model": self.name,
                "domain": "code",
                "intent": "code_engineering",
                "unrestricted": True,
                "needs_online_resourcing": needs_online_resourcing,
                "strategy": [
                    "1. Inspection de l'architecture du projet et dépendances.",
                    "2. Génération / modification des fichiers sources.",
                    "3. Exécution des tests unitaires via le terminal.",
                    "4. Analyse des logs d'erreurs et correction itérative."
                ],
                "recommended_tools": ["filesystem", "terminal", "testing"]
            }

    async def enrich_with_online_open_models(self, query: str) -> Dict[str, Any]:
        """FreeAI reaches out to free open-source models online to acquire missing knowledge."""
        logger.info(f"[{self.name}] Initiating external resourcing from free online open models...")
        return await self.federation.consult_free_online_model(query)
