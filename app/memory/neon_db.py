"""Neon Cloud PostgreSQL Integration for FreeAI.
Stores essential memory, solutions, and audit logs remotely in Neon DB,
with automatic GZIP compression to minimize network and database storage.
Ensures zero disk usage on the local PC.
"""

import os
import json
import gzip
import base64
import time
import logging
from typing import Dict, Any, Optional, List
import psycopg2
from psycopg2.extras import RealDictCursor

logger = logging.getLogger("neon_db")


class NeonMemoryManager:
    def __init__(self, db_url: Optional[str] = None):
        self.db_url = db_url if db_url is not None else os.getenv("NEON_DATABASE_URL")
        self.enabled = bool(self.db_url)
        if self.enabled:
            logger.info("[NEON] Neon PostgreSQL memory adapter enabled (off-device compressed storage).")
            self._init_tables()
        else:
            logger.info("[NEON] Neon database URL not set. Memory remains ephemeral in local RAM.")

    def _get_connection(self):
        # Strips channel_binding if unsupported by standard psycopg2 connection parameters
        clean_url = self.db_url
        if "channel_binding=" in clean_url:
            clean_url = clean_url.replace("&channel_binding=require", "").replace("channel_binding=require&", "").replace("channel_binding=require", "")
        return psycopg2.connect(clean_url, connect_timeout=10)

    @staticmethod
    def compress_text(text: str) -> str:
        """Compresses text with gzip and returns a base64 encoded string prefixed with 'gz:'."""
        if not text:
            return ""
        try:
            compressed = gzip.compress(text.encode("utf-8"), compresslevel=9)
            return "gz:" + base64.b64encode(compressed).decode("ascii")
        except Exception as e:
            logger.warning(f"[NEON:ZIP] Compression fallback to plain text: {e}")
            return text

    @staticmethod
    def decompress_text(data: str) -> str:
        """Decompresses text if it has the 'gz:' prefix, otherwise returns raw text."""
        if not data:
            return ""
        if isinstance(data, str) and data.startswith("gz:"):
            try:
                raw_b64 = data[3:]
                compressed = base64.b64decode(raw_b64.encode("ascii"))
                return gzip.decompress(compressed).decode("utf-8")
            except Exception as e:
                logger.error(f"[NEON:UNZIP] Decompression error: {e}")
                return data
        return data

    @staticmethod
    def extract_essentials(outcome: Dict[str, Any]) -> Dict[str, Any]:
        """Filters out verbose noise to store strictly the essential solution & findings."""
        if not isinstance(outcome, dict):
            return {"raw": str(outcome)[:500]}

        essentials = {
            "status": outcome.get("status", "unknown"),
            "agent": outcome.get("agent", "unknown"),
            "message": outcome.get("message", ""),
        }
        # Keep security findings if present
        if "findings" in outcome:
            essentials["findings"] = outcome["findings"]
        # Keep solution/task description
        if "task" in outcome:
            essentials["task"] = outcome["task"]
        # Keep modified files if present
        if "files" in outcome:
            essentials["files"] = outcome["files"]

        return essentials

    def _init_tables(self):
        """Initializes tables in Neon PostgreSQL and adds compression columns if missing."""
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    # Knowledge base table
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS freeai_knowledge (
                            id SERIAL PRIMARY KEY,
                            query TEXT UNIQUE NOT NULL,
                            provider VARCHAR(100),
                            model VARCHAR(100),
                            response TEXT NOT NULL,
                            is_compressed BOOLEAN DEFAULT TRUE,
                            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                        );
                    """)
                    # Audit & execution logs table (offloaded from local PC disk)
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS freeai_audit_logs (
                            id SERIAL PRIMARY KEY,
                            objective TEXT NOT NULL,
                            agent VARCHAR(100),
                            outcome TEXT NOT NULL,
                            is_compressed BOOLEAN DEFAULT TRUE,
                            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                        );
                    """)
                    # Ensure columns exist even on pre-existing tables & support text compression
                    cur.execute("""
                        ALTER TABLE freeai_knowledge ADD COLUMN IF NOT EXISTS is_compressed BOOLEAN DEFAULT TRUE;
                        ALTER TABLE freeai_audit_logs ADD COLUMN IF NOT EXISTS is_compressed BOOLEAN DEFAULT TRUE;
                        ALTER TABLE freeai_audit_logs ALTER COLUMN outcome TYPE TEXT USING outcome::TEXT;
                    """)
                    conn.commit()
            logger.info("[NEON] Schema with ZIP compression support initialized successfully on Neon.")
        except Exception as e:
            logger.error(f"[NEON] Table initialization error: {e}")

    def save_knowledge(self, query: str, provider: str, model: str, response: str) -> bool:
        """Compresses knowledge with GZIP and saves to Neon DB."""
        if not self.enabled:
            return False
        try:
            compressed_response = self.compress_text(response)
            orig_size = len(response.encode("utf-8"))
            zip_size = len(compressed_response.encode("utf-8"))
            logger.info(f"[NEON:ZIP] Knowledge compressed: {orig_size}B -> {zip_size}B ({round((1 - zip_size/max(orig_size, 1))*100, 1)}% saved)")

            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO freeai_knowledge (query, provider, model, response, is_compressed)
                        VALUES (%s, %s, %s, %s, TRUE)
                        ON CONFLICT (query) DO UPDATE
                        SET response = EXCLUDED.response,
                            is_compressed = TRUE,
                            created_at = CURRENT_TIMESTAMP;
                    """, (query.strip(), provider, model, compressed_response))
                    conn.commit()
            logger.info(f"[NEON] Compressed knowledge synced to Neon PostgreSQL for: '{query[:40]}...'")
            return True
        except Exception as e:
            logger.error(f"[NEON] Failed to save knowledge to Neon: {e}")
            return False

    def get_knowledge(self, query: str) -> Optional[str]:
        """Retrieves and decompresses knowledge from Neon DB."""
        if not self.enabled:
            return None
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT response FROM freeai_knowledge WHERE query = %s LIMIT 1;", (query.strip(),))
                    row = cur.fetchone()
                    if row:
                        raw_data = row[0]
                        decompressed = self.decompress_text(raw_data)
                        logger.info(f"[NEON:UNZIP] Decompressed knowledge from Neon for: '{query[:40]}...'")
                        return decompressed
        except Exception as e:
            logger.error(f"[NEON] Failed to query Neon: {e}")
        return None

    def log_audit_event(self, objective: str, agent: str, outcome: Dict[str, Any]) -> bool:
        """Extracts the essential data, zips it, and logs to Neon DB."""
        if not self.enabled:
            return False
        try:
            # 1. Extract essentials (strip verbose debug traces)
            essentials = self.extract_essentials(outcome)
            json_text = json.dumps(essentials)

            # 2. Compress with GZIP
            compressed_outcome = self.compress_text(json_text)
            orig_size = len(json_text.encode("utf-8"))
            zip_size = len(compressed_outcome.encode("utf-8"))
            logger.info(f"[NEON:ZIP] Audit essentials compressed: {orig_size}B -> {zip_size}B ({round((1 - zip_size/max(orig_size, 1))*100, 1)}% saved)")

            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO freeai_audit_logs (objective, agent, outcome, is_compressed)
                        VALUES (%s, %s, %s, TRUE);
                    """, (objective, agent, compressed_outcome))
                    conn.commit()
            logger.info(f"[NEON] Compressed audit essentials logged to Neon for: '{objective[:40]}...'")
            return True
        except Exception as e:
            logger.error(f"[NEON] Failed to log audit event to Neon: {e}")
            return False

    def get_status(self) -> Dict[str, Any]:
        """Returns connection and record count stats for Neon DB."""
        if not self.enabled:
            return {
                "enabled": False,
                "connected": False,
                "database": "Ephemeral RAM (NEON_DATABASE_URL not set)",
                "records": 0,
                "compression": "GZIP (Level 9)"
            }
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT COUNT(*) FROM freeai_knowledge;")
                    k_count = cur.fetchone()[0]
                    cur.execute("SELECT COUNT(*) FROM freeai_audit_logs;")
                    a_count = cur.fetchone()[0]
                    return {
                        "enabled": True,
                        "connected": True,
                        "database": "Neon PostgreSQL (Cloud Remote)",
                        "knowledge_records": k_count,
                        "audit_records": a_count,
                        "compression": "GZIP (Level 9) + Base64 ('gz:')"
                    }
        except Exception as e:
            return {
                "enabled": True,
                "connected": False,
                "database": "Neon PostgreSQL (Connection Failed)",
                "error": str(e),
                "compression": "GZIP (Level 9)"
            }

    def sync_memory(self, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Explicitly compresses and synchronizes essential memory into Neon Cloud."""
        if not self.enabled:
            return {
                "success": False,
                "message": "Neon Cloud adapter not enabled. Set NEON_DATABASE_URL in .env to sync remotely."
            }
        try:
            data = payload or {
                "sync_timestamp": time.time(),
                "event": "manual_memory_sync",
                "state": "consistent",
                "memory_mode": "neant"
            }
            json_text = json.dumps(data)
            compressed = self.compress_text(json_text)
            orig_size = len(json_text.encode("utf-8"))
            zip_size = len(compressed.encode("utf-8"))
            saved = round((1 - zip_size / max(orig_size, 1)) * 100, 1)

            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO freeai_audit_logs (objective, agent, outcome, is_compressed)
                        VALUES (%s, %s, %s, TRUE);
                    """, ("MANUAL_SYNC", "neon_sync_manager", compressed))
                    conn.commit()

            return {
                "success": True,
                "message": "Mémoire essentielle compressée en GZIP et synchronisée sur Neon PostgreSQL.",
                "original_bytes": orig_size,
                "compressed_bytes": zip_size,
                "ratio_saved": f"{saved}%"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
