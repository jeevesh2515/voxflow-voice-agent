#!/usr/bin/env python3
"""VoxFlow Voice Agent — Live Pipeline Latency & TTFT Benchmark Harness.

Measures high-precision millisecond latencies across each pipeline stage:
  1. Speech-to-Text (STT): Transcription latency & Real-Time Factor (RTF)
  2. LLM Streaming & Reasoning: Time to First Token (TTFT), Inter-Token Latency (ITL), and TPS throughput
  3. Text-to-Speech (TTS): Streaming Time to First Byte (TTFB) and synthesis latency
  4. End-to-End Turn: Glass-to-glass turn turnaround with tool execution

Outputs:
  - Terminal ASCII percentile distribution table & bar chart (P50, P90, P95, P99)
  - JSON telemetry artifact (`data/latency_benchmark.json`)
  - GitHub-ready Markdown report (`BENCHMARK_REPORT.md`)

Usage:
  python scripts/benchmark_latency.py --iterations 5
  python scripts/benchmark_latency.py --stages llm --mode live --iterations 10
  python scripts/benchmark_latency.py --mode mock --export-markdown BENCHMARK_REPORT.md
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from datetime import datetime, timezone

# Ensure project root is in python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "apps", "api")))

from voxflow_api.benchmarks.e2e_bench import run_e2e_benchmark
from voxflow_api.benchmarks.engine import (
    BenchmarkSummary,
    StageLatencyResult,
    format_ascii_table,
    to_markdown_report,
)
from voxflow_api.benchmarks.llm_bench import run_llm_benchmark
from voxflow_api.benchmarks.stt_bench import run_stt_benchmark
from voxflow_api.benchmarks.tts_bench import run_tts_benchmark
from voxflow_api.config import get_settings


async def main_async(args: argparse.Namespace) -> int:
    settings = get_settings()
    has_groq = bool(settings.groq_api_key)

    if args.mode == "live" and not has_groq:
        print("⚠️ Warning: --mode live requested but GROQ_API_KEY is not set. Falling back to mock mode.")
        mode = "mock"
    elif args.mode == "auto":
        mode = "live" if has_groq else "mock"
    else:
        mode = args.mode

    model = args.model or settings.groq_model
    iterations = max(1, args.iterations)
    selected_stages = args.stages.lower().split(",")

    run_all = "all" in selected_stages

    print("\n" + "━" * 70)
    print(f"🎙️  VoxFlow High-Precision Latency Benchmark Suite")
    print(f"    Mode: {mode.upper()}  │  Iterations: {iterations}  │  LLM: {model}")
    print("━" * 70)

    stages_results: list[StageLatencyResult] = []

    # 1. STT Stage
    if run_all or "stt" in selected_stages:
        print(f"\n⏳ [1/4] Benchmarking Speech-to-Text (STT)...")
        stt_res = await run_stt_benchmark(iterations=iterations, mode=mode)
        stages_results.append(stt_res)
        print(f"    ✓ STT P50: {stt_res.distribution.p50_ms:.1f}ms  (RTF: {stt_res.extra_metrics.get('real_time_factor_rtf')})")

    # 2. LLM TTFT Stage
    if run_all or "llm" in selected_stages:
        print(f"\n⏳ [2/4] Benchmarking LLM Streaming & TTFT ({model})...")
        llm_res = await run_llm_benchmark(iterations=iterations, mode=mode, model_override=model)
        stages_results.append(llm_res)
        print(f"    ✓ LLM TTFT P50: {llm_res.distribution.p50_ms:.1f}ms  │  Throughput: {llm_res.extra_metrics.get('generation_throughput_tps')} tokens/sec")

    # 3. TTS Stage
    if run_all or "tts" in selected_stages:
        print(f"\n⏳ [3/4] Benchmarking Text-to-Speech (TTS)...")
        tts_res = await run_tts_benchmark(iterations=iterations, mode=mode)
        stages_results.append(tts_res)
        print(f"    ✓ TTS TTFB P50: {tts_res.extra_metrics.get('ttfb_p50_ms')}ms  │  Total Synth P50: {tts_res.distribution.p50_ms:.1f}ms")

    # 4. E2E Turn Stage
    if run_all or "e2e" in selected_stages:
        print(f"\n⏳ [4/4] Benchmarking End-to-End Glass-to-Glass Turn Pipeline...")
        e2e_res = await run_e2e_benchmark(iterations=iterations, mode=mode)
        stages_results.append(e2e_res)
        print(f"    ✓ Glass-to-Glass P50: {e2e_res.distribution.p50_ms:.1f}ms  │  P90: {e2e_res.distribution.p90_ms:.1f}ms")

    # Compile Summary
    summary = BenchmarkSummary(
        timestamp=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
        mode=mode,
        model=model,
        total_iterations=iterations,
        stages=stages_results,
        metadata={
            "python_version": sys.version.split()[0],
            "stt_provider": settings.stt_provider,
            "tts_voice": settings.tts_voice_en,
        },
    )

    # Print ASCII Report
    report_text = format_ascii_table(summary)
    print(report_text)

    # Export JSON if requested
    if args.export_json:
        out_dir = os.path.dirname(os.path.abspath(args.export_json))
        os.makedirs(out_dir, exist_ok=True)
        with open(args.export_json, "w", encoding="utf-8") as f:
            json.dump(summary.to_dict(), f, indent=2)
        print(f"\n📁 JSON Telemetry exported to: {args.export_json}")

    # Export Markdown if requested
    if args.export_markdown:
        md_dir = os.path.dirname(os.path.abspath(args.export_markdown))
        os.makedirs(md_dir, exist_ok=True)
        with open(args.export_markdown, "w", encoding="utf-8") as f:
            f.write(to_markdown_report(summary))
        print(f"📄 Markdown Report exported to: {args.export_markdown}")

    print("\n✅ Benchmark execution complete.\n")
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(
        description="VoxFlow Voice Agent — Live Pipeline Latency & TTFT Benchmark Harness"
    )
    parser.add_argument(
        "--iterations",
        type=int,
        default=5,
        help="Number of test iterations per stage (default: 5)",
    )
    parser.add_argument(
        "--stages",
        type=str,
        default="all",
        help="Comma-separated stages to run: all, stt, llm, tts, e2e (default: all)",
    )
    parser.add_argument(
        "--mode",
        type=str,
        choices=["auto", "live", "mock"],
        default="auto",
        help="Benchmark mode: auto (uses live if keys present), live, or mock (default: auto)",
    )
    parser.add_argument(
        "--model",
        type=str,
        default=None,
        help="Override LLM model name (e.g. openai/gpt-oss-20b, llama-3.3-70b-versatile)",
    )
    parser.add_argument(
        "--export-json",
        type=str,
        default="data/latency_benchmark.json",
        help="Destination path for JSON telemetry export (default: data/latency_benchmark.json)",
    )
    parser.add_argument(
        "--export-markdown",
        type=str,
        default="BENCHMARK_REPORT.md",
        help="Destination path for Markdown report export (default: BENCHMARK_REPORT.md)",
    )
    args = parser.parse_args()

    sys.exit(asyncio.run(main_async(args)))


if __name__ == "__main__":
    main()
