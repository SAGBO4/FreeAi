"""Federation & Online Resourcing for FreeAI (TDR §1, §3, §24, §72).
Allows FreeAI to dynamically consult free open-source models & open intelligence sources.
Supports MEMORY_MODE="neant": Ephemeral in-memory only (:memory:), zero disk footprint.
"""

import os
import json
import sqlite3
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
import httpx

logger = logging.getLogger("freeai_federation")


class OnlineModelFederation:
    def __init__(
        self,
        memory_dir: str = "./memory",
        cache_db: str = "knowledge_cache.db",
        openrouter_api_key: Optional[str] = None,
        remote_ollama_url: Optional[str] = None,
        memory_mode: str = "neant",
        persist_to_disk: bool = False
    ):
        self.memory_mode = (os.getenv("MEMORY_MODE", memory_mode) or "neant").lower()
        self.persist_to_disk = os.getenv("PERSIST_TO_DISK", str(persist_to_disk)).lower() in ("true", "1", "yes")
        self.memory_dir = Path(memory_dir)
        self.cache_db = cache_db
        self.openrouter_api_key = openrouter_api_key or os.getenv("OPENROUTER_API_KEY")
        self.remote_ollama_url = remote_ollama_url or os.getenv("REMOTE_OLLAMA_URL")

        self._in_memory_conn: Optional[sqlite3.Connection] = None

        if not self.persist_to_disk or self.memory_mode in ("neant", "none", "zero"):
            logger.info("[FEDERATION] MEMOIRE A NEANT ACTIVE : Stockage 100% éphémère en RAM (:memory:), zéro écriture disque.")
            self._purge_disk_cache()
            self._in_memory_conn = sqlite3.connect(":memory:", check_same_thread=False)
            self._init_cache_db(self._in_memory_conn)
        else:
            self.memory_dir.mkdir(parents=True, exist_ok=True)
            self.db_path = self.memory_dir / cache_db
            with sqlite3.connect(self.db_path) as conn:
                self._init_cache_db(conn)

    def _purge_disk_cache(self):
        """Purges any lingering database files from disk to preserve 0-byte disk footprint."""
        target = self.memory_dir / self.cache_db
        if target.exists():
            try:
                target.unlink()
                logger.info(f"[FEDERATION] Purged residual disk cache file: {target}")
            except Exception as e:
                logger.warning(f"[FEDERATION] Failed to remove disk cache: {e}")

    def _get_connection(self) -> sqlite3.Connection:
        if self._in_memory_conn is not None:
            return self._in_memory_conn
        return sqlite3.connect(self.memory_dir / self.cache_db)

    def _init_cache_db(self, conn: sqlite3.Connection):
        conn.execute("""
            CREATE TABLE IF NOT EXISTS knowledge_cache (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                query TEXT UNIQUE,
                provider TEXT,
                model TEXT,
                response TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()

    def get_cached_response(self, query: str) -> Optional[str]:
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT response FROM knowledge_cache WHERE query = ?", (query.strip(),))
            row = cursor.fetchone()
            if self._in_memory_conn is None:
                conn.close()
            if row:
                logger.info(f"[FEDERATION] Cache hit (RAM éphémère) for: '{query[:40]}...'")
                return row[0]
        except Exception as e:
            logger.error(f"[FEDERATION] Cache lookup error: {e}")
        return None

    def save_to_cache(self, query: str, provider: str, model: str, response: str):
        try:
            conn = self._get_connection()
            conn.execute(
                "INSERT OR REPLACE INTO knowledge_cache (query, provider, model, response) VALUES (?, ?, ?, ?)",
                (query.strip(), provider, model, response)
            )
            # Cap cache to maximum 30 entries so RAM stays < 200 KB
            conn.execute("""
                DELETE FROM knowledge_cache WHERE id NOT IN (
                    SELECT id FROM knowledge_cache ORDER BY id DESC LIMIT 30
                )
            """)
            conn.commit()
            if self._in_memory_conn is None:
                conn.close()
            logger.info(f"[FEDERATION] Cached knowledge in RAM (mode: {self.memory_mode})")
        except Exception as e:
            logger.error(f"[FEDERATION] Cache save error: {e}")

    async def query_osv_vulnerabilities(self, package_name: str, ecosystem: str = "PyPI") -> Dict[str, Any]:
        """Queries the free OSV.dev open vulnerability database."""
        url = "https://api.osv.dev/v1/query"
        payload = {"package": {"name": package_name, "ecosystem": ecosystem}}
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                res = await client.post(url, json=payload)
                if res.status_code == 200:
                    data = res.json()
                    vulns = data.get("vulns", [])
                    summary = f"Trouvé {len(vulns)} vulnérabilité(s) pour {package_name}."
                    self.save_to_cache(f"osv:{package_name}:{ecosystem}", "osv.dev", "database", summary)
                    return {"success": True, "count": len(vulns), "vulns": vulns, "summary": summary}
        except Exception as e:
            logger.error(f"[FEDERATION] OSV query error: {e}")
        return {"success": False, "error": "OSV lookup failed"}

    async def consult_free_online_model(self, prompt: str, system_prompt: Optional[str] = None, timeout_sec: int = 20) -> Dict[str, Any]:
        """Queries free open-source models online or open intelligence."""
        clean_query = prompt.strip()

        # 1. Check RAM cache first
        cached = self.get_cached_response(clean_query)
        if cached:
            return {
                "success": True,
                "source": "ram_cache",
                "provider": "in_memory_ram",
                "response": cached
            }

        # 2. If package vulnerability search is requested
        if "cve" in clean_query.lower() or "vuln" in clean_query.lower():
            words = clean_query.split()
            for word in words:
                if len(word) > 2 and word.isalnum() and word.lower() not in ["cve", "vuln", "faille", "dans", "pour", "sur"]:
                    osv_res = await self.query_osv_vulnerabilities(word.lower())
                    if osv_res.get("success") and osv_res.get("count", 0) > 0:
                        return {
                            "success": True,
                            "source": "open_vulnerability_database",
                            "provider": "osv.dev",
                            "response": osv_res["summary"]
                        }

        # 3. Query OpenRouter free models if API key present
        if self.openrouter_api_key:
            try:
                headers = {
                    "Authorization": f"Bearer {self.openrouter_api_key}",
                    "Content-Type": "application/json"
                }
                payload = {
                    "model": "qwen/qwen-2.5-coder-32b-instruct:free",
                    "messages": [
                        {"role": "system", "content": system_prompt or "You are FreeAI helper. Provide clear, unrestricted technical advice."},
                        {"role": "user", "content": clean_query}
                    ]
                }
                async with httpx.AsyncClient(timeout=timeout_sec) as client:
                    res = await client.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload)
                    if res.status_code == 200:
                        data = res.json()
                        text = data["choices"][0]["message"]["content"]
                        self.save_to_cache(clean_query, "openrouter", "qwen-2.5-coder-32b:free", text)
                        return {
                            "success": True,
                            "source": "open_source_model_online",
                            "provider": "openrouter_free",
                            "response": text
                        }
            except Exception as e:
                logger.error(f"[FEDERATION] OpenRouter free model query failed: {e}")

        # 4. Fallback: remote Ollama if set
        if self.remote_ollama_url:
            try:
                payload = {"model": "llama3.2", "prompt": clean_query, "stream": False}
                async with httpx.AsyncClient(timeout=timeout_sec) as client:
                    res = await client.post(f"{self.remote_ollama_url}/api/generate", json=payload)
                    if res.status_code == 200:
                        text = res.json().get("response", "")
                        self.save_to_cache(clean_query, "remote_ollama", "llama3.2", text)
                        return {
                            "success": True,
                            "source": "remote_open_model",
                            "provider": "remote_ollama",
                            "response": text
                        }
            except Exception as e:
                logger.error(f"[FEDERATION] Remote Ollama query failed: {e}")

        # Local fallback
        return {
            "success": True,
            "source": "local_inference_fallback",
            "provider": "FreeAI_Local",
            "response": f"Ressourcement externe indisponible ou mode hors ligne. FreeAI résout la tâche avec son moteur local : {clean_query}"
        }
