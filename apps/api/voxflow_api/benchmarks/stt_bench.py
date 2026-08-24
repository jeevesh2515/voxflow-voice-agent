"""Speech-to-Text (STT) latency & Real-Time Factor (RTF) benchmarking."""

from __future__ import annotations

import asyncio
import math
import random
import struct
import time
from typing import Any

import numpy as np

from .engine import StageLatencyResult, calculate_percentiles
from ..config import get_settings
from ..voice.stt import SpeechToText


def generate_synthetic_pcm(duration_sec: float = 1.5, sample_rate: int = 16000) -> np.ndarray:
    """Generate 16kHz float32 mono audio simulating voice energy bursts."""
    num_samples = int(duration_sec * sample_rate)
    t = np.linspace(0, duration_sec, num_samples, endpoint=False)
    # Mixture of fundamental vocal frequencies (120Hz, 240Hz, 800Hz)
    audio = 0.4 * np.sin(2 * np.pi * 120 * t) + 0.3 * np.sin(2 * np.pi * 240 * t) + 0.2 * np.sin(2 * np.pi * 800 * t)
    return audio.astype(np.float32)


async def run_stt_benchmark(
    iterations: int = 5,
    mode: str = "auto",
    duration_sec: float = 1.5,
) -> StageLatencyResult:
    """Benchmark STT latency and calculate Real-Time Factor (RTF)."""
    settings = get_settings()
    has_groq = bool(settings.groq_api_key)
    is_live = (mode == "live") or (mode == "auto" and has_groq)

    tech_name = f"Groq {settings.groq_stt_model}" if is_live else "Mock Whisper-v3-Turbo"
    pcm = generate_synthetic_pcm(duration_sec=duration_sec, sample_rate=16000)

    samples: list[float] = []
    transcriptions: list[str] = []

    stt = SpeechToText.instance() if is_live else None

    for _ in range(iterations):
        t0 = time.perf_counter()
        if is_live and stt:
            loop = asyncio.get_running_loop()
            res = await loop.run_in_executor(
                None, lambda: stt.transcribe_pcm(pcm, sample_rate=16000, language="en")
            )
            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            transcriptions.append(res.text or "(empty)")
        else:
            # Calibrated deterministic simulated Whisper turnaround (~185ms + random jitter)
            await asyncio.sleep(random.uniform(0.16, 0.22))
            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            transcriptions.append("test po delivery eta lookup")

        samples.append(elapsed_ms)

    dist = calculate_percentiles(samples)
    audio_duration_ms = duration_sec * 1000.0
    mean_rtf = dist.mean_ms / audio_duration_ms

    return StageLatencyResult(
        stage_id="stt",
        stage_name="1. Speech-to-Text (STT)",
        technology=tech_name,
        sample_latencies_ms=samples,
        distribution=dist,
        extra_metrics={
            "audio_duration_sec": duration_sec,
            "real_time_factor_rtf": round(mean_rtf, 4),
            "rtf_description": f"{round(1.0 / mean_rtf, 1)}x faster than real-time" if mean_rtf > 0 else "N/A",
        },
    )
