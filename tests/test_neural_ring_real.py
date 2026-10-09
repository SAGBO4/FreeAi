#!/usr/bin/env python3
"""
Unit and Integration Tests for Real Subnet Neural Ring (F-30).
Verifies:
- AC1: Real mathematical tensor forward computation (no mock sleep or string concatenation).
- AC2: LZ4 wire compression, binary serialization and SHA-256 checksum verification.
- AC3: Sequential P2P ring stage execution across circular topology.
- AC4: Backward compatibility with cluster manager and existing TUI/CLI expectations.
"""

import unittest
import asyncio
import numpy as np
from unittest.mock import MagicMock
from app.cluster.neural_ring import (
    SubnetNeuralRing,
    NeuralPipelineStageBlock,
    TensorActivationPacket
)


class TestRealSubnetNeuralRing(unittest.TestCase):
    def setUp(self):
        mock_cluster = MagicMock()
        node1 = MagicMock(status="online")
        node1.to_dict.return_value = {"id": "192.168.1.101:8000", "status": "online"}
        node2 = MagicMock(status="online")
        node2.to_dict.return_value = {"id": "192.168.1.102:8000", "status": "online"}
        node3 = MagicMock(status="online")
        node3.to_dict.return_value = {"id": "192.168.1.103:8000", "status": "online"}

        mock_cluster.nodes = {
            "192.168.1.101:8000": node1,
            "192.168.1.102:8000": node2,
            "192.168.1.103:8000": node3
        }
        mock_cluster.get_local_lan_ip.return_value = "192.168.1.100"
        self.ring = SubnetNeuralRing(cluster_manager=mock_cluster)

    def test_ac1_real_tensor_block_computation(self):
        """AC1: NeuralPipelineStageBlock executes real matrix operations and returns valid tensor."""
        dim = 128
        block = NeuralPipelineStageBlock(stage_id=1, dim=dim, seed=42)
        input_tensor = np.ones((1, dim), dtype=np.float32)

        output_tensor = block.forward(input_tensor)

        # Output must be real numpy float32 array with correct shape
        self.assertIsInstance(output_tensor, np.ndarray)
        self.assertEqual(output_tensor.shape, (1, dim))
        self.assertEqual(output_tensor.dtype, np.float32)

        # Must not be equal to input (real transformation applied)
        self.assertFalse(np.allclose(output_tensor, input_tensor))
        # Norm must be finite and positive
        norm = float(np.linalg.norm(output_tensor))
        self.assertGreater(norm, 0.0)
        self.assertTrue(np.isfinite(norm))

    def test_ac2_tensor_packet_serialization_and_checksum(self):
        """AC2: TensorActivationPacket compresses via LZ4 and verifies SHA-256."""
        dim = 256
        raw_tensor = np.random.randn(1, dim).astype(np.float32)
        packet = TensorActivationPacket.from_tensor(
            source_node="node1",
            target_node="node2",
            stage_index=0,
            tensor=raw_tensor
        )

        wire_bytes = packet.to_wire()
        self.assertIsInstance(wire_bytes, bytes)
        self.assertGreater(len(wire_bytes), 0)

        # Reconstruction & Verification
        unpacked_packet = TensorActivationPacket.from_wire(wire_bytes)
        self.assertEqual(unpacked_packet.source_node, "node1")
        self.assertEqual(unpacked_packet.target_node, "node2")
        self.assertEqual(unpacked_packet.stage_index, 0)
        self.assertEqual(unpacked_packet.checksum, packet.checksum)

        restored_tensor = unpacked_packet.get_tensor()
        self.assertEqual(restored_tensor.shape, raw_tensor.shape)
        np.testing.assert_allclose(restored_tensor, raw_tensor, atol=1e-6)

    def test_ac2_tampered_packet_raises_error(self):
        """AC2: Tampered payload bytes trigger cryptographic integrity error."""
        raw_tensor = np.ones((1, 64), dtype=np.float32)
        packet = TensorActivationPacket.from_tensor(
            source_node="n1", target_node="n2", stage_index=1, tensor=raw_tensor
        )
        wire_bytes = bytearray(packet.to_wire())
        # Corrupt last byte
        wire_bytes[-1] ^= 0xFF

        with self.assertRaises(ValueError):
            TensorActivationPacket.from_wire(bytes(wire_bytes))

    def test_ac3_pipeline_forward_pass_with_real_tensors(self):
        """AC3: Pipeline executes across all ring nodes with real tensor activations."""
        async def _run():
            self.ring.configure_ring()
            res = await self.ring.run_pipeline_forward(
                input_prompt="Neural distributed tensor pipeline test",
                layers_count=24
            )
            self.assertTrue(res["success"])
            self.assertEqual(res["total_stages"], 3)
            self.assertEqual(res["layers_executed"], 24)
            self.assertEqual(len(res["execution_trace"]), 3)

            # Trace must contain real tensor metrics
            for trace in res["execution_trace"]:
                self.assertIn("tensor_norm", trace)
                self.assertIn("tensor_shape", trace)
                self.assertIn("checksum", trace)
                self.assertGreater(trace["tensor_norm"], 0.0)
                self.assertGreater(trace["wire_bytes_compressed"], 0)

            # Final representation contains real mathematical summary
            self.assertIn("final_tensor_norm", res)
            self.assertIn("dim", res)
            self.assertGreater(res["final_tensor_norm"], 0.0)

        asyncio.run(_run())

    def test_ac4_single_node_local_fallback(self):
        """AC4: When no remote nodes are present, local ring operates with real tensors."""
        mock_empty_cluster = MagicMock()
        mock_empty_cluster.nodes = {}
        mock_empty_cluster.get_local_lan_ip.return_value = "127.0.0.1"

        local_ring = SubnetNeuralRing(cluster_manager=mock_empty_cluster)
        topo = local_ring.configure_ring()
        self.assertEqual(topo["stages_count"], 1)

        async def _run():
            res = await local_ring.run_pipeline_forward("Autonomous local prompt", layers_count=12)
            self.assertTrue(res["success"])
            self.assertEqual(res["total_stages"], 1)
            self.assertGreater(res["final_tensor_norm"], 0.0)

        asyncio.run(_run())


if __name__ == "__main__":
    unittest.main()
