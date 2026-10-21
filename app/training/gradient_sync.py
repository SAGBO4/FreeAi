"""Gradient pulse: ephemeral weight-difference vector broadcast in RAM."Innovation: LZ4-compressed Π operator delta, 0-Disk bedding.
"""

import io
import time
import struct
import hashlib
import lz4.frame
from dataclasses import dataclass, field
from typing import Dict, Any, Tuple


@dataclass
class GradientPulse:
    """A small, mathematically exact, ephemeral pulse of gradient delta from a worker."""
    worker_id: str
    pulse_id: str
    epoch: int
    vector_hash: str
    packed_delta: bytes
    lz4_ratio: float
    payload_hash: str = ""
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @staticmethod
    def from_tensor_delta(worker_id: str, epoch: int, delta: bytes) -> "GradientPulse":
        lz4_buf = lz4.frame.compress(delta)
        pulse_id = hashlib.sha256(f"{worker_id}:{epoch}:{time.time()}".encode()).hexdigest()[:12]
        packed_hash = hashlib.sha256(lz4_buf).hexdigest()
        return GradientPulse(
            worker_id=worker_id,
            pulse_id=pulse_id,
            epoch=epoch,
            vector_hash=hashlib.sha256(delta).hexdigest()[:16],
            packed_delta=lz4_buf,
            lz4_ratio=len(lz4_buf) / max(len(delta), 1),
            payload_hash=packed_hash,
            metadata={"uncompressed_bytes": len(delta)}
        )

    def decompress(self, max_size: int = 50 * 1024 * 1024) -> bytes:
        if self.payload_hash:
            actual_hash = hashlib.sha256(self.packed_delta).hexdigest()
            if actual_hash != self.payload_hash:
                raise ValueError("Payload hash mismatch")
                
        # Use LZ4FrameDecompressor to enforce decompression size limit
        d = lz4.frame.LZ4FrameDecompressor()
        result = bytearray()
        
        chunk_size = 4096
        for i in range(0, len(self.packed_delta), chunk_size):
            chunk = self.packed_delta[i:i+chunk_size]
            result.extend(d.decompress(chunk))
            if len(result) > max_size:
                raise ValueError(f"Decompression bomb detected! Exceeds {max_size} bytes")
                
        return bytes(result)

    def to_wire(self) -> bytes:
        header = f"{self.worker_id}|{self.pulse_id}|{self.epoch}|{self.vector_hash}|{self.payload_hash}|{len(self.packed_delta)}\n"
        return header.encode() + self.packed_delta
