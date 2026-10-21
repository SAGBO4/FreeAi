"""
Tests for Feature F-32: Sovereign P2P Voice Conduit & Audio Mesh (SVC).
Validates AC1 through AC5:
- AC1: Cryptographic Audio Framing & Session Handshake (HMAC-SHA256, sequence counter)
- AC2: Volatile Jitter Ring Buffer & Out-of-order handling
- AC3: Carrier-Free P2P Addressing & Transport Routing (Tor SOCKS5 / Direct P2P)
- AC4: Cognitive AI Voice Ingestion & Audio Loopback Bridge
- AC5: Tamper resistance, zero-simulation, and breakage resilience
"""

import asyncio
import os
import time
import unittest
import hmac
import hashlib

from app.network.sovereign_voice_conduit import (
    VoicePacket,
    VoiceJitterBuffer,
    SovereignVoiceConduit,
    VoiceCognitiveBridge,
    PeerIdentity,
)


class TestSovereignVoiceConduit(unittest.TestCase):

    def test_ac1_voice_packet_cryptographic_framing(self):
        """Verify HMAC-SHA256 packet authentication and tamper rejection."""
        secret_key = b"sovereign_voice_secret_test_key"
        payload = b"\x00\x01\x02\x03" * 64  # simulated PCM audio chunk (256 bytes)

        packet = VoicePacket.create(
            seq=1,
            timestamp_ms=1000,
            payload=payload,
            secret_key=secret_key,
            channel_id="chan-alpha",
        )

        # Valid verification
        self.assertTrue(packet.verify(secret_key))
        self.assertEqual(packet.seq, 1)
        self.assertEqual(packet.channel_id, "chan-alpha")

        # Serialized bytes test
        raw_bytes = packet.to_bytes()
        restored = VoicePacket.from_bytes(raw_bytes)
        self.assertTrue(restored.verify(secret_key))
        self.assertEqual(restored.payload, payload)

        # Tamper detection
        tampered_bytes = bytearray(raw_bytes)
        tampered_bytes[-1] ^= 0xFF  # flip a bit in payload or hmac
        tampered_packet = VoicePacket.from_bytes(bytes(tampered_bytes))
        self.assertFalse(tampered_packet.verify(secret_key))

    def test_ac2_jitter_buffer_ordering_and_telemetry(self):
        """Verify volatile jitter buffer re-orders out-of-order packets and drops duplicates."""
        secret_key = b"secret_key"
        buf = VoiceJitterBuffer(max_packets=32)

        p1 = VoicePacket.create(seq=1, timestamp_ms=100, payload=b"audio1", secret_key=secret_key)
        p2 = VoicePacket.create(seq=2, timestamp_ms=120, payload=b"audio2", secret_key=secret_key)
        p3 = VoicePacket.create(seq=3, timestamp_ms=140, payload=b"audio3", secret_key=secret_key)

        # Insert out of order: 2, 1, 3
        buf.push(p2)
        buf.push(p1)
        buf.push(p3)

        # Pop ordered
        self.assertEqual(buf.pop_ordered().seq, 1)
        self.assertEqual(buf.pop_ordered().seq, 2)
        self.assertEqual(buf.pop_ordered().seq, 3)
        self.assertIsNone(buf.pop_ordered())

        # Duplicate rejection
        buf.push(p1)
        buf.push(p1)
        self.assertEqual(buf.qsize, 1)

    def test_ac3_peer_identity_validation(self):
        """Verify address parsing: accepts p2p:// and onion://; rejects invalid carriers/numbers."""
        valid_p2p = PeerIdentity.parse("p2p://node_alpha_98f1")
        self.assertEqual(valid_p2p.scheme, "p2p")
        self.assertEqual(valid_p2p.node_id, "node_alpha_98f1")

        valid_onion = PeerIdentity.parse("onion://expyuzv732kjlms6.onion:9050")
        self.assertEqual(valid_onion.scheme, "onion")
        self.assertIn("expyuzv732kjlms6.onion", valid_onion.node_id)

        # Rejection of phone numbers, telecom IMSI, or invalid schemes
        with self.assertRaises(ValueError):
            PeerIdentity.parse("+33612345678")

        with self.assertRaises(ValueError):
            PeerIdentity.parse("tel:0612345678")

        with self.assertRaises(ValueError):
            PeerIdentity.parse("http://malicious.link")

    def test_ac3_p2p_socket_exchange_in_ram(self):
        """Verify live peer-to-peer audio packet exchange between two conduits in volatile RAM."""
        async def _test():
            secret = b"mutual_mesh_secret_key"
            alice = SovereignVoiceConduit(node_id="node_alice", secret_key=secret, port=18765)
            bob = SovereignVoiceConduit(node_id="node_bob", secret_key=secret, port=18766)

            try:
                await alice.start()
                await bob.start()

                # Alice sends audio chunk to Bob
                audio_frame = b"raw_pcm_frame_data_44100hz"
                sent = await alice.send_audio_to_peer(
                    peer_host="127.0.0.1",
                    peer_port=18766,
                    payload=audio_frame,
                    channel_id="direct_session",
                )
                self.assertTrue(sent)

                # Wait for Bob's jitter buffer to receive
                received_packet = None
                for _ in range(20):
                    if bob.jitter_buffer.qsize > 0:
                        received_packet = bob.jitter_buffer.pop_ordered()
                        break
                    await asyncio.sleep(0.05)

                self.assertIsNotNone(received_packet)
                self.assertEqual(received_packet.payload, audio_frame)
                self.assertTrue(received_packet.verify(secret))
            finally:
                await alice.stop()
                await bob.stop()

        asyncio.run(_test())

    def test_ac4_cognitive_ai_voice_bridge(self):
        """Verify cognitive AI bridge feeds incoming audio and generates synthesized response frames in RAM."""
        async def _test():
            bridge = VoiceCognitiveBridge()
            secret = b"test_secret"

            # Feed input audio frame
            pcm_input = b"\x10\x20" * 128
            packet = VoicePacket.create(seq=1, timestamp_ms=200, payload=pcm_input, secret_key=secret)

            ingested = bridge.ingest_audio_packet(packet)
            self.assertTrue(ingested)
            self.assertEqual(bridge.buffered_audio_bytes, len(pcm_input))

            # Synthesize AI vocal reply
            response_packets = await bridge.synthesize_speech_response(
                text_response="Souveraineté validée. Réseau P2P actif.",
                secret_key=secret,
                channel_id="chan_ai",
            )

            self.assertGreater(len(response_packets), 0)
            for p in response_packets:
                self.assertTrue(p.verify(secret))
                self.assertEqual(p.channel_id, "chan_ai")
                self.assertGreater(len(p.payload), 0)

        asyncio.run(_test())

    def test_ac5_tamper_and_breakage_resilience(self):
        """Verify resilience under malformed packets, socket disconnects and Tor offline fallback."""
        async def _test():
            conduit = SovereignVoiceConduit(node_id="resilient_node", secret_key=b"k", port=18770)
            await conduit.start()

            try:
                # Pushing corrupted raw bytes to receive handler
                corrupted_bytes = b"garbage_non_json_or_bad_payload"
                handled = conduit.handle_incoming_raw_bytes(corrupted_bytes, ("127.0.0.1", 9999))
                self.assertFalse(handled)

                # Check Tor status probe
                tor_status = conduit.probe_tor_conduit()
                self.assertIn("is_tor_active", tor_status)
                self.assertIn("mode", tor_status)

                # Send to unreachable port returns False, no crash
                result = await conduit.send_audio_to_peer("127.0.0.1", 59999, b"test", "chan")
                self.assertFalse(result)
            finally:
                await conduit.stop()

        asyncio.run(_test())

    def test_ac6_tech_lead_orchestrator_voice_routing(self):
        """AC6: TechLeadOrchestrator routes '/call' to SovereignVoiceConduit directly."""
        from app.orchestrator.orchestrator import TechLeadOrchestrator
        from app.tools.gateway import ToolGateway
        from app.resource_manager.watchdog import ResourceManager

        async def _test():
            gw = ToolGateway(workspace_root="/tmp")
            rm = ResourceManager()
            orch = TechLeadOrchestrator(tool_gateway=gw, resource_manager=rm)

            res = await orch.handle_objective("/call p2p://node_bravo", autonomous=False)
            self.assertTrue(res["success"])
            self.assertEqual(res["assigned_agent"], "sovereign_voice_conduit")
            self.assertIn("SOVEREIGN VOICE CONDUIT", res["output"])
            self.assertIn("p2p://", res["output"])

        asyncio.run(_test())

    def test_ac1_packet_framing_rejection_of_truncated_and_bad_magic(self):
        """AC1: VoicePacket rejects truncated packets and invalid magic bytes with ValueError."""
        # Truncated data
        with self.assertRaises(ValueError):
            VoicePacket.from_bytes(b"VC" + b"\x00" * 5)

        # Invalid magic header
        valid_packet = VoicePacket.create(1, 100, b"data", b"key").to_bytes()
        corrupted_magic = b"XX" + valid_packet[2:]
        with self.assertRaises(ValueError):
            VoicePacket.from_bytes(corrupted_magic)

    def test_ac2_jitter_buffer_capacity_eviction(self):
        """AC2: JitterBuffer evicts oldest packet when capacity is exceeded."""
        buf = VoiceJitterBuffer(max_packets=3)
        secret = b"k"
        p1 = VoicePacket.create(1, 100, b"1", secret)
        p2 = VoicePacket.create(2, 101, b"2", secret)
        p3 = VoicePacket.create(3, 102, b"3", secret)
        p4 = VoicePacket.create(4, 103, b"4", secret)

        buf.push(p1)
        buf.push(p2)
        buf.push(p3)
        self.assertEqual(buf.qsize, 3)

        # Pushing 4 should evict oldest (seq 1)
        buf.push(p4)
        self.assertEqual(buf.qsize, 3)
        first_pop = buf.pop_ordered()
        self.assertEqual(first_pop.seq, 2)

    def test_ac5_invalid_host_connection_resilience(self):
        """AC5: Connection to invalid/unresolvable host returns False without unhandled exception."""
        async def _test():
            conduit = SovereignVoiceConduit(node_id="test_node", secret_key=b"k", port=18780)
            res = await conduit.send_audio_to_peer("999.999.999.999", 12345, b"payload", "test")
            self.assertFalse(res)

        asyncio.run(_test())


