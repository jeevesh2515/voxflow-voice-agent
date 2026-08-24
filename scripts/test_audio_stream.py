#!/usr/bin/env python3
"""
VoxFlow Mock Audio Stream & Pipeline Feeder
Generates a synthetic PCM burst and prints the real turn-pipeline component stack.
Actual per-turn latency is measured live by the API (`latency_ms` on POST /api/connect/turn),
not by this script.
"""

import sys
import time
import argparse
import asyncio
import math
import struct

def generate_mock_sine_pcm(duration_sec: float = 1.5, sample_rate: int = 16000, freq: float = 440.0) -> bytes:
    """Generate 16kHz 16-bit mono PCM sine wave as mock audio frame."""
    num_samples = int(duration_sec * sample_rate)
    buffer = bytearray()
    for i in range(num_samples):
        sample = int(32767.0 * 0.5 * math.sin(2.0 * math.pi * freq * (i / sample_rate)))
        buffer.extend(struct.pack("<h", max(-32768, min(32767, sample))))
    return bytes(buffer)

async def test_mock_feeder(host: str = "localhost", port: int = 8000, tenant_id: str = "default"):
    print(f"\n🎙️  VoxFlow Mock Audio Stream Feeder")
    print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"Target Host       : http://{host}:{port}")
    print(f"Tenant Partition  : {tenant_id}")
    print(f"Audio Format      : 16kHz 16-bit Linear PCM (Mono)")
    print(f"Chunk Frame Size  : 512 samples (~32ms per packet)")
    print(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")

    print(f"⏳ Generating synthetic voice audio buffer (1.5s speech burst)...")
    pcm_data = generate_mock_sine_pcm(duration_sec=1.5, sample_rate=16000)
    print(f"✓ Audio frame created: {len(pcm_data)} bytes ({len(pcm_data) // 2} samples)")

    print(f"\n⚡ Turn Pipeline Stages (real per-turn latency_ms is logged by /api/connect/turn on live calls):")
    print(f"  [1] Audio Capture & Chunking  : Amazon Connect PSTN / Web Audio AudioWorklet")
    print(f"  [2] Speech Gate (VAD)         : server-side RMS energy gate, 450ms trailing silence")
    print(f"  [3] Speech-to-Text (STT)      : Amazon Lex V2 en-GB (calls) / Groq Whisper (sim)")
    print(f"  [4] Agent Reasoning           : Groq openai/gpt-oss-20b, tool-calling AgentRunner")
    print(f"  [5] Neural Audio Synthesis    : Amazon Polly en-GB (calls) / edge-tts (sim)")
    print(f"  -------------------------------------------------------------")
    print(f"  🎯 Glass-to-Glass Round-Trip  : measured live via latency_ms (real UK calls)\n")
    print(f"✓ Mock stream test completed successfully.")

def main():
    parser = argparse.ArgumentParser(description="VoxFlow Mock Audio Stream Feeder")
    parser.add_argument("--host", default="localhost", help="API host")
    parser.add_argument("--port", type=int, default=8000, help="API port")
    parser.add_argument("--tenant", default="default", help="Tenant ID")
    args = parser.parse_args()

    asyncio.run(test_mock_feeder(args.host, args.port, args.tenant))

if __name__ == "__main__":
    main()
