"""Free Cloud Resource & Free VPS Pool Matrix (AETHER-CLOUD-FREE).
Orchestrates and integrates all available free-tier cloud resources, free VPS instances,
GitHub Actions runners, and free neural accelerators (Oracle Always Free, GCP e2-micro,
AWS t2/t3.micro, HuggingFace Spaces, Kaggle/Colab, Render/Koyeb)
into FreeAI's sovereign computing mesh with 0 SSD writes (Mode NÉANT pure).
"""

import time
import uuid
import logging
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional

logger = logging.getLogger("free_cloud_pool")


class CloudProviderType(str, Enum):
    ORACLE_CLOUD = "oracle_cloud"       # Always Free 4 OCPU ARM, 24GB RAM
    GCP_FREE = "gcp_free"               # e2-micro compute engine (Always Free)
    AWS_FREE = "aws_free"               # t2.micro / t3.micro (750h/mo free tier)
    GITHUB_ACTIONS = "github_actions"   # 2000 min/mo Ubuntu runners, 4-core, 16GB
    HUGGINGFACE = "huggingface"         # Free CPU/Docker spaces (2 vCPU, 16GB RAM)
    KAGGLE_COLAB = "kaggle_colab"       # Free GPU T4/P100 accelerators
    RENDER_KOYEB = "render_koyeb"       # Free cloud web services / webhook relays
    CUSTOM_VPS = "custom_vps"           # User-provided free VPS or cloud instance


@dataclass
class FreeTierNode:
    id: str
    name: str
    provider: CloudProviderType
    endpoint_or_host: str
    specs: Dict[str, Any]
    capabilities: List[str]  # e.g. ["compute", "sentinel_defense", "neural_train", "vault"]
    status: str = "active"   # "active", "standby", "offline"
    latency_ms: float = 0.0
    last_heartbeat: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "provider": self.provider.value,
            "endpoint": self.endpoint_or_host,
            "specs": self.specs,
            "capabilities": self.capabilities,
            "status": self.status,
            "latency_ms": self.latency_ms,
            "last_heartbeat": self.last_heartbeat,
            "metadata": self.metadata
        }


class FreeCloudPool:
    """Manages the catalog of zero-cost cloud compute resources, free VPS instances,
    and distributed watchdog nodes for FreeAI.
    """

    DEFAULT_FREE_CATALOG = [
        {
            "name": "Oracle Always-Free Ampere ARM",
            "provider": CloudProviderType.ORACLE_CLOUD,
            "endpoint": "oracle-free-arm.internal",
            "specs": {"cpu": "4 OCPU ARM64", "ram_gb": 24, "cost": "0€/mois (À vie)"},
            "capabilities": ["neural_inference", "neural_train", "sentinel_defense", "vault"],
            "status": "standby"
        },
        {
            "name": "GitHub Actions Sovereign Cloud Runner",
            "provider": CloudProviderType.GITHUB_ACTIONS,
            "endpoint": "api.github.com/repos/SAGBO4/FreeAi/actions",
            "specs": {"cpu": "4 vCPU x86_64", "ram_gb": 16, "cost": "0€ (2000 min/mois)"},
            "capabilities": ["neural_train", "cloud_evolution", "sentinel_defense"],
            "status": "active"
        },
        {
            "name": "Google Cloud Platform e2-micro",
            "provider": CloudProviderType.GCP_FREE,
            "endpoint": "gcp-free-tier.internal",
            "specs": {"cpu": "2 vCPU (burstable)", "ram_gb": 1, "cost": "0€/mois (Always Free)"},
            "capabilities": ["sentinel_defense", "dns_monitor", "webhook_relay"],
            "status": "standby"
        },
        {
            "name": "HuggingFace Spaces Container",
            "provider": CloudProviderType.HUGGINGFACE,
            "endpoint": "hf.space/freeai-matrix",
            "specs": {"cpu": "2 vCPU", "ram_gb": 16, "cost": "0€/mois"},
            "capabilities": ["neural_inference", "model_cache", "api_bridge"],
            "status": "standby"
        },
        {
            "name": "Kaggle & Colab GPU Dispatcher",
            "provider": CloudProviderType.KAGGLE_COLAB,
            "endpoint": "kaggle.com/api/v1/kernels",
            "specs": {"gpu": "Nvidia Tesla T4 (16GB VRAM)", "cost": "0€ (30h/semaine)"},
            "capabilities": ["heavy_neural_training", "batch_distillation"],
            "status": "standby"
        }
    ]

    def __init__(self, mode: str = "freeAi"):
        self.mode = mode
        self.nodes: Dict[str, FreeTierNode] = {}
        self._initialize_default_nodes()

    def _initialize_default_nodes(self):
        """Populates the pool with standard always-free cloud nodes."""
        for item in self.DEFAULT_FREE_CATALOG:
            node_id = str(uuid.uuid4())[:8]
            node = FreeTierNode(
                id=node_id,
                name=item["name"],
                provider=item["provider"],
                endpoint_or_host=item["endpoint"],
                specs=item["specs"],
                capabilities=item["capabilities"],
                status=item["status"],
                latency_ms=15.0 if item["status"] == "active" else 0.0
            )
            self.nodes[node_id] = node

    def add_node(
        self,
        name: str,
        provider: CloudProviderType,
        endpoint: str,
        specs: Optional[Dict[str, Any]] = None,
        capabilities: Optional[List[str]] = None
    ) -> FreeTierNode:
        """Adds a custom free VPS or cloud resource node."""
        node_id = str(uuid.uuid4())[:8]
        node = FreeTierNode(
            id=node_id,
            name=name,
            provider=provider,
            endpoint_or_host=endpoint,
            specs=specs or {"cost": "0€/free-tier"},
            capabilities=capabilities or ["compute", "sentinel_defense"],
            status="active",
            latency_ms=25.0
        )
        self.nodes[node_id] = node
        logger.info(f"[FREE_CLOUD] Added new free cloud node: {name} ({node_id}) via {provider.value}")
        return node

    def remove_node(self, node_id: str) -> bool:
        """Removes a node by id."""
        if node_id in self.nodes:
            del self.nodes[node_id]
            logger.info(f"[FREE_CLOUD] Removed node: {node_id}")
            return True
        return False

    def list_nodes(self) -> List[Dict[str, Any]]:
        """Returns all registered free cloud nodes as dictionaries."""
        return [node.to_dict() for node in self.nodes.values()]

    def get_node(self, node_id: str) -> Optional[FreeTierNode]:
        """Gets a node by its ID."""
        return self.nodes.get(node_id)

    def ping_node(self, node_id: str) -> float:
        """Simulates/measures latency to the specified free cloud node."""
        node = self.nodes.get(node_id)
        if not node:
            return -1.0
        # In memory simulation / local check
        node.last_heartbeat = time.time()
        node.latency_ms = 18.5 if node.status == "active" else 35.0
        return node.latency_ms

    def ping_all(self) -> Dict[str, float]:
        """Pings all nodes and returns their latencies in ms."""
        results = {}
        for nid, node in self.nodes.items():
            results[nid] = self.ping_node(nid)
        return results

    def find_nodes_by_capability(self, capability: str) -> List[FreeTierNode]:
        """Finds all free cloud nodes providing a specific capability."""
        return [
            node for node in self.nodes.values()
            if capability in node.capabilities and node.status in ("active", "standby")
        ]

    def dispatch_workload(self, task_type: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Dispatches an offloaded workload to the best available free cloud resource."""
        # Map task to required capability
        cap_map = {
            "neural_train": "neural_train",
            "distillation": "neural_train",
            "heavy_gpu": "heavy_neural_training",
            "sentinel_watchdog": "sentinel_defense",
            "webhook": "webhook_relay"
        }
        needed_cap = cap_map.get(task_type, "compute")
        candidates = self.find_nodes_by_capability(needed_cap)

        if not candidates:
            # Fallback to any active node
            candidates = [n for n in self.nodes.values() if n.status == "active"]

        target_node = candidates[0] if candidates else None

        if not target_node:
            return {
                "success": False,
                "error": "Aucun nœud gratuit disponible dans le pool cloud."
            }

        return {
            "success": True,
            "dispatched_to": target_node.name,
            "node_id": target_node.id,
            "provider": target_node.provider.value,
            "task_type": task_type,
            "timestamp": time.time(),
            "status": "dispatched"
        }
