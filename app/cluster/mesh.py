"""Zero-Conf P2P Mesh Swarm for FreeAI.
Discovers and networks compute nodes across local Wi-Fi / Ethernet automatically
without manual IP configuration using UDP Broadcast Beacons & Gossip Announcements.
"""

import os
import json
import time
import socket
import asyncio
import logging
from typing import Dict, Any, List, Optional, Callable

logger = logging.getLogger("freeai_mesh")


class P2PMeshBeacon:
    """Listens for and broadcasts discovery beacons to form a zero-configuration compute mesh."""

    BEACON_PORT = 41234
    BEACON_MAGIC = "FREEAI_MESH_V1"

    def __init__(
        self,
        node_id: Optional[str] = None,
        node_port: int = 8000,
        is_gpu: bool = False,
        allow_network: bool = True
    ):
        self.hostname = socket.gethostname()
        self.node_id = node_id or f"{self.hostname}_{int(time.time())}"
        self.node_port = node_port
        self.is_gpu = is_gpu
        self.allow_network = allow_network
        self.discovered_peers: Dict[str, Dict[str, Any]] = {}
        self._running = False
        self._listener_task: Optional[asyncio.Task] = None
        self._broadcaster_task: Optional[asyncio.Task] = None

    def get_local_ip(self) -> str:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.settimeout(0.5)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "127.0.0.1"

    def create_beacon_payload(self) -> bytes:
        payload = {
            "magic": self.BEACON_MAGIC,
            "node_id": self.node_id,
            "hostname": self.hostname,
            "ip": self.get_local_ip(),
            "port": self.node_port,
            "is_gpu": self.is_gpu,
            "timestamp": time.time()
        }
        return json.dumps(payload).encode("utf-8")

    async def broadcast_beacon_once(self) -> bool:
        """Sends a single UDP broadcast beacon on the local subnet."""
        if not self.allow_network:
            return False

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            sock.setblocking(False)

            data = self.create_beacon_payload()
            # Broadcast to 255.255.255.255
            loop = asyncio.get_running_loop()
            await loop.sock_sendto(sock, data, ("<broadcast>", self.BEACON_PORT))
            sock.close()
            return True
        except Exception as e:
            logger.debug(f"[MESH] Broadcast error: {e}")
            return False

    def handle_incoming_beacon(self, raw_data: bytes, addr: tuple) -> Optional[Dict[str, Any]]:
        """Parses and registers an incoming peer beacon."""
        try:
            data = json.loads(raw_data.decode("utf-8"))
            if data.get("magic") != self.BEACON_MAGIC:
                return None

            peer_id = data.get("node_id")
            if peer_id == self.node_id:
                return None  # Ignore self-beacon

            peer_ip = addr[0]
            peer_port = data.get("port", 8000)
            peer_info = {
                "node_id": peer_id,
                "hostname": data.get("hostname", "unknown"),
                "ip": peer_ip,
                "port": peer_port,
                "target": f"{peer_ip}:{peer_port}",
                "is_gpu": data.get("is_gpu", False),
                "last_seen": time.time()
            }
            self.discovered_peers[peer_id] = peer_info
            logger.info(f"[MESH] Discovered zero-conf peer: {peer_info['target']} ({peer_info['hostname']})")
            return peer_info
        except Exception:
            return None

    async def listen_for_beacons(self, duration_sec: float = 2.0) -> List[Dict[str, Any]]:
        """Listens for UDP beacons from neighboring computers for a short burst."""
        if not self.allow_network:
            return []

        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            if hasattr(socket, "SO_REUSEPORT"):
                try:
                    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
                except Exception:
                    pass
            sock.bind(("", self.BEACON_PORT))
            sock.setblocking(False)
        except Exception as e:
            logger.warning(f"[MESH] Could not bind mesh port {self.BEACON_PORT}: {e}")
            sock.close()
            return list(self.discovered_peers.values())

        loop = asyncio.get_running_loop()
        t_end = time.time() + duration_sec

        try:
            while time.time() < t_end:
                timeout = max(0.1, t_end - time.time())
                try:
                    data, addr = await asyncio.wait_for(loop.sock_recvfrom(sock, 2048), timeout=timeout)
                    self.handle_incoming_beacon(data, addr)
                except asyncio.TimeoutError:
                    break
                except Exception:
                    break
        finally:
            sock.close()

        return list(self.discovered_peers.values())

    def get_mesh_status(self) -> Dict[str, Any]:
        """Returns the summary of discovered zero-configuration mesh peers."""
        now = time.time()
        # Keep peers seen within last 120 seconds
        active_peers = [p for p in self.discovered_peers.values() if (now - p.get("last_seen", 0)) < 120]
        return {
            "node_id": self.node_id,
            "hostname": self.hostname,
            "local_ip": self.get_local_ip(),
            "mesh_port": self.BEACON_PORT,
            "active_peers_count": len(active_peers),
            "peers": active_peers
        }
