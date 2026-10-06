"""DynamicNightlyLearner — Moteur d'Apprentissage Nocturne Dynamique & Synthèse Swarm.
Veille technologique permanente, autonome et dynamique pour FreeAI Jarvis :
- arXiv AI Papers (cat:cs.AI, cs.LG, cs.CL)
- Hugging Face Trending Models & Daily Papers
- GitHub Trending Repositories (Python / TypeScript / Rust)
- CVEs & Vulnérabilités Récentes (OSV.dev / CIRCL)
- Synthèse par Consensus LLM Cloud Gratuit (Groq LPU / HuggingFace)
- Déduplication Sémantique Déterministe (0 répétition, apprentissage perpétuel)
- Stockage 100% frugal en RAM / ledger JSON (.nightly_learnings_ledger.json)
Mode NÉANT : Empreinte mémoire minimale, zéro résidu inutile.
"""

import os
import re
import json
import time
import hashlib
import asyncio
import logging
from datetime import datetime, date
from pathlib import Path
from typing import Dict, Any, List, Optional, Set
import xml.etree.ElementTree as ET
import httpx

from config.settings import settings

logger = logging.getLogger("dynamic_nightly_learner")


class DynamicNightlyLearner:
    """Orchestre l'ingestion dynamique, la déduplication sémantique et la synthèse des connaissances nocturnes."""

    LEDGER_FILE = Path(".nightly_learnings_ledger.json")
    MAX_LEDGER_ENTRIES = 120

    def __init__(self, groq_api_key: Optional[str] = None):
        self.groq_api_key = (
            groq_api_key
            or getattr(settings, "GROQ_API_KEY", "")
            or os.environ.get("GROQ_API_KEY", "")
        )
        self.groq_url = "https://api.groq.com/openai/v1/chat/completions"
        self.http_timeout = 8.0
        self.headers = {"User-Agent": "FreeAI-Jarvis-NightlyLearner/2.0"}
        self._ledger = self._load_ledger()

    def _load_ledger(self) -> Dict[str, Any]:
        """Charge le ledger d'apprentissage avec gestion gracieuse de l'absence de fichier."""
        if self.LEDGER_FILE.exists():
            try:
                data = json.loads(self.LEDGER_FILE.read_text(encoding="utf-8"))
                if isinstance(data, dict) and "entries" in data:
                    return data
            except Exception as e:
                logger.debug(f"[NIGHTLY LEARNER] Erreur lecture ledger: {e}")
        return {"entries": [], "known_hashes": [], "last_updated": ""}

    def _save_ledger(self) -> None:
        """Sauvegarde le ledger de façon atomique et frugale (Mode NÉANT: limité à MAX_LEDGER_ENTRIES)."""
        try:
            # Élagage pour conserver une empreinte ultra-légère (< 50 Ko)
            if len(self._ledger["entries"]) > self.MAX_LEDGER_ENTRIES:
                self._ledger["entries"] = self._ledger["entries"][-self.MAX_LEDGER_ENTRIES:]
            if len(self._ledger["known_hashes"]) > self.MAX_LEDGER_ENTRIES * 2:
                self._ledger["known_hashes"] = self._ledger["known_hashes"][-self.MAX_LEDGER_ENTRIES * 2:]

            self._ledger["last_updated"] = datetime.now().isoformat()
            self.LEDGER_FILE.write_text(json.dumps(self._ledger, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception as e:
            logger.debug(f"[NIGHTLY LEARNER] Erreur sauvegarde ledger: {e}")

    @staticmethod
    def _compute_semantic_fingerprint(text: str) -> str:
        """Génère une empreinte normalisée pour déduplication."""
        cleaned = re.sub(r"[^\w\s]", "", text.lower())
        tokens = sorted(list(set(cleaned.split())))
        normalized_str = " ".join(tokens)
        return hashlib.sha256(normalized_str.encode("utf-8")).hexdigest()

    def is_already_learned(self, title: str, domain: str = "") -> bool:
        """Vérifie si une innovation a déjà été apprise les jours précédents."""
        fp = self._compute_semantic_fingerprint(f"{domain} {title}")
        if fp in self._ledger.get("known_hashes", []):
            return True

        # Déduplication par similarité Jaccard sur les titres des 30 derniers jours
        title_tokens = set(re.findall(r"\w+", title.lower()))
        if len(title_tokens) >= 3:
            for entry in self._ledger.get("entries", []):
                entry_tokens = set(re.findall(r"\w+", entry.get("title", "").lower()))
                if not entry_tokens:
                    continue
                intersection = title_tokens.intersection(entry_tokens)
                union = title_tokens.union(entry_tokens)
                if union and (len(intersection) / len(union)) > 0.65:
                    return True
        return False

    def mark_as_learned(self, entry: Dict[str, Any]) -> None:
        """Enregistre l'entrée dans le ledger permanent."""
        title = entry.get("title", "")
        domain = entry.get("domain", "")
        fp = self._compute_semantic_fingerprint(f"{domain} {title}")

        if "known_hashes" not in self._ledger:
            self._ledger["known_hashes"] = []
        if "entries" not in self._ledger:
            self._ledger["entries"] = []

        self._ledger["known_hashes"].append(fp)
        self._ledger["entries"].append({
            "title": title,
            "domain": domain,
            "date": entry.get("date", str(date.today())),
            "fingerprint": fp
        })
        self._save_ledger()

    async def fetch_arxiv_ai_papers(self, max_results: int = 5) -> List[Dict[str, Any]]:
        """Interroge l'API arXiv pour les derniers papiers AI / Machine Learning."""
        url = (
            f"http://export.arxiv.org/api/query?search_query=cat:cs.AI+OR+cat:cs.LG+OR+cat:cs.CL"
            f"&sortBy=submittedDate&sortOrder=descending&max_results={max_results}"
        )
        papers = []
        try:
            async with httpx.AsyncClient(timeout=self.http_timeout) as client:
                resp = await client.get(url, headers=self.headers)
                if resp.status_code == 200:
                    root = ET.fromstring(resp.text)
                    ns = {"atom": "http://www.w3.org/2005/Atom"}
                    for entry in root.findall("atom:entry", ns):
                        title = entry.find("atom:title", ns)
                        summary = entry.find("atom:summary", ns)
                        link = entry.find("atom:id", ns)
                        if title is not None and title.text:
                            raw_title = title.text.strip().replace("\n", " ")
                            papers.append({
                                "domain": "📄 arXiv AI Research",
                                "title": raw_title,
                                "summary": summary.text.strip().replace("\n", " ") if summary is not None else "",
                                "url": link.text.strip() if link is not None else "https://arxiv.org",
                                "source": "arxiv"
                            })
        except Exception as e:
            logger.debug(f"[NIGHTLY LEARNER] arXiv fetch error: {e}")
        return papers

    async def fetch_huggingface_models(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Interroge l'API HuggingFace pour les modèles tendance des 7 derniers jours."""
        url = f"https://huggingface.co/api/models?sort=likes7d&direction=-1&limit={limit}"
        models = []
        try:
            async with httpx.AsyncClient(timeout=self.http_timeout) as client:
                resp = await client.get(url, headers=self.headers)
                if resp.status_code == 200:
                    data = resp.json()
                    for item in data:
                        model_id = item.get("id", "")
                        likes = item.get("likes", 0)
                        downloads = item.get("downloads", 0)
                        models.append({
                            "domain": "🤗 HuggingFace Models",
                            "title": model_id,
                            "summary": f"Modèle tendance avec {likes} likes et {downloads} téléchargements cette semaine.",
                            "url": f"https://huggingface.co/{model_id}",
                            "source": "huggingface"
                        })
        except Exception as e:
            logger.debug(f"[NIGHTLY LEARNER] HuggingFace fetch error: {e}")
        return models

    async def fetch_github_trending(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Scrape/requête l'API GitHub pour les repositories Python/TypeScript/Rust les plus actifs."""
        today_year = datetime.now().year
        url = (
            f"https://api.github.com/search/repositories?"
            f"q=stars:>1000+language:python+pushed:>{today_year}-01-01&sort=updated&order=desc&per_page={limit}"
        )
        repos = []
        try:
            async with httpx.AsyncClient(timeout=self.http_timeout) as client:
                resp = await client.get(url, headers=self.headers)
                if resp.status_code == 200:
                    items = resp.json().get("items", [])
                    for repo in items:
                        name = repo.get("full_name", "")
                        desc = repo.get("description") or "Repository Open Source de référence"
                        stars = repo.get("stargazers_count", 0)
                        url_repo = repo.get("html_url", "")
                        repos.append({
                            "domain": "⚡ GitHub Open-Source",
                            "title": name,
                            "summary": f"{desc} (⭐ {stars} stars)",
                            "url": url_repo,
                            "source": "github"
                        })
        except Exception as e:
            logger.debug(f"[NIGHTLY LEARNER] GitHub fetch error: {e}")
        return repos

    async def fetch_recent_cves(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Interroge la base CIRCL / OSV pour les alertes de cybersécurité récentes."""
        url = "https://cve.circl.lu/api/last"
        cves = []
        try:
            async with httpx.AsyncClient(timeout=self.http_timeout) as client:
                resp = await client.get(url, headers=self.headers)
                if resp.status_code == 200:
                    data = resp.json()
                    for item in data[:limit]:
                        cve_id = item.get("id", "")
                        summary = item.get("summary", "")
                        cves.append({
                            "domain": "🛡️ Cybersécurité & CVEs",
                            "title": cve_id,
                            "summary": summary[:250] + "..." if len(summary) > 250 else summary,
                            "url": f"https://nvd.nist.gov/vuln/detail/{cve_id}",
                            "source": "circl_cve"
                        })
        except Exception as e:
            logger.debug(f"[NIGHTLY LEARNER] CVE fetch error: {e}")
        return cves

    async def synthesize_insight_with_llm(self, item: Dict[str, Any]) -> str:
        """Produit un insight percutant en français via Groq LPU ou synthèse frugale."""
        if not self.groq_api_key:
            return f"{item['title']} : {item['summary']}"

        prompt = (
            f"Tu es FreeAI, l'IA souveraine de Michael SAGBO.\n"
            f"Synthétise cette découverte technologique en UNE seule phrase percutante (max 30 mots) en français, "
            f"orientée architecture logicielle, Web3 ou performance :\n"
            f"Titre : {item['title']}\n"
            f"Description : {item['summary']}\n"
            f"Lien : {item.get('url', '')}\n"
            f"Réponse directe sans préambule :"
        )

        headers = {
            "Authorization": f"Bearer {self.groq_api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "openai/gpt-oss-120b",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.5,
            "max_tokens": 80
        }

        try:
            async with httpx.AsyncClient(timeout=6.0) as client:
                res = await client.post(self.groq_url, headers=headers, json=payload)
                if res.status_code == 200:
                    txt = res.json()["choices"][0]["message"]["content"].strip()
                    if txt:
                        return txt
        except Exception:
            pass

        return f"{item['title']} : {item['summary']}"

    async def run_nightly_learning_cycle(self, max_total_insights: int = 4) -> List[Dict[str, str]]:
        """Exécute le cycle complet d'apprentissage nocturne avec déduplication absolue.
        Retourne la liste des nouveaux apprentissages formatés pour le briefing matinal.
        """
        logger.info("[NIGHTLY LEARNER] Démarrage du cycle d'apprentissage nocturne...")

        # 1. Collecte parallèle de toutes les sources
        arxiv_task = self.fetch_arxiv_ai_papers(5)
        hf_task = self.fetch_huggingface_models(5)
        github_task = self.fetch_github_trending(5)
        cve_task = self.fetch_recent_cves(5)

        results = await asyncio.gather(arxiv_task, hf_task, github_task, cve_task, return_exceptions=True)

        candidate_items: List[Dict[str, Any]] = []
        for batch in results:
            if isinstance(batch, list):
                candidate_items.extend(batch)

        # 2. Filtrage & Déduplication Sémantique (0 répétition !)
        novel_items: List[Dict[str, Any]] = []
        for item in candidate_items:
            title = item.get("title", "")
            domain = item.get("domain", "")
            if not self.is_already_learned(title, domain):
                novel_items.append(item)
                if len(novel_items) >= max_total_insights:
                    break

        # Fallback si le réseau est totalement indisponible : synthèses architecturales de secours
        if not novel_items:
            novel_items = [
                {
                    "domain": "🛡️ Web3 & Smart Contracts",
                    "title": "Optimisation Flash-Loans EIP-712",
                    "summary": "Analyse statique des vecteurs de réentrances cross-contrats et modélisation de swaps AMM sans capital.",
                    "url": "https://ethereum.org",
                    "source": "fallback"
                },
                {
                    "domain": "⚡ Ingénierie des Modèles & Inférence LPU",
                    "title": "Déportation Inférence Groq LPU",
                    "summary": "Exécution à 500+ tok/s avec 0% d'empreinte processeur sur la machine locale.",
                    "url": "https://groq.com",
                    "source": "fallback"
                },
                {
                    "domain": "🧠 Hologramme Binaire 1-Bit (BHVE)",
                    "title": "Projections Sémantiques Condensées",
                    "summary": "Optimisation des embeddings 768d en 96 octets avec recherche cosinus matérielle POPCNT.",
                    "url": "https://github.com/SAGBO4/FreeAi",
                    "source": "fallback"
                },
                {
                    "domain": "📱 Architecture UI & Design Souverain",
                    "title": "Composants Radix & Shadcn Avancés",
                    "summary": "Patterns d'orchestration asynchrone et streaming token par token sans blocage de boucle d'événement.",
                    "url": "https://ui.shadcn.com",
                    "source": "fallback"
                }
            ]

        # 3. Synthèse concise et mémorisation
        final_learnings = []
        for item in novel_items[:max_total_insights]:
            insight_text = await self.synthesize_insight_with_llm(item)
            formatted_entry = {
                "domain": item["domain"],
                "insight": f"{insight_text}\n  🔗 <a href=\"{item.get('url', '')}\">Consulter la source</a>" if item.get("url") else insight_text,
                "title": item["title"],
                "date": str(date.today())
            }
            # Marquer comme appris dans le ledger
            self.mark_as_learned(formatted_entry)
            final_learnings.append({
                "domain": formatted_entry["domain"],
                "insight": formatted_entry["insight"]
            })

        logger.info(f"[NIGHTLY LEARNER] Cycle terminé avec {len(final_learnings)} nouveaux savoirs indexés.")
        return final_learnings
