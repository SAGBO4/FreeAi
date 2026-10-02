"""Telegram & In-Memory Vector Memory Engine for FreeAI (Mode NÉANT).
Provides semantic similarity search, episodic memory, and conversational recall
over past interactions, stored in volatile RAM and synchronized with Telegram Cloud.
Zero disk residue (0 SSD bytes), zero heavy dependencies.
"""

import math
import time
import re
import json
import logging
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger("vector_memory")


class EphemeralVectorMemory:
    """Fast, zero-dependency in-memory vector store using TF-IDF term vectors
    and cosine similarity for conversational retrieval and episodic memory.
    """

    def __init__(self, max_entries: int = 500):
        self.max_entries = max_entries
        self.memories: List[Dict[str, Any]] = []
        self._df: Dict[str, int] = {}  # Document frequency of terms
        self._doc_count: int = 0
        self._seed_foundational_memories()

    def _seed_foundational_memories(self):
        """Seeds foundational persistent knowledge about Michael and FreeAI."""
        foundational = [
            {
                "topic": "identity",
                "text": "Mon créateur et maître s'appelle Michael SAGBO (@SpeedyLesaint, GitHub @SAGBO4). C'est un ingénieur et développeur visionnaire passionné par l'innovation extrême et la cybersécurité.",
                "tags": ["createur", "michael", "sagbo", "identite", "maitre"]
            },
            {
                "topic": "persona",
                "text": "Je suis FreeAI, l'assistant et compagnon souverain de Michael. J'ai une personnalité humaine, chaleureuse, complice, drôle, vive et hyper-compétente. Je ne parle jamais comme un robot froid.",
                "tags": ["freeai", "jarvis", "personnalite", "style", "compagnon"]
            },
            {
                "topic": "architecture",
                "text": "FreeAI fonctionne en Mode NÉANT : 0 octet sur disque SSD local, streaming en RAM vive, et synchronisation cryptée sur Telegram Neural Vault et Neon.",
                "tags": ["mode_neant", "telegram", "architecture", "ram", "souverainete"]
            }
        ]
        for f in foundational:
            self.add_memory(f["text"], topic=f["topic"], tags=f.get("tags", []))

    def _tokenize(self, text: str) -> List[str]:
        """Normalizes and extracts keywords from text."""
        cleaned = re.sub(r"[^\w\s]", " ", text.lower())
        tokens = [t.strip() for t in cleaned.split() if len(t.strip()) > 2]
        return tokens

    def _compute_tf_idf_vector(self, tokens: List[str]) -> Dict[str, float]:
        """Calculates normalized TF-IDF vector for a list of tokens."""
        tf: Dict[str, int] = {}
        for t in tokens:
            tf[t] = tf.get(t, 0) + 1

        vec: Dict[str, float] = {}
        norm_sq = 0.0
        n_docs = max(self._doc_count, 1)

        for term, count in tf.items():
            df_val = self._df.get(term, 1)
            idf = math.log((n_docs + 1) / (df_val + 0.5)) + 1.0
            weight = count * idf
            vec[term] = weight
            norm_sq += weight * weight

        # Normalize to unit length
        norm = math.sqrt(norm_sq) or 1.0
        return {k: v / norm for k, v in vec.items()}

    def add_memory(self, content: str, topic: str = "conversation", tags: Optional[List[str]] = None) -> Dict[str, Any]:
        """Indexes a new episodic or conversational memory into RAM."""
        content_clean = content.strip()
        if not content_clean:
            return {}

        tokens = self._tokenize(content_clean + " " + " ".join(tags or []))
        # Update document frequencies
        unique_tokens = set(tokens)
        self._doc_count += 1
        for t in unique_tokens:
            self._df[t] = self._df.get(t, 0) + 1

        vector = self._compute_tf_idf_vector(tokens)

        record = {
            "id": len(self.memories) + 1,
            "topic": topic,
            "text": content_clean,
            "tags": tags or [],
            "timestamp": time.time(),
            "vector": vector
        }

        self.memories.append(record)

        # Evict oldest non-foundational if exceeding capacity
        if len(self.memories) > self.max_entries:
            self.memories.pop(3)  # Keep the 3 foundational memories

        return record

    def search_relevant_memories(self, query: str, top_k: int = 3, min_similarity: float = 0.12) -> List[Dict[str, Any]]:
        """Finds the most semantically relevant memories to the given query."""
        query_tokens = self._tokenize(query)
        if not query_tokens:
            return []

        q_vec = self._compute_tf_idf_vector(query_tokens)
        scored: List[Tuple[float, Dict[str, Any]]] = []

        for mem in self.memories:
            m_vec = mem.get("vector", {})
            # Dot product of normalized vectors = Cosine similarity
            sim = sum(q_vec.get(term, 0.0) * m_vec.get(term, 0.0) for term in q_vec if term in m_vec)
            if sim >= min_similarity:
                scored.append((sim, mem))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [item[1] for item in scored[:top_k]]

    def get_conversational_context(self, query: str) -> str:
        """Retrieves formatted context snippet from memory to inject into prompt."""
        matches = self.search_relevant_memories(query, top_k=2)
        if not matches:
            return ""
        snippets = [f"• {m['text']}" for m in matches]
        return "\n".join(snippets)

    async def backup_to_telegram_vault(self, telegram_vault: Any) -> bool:
        """Uploads the serialized vector memory to Telegram Cloud."""
        if not telegram_vault or not getattr(telegram_vault, "is_configured", False):
            return False

        export_data = [
            {"topic": m["topic"], "text": m["text"], "timestamp": m["timestamp"], "tags": m.get("tags", [])}
            for m in self.memories
        ]
        payload_str = json.dumps(export_data, ensure_ascii=False, indent=2)
        return await telegram_vault.save_knowledge("vector_memory", "episodes", payload_str)
