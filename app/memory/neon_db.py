"""Neon Cloud PostgreSQL Integration for FreeAI.
Stores memory, knowledge, and critical logs remotely in Neon DB,
ensuring zero disk usage on the local PC.
"""

import os
import logging
from typing import Dict, Any, Optional, List
import psycopg2
from psycopg2.extras import RealDictCursor

logger = logging.getLogger("neon_db")


class NeonMemoryManager:
    def __init__(self, db_url: Optional[str] = None):
        self.db_url = db_url or os.getenv("NEON_DATABASE_URL")
        self.enabled = bool(self.db_url)
        if self.enabled:
            logger.info("[NEON] Neon PostgreSQL memory adapter enabled (off-device cloud persistence).")
            self._init_tables()
        else:
            logger.info("[NEON] Neon database URL not set. Memory remains ephemeral in local RAM.")

    def _get_connection(self):
        # Strips channel_binding if unsupported by standard psycopg2 connection parameters
        clean_url = self.db_url
        if "channel_binding=" in clean_url:
            clean_url = clean_url.replace("&channel_binding=require", "").replace("channel_binding=require&", "").replace("channel_binding=require", "")
        return psycopg2.connect(clean_url, connect_timeout=10)

    def _init_tables(self):
        """Initializes tables in Neon PostgreSQL with parameter-safe DDL."""
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
                            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                        );
                    """)
                    # Audit & execution logs table (offloaded from local PC disk)
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS freeai_audit_logs (
                            id SERIAL PRIMARY KEY,
                            objective TEXT NOT NULL,
                            agent VARCHAR(100),
                            outcome JSONB,
                            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                        );
                    """)
                    conn.commit()
            logger.info("[NEON] Schema initialized successfully on Neon PostgreSQL.")
        except Exception as e:
            logger.error(f"[NEON] Table initialization error: {e}")

    def save_knowledge(self, query: str, provider: str, model: str, response: str) -> bool:
        """Saves a knowledge snippet to Neon DB using parameterized queries (SQLi safe)."""
        if not self.enabled:
            return False
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO freeai_knowledge (query, provider, model, response)
                        VALUES (%s, %s, %s, %s)
                        ON CONFLICT (query) DO UPDATE
                        SET response = EXCLUDED.response,
                            created_at = CURRENT_TIMESTAMP;
                    """, (query.strip(), provider, model, response))
                    conn.commit()
            logger.info(f"[NEON] Knowledge synced to Neon PostgreSQL for: '{query[:40]}...'")
            return True
        except Exception as e:
            logger.error(f"[NEON] Failed to save knowledge to Neon: {e}")
            return False

    def get_knowledge(self, query: str) -> Optional[str]:
        """Retrieves a cached knowledge snippet from Neon DB."""
        if not self.enabled:
            return None
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT response FROM freeai_knowledge WHERE query = %s LIMIT 1;", (query.strip(),))
                    row = cur.fetchone()
                    if row:
                        logger.info(f"[NEON] Knowledge retrieved from Neon for: '{query[:40]}...'")
                        return row[0]
        except Exception as e:
            logger.error(f"[NEON] Failed to query Neon: {e}")
        return None

    def log_audit_event(self, objective: str, agent: str, outcome: Dict[str, Any]) -> bool:
        """Stores execution history and audit logs remotely in Neon (0 byte local disk)."""
        if not self.enabled:
            return False
        try:
            import json
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        INSERT INTO freeai_audit_logs (objective, agent, outcome)
                        VALUES (%s, %s, %s);
                    """, (objective, agent, json.dumps(outcome)))
                    conn.commit()
            logger.info(f"[NEON] Audit event logged to Neon for objective: '{objective[:40]}...'")
            return True
        except Exception as e:
            logger.error(f"[NEON] Failed to log audit event to Neon: {e}")
            return False
