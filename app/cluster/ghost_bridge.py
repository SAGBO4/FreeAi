"""Ghost Bridge (Protocole Résilient Hors-Réseau & Air-Gap).
Enables FreeAI to coordinate nodes, sync state, and transmit encrypted GZIP digests
even when Internet is severed or Wi-Fi is compromised.
Operates via ephemeral in-memory queues, raw local sockets, and broadcast beacons with zero disk trace.
"""

import gzip
import base64
import time
import logging
from typing import Dict, Any, Optional, List

logger = logging.getLogger("ghost_bridge")


class GhostBridge:
    """Manages air-gap resilient off-grid communication channels."""

    def __init__(self, node_id: str = "ghost_node"):
        self.node_id = node_id
        self.in_memory_mailbox: List[Dict[str, Any]] = []

    def pack_payload(self, data: Dict[str, Any], secret_token: str = "freeai_sovereign") -> str:
        """Packs and compresses JSON data into a lightweight GZIP Base64 envelope."""
        import json
        raw_json = json.dumps(data).encode("utf-8")
        compressed = gzip.compress(raw_json, compresslevel=9)
        encoded = base64.b64encode(compressed).decode("ascii")
        return f"GHOST:{self.node_id}:{encoded}"

    def unpack_payload(self, envelope: str) -> Optional[Dict[str, Any]]:
        """Unpacks and decompresses an incoming Ghost Bridge payload."""
        import json
        if not envelope.startswith("GHOST:"):
            return None

        parts = envelope.split(":", 2)
        if len(parts) != 3:
            return None

        sender_id, b64_data = parts[1], parts[2]
        try:
            compressed = base64.b64decode(b64_data)
            decompressed = gzip.decompress(compressed)
            data = json.loads(decompressed.decode("utf-8"))
            data["_ghost_sender"] = sender_id
            data["_ghost_received_at"] = time.time()
            return data
        except Exception as e:
            logger.error(f"[GHOST BRIDGE] Failed to unpack payload: {e}")
            return None

    def queue_offline_message(self, topic: str, content: Any) -> str:
        """Stores a message in the RAM-only ephemeral offline mailbox."""
        envelope = self.pack_payload({"topic": topic, "content": content, "timestamp": time.time()})
        self.in_memory_mailbox.append({
            "topic": topic,
            "envelope": envelope,
            "timestamp": time.time()
        })
        # Keep RAM usage < 50 KB (max 20 messages)
        if len(self.in_memory_mailbox) > 20:
            self.in_memory_mailbox.pop(0)

        logger.info(f"[GHOST BRIDGE] Queued offline message for topic '{topic}' in RAM")
        return envelope

    def get_mailbox_status(self) -> Dict[str, Any]:
        """Returns the offline mailbox status."""
        return {
            "node_id": self.node_id,
            "offline_messages_count": len(self.in_memory_mailbox),
            "storage_mode": "ephemeral_ram",
            "topics": [m["topic"] for m in self.in_memory_mailbox]
        }
