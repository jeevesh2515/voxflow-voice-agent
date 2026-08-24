"""Core statistical engine and data structures for latency benchmarking."""

from __future__ import annotations

import math
import statistics
from dataclasses import dataclass, field
from typing import Any


@dataclass
class PercentileDistribution:
    sample_count: int
    min_ms: float
    mean_ms: float
    max_ms: float
    std_dev_ms: float
    p50_ms: float
    p90_ms: float
    p95_ms: float
    p99_ms: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "sample_count": self.sample_count,
            "min_ms": round(self.min_ms, 2),
            "mean_ms": round(self.mean_ms, 2),
            "max_ms": round(self.max_ms, 2),
            "std_dev_ms": round(self.std_dev_ms, 2),
            "p50_ms": round(self.p50_ms, 2),
            "p90_ms": round(self.p90_ms, 2),
            "p95_ms": round(self.p95_ms, 2),
            "p99_ms": round(self.p99_ms, 2),
        }


def _percentile(sorted_data: list[float], percent: float) -> float:
    """Calculate the p-th percentile of a sorted list of numbers (0.0 to 100.0)."""
    if not sorted_data:
        return 0.0
    if len(sorted_data) == 1:
        return sorted_data[0]
    
    k = (len(sorted_data) - 1) * (percent / 100.0)
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return sorted_data[int(k)]
    d0 = sorted_data[int(f)] * (c - k)
    d1 = sorted_data[int(c)] * (k - f)
    return d0 + d1


def calculate_percentiles(samples: list[float]) -> PercentileDistribution:
    """Compute comprehensive statistical distribution over millisecond samples."""
    if not samples:
        return PercentileDistribution(
            sample_count=0,
            min_ms=0.0,
            mean_ms=0.0,
            max_ms=0.0,
            std_dev_ms=0.0,
            p50_ms=0.0,
            p90_ms=0.0,
            p95_ms=0.0,
            p99_ms=0.0,
        )

    clean_samples = [float(x) for x in samples]
    sorted_samples = sorted(clean_samples)
    n = len(sorted_samples)

    min_val = sorted_samples[0]
    max_val = sorted_samples[-1]
    mean_val = statistics.mean(sorted_samples)
    std_dev_val = statistics.stdev(sorted_samples) if n > 1 else 0.0

    p50_val = _percentile(sorted_samples, 50.0)
    p90_val = _percentile(sorted_samples, 90.0)
    p95_val = _percentile(sorted_samples, 95.0)
    p99_val = _percentile(sorted_samples, 99.0)

    return PercentileDistribution(
        sample_count=n,
        min_ms=min_val,
        mean_ms=mean_val,
        max_ms=max_val,
        std_dev_ms=std_dev_val,
        p50_ms=p50_val,
        p90_ms=p90_val,
        p95_ms=p95_val,
        p99_ms=p99_val,
    )


@dataclass
class StageLatencyResult:
    stage_id: str
    stage_name: str
    technology: str
    sample_latencies_ms: list[float]
    distribution: PercentileDistribution
    extra_metrics: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "stage_id": self.stage_id,
            "stage_name": self.stage_name,
            "technology": self.technology,
            "distribution": self.distribution.to_dict(),
            "extra_metrics": self.extra_metrics,
            "raw_samples_ms": [round(x, 2) for x in self.sample_latencies_ms],
        }


@dataclass
class BenchmarkSummary:
    timestamp: str
    mode: str
    model: str
    total_iterations: int
    stages: list[StageLatencyResult]
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "mode": self.mode,
            "model": self.model,
            "total_iterations": self.total_iterations,
            "metadata": self.metadata,
            "stages": [s.to_dict() for s in self.stages],
        }


def render_ascii_bar_chart(title: str, items: list[tuple[str, float]], max_bar_width: int = 25) -> str:
    """Render a visual ASCII horizontal bar chart."""
    if not items:
        return ""
    max_val = max(val for _, val in items) if any(val > 0 for _, val in items) else 1.0
    lines = [f"\n📊 {title}", "─" * 68]
    
    max_label_len = max(len(label) for label, _ in items)
    for label, val in items:
        bar_len = int((val / max_val) * max_bar_width) if max_val > 0 else 0
        bar = "█" * bar_len
        lines.append(f"  {label.ljust(max_label_len)} │ {bar.ljust(max_bar_width)} {val:>7.1f} ms")
    lines.append("─" * 68)
    return "\n".join(lines)


def format_ascii_table(summary: BenchmarkSummary) -> str:
    """Format full benchmark summary as a clean, publication-ready terminal table."""
    lines: list[str] = []
    lines.append("\n" + "=" * 90)
    lines.append("⚡ VOXFLOW PIPELINE LATENCY & TTFT BENCHMARK REPORT")
    lines.append(f"   Mode: {summary.mode.upper()}  │  Model: {summary.model}  │  Iterations: {summary.total_iterations}  │  {summary.timestamp}")
    lines.append("=" * 90)

    header = f"{'Pipeline Stage':<22} | {'Tech Stack':<22} | {'Min':>6} | {'Mean':>7} | {'P50':>7} | {'P90':>7} | {'P99':>7}"
    lines.append(header)
    lines.append("-" * len(header))

    chart_items: list[tuple[str, float]] = []

    for stage in summary.stages:
        dist = stage.distribution
        line = (
            f"{stage.stage_name:<22} | "
            f"{stage.technology:<22} | "
            f"{dist.min_ms:>5.1f}m | "
            f"{dist.mean_ms:>6.1f}m | "
            f"{dist.p50_ms:>6.1f}m | "
            f"{dist.p90_ms:>6.1f}m | "
            f"{dist.p99_ms:>6.1f}m"
        )
        lines.append(line)
        chart_items.append((stage.stage_name, dist.p50_ms))

    lines.append("-" * len(header))

    # Add extra metrics details
    lines.append("\n🔍 Specialized Stage Telemetry:")
    for stage in summary.stages:
        if stage.extra_metrics:
            metrics_str = ", ".join(f"{k}: {v}" for k, v in stage.extra_metrics.items())
            lines.append(f"  • {stage.stage_name} ({stage.technology}): {metrics_str}")

    # Add visual chart
    lines.append(render_ascii_bar_chart("Median Latency Profile (P50 Breakdown)", chart_items))

    return "\n".join(lines)


def to_markdown_report(summary: BenchmarkSummary) -> str:
    """Export benchmark summary as formatted GitHub Flavored Markdown."""
    lines: list[str] = []
    lines.append("# ⚡ VoxFlow Voice Agent Latency & Throughput Benchmark Report")
    lines.append("")
    lines.append(f"**Execution Timestamp:** `{summary.timestamp}`  ")
    lines.append(f"**Benchmark Mode:** `{summary.mode.upper()}`  ")
    lines.append(f"**Target Model:** `{summary.model}`  ")
    lines.append(f"**Evaluation Iterations:** `{summary.total_iterations}`  ")
    lines.append("")
    lines.append("## 📈 Percentile Latency Distribution (ms)")
    lines.append("")
    lines.append("| Pipeline Stage | Technology | Samples | Min (ms) | Mean (ms) | P50 (ms) | P90 (ms) | P95 (ms) | P99 (ms) | StdDev |")
    lines.append("| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |")

    for s in summary.stages:
        d = s.distribution
        lines.append(
            f"| **{s.stage_name}** | `{s.technology}` | {d.sample_count} | {d.min_ms:.1f} | {d.mean_ms:.1f} | **{d.p50_ms:.1f}** | {d.p90_ms:.1f} | {d.p95_ms:.1f} | {d.p99_ms:.1f} | ±{d.std_dev_ms:.1f} |"
        )

    lines.append("")
    lines.append("## 🔬 Detailed Component Breakdown & Metrics")
    lines.append("")

    for s in summary.stages:
        lines.append(f"### {s.stage_name} (`{s.technology}`)")
        if s.extra_metrics:
            for k, v in s.extra_metrics.items():
                lines.append(f"- **{k.replace('_', ' ').title()}**: `{v}`")
        lines.append(f"- **Raw Samples (ms)**: `{[round(x, 1) for x in s.sample_latencies_ms]}`")
        lines.append("")

    lines.append("---")
    lines.append("*Generated automatically by the VoxFlow High-Precision Latency Benchmark Suite.*")
    return "\n".join(lines)
