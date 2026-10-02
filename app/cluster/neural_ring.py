"""Subnet Neural Ring (Calcul de Tenseurs en Anneau P2P & Pipeline Parallelism).
Allows a collection of modest, low-RAM computers on the LAN (e.g. 4 laptops with 4GB RAM each)
to pool their resources into a closed-loop compute ring.
A large model or complex task is segmented into N sequential pipeline stages,
each node processing its stage and streaming activation tensors to the next node in the ring.
"""

import time
import asyncio
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger("neural_ring")


class SubnetNeuralRing:
    """Manages pipeline parallelism across nodes in a circular network topology."""

    def __init__(self, cluster_manager):
        self.cluster_manager = cluster_manager
        self.ring_nodes: List[Dict[str, Any]] = []
        self.active_stages: int = 1

    def configure_ring(self, nodes: Optional[List[str]] = None) -> Dict[str, Any]:
        """Configures the ring topology from available cluster nodes or manual IP list."""
        all_nodes = []
        for n in self.cluster_manager.nodes.values():
            if isinstance(n, dict):
                st = n.get("status")
                node_dict = n
            else:
                st = getattr(n, "status", None)
                node_dict = n.to_dict() if hasattr(n, "to_dict") else vars(n)
            if st == "online":
                all_nodes.append(node_dict)

        if nodes:
            # Filter specifically requested nodes
            target_ids = set(nodes)
            self.ring_nodes = [n for n in all_nodes if n.get("id") in target_ids]
        else:
            self.ring_nodes = all_nodes

        # If no remote nodes, local machine forms a single-node ring
        if not self.ring_nodes:
            local_node = {
                "id": f"{self.cluster_manager.get_local_lan_ip()}:local",
                "host": self.cluster_manager.get_local_lan_ip(),
                "port": 8000,
                "node_type": "local_cpu",
                "status": "online",
                "stage_index": 0
            }
            self.ring_nodes = [local_node]

        # Assign circular pipeline stage indices
        self.active_stages = len(self.ring_nodes)
        for idx, node in enumerate(self.ring_nodes):
            node["stage_index"] = idx
            node["next_node_id"] = self.ring_nodes[(idx + 1) % self.active_stages]["id"]

        logger.info(f"[NEURAL RING] Ring configured with {self.active_stages} stages.")
        return self.get_ring_topology()

    def get_ring_topology(self) -> Dict[str, Any]:
        """Returns the current ring topology, stages, and pooled RAM estimate."""
        # 4GB RAM per node with 3.5GB budget
        pooled_ram_gb = round(self.active_stages * 3.5, 1)
        max_model_params = f"~{min(70, self.active_stages * 7)}B" if self.active_stages > 1 else "~1.5B - 3B"

        return {
            "stages_count": self.active_stages,
            "pooled_capacity_ram_gb": pooled_ram_gb,
            "max_supported_params": max_model_params,
            "topology": "closed_loop_ring",
            "stages": [
                {
                    "stage": n["stage_index"] + 1,
                    "node_id": n["id"],
                    "next_hop": n.get("next_node_id")
                }
                for n in self.ring_nodes
            ]
        }

    async def run_pipeline_forward(self, input_prompt: str, layers_count: int = 32) -> Dict[str, Any]:
        """Simulates and coordinates sequential pipeline execution across the ring nodes."""
        if not self.ring_nodes:
            self.configure_ring()

        t0 = time.time()
        stage_results = []
        current_data = f"Initial_Tensor_Embeddings({input_prompt[:40]})"

        layers_per_stage = max(1, layers_count // self.active_stages)

        for stage in self.ring_nodes:
            stage_idx = stage.get("stage_index", 0)
            start_layer = stage_idx * layers_per_stage
            end_layer = min(layers_count, (stage_idx + 1) * layers_per_stage)

            # Simulated tensor layer computation
            await asyncio.sleep(0.01)  # Minimal non-blocking latency
            output_tensor = f"Activations(Layer {start_layer}➔{end_layer} on {stage['id']})"
            stage_results.append({
                "stage": stage_idx + 1,
                "node_id": stage['id'],
                "layers": f"{start_layer}-{end_layer}",
                "input": current_data,
                "output": output_tensor
            })
            current_data = output_tensor

        total_latency = round((time.time() - t0) * 1000, 2)
        return {
            "success": True,
            "prompt": input_prompt,
            "total_stages": self.active_stages,
            "layers_executed": layers_count,
            "latency_ms": total_latency,
            "execution_trace": stage_results,
            "final_representation": current_data
        }
