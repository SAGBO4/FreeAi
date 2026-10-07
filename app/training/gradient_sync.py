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
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @staticmethod
    def from_tensor_delta(worker_id: str, epoch: int, delta: bytes) -> "GradientPulse":
        lz4_buf = lz4.frame.compress(io.BytesIO(delta)).getvalue()
        pulse_id = hashlib.sha256(f"{worker_id}:{epoch}:{time.time()}".encode()).hexdigest()[:12]
        return GradientPulse(
            worker_id=worker_id,
            pulse_id=pulse_id,
            epoch=epoch,
            vector_hash=hashlib.sha256(delta).hexdigest()[:16],
            packed_delta=lz4_buf,
            lz4_ratio=len(lz4_buf) / max(len(delta), 1),
            metadata={"uncompressed_bytes": len(delta)}
        )

    def decompress(self) -> bytes:
        return lz4.frame.decompress(self.packed_delta)

    def to_wire(self) -> bytes:
        header = f"{self.worker_id}|{self.pulse_id}|{self.epoch}|{self.vector_hash}|{len(self.packed_delta)}\n"
        return header.encode() + self.packed_delta
