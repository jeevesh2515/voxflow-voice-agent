"""Audio codec and resampling utilities for telephony and voice pipelines."""

from __future__ import annotations

import io
import math

import numpy as np


def _build_ulaw_tables() -> tuple[list[int], list[int]]:
    """Generate 8-bit μ-law <-> 16-bit linear PCM conversion lookup tables."""
    BIAS = 0x84
    CLIP = 32635
    exp_lut = [0, 132, 396, 924, 1980, 4092, 8316, 16764]

    u2l = [0] * 256
    for i in range(256):
        c = ~i & 0xFF
        sign = c & 0x80
        exponent = (c >> 4) & 0x07
        mantissa = c & 0x0F
        sample = exp_lut[exponent] + (mantissa << (exponent + 3))
        if sign != 0:
            sample = -sample
        u2l[i] = sample

    l2u = [0] * 65536
    for idx in range(65536):
        sample = idx - 32768
        sign = 0
        if sample < 0:
            sign = 0x80
            sample = -sample
        if sample > CLIP:
            sample = CLIP
        sample += BIAS
        exponent = 7
        for exp in range(7):
            if sample <= (exp_lut[exp + 1] if exp + 1 < 8 else 32767):
                exponent = exp
                break
        mantissa = (sample >> (exponent + 3)) & 0x0F
        byte_val = ~(sign | (exponent << 4) | mantissa) & 0xFF
        l2u[idx] = byte_val

    return u2l, l2u


_ULAW_TO_LINEAR_LUT, _LINEAR_TO_ULAW_LUT = _build_ulaw_tables()
_ULAW_TO_LINEAR_ARR = np.array(_ULAW_TO_LINEAR_LUT, dtype=np.int16)
_LINEAR_TO_ULAW_ARR = np.array(_LINEAR_TO_ULAW_LUT, dtype=np.uint8)


def mulaw_to_pcm(mulaw_bytes: bytes) -> bytes:
    """Convert G.711 μ-law audio to 16-bit mono linear PCM."""
    if not mulaw_bytes:
        return b""
    idx = np.frombuffer(mulaw_bytes, dtype=np.uint8)
    return _ULAW_TO_LINEAR_ARR[idx].tobytes()


def pcm_to_mulaw(pcm_bytes: bytes) -> bytes:
    """Convert 16-bit mono linear PCM to 8-bit G.711 μ-law."""
    if not pcm_bytes:
        return b""
    samples = np.frombuffer(pcm_bytes, dtype=np.int16).astype(np.int32) + 32768
    return _LINEAR_TO_ULAW_ARR[samples].tobytes()


def resample_8k_to_16k(pcm_8k: bytes) -> bytes:
    """Upsample 8kHz 16-bit mono PCM to 16kHz via linear interpolation."""
    if not pcm_8k:
        return b""
    s8 = np.frombuffer(pcm_8k, dtype=np.int16)
    if len(s8) == 0:
        return b""
    s16 = np.empty(len(s8) * 2, dtype=np.int16)
    s16[0::2] = s8
    s16[1:-1:2] = ((s8[:-1].astype(np.int32) + s8[1:].astype(np.int32)) // 2).astype(np.int16)
    s16[-1] = s8[-1]
    return s16.tobytes()


def mp3_to_pcm8k(mp3_bytes: bytes) -> bytes:
    """Decode MP3 audio to 8kHz 16-bit mono PCM using PyAV."""
    if not mp3_bytes:
        return b""
    try:
        import av
        container = av.open(io.BytesIO(mp3_bytes))
        resampler = av.AudioResampler(format="s16", layout="mono", rate=8000)
        pcm_chunks = []
        for frame in container.decode(audio=0):
            resampled = resampler.resample(frame)
            if resampled:
                for r_frame in (resampled if isinstance(resampled, list) else [resampled]):
                    pcm_chunks.append(r_frame.to_ndarray().tobytes())
        return b"".join(pcm_chunks)
    except Exception:
        return b""


def compute_rms(pcm_bytes: bytes) -> float:
    """Compute Root-Mean-Square (RMS) audio signal energy."""
    if not pcm_bytes:
        return 0.0
    samples = np.frombuffer(pcm_bytes, dtype=np.int16)
    if len(samples) == 0:
        return 0.0
    mean_sq = np.mean(samples.astype(np.float32) ** 2)
    return math.sqrt(mean_sq)
