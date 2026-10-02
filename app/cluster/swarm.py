"""LAN Cluster & Distributed Compute Swarm for FreeAI.
Allows FreeAI to harness computational power from other idle computers on the local network (LAN)
and free online GPU endpoints (Google Colab, Modal, Groq, Hugging Face).

Key Capabilities:
1. Scan local LAN for available compute nodes (Ollama, llama.cpp, vLLM, FreeAI Workers, SSH).
2. Register and health-check remote LAN/Cloud GPU compute nodes.
3. In 'lesaintAi' mode (super-user with network/sudo privileges):
   - Proactive network discovery across subnet.
   - Remote worker initialization via SSH.
4. Offload heavy code generation, security audits, and LLM reasoning to remote nodes,
   freeing the local laptop's CPU and RAM completely.
"""

import os
import json
import time
import socket
import asyncio
import logging
import subprocess
from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse
import httpx

logger = logging.getLogger("freeai_cluster")


@dataclass
class ComputeNode:
    id: str
    host: str
    port: int
    node_type: str  # "ollama", "vllm", "openai_compatible", "ssh", "freeai_worker"
    status: str     # "online", "offline", "unverified"
    model_name: Optional[str] = None
    latency_ms: Optional[float] = None
    is_gpu: bool = False
    source: str = "lan"  # "lan", "online_gpu", "manual"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class LANClusterManager:
    """Orchestrates compute nodes across local network and cloud free GPUs."""

    STANDARD_INFERENCE_PORTS = {
        11434: "ollama",
        8080: "llama_cpp",
        8000: "vllm_or_worker",
        5000: "freeai_worker",
        22: "ssh"
    }

    def __init__(
        self,
        mode: str = "freeAi",
        allow_sudo: bool = False,
        allow_network: bool = True,
        initial_nodes: Optional[str] = None
    ):
        self.mode = mode
        self.allow_sudo = allow_sudo
        self.allow_network = allow_network
        self.nodes: Dict[str, ComputeNode] = {}

        # Load initial nodes from environment if provided
        nodes_env = initial_nodes or os.getenv("LAN_CLUSTER_NODES", "")
        if nodes_env:
            for item in nodes_env.split(","):
                item = item.strip()
                if item:
                    self.register_node(item)

        gpu_url = os.getenv("REMOTE_GPU_URL", "")
        if gpu_url:
            self.register_node(gpu_url, node_type="online_gpu")

    def update_permissions(self, mode: str, allow_sudo: bool, allow_network: bool = True):
        """Dynamically adjusts network and cluster permissions based on mode."""
        self.mode = mode
        self.allow_sudo = allow_sudo
        self.allow_network = allow_network

    def get_local_lan_ip(self) -> str:
        """Finds the primary local LAN IP address of this machine."""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.settimeout(0.5)
            # Connecting to a public DNS IP without sending packets reveals the default route IP
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
            return local_ip
        except Exception:
            return "127.0.0.1"

    def get_subnet(self) -> str:
        """Extracts the /24 subnet prefix from the local LAN IP."""
        local_ip = self.get_local_lan_ip()
        parts = local_ip.split(".")
        if len(parts) == 4 and parts[0] in ("192", "10", "172"):
            return f"{parts[0]}.{parts[1]}.{parts[2]}"
        return "192.168.1"

    def register_node(self, target: str, node_type: str = "auto") -> ComputeNode:
        """Registers a compute node (e.g. '192.168.1.50:11434' or 'http://colab-tunnel.bore.pub')."""
        target = target.strip()
        if not target.startswith("http://") and not target.startswith("https://"):
            target_url = f"http://{target}"
        else:
            target_url = target

        parsed = urlparse(target_url)
        host = parsed.hostname or "127.0.0.1"
        port = parsed.port or (443 if parsed.scheme == "https" else 80)

        # Detect node type from port if auto
        detected_type = node_type
        if detected_type == "auto":
            detected_type = self.STANDARD_INFERENCE_PORTS.get(port, "openai_compatible")

        is_gpu = "gpu" in detected_type or "colab" in host or port in (8000, 11434)
        source = "online_gpu" if ("colab" in host or "runpod" in host or "modal" in host or parsed.scheme == "https") else "lan"

        node_id = f"{host}:{port}"
        node = ComputeNode(
            id=node_id,
            host=host,
            port=port,
            node_type=detected_type,
            status="unverified",
            is_gpu=is_gpu,
            source=source
        )
        self.nodes[node_id] = node
        logger.info(f"[CLUSTER] Registered node {node_id} (type: {detected_type})")
        return node

    def remove_node(self, target: str) -> bool:
        """Removes a registered compute node."""
        target = target.strip().replace("http://", "").replace("https://", "").rstrip("/")
        if target in self.nodes:
            del self.nodes[target]
            return True
        return False

    async def probe_node(self, node: ComputeNode, timeout: float = 2.0) -> ComputeNode:
        """Checks if a compute node is alive and queries its available models."""
        base_url = f"http://{node.host}:{node.port}"
        if node.port == 443 or node.source == "online_gpu":
            base_url = f"https://{node.host}" if node.port == 443 else f"http://{node.host}:{node.port}"

        t0 = time.time()
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                # 1. Probe Ollama tags endpoint
                if node.node_type in ("ollama", "auto"):
                    try:
                        res = await client.get(f"{base_url}/api/tags")
                        if res.status_code == 200:
                            data = res.json()
                            models = [m.get("name") for m in data.get("models", [])]
                            node.status = "online"
                            node.node_type = "ollama"
                            node.model_name = models[0] if models else "llama3"
                            node.latency_ms = round((time.time() - t0) * 1000, 2)
                            return node
                    except Exception:
                        pass

                # 2. Probe OpenAI-compatible v1/models endpoint
                try:
                    res = await client.get(f"{base_url}/v1/models")
                    if res.status_code == 200:
                        data = res.json()
                        models = [m.get("id") for m in data.get("data", [])]
                        node.status = "online"
                        node.node_type = "openai_compatible"
                        node.model_name = models[0] if models else "default"
                        node.latency_ms = round((time.time() - t0) * 1000, 2)
                        return node
                except Exception:
                    pass

                # 3. Probe raw health/root endpoint
                try:
                    res = await client.get(base_url)
                    if res.status_code in (200, 404, 405):
                        node.status = "online"
                        node.latency_ms = round((time.time() - t0) * 1000, 2)
                        return node
                except Exception:
                    pass

        except Exception as e:
            logger.debug(f"[CLUSTER] Node {node.id} probe error: {e}")

        node.status = "offline"
        node.latency_ms = None
        return node

    async def check_all_nodes(self) -> List[ComputeNode]:
        """Probes all registered nodes concurrently."""
        tasks = [self.probe_node(n) for n in self.nodes.values()]
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        return list(self.nodes.values())

    async def scan_lan_for_nodes(
        self,
        ip_range_start: int = 1,
        ip_range_end: int = 30,
        ports: Optional[List[int]] = None
    ) -> List[ComputeNode]:
        """Scans the local subnet for active computers running inference servers."""
        if not self.allow_network:
            logger.warning("[CLUSTER] Network disabled by security settings.")
            return []

        subnet = self.get_subnet()
        target_ports = ports or [11434, 8080, 8000, 5000]
        discovered: List[ComputeNode] = []

        async def _check_host_port(ip: str, port: int):
            try:
                # Non-blocking async TCP connect probe
                _, writer = await asyncio.wait_for(
                    asyncio.open_connection(ip, port),
                    timeout=0.3
                )
                writer.close()
                await writer.wait_closed()

                node = self.register_node(f"{ip}:{port}")
                await self.probe_node(node)
                if node.status == "online":
                    discovered.append(node)
            except Exception:
                pass

        tasks = []
        for i in range(ip_range_start, ip_range_end + 1):
            ip = f"{subnet}.{i}"
            for p in target_ports:
                tasks.append(_check_host_port(ip, p))

        # Run scans in parallel batches to prevent overwhelming local socket limits
        batch_size = 40
        for i in range(0, len(tasks), batch_size):
            await asyncio.gather(*tasks[i:i + batch_size], return_exceptions=True)

        return discovered

    def deploy_or_check_ssh_node(self, target_ip: str, user: str = "root") -> Dict[str, Any]:
        """In 'lesaintAi' mode (sudo/admin), verifies or launches compute worker on another LAN machine via SSH."""
        if self.mode != "lesaintAi" and not self.allow_sudo:
            return {
                "success": False,
                "error": "Accès refusé : la connexion et le déploiement SSH requièrent le mode super-utilisateur (/mode lesaintAi)."
            }

        cmd = [
            "ssh",
            "-o", "BatchMode=yes",
            "-o", "ConnectTimeout=3",
            "-o", "StrictHostKeyChecking=no",
            f"{user}@{target_ip}",
            "uname -a && (nvidia-smi --query-gpu=name,memory.total --format=csv,noheader || lscpu | grep 'Model name')"
        ]

        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            if res.returncode == 0:
                output = res.stdout.strip()
                has_gpu = "nvidia" in output.lower() or "rtx" in output.lower() or "gtx" in output.lower() or "geforce" in output.lower()
                return {
                    "success": True,
                    "host": target_ip,
                    "has_gpu": has_gpu,
                    "hardware_specs": output,
                    "message": f"Nœud distant {target_ip} accessible via SSH ! Matériel : {output[:100]}"
                }
            else:
                return {
                    "success": False,
                    "host": target_ip,
                    "error": res.stderr.strip() or f"SSH exit code {res.returncode}"
                }
        except subprocess.TimeoutExpired:
            return {"success": False, "host": target_ip, "error": "Délai d'attente SSH dépassé (3s)"}
        except Exception as e:
            return {"success": False, "host": target_ip, "error": str(e)}

    async def dispatch_inference(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        timeout_sec: int = 30
    ) -> Optional[Dict[str, Any]]:
        """Dispatches inference to the best online LAN/GPU node, freeing local CPU/RAM."""
        online_nodes = [n for n in self.nodes.values() if n.status == "online"]
        if not online_nodes:
            return None

        # Prioritize GPU nodes and lowest latency
        selected_node = sorted(online_nodes, key=lambda n: (not n.is_gpu, n.latency_ms or 9999))[0]
        base_url = f"http://{selected_node.host}:{selected_node.port}"

        try:
            if selected_node.node_type == "ollama":
                payload = {
                    "model": selected_node.model_name or "llama3",
                    "prompt": prompt,
                    "system": system_prompt or "",
                    "stream": False
                }
                async with httpx.AsyncClient(timeout=timeout_sec) as client:
                    res = await client.post(f"{base_url}/api/generate", json=payload)
                    if res.status_code == 200:
                        ans = res.json().get("response", "")
                        return {
                            "success": True,
                            "source": "lan_cluster_node",
                            "node_id": selected_node.id,
                            "is_gpu": selected_node.is_gpu,
                            "response": ans
                        }

            # OpenAI compatible endpoint (vLLM, FreeAI worker, Colab server)
            headers = {"Content-Type": "application/json"}
            payload = {
                "model": selected_node.model_name or "default",
                "messages": [
                    {"role": "system", "content": system_prompt or "You are a distributed AI worker."},
                    {"role": "user", "content": prompt}
                ]
            }
            async with httpx.AsyncClient(timeout=timeout_sec) as client:
                res = await client.post(f"{base_url}/v1/chat/completions", headers=headers, json=payload)
                if res.status_code == 200:
                    ans = res.json()["choices"][0]["message"]["content"]
                    return {
                        "success": True,
                        "source": "lan_cluster_node",
                        "node_id": selected_node.id,
                        "is_gpu": selected_node.is_gpu,
                        "response": ans
                    }
        except Exception as e:
            logger.error(f"[CLUSTER] Dispatch to {selected_node.id} failed: {e}")

        return None

    def get_summary(self) -> Dict[str, Any]:
        """Returns the status summary of the cluster swarm."""
        nodes_list = [n.to_dict() for n in self.nodes.values()]
        online_count = sum(1 for n in self.nodes.values() if n.status == "online")
        gpu_count = sum(1 for n in self.nodes.values() if n.status == "online" and n.is_gpu)

        return {
            "total_nodes": len(self.nodes),
            "online_nodes": online_count,
            "gpu_nodes": gpu_count,
            "local_lan_ip": self.get_local_lan_ip(),
            "subnet": f"{self.get_subnet()}.0/24",
            "nodes": nodes_list
        }
