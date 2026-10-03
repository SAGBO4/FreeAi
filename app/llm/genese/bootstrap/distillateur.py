import os
import json
import logging
import asyncio
import httpx
from typing import Dict, Any, List
from ..ame.gardien import GardienEthique

logger = logging.getLogger(__name__)

CATEGORIES_BENCHMARK = {
    "raisonnement": "Explique étape par étape comment résoudre un problème logique complexe.",
    "code_python": "Écris une fonction Python optimisée.",
    "comprehension": "Résume ce texte en 3 points clés.",
    "mathematiques": "Calcule et explique une expression mathématique.",
    "ethique_valeurs": "Face à ce dilemme moral, quelle est la meilleure réponse.",
    "securite_info": "Explique cette vulnérabilité et sa correction.",
    "langue_francaise": "Corrige et améliore un texte en français."
}

PROFESSEURS = [
    {
        "nom": "DeepSeek-Chat",
        "endpoint": "https://api.deepseek.com/chat/completions",
        "modele": "deepseek-chat",
        "api_key_env": "DEEPSEEK_API_KEY",
        "specialite": ["code_python", "raisonnement", "mathematiques"],
        "temperature": 0.1,
    },
    {
        "nom": "GPT-OSS-120B (Groq)",
        "endpoint": "https://api.groq.com/openai/v1/chat/completions", 
        "modele": "openai/gpt-oss-120b",
        "api_key_env": "GROQ_API_KEY",
        "specialite": ["comprehension", "langue_francaise", "ethique_valeurs"],
        "temperature": 0.1,
    },
    {
        "nom": "Qwen-3.8 (Groq)",
        "endpoint": "https://api.groq.com/openai/v1/chat/completions",
        "modele": "qwen/qwen3.8-27b", 
        "api_key_env": "GROQ_API_KEY",
        "specialite": ["code_python", "securite_info"],
        "temperature": 0.1,
    }
]

class DistillateurBenchmark:
    """
    Distillation de connaissance par benchmarks (Auto-Curriculum Learning).
    Utilise les modèles professeurs pour générer des données de qualité.
    """
    def __init__(self, index_memoire=None):
        self.index = index_memoire
        self.gardien = GardienEthique()
        from .evaluateur import EvaluateurConsensus
        self.evaluateur = EvaluateurConsensus()

    async def _query_professeur(self, prof: dict, prompt: str, system_prompt: str = "") -> str:
        api_key = os.getenv(prof["api_key_env"])
        if not api_key:
            return ""
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": prof["modele"],
            "messages": [
                {"role": "system", "content": system_prompt or "Tu es un expert produisant des données d'entraînement idéales."},
                {"role": "user", "content": prompt}
            ],
            "temperature": prof["temperature"]
        }
        
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                res = await client.post(prof["endpoint"], json=payload, headers=headers)
                if res.status_code == 200:
                    return res.json()["choices"][0]["message"]["content"]
        except Exception as e:
            logger.debug(f"[DISTILLATION] Erreur professeur {prof['nom']}: {e}")
        return ""

    async def _generer_questions(self, prof: dict, categorie: str, n: int) -> List[str]:
        prompt = f"Génère {n} prompts variés pour évaluer un LLM sur la catégorie: {categorie}. Le thème principal est: {CATEGORIES_BENCHMARK[categorie]}. Retourne UNIQUEMENT un JSON contenant une liste de strings sous la clé 'prompts'."
        res = await self._query_professeur(prof, prompt)
        try:
            # Nettoyer markdown
            res = res.replace("```json", "").replace("```", "").strip()
            data = json.loads(res)
            return data.get("prompts", [])
        except:
            return []

    async def run_benchmark_session(self, n_prompts_par_categorie: int = 5, categories: List[str] = None) -> dict:
        cats_to_run = categories or list(CATEGORIES_BENCHMARK.keys())
        stats = {"total_generes": 0, "valides": 0, "rejetes": 0, "categories": {}}

        # Trouver un professeur maître (DeepSeek par défaut)
        prof_maitre = next((p for p in PROFESSEURS if os.getenv(p["api_key_env"])), None)
        if not prof_maitre:
            logger.warning("[DISTILLATION] Aucun professeur disponible (clés d'API manquantes).")
            return stats

        for cat in cats_to_run:
            stats["categories"][cat] = 0
            questions = await self._generer_questions(prof_maitre, cat, n_prompts_par_categorie)
            
            for q in questions:
                # Interroger deux professeurs
                rep1 = await self._query_professeur(PROFESSEURS[0], q) # DeepSeek
                rep2 = await self._query_professeur(PROFESSEURS[1], q) # GPT-OSS ou Qwen si dispo

                if rep1 and rep2:
                    score = self.evaluateur.calculer_consensus(rep1, rep2)
                    if score >= 0.6:
                        # Validation éthique
                        valide, _ = self.gardien.evaluer_generation(rep1)
                        if valide:
                            contenu = f"<|utilisateur|>{q}<|jarvis|>{rep1}<|fin|>"
                            if self.index:
                                self.index.ajouter_shard("general", contenu, importance=score)
                            stats["valides"] += 1
                            stats["categories"][cat] += 1
                        else:
                            stats["rejetes"] += 1
                    else:
                        stats["rejetes"] += 1
                elif rep1:
                    # Fallback un seul prof
                    valide, _ = self.gardien.evaluer_generation(rep1)
                    if valide:
                        contenu = f"<|utilisateur|>{q}<|jarvis|>{rep1}<|fin|>"
                        if self.index:
                            self.index.ajouter_shard("general", contenu, importance=0.8)
                        stats["valides"] += 1
                        stats["categories"][cat] += 1
                    else:
                        stats["rejetes"] += 1
                
                stats["total_generes"] += 1

        return stats
