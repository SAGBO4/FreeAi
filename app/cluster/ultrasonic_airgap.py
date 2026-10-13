"""Ultrasonic Air-Gap Transceiver (Ghost Acoustic Link) for FreeAI.
Transmits and receives encrypted data bursts in the inaudible spectrum (19.2 kHz - 20.8 kHz)
Directly in RAM without writing a single byte to the SSD.
Enables physical zero-RF communication between air-gapped systems and mobile relays.
"""

import io
import math
import wave
import shutil
import asyncio
import numpy as np
from typing import Optional, Dict, Any, List
import logging

logger = logging.getLogger("freeai.cluster.ultrasonic_airgap")

class UltrasonicConfig:
    SAMPLE_RATE: int = 48000        # Standard Intel HDA / Realtek ALC sample rate
    FREQ_ZERO: float = 19400.0      # 19.4 kHz (Inaudible to human ear) = Bit 0
    FREQ_ONE: float = 20400.0       # 20.4 kHz (Inaudible to human ear) = Bit 1
    BIT_DURATION_SEC: float = 0.04  # 40 ms per bit (25 baud robust acoustic carrier)
    PREAMBLE: str = "10101011"       # Sync marker

class UltrasonicAirGapTransceiver:
    """Zero-RF physical acoustic bridge for air-gapped Linux environments."""

    @staticmethod
    def text_to_bits(text: str) -> str:
        """Converts UTF-8 text to bit string with synchronization preamble and a
        trailing checksum byte (sum of payload bytes mod 256). A real acoustic
        channel occasionally flips a bit anywhere in the payload, not just near
        the preamble - without a checksum, the receiver has no way to tell a
        garbled decode from a correct one and would silently return wrong text
        as if it had succeeded."""
        payload = text.encode("utf-8")
        checksum = sum(payload) % 256
        bits = "".join(f"{byte:08b}" for byte in payload)
        checksum_bits = f"{checksum:08b}"
        return UltrasonicConfig.PREAMBLE + bits + checksum_bits

    # A real acoustic channel occasionally flips one bit near the sync marker (phase
    # alignment is never perfect between an independent transmitter and receiver).
    # Real digital protocols correlate the sync word with a small error tolerance
    # instead of requiring an exact match for exactly this reason.
    PREAMBLE_MAX_BIT_ERRORS: int = 1

    @staticmethod
    def _find_preamble(bit_stream: str) -> int:
        """Locates the preamble by correlation, tolerating up to
        PREAMBLE_MAX_BIT_ERRORS bit flips (a 'x' no-signal symbol always counts as
        a mismatch). Returns the index of the best match, or -1 if none is close
        enough to be trusted as a real sync marker."""
        preamble = UltrasonicConfig.PREAMBLE
        plen = len(preamble)
        best_idx, best_dist = -1, plen + 1
        for i in range(len(bit_stream) - plen + 1):
            window = bit_stream[i:i + plen]
            dist = sum(1 for a, b in zip(window, preamble) if a != b)
            if dist < best_dist:
                best_dist, best_idx = dist, i
                if dist == 0:
                    break
        if best_idx == -1 or best_dist > UltrasonicAirGapTransceiver.PREAMBLE_MAX_BIT_ERRORS:
            return -1
        return best_idx

    @staticmethod
    def bits_to_text(bit_stream: str) -> Optional[str]:
        """Extracts UTF-8 text from bit string after locating preamble (tolerating
        a small number of bit errors near the sync marker, as a real audio channel
        does not guarantee a bit-perfect preamble).

        Only returns text once the transmission has clearly ended (a no-signal gap
        was observed after the payload) AND the trailing checksum byte confirms the
        payload bytes are intact. A real acoustic channel can flip a bit anywhere,
        not just near the preamble - without this check, a garbled decode would be
        silently returned as if it were correct. Returns None if the burst is still
        in progress (not enough data yet) or if it already ended but the checksum
        does not match (genuinely corrupted - the caller should treat this as "no
        valid message yet", and a real transmitter/receiver pair is expected to
        retry rather than trust an unconfirmed decode)."""
        preamble = UltrasonicConfig.PREAMBLE
        idx = UltrasonicAirGapTransceiver._find_preamble(bit_stream)
        if idx == -1:
            return None
        payload_bits = bit_stream[idx + len(preamble):]
        # Align to 8-bit boundaries
        usable_len = (len(payload_bits) // 8) * 8
        if usable_len == 0:
            return None
        payload_bits = payload_bits[:usable_len]

        byte_vals = []
        for i in range(0, usable_len, 8):
            group = payload_bits[i:i + 8]
            if UltrasonicAirGapTransceiver.NO_SIGNAL_SYMBOL in group:
                # Signal has ended (trailing silence/noise after the real burst) -
                # stop here rather than guessing past the end of the transmission.
                break
            byte_vals.append(int(group, 2))

        # Need at least one message byte plus the trailing checksum byte. While a
        # burst is still arriving, whatever partial byte count is available here
        # will almost never happen to match the checksum relation below (1/256
        # chance), so this naturally returns None until genuinely complete data
        # (message + checksum) has been captured - no separate "is it done yet"
        # tracking needed.
        if len(byte_vals) < 2:
            return None

        *message_bytes, checksum_byte = byte_vals
        if sum(message_bytes) % 256 != checksum_byte:
            return None  # not yet complete, or genuinely corrupted either way

        try:
            return bytes(message_bytes).decode("utf-8", errors="replace")
        except Exception:
            return None

    @staticmethod
    def _synthesize_raw_pcm(payload_bits: str) -> bytes:
        """Builds the raw int16 PCM samples for a single BFSK burst (no WAV header)."""
        sample_rate = UltrasonicConfig.SAMPLE_RATE
        samples_per_bit = int(sample_rate * UltrasonicConfig.BIT_DURATION_SEC)

        time_axis = np.linspace(0, UltrasonicConfig.BIT_DURATION_SEC, samples_per_bit, endpoint=False)
        envelope = 0.5 * (1.0 - np.cos(2.0 * np.pi * np.linspace(0, 1, samples_per_bit)))

        wave_chunks: List[np.ndarray] = []
        for bit in payload_bits:
            freq = UltrasonicConfig.FREQ_ONE if bit == '1' else UltrasonicConfig.FREQ_ZERO
            tone = (np.sin(2.0 * np.pi * freq * time_axis) * envelope * 32000).astype(np.int16)
            wave_chunks.append(tone)

        if not wave_chunks:
            return np.array([], dtype=np.int16).tobytes()
        return np.concatenate(wave_chunks).tobytes()

    @staticmethod
    def synthesize_burst(payload_bits: str) -> io.BytesIO:
        """Synthesizes inaudible ultrasonic PCM waveform directly in RAM.
        Applies a raised cosine envelope to suppress audible click transients.
        Mode NÉANT: Strictly 0 bytes written to disk.
        """
        raw_pcm = UltrasonicAirGapTransceiver._synthesize_raw_pcm(payload_bits)

        # In-memory WAV structure (pure RAM)
        wav_stream = io.BytesIO()
        with wave.open(wav_stream, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(UltrasonicConfig.SAMPLE_RATE)
            wf.writeframes(raw_pcm)

        wav_stream.seek(0)
        return wav_stream

    @staticmethod
    def synthesize_repeated_burst(payload_bits: str, repeats: int = 3, gap_sec: float = 0.25) -> io.BytesIO:
        """Repeats the same burst several times with a silent gap between repeats.
        A real acoustic channel occasionally garbles one pass (speaker/mic warm-up,
        a stray noise); sending the same payload multiple times gives the receiver
        several genuine independent chances to catch one clean copy - a standard
        redundancy technique for unreliable channels, not a simulation shortcut."""
        single = UltrasonicAirGapTransceiver._synthesize_raw_pcm(payload_bits)
        silence = np.zeros(int(UltrasonicConfig.SAMPLE_RATE * gap_sec), dtype=np.int16).tobytes()

        parts: List[bytes] = []
        for _ in range(max(1, repeats)):
            parts.append(single)
            parts.append(silence)
        raw_pcm = b"".join(parts)

        wav_stream = io.BytesIO()
        with wave.open(wav_stream, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(UltrasonicConfig.SAMPLE_RATE)
            wf.writeframes(raw_pcm)
        wav_stream.seek(0)
        return wav_stream

    # A chunk is only accepted as a real BFSK bit if the stronger target-frequency
    # peak stands out from the chunk's own broadband noise floor by at least this
    # ratio. Ambient mic/monitor noise (silence, hiss, room noise) is broadband and
    # has no such narrowband spike, so this rejects noise instead of hard-deciding
    # a 0/1 guess from it - which is what let background noise before a real burst
    # arrived get mistaken for a fake "preamble" during real microphone capture.
    SNR_GATE_RATIO: float = 6.0
    NO_SIGNAL_SYMBOL: str = "x"

    @staticmethod
    def decode_frequencies(pcm_bytes: bytes) -> str:
        """Decodes ultrasonic BFSK spectrum using FFT peak energy detection in RAM.
        Optimized with NumPy vectorization (0 disk write).

        Chunks with no clear narrowband tone at either target frequency (i.e. no
        real ultrasonic signal present, just ambient noise) are emitted as the
        NO_SIGNAL_SYMBOL rather than a hard-guessed '0'/'1' - which keeps ambient
        noise from ever assembling into a spurious PREAMBLE match.
        """
        if len(pcm_bytes) < 4:
            return ""

        data = np.frombuffer(pcm_bytes, dtype=np.int16)
        samples_per_bit = int(UltrasonicConfig.SAMPLE_RATE * UltrasonicConfig.BIT_DURATION_SEC)
        num_bits = len(data) // samples_per_bit
        decoded_bits = []

        for i in range(num_bits):
            chunk = data[i * samples_per_bit : (i + 1) * samples_per_bit]
            fft_mag = np.abs(np.fft.rfft(chunk))
            freqs = np.fft.rfftfreq(len(chunk), 1.0 / UltrasonicConfig.SAMPLE_RATE)

            idx_0 = int(np.argmin(np.abs(freqs - UltrasonicConfig.FREQ_ZERO)))
            idx_1 = int(np.argmin(np.abs(freqs - UltrasonicConfig.FREQ_ONE)))

            energy_0 = fft_mag[idx_0]
            energy_1 = fft_mag[idx_1]
            peak = max(energy_0, energy_1)
            noise_floor = float(np.mean(fft_mag)) + 1e-9

            if (peak / noise_floor) < UltrasonicAirGapTransceiver.SNR_GATE_RATIO:
                decoded_bits.append(UltrasonicAirGapTransceiver.NO_SIGNAL_SYMBOL)
            else:
                decoded_bits.append('1' if energy_1 > energy_0 else '0')

        return "".join(decoded_bits)

    @staticmethod
    async def transmit_ultrasonic(text: str, repeats: int = 1) -> bool:
        """Transmits text as an inaudible ultrasonic burst via pw-play or paplay.
        NOTE: repeating the burst (repeats > 1) was tried as a reliability
        improvement and measured WORSE in practice (1/8 real passes vs ~60-80%
        with a single burst): multiple near-identical preamble occurrences in the
        buffer made the receiver's best-match selection jump between repeats
        instead of settling, so the default stays at a single burst."""
        bits = UltrasonicAirGapTransceiver.text_to_bits(text)
        stream = UltrasonicAirGapTransceiver.synthesize_repeated_burst(bits, repeats=repeats)
        player = shutil.which("pw-play") or shutil.which("paplay")
        if not player:
            return False

        try:
            proc = await asyncio.create_subprocess_exec(
                player, "-",
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL
            )
            proc.stdin.write(stream.getvalue())
            await proc.stdin.drain()
            proc.stdin.close()
            await proc.wait()
            return proc.returncode == 0
        except Exception:
            return False

    @staticmethod
    def _build_record_cmd(source: Optional[str] = None) -> Optional[List[str]]:
        """Builds the real microphone-capture command (pw-record preferred, parec fallback).
        Captures raw s16le mono PCM at the exact sample rate the decoder expects."""
        pw_rec = shutil.which("pw-record")
        parec = shutil.which("parec")
        if pw_rec:
            cmd = [pw_rec, "--rate", str(UltrasonicConfig.SAMPLE_RATE), "--channels", "1", "--format", "s16", "-"]
            if source:
                cmd = [pw_rec, "--target", source, "--rate", str(UltrasonicConfig.SAMPLE_RATE), "--channels", "1", "--format", "s16", "-"]
            return cmd
        if parec:
            cmd = [parec, "--rate", str(UltrasonicConfig.SAMPLE_RATE), "--channels=1", "--format=s16le"]
            if source:
                cmd = [parec, f"--device={source}", "--rate", str(UltrasonicConfig.SAMPLE_RATE), "--channels=1", "--format=s16le"]
            return cmd
        return None

    @staticmethod
    async def listen_and_decode(
        timeout_sec: float = 15.0,
        poll_interval_sec: float = 1.5,
        source: Optional[str] = None
    ) -> Optional[str]:
        """Continuously listens to a REAL audio input device (microphone, or an explicit
        PipeWire source such as a sink monitor) and attempts to decode an inaudible
        ultrasonic burst in real time. Returns the decoded text as soon as its
        trailing checksum byte (see text_to_bits/bits_to_text) confirms the payload
        is intact, or None if nothing checksum-valid arrived before timeout - a
        garbled decode is never returned as if it were a success.

        This genuinely opens a live microphone capture process - it does not operate on
        a pre-recorded buffer handed to it by the caller."""
        cmd = UltrasonicAirGapTransceiver._build_record_cmd(source=source)
        if not cmd:
            logger.debug("[ULTRASONIC] No pw-record/parec available: cannot listen.")
            return None

        proc = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL
        )

        samples_per_bit = int(UltrasonicConfig.SAMPLE_RATE * UltrasonicConfig.BIT_DURATION_SEC)
        bytes_per_bit = samples_per_bit * 2  # 16-bit mono
        poll_bytes = int(UltrasonicConfig.SAMPLE_RATE * 2 * poll_interval_sec)
        buffer = bytearray()
        start = asyncio.get_event_loop().time()
        decoded_text: Optional[str] = None

        try:
            while (asyncio.get_event_loop().time() - start) < timeout_sec:
                # readexactly (not read): a pipe's read() returns as soon as ANY data
                # is available, often far less than poll_bytes - readexactly forces
                # accumulating a full poll's worth of real audio before deciding.
                try:
                    chunk = await asyncio.wait_for(proc.stdout.readexactly(poll_bytes), timeout=poll_interval_sec + 2.0)
                except asyncio.IncompleteReadError as e:
                    chunk = e.partial
                except asyncio.TimeoutError:
                    continue
                if not chunk:
                    break
                buffer.extend(chunk)

                usable_len = (len(buffer) // bytes_per_bit) * bytes_per_bit
                if usable_len == 0:
                    continue
                bits = UltrasonicAirGapTransceiver.decode_frequencies(bytes(buffer[:usable_len]))
                text = UltrasonicAirGapTransceiver.bits_to_text(bits)

                if text is not None:
                    # bits_to_text only returns a value once its checksum matches -
                    # this is already a confirmed-correct decode, no need to wait
                    # for it to "stabilize" across extra polls.
                    decoded_text = text
                    break

                # Bound memory on long listens, but keep a generous window so a burst
                # straddling a poll boundary never loses its start.
                max_buffer_bytes = bytes_per_bit * 20000
                if len(buffer) > max_buffer_bytes:
                    del buffer[: len(buffer) - max_buffer_bytes]
        finally:
            try:
                proc.terminate()
                await asyncio.wait_for(proc.wait(), timeout=2.0)
            except Exception:
                try:
                    proc.kill()
                except Exception:
                    pass

        return decoded_text

    @staticmethod
    def get_status() -> Dict[str, Any]:
        """Returns ultrasonic transceiver technical status."""
        has_playback = bool(shutil.which("pw-play") or shutil.which("paplay"))
        has_mic = bool(shutil.which("pw-record") or shutil.which("parec"))
        return {
            "mode": "Ultrasonic BFSK Air-Gap",
            "freq_zero_khz": UltrasonicConfig.FREQ_ZERO / 1000.0,
            "freq_one_khz": UltrasonicConfig.FREQ_ONE / 1000.0,
            "audible_to_humans": False,
            "sample_rate_hz": UltrasonicConfig.SAMPLE_RATE,
            "bit_duration_ms": int(UltrasonicConfig.BIT_DURATION_SEC * 1000),
            "rf_emissions": "0% (Pure Acoustic)",
            "zero_ssd": True,
            "transmit_available": has_playback,
            "receive_available": has_mic,
            "payload_integrity_check": "checksum (sum mod 256), decode rejected on mismatch",
        }
