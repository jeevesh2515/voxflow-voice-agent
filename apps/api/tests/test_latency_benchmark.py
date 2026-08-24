"""Unit tests for the latency benchmarking engine, percentiles, and report generators."""

from __future__ import annotations

import pytest

from voxflow_api.benchmarks.e2e_bench import run_e2e_benchmark
from voxflow_api.benchmarks.engine import (
    BenchmarkSummary,
    PercentileDistribution,
    StageLatencyResult,
    calculate_percentiles,
    format_ascii_table,
    render_ascii_bar_chart,
    to_markdown_report,
)
from voxflow_api.benchmarks.llm_bench import run_llm_benchmark
from voxflow_api.benchmarks.stt_bench import run_stt_benchmark
from voxflow_api.benchmarks.tts_bench import run_tts_benchmark


def test_calculate_percentiles_empty():
    dist = calculate_percentiles([])
    assert dist.sample_count == 0
    assert dist.p50_ms == 0.0
    assert dist.mean_ms == 0.0
    assert dist.min_ms == 0.0
    assert dist.max_ms == 0.0


def test_calculate_percentiles_known_dataset():
    # 10 values: 10, 20, 30, 40, 50, 60, 70, 80, 90, 100
    samples = [10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0, 90.0, 100.0]
    dist = calculate_percentiles(samples)

    assert dist.sample_count == 10
    assert dist.min_ms == 10.0
    assert dist.max_ms == 100.0
    assert dist.mean_ms == 55.0
    assert dist.p50_ms == 55.0
    assert dist.p90_ms == 91.0
    assert dist.p99_ms == 99.1
    assert round(dist.std_dev_ms, 2) == 30.28


def test_stage_latency_result_serialization():
    samples = [100.0, 150.0, 200.0]
    dist = calculate_percentiles(samples)
    stage = StageLatencyResult(
        stage_id="test_stage",
        stage_name="Test Stage",
        technology="Mock Tech",
        sample_latencies_ms=samples,
        distribution=dist,
        extra_metrics={"tps": 120.5},
    )

    data = stage.to_dict()
    assert data["stage_id"] == "test_stage"
    assert data["stage_name"] == "Test Stage"
    assert data["technology"] == "Mock Tech"
    assert data["distribution"]["p50_ms"] == 150.0
    assert data["extra_metrics"]["tps"] == 120.5
    assert len(data["raw_samples_ms"]) == 3


def test_ascii_and_markdown_formatting():
    samples = [50.0, 100.0, 150.0]
    dist = calculate_percentiles(samples)
    stage = StageLatencyResult(
        stage_id="stage_1",
        stage_name="STT Processing",
        technology="Whisper-Turbo",
        sample_latencies_ms=samples,
        distribution=dist,
        extra_metrics={"rtf": 0.15},
    )
    summary = BenchmarkSummary(
        timestamp="2026-08-24 12:00:00 UTC",
        mode="mock",
        model="openai/gpt-oss-20b",
        total_iterations=3,
        stages=[stage],
        metadata={"platform": "test"},
    )

    ascii_report = format_ascii_table(summary)
    assert "VOXFLOW PIPELINE LATENCY" in ascii_report
    assert "STT Processing" in ascii_report
    assert "Whisper-Turbo" in ascii_report

    bar_chart = render_ascii_bar_chart("Test Chart", [("STT", 100.0), ("LLM", 200.0)])
    assert "📊 Test Chart" in bar_chart
    assert "STT" in bar_chart
    assert "LLM" in bar_chart

    md_report = to_markdown_report(summary)
    assert "# ⚡ VoxFlow Voice Agent Latency & Throughput Benchmark Report" in md_report
    assert "STT Processing" in md_report
    assert "| `Whisper-Turbo` |" in md_report


@pytest.mark.asyncio
async def test_mock_stt_benchmark():
    res = await run_stt_benchmark(iterations=2, mode="mock", duration_sec=1.0)
    assert res.stage_id == "stt"
    assert len(res.sample_latencies_ms) == 2
    assert res.distribution.p50_ms > 0
    assert "real_time_factor_rtf" in res.extra_metrics


@pytest.mark.asyncio
async def test_mock_llm_benchmark():
    res = await run_llm_benchmark(iterations=2, mode="mock")
    assert res.stage_id == "llm_ttft"
    assert len(res.sample_latencies_ms) == 2
    assert res.distribution.p50_ms > 0
    assert "generation_throughput_tps" in res.extra_metrics
    assert "inter_token_latency_ms" in res.extra_metrics


@pytest.mark.asyncio
async def test_mock_tts_benchmark():
    res = await run_tts_benchmark(iterations=2, mode="mock")
    assert res.stage_id == "tts_synth"
    assert len(res.sample_latencies_ms) == 2
    assert res.distribution.p50_ms > 0
    assert "ttfb_p50_ms" in res.extra_metrics


@pytest.mark.asyncio
async def test_mock_e2e_benchmark():
    res = await run_e2e_benchmark(iterations=2, mode="mock")
    assert res.stage_id == "e2e_turn"
    assert len(res.sample_latencies_ms) == 2
    assert res.distribution.p50_ms > 0
