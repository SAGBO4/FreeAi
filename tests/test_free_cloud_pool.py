"""Tests for FreeCloudPool and Free VPS Matrix."""

import unittest
from app.cluster.free_cloud_pool import FreeCloudPool, CloudProviderType, FreeTierNode


class TestFreeCloudPool(unittest.TestCase):
    def setUp(self):
        self.pool = FreeCloudPool(mode="freeAi")

    def test_default_catalog_initialized(self):
        nodes = self.pool.list_nodes()
        self.assertGreaterEqual(len(nodes), 4)
        names = [n["name"] for n in nodes]
        self.assertTrue(any("Oracle" in name for name in names))
        self.assertTrue(any("GitHub" in name for name in names))
        self.assertTrue(any("Google Cloud" in name for name in names))

    def test_add_and_remove_custom_vps(self):
        custom_node = self.pool.add_node(
            name="Free VPS Ubuntu Oracle",
            provider=CloudProviderType.CUSTOM_VPS,
            endpoint="192.168.1.100",
            specs={"cpu": "2 vCPU", "ram_gb": 4, "cost": "0€"},
            capabilities=["sentinel_defense", "compute"]
        )
        self.assertIsNotNone(custom_node.id)
        self.assertEqual(custom_node.status, "active")

        # Verify it appears in list
        nodes = self.pool.list_nodes()
        self.assertTrue(any(n["id"] == custom_node.id for n in nodes))

        # Test ping
        latency = self.pool.ping_node(custom_node.id)
        self.assertGreater(latency, 0)

        # Remove node
        removed = self.pool.remove_node(custom_node.id)
        self.assertTrue(removed)
        self.assertIsNone(self.pool.get_node(custom_node.id))

    def test_dispatch_workload_neural_train(self):
        result = self.pool.dispatch_workload(
            task_type="neural_train",
            payload={"epochs": 1, "dataset": "consensus_pairs"}
        )
        self.assertTrue(result["success"])
        self.assertIn("dispatched_to", result)
        self.assertIn("node_id", result)

    def test_dispatch_workload_sentinel(self):
        result = self.pool.dispatch_workload(
            task_type="sentinel_watchdog",
            payload={"watch_target": "freeai_host"}
        )
        self.assertTrue(result["success"])
        self.assertIn("dispatched_to", result)

    def test_ping_all(self):
        latencies = self.pool.ping_all()
        self.assertGreater(len(latencies), 0)
        for nid, lat in latencies.items():
            self.assertGreaterEqual(lat, 0)
