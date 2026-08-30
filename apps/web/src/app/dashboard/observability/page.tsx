"use client";

import { useEffect, useMemo, useState } from "react";
import useSWR from "swr";
import {
  Activity,
  AlertTriangle,
  BellRing,
  CheckCircle2,
  Clock3,
  Database,
  Gauge,
  PhoneCall,
  RefreshCw,
  Send,
  ShieldCheck,
  Sheet,
  Signal,
  TrendingDown,
  TrendingUp,
  Zap,
} from "lucide-react";
import { api } from "@/lib/api";
import { useTenant } from "@/lib/tenant-context";
import { trackEvent } from "@/lib/observability";
import type {
  ObservabilityAlertEvaluation,
  ObservabilityKPIs,
  OperationalEvent,
  OperationalEventsResponse,
  SubsystemHealth,
  SubsystemStatus,
  SystemHealthStatus,
} from "@/lib/types";

const RANGES = [
  { days: 1, label: "24H" },
  { days: 7, label: "7D" },
  { days: 30, label: "30D" },
] as const;

const FCR_TARGET = 85;

const GLASS = "rounded-2xl border border-[#28283c]/80 bg-[#141422]/70 backdrop-blur-xl";

function titleCase(value: string) {
  return value.replace(/_/g, " ").replace(/\b\w/g, (character) => character.toUpperCase());
}

function ms(value: number | null | undefined) {
  if (value === null || value === undefined) return "—";
  if (value >= 1000) return `${(value / 1000).toFixed(2)}s`;
  return `${Math.round(value)}ms`;
}

function relativeTime(iso: string | null) {
  if (!iso) return "—";
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return "—";
  const seconds = Math.max(0, Math.round((Date.now() - then) / 1000));
  if (seconds < 60) return `${seconds}s ago`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
  return `${Math.floor(seconds / 86400)}d ago`;
}

const STATUS_TONE: Record<SubsystemStatus, string> = {
  operational: "text-[#00ffcc] border-[#00ffcc]/30 bg-[#00ffcc]/10",
  degraded: "text-[#ffe04a] border-[#ffe04a]/30 bg-[#ffe04a]/10",
  critical: "text-[#ff2d78] border-[#ff2d78]/30 bg-[#ff2d78]/10",
  down: "text-[#ff2d78] border-[#ff2d78]/30 bg-[#ff2d78]/10",
  idle: "text-[#94a3b8] border-[#94a3b8]/25 bg-[#94a3b8]/10",
  not_configured: "text-[#94a3b8] border-[#94a3b8]/25 bg-[#94a3b8]/10",
};

const SUBSYSTEM_ICON: Record<string, React.ReactNode> = {
  database: <Database size={15} />,
  llm: <Zap size={15} />,
  telephony: <Signal size={15} />,
  sheets_mirror: <Sheet size={15} />,
  durable_jobs: <Activity size={15} />,
};

function PulseBadge({ status }: { status: SystemHealthStatus["overall_status"] | undefined }) {
  const map = {
    operational: { dot: "bg-[#00ffcc]", text: "text-[#00ffcc]", label: "All Systems Operational" },
    degraded: { dot: "bg-[#ffe04a]", text: "text-[#ffe04a]", label: "Degraded Performance" },
    critical: { dot: "bg-[#ff2d78]", text: "text-[#ff2d78]", label: "Critical — Action Required" },
  } as const;
  const tone = map[status || "operational"];
  return (
    <span
      className={`inline-flex items-center gap-2 rounded-xl border border-current/25 bg-current/5 px-3 py-1.5 text-xs font-mono font-bold ${tone.text}`}
    >
      <span className="relative flex h-2 w-2">
        <span className={`absolute inline-flex h-full w-full animate-ping rounded-full opacity-70 ${tone.dot}`} />
        <span className={`relative inline-flex h-2 w-2 rounded-full ${tone.dot}`} />
      </span>
      {tone.label}
    </span>
  );
}

function DeltaChip({ value, invert = false }: { value: number | null; invert?: boolean }) {
  if (value === null || value === 0) {
    return <span className="text-[10px] font-mono text-[#64748b]">no prior baseline</span>;
  }
  // For escalation rate and latency, a rise is bad — invert the colour semantics.
  const good = invert ? value < 0 : value > 0;
  const Icon = value > 0 ? TrendingUp : TrendingDown;
  return (
    <span
      className={`inline-flex items-center gap-1 text-[10px] font-mono font-bold ${good ? "text-[#00ffcc]" : "text-[#ff2d78]"}`}
    >
      <Icon size={11} />
      {value > 0 ? "+" : ""}
      {value}% vs prior
    </span>
  );
}

function ScoreCard({
  label,
  value,
  icon,
  delta,
  invertDelta,
  footnote,
  tone = "teal",
}: {
  label: string;
  value: string;
  icon: React.ReactNode;
  delta?: number | null;
  invertDelta?: boolean;
  footnote: string;
  tone?: "teal" | "amber" | "rose" | "blue";
}) {
  const tones = {
    teal: "text-[#00ffcc] bg-[#00ffcc]/10 border-[#00ffcc]/25",
    amber: "text-[#ffe04a] bg-[#ffe04a]/10 border-[#ffe04a]/25",
    rose: "text-[#ff2d78] bg-[#ff2d78]/10 border-[#ff2d78]/25",
    blue: "text-blue-400 bg-blue-400/10 border-blue-400/25",
  };
  return (
    <div className={`${GLASS} p-5`}>
      <div className="mb-3 flex items-center justify-between text-xs font-mono text-[#94a3b8]">
        <span>{label}</span>
        <span className={`flex h-8 w-8 items-center justify-center rounded-xl border ${tones[tone]}`}>{icon}</span>
      </div>
      <div className="text-3xl font-black tracking-tight text-white">{value}</div>
      <div className="mt-1.5 flex flex-col gap-0.5">
        {delta !== undefined && <DeltaChip value={delta ?? null} invert={invertDelta} />}
        <p className="text-[11px] text-[#64748b]">{footnote}</p>
      </div>
    </div>
  );
}

function VolumeChart({ points }: { points: ObservabilityKPIs["calls_over_time"] }) {
  const max = Math.max(...points.map((point) => point.calls), 1);
  return (
    <div className={`${GLASS} p-6`}>
      <div className="flex flex-wrap items-start justify-between gap-3 border-b border-[#242436] pb-4">
        <div>
          <div className="flex items-center gap-2">
            <PhoneCall size={17} className="text-[#00ffcc]" />
            <h2 className="font-headline text-base font-bold text-white">Volume &amp; Resolution Trend</h2>
          </div>
          <p className="mt-1 text-xs text-[#94a3b8]">Calls, resolved, and escalated per day from persisted tenant records.</p>
        </div>
        <div className="flex items-center gap-3 text-[10px] font-mono">
          <span className="flex items-center gap-1.5 text-[#94a3b8]"><i className="h-2 w-2 rounded-sm bg-[#2f3350]" />Calls</span>
          <span className="flex items-center gap-1.5 text-[#94a3b8]"><i className="h-2 w-2 rounded-sm bg-[#00ffcc]" />Resolved</span>
          <span className="flex items-center gap-1.5 text-[#94a3b8]"><i className="h-2 w-2 rounded-sm bg-[#ff2d78]" />Escalated</span>
        </div>
      </div>
      <div className="mt-6 flex h-44 items-end gap-1.5">
        {points.map((point) => {
          const total = (point.calls / max) * 100;
          const resolved = point.calls ? (point.resolved / point.calls) * total : 0;
          const escalated = point.calls ? (point.escalated / point.calls) * total : 0;
          return (
            <div key={point.date} className="group flex min-w-0 flex-1 flex-col items-center gap-2">
              <div className="relative flex h-32 w-full flex-col justify-end overflow-hidden rounded-t-md bg-[#181826]">
                <div
                  className="w-full bg-[#2f3350] transition-opacity group-hover:opacity-80"
                  style={{ height: `${Math.max(total - resolved - escalated, point.calls ? 3 : 1)}%` }}
                  title={`${point.date}: ${point.calls} calls`}
                />
                <div className="w-full bg-[#ff2d78]" style={{ height: `${escalated}%` }} title={`${point.escalated} escalated`} />
                <div className="w-full bg-[#00ffcc]" style={{ height: `${resolved}%` }} title={`${point.resolved} resolved`} />
              </div>
              <span className="text-[9px] font-mono text-[#64748b]">{point.date.slice(5)}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function LatencyCurve({ kpis }: { kpis: ObservabilityKPIs }) {
  const distribution = kpis.latency_distribution;
  const bars = [
    { label: "P50", value: distribution.p50_ms, tone: "bg-[#00ffcc]" },
    { label: "P90", value: distribution.p90_ms, tone: "bg-[#ffe04a]" },
    { label: "P95", value: distribution.p95_ms, tone: "bg-[#ff9d4a]" },
    { label: "P99", value: distribution.p99_ms, tone: "bg-[#ff2d78]" },
  ];
  const max = Math.max(...bars.map((bar) => bar.value), 1);
  return (
    <div className={`${GLASS} p-6`}>
      <div className="flex items-center gap-2 border-b border-[#242436] pb-4">
        <Gauge size={17} className="text-[#ffe04a]" />
        <div>
          <h2 className="font-headline text-base font-bold text-white">Turn Latency Distribution</h2>
          <p className="mt-1 text-xs text-[#94a3b8]">
            Glass-to-glass server turn latency across {distribution.sample_count} sampled call(s).
          </p>
        </div>
      </div>
      {distribution.sample_count ? (
        <div className="mt-5 space-y-3">
          {bars.map((bar) => (
            <div key={bar.label}>
              <div className="mb-1 flex items-center justify-between text-xs">
                <span className="font-mono text-[#cbd5e1]">{bar.label}</span>
                <span className="font-mono font-bold text-white">{ms(bar.value)}</span>
              </div>
              <div className="h-2 overflow-hidden rounded-full bg-[#181826]">
                <div className={`h-full rounded-full ${bar.tone}`} style={{ width: `${(bar.value / max) * 100}%` }} />
              </div>
            </div>
          ))}
          <div className="grid grid-cols-3 gap-3 border-t border-[#242436] pt-4 text-xs">
            <div><span className="text-[#64748b]">Min</span><p className="mt-1 font-mono font-bold text-white">{ms(distribution.min_ms)}</p></div>
            <div><span className="text-[#64748b]">Mean</span><p className="mt-1 font-mono font-bold text-white">{ms(distribution.mean_ms)}</p></div>
            <div><span className="text-[#64748b]">Max</span><p className="mt-1 font-mono font-bold text-white">{ms(distribution.max_ms)}</p></div>
          </div>
        </div>
      ) : (
        <p className="mt-6 text-xs text-[#64748b]">No turn-latency samples were recorded in this period.</p>
      )}
    </div>
  );
}

function BreakdownBars({ title, values, emptyLabel }: { title: string; values: Record<string, number>; emptyLabel: string }) {
  const entries = Object.entries(values).sort((a, b) => b[1] - a[1]).slice(0, 6);
  const max = Math.max(...entries.map(([, value]) => value), 1);
  return (
    <div className={`${GLASS} p-5`}>
      <h3 className="font-headline text-sm font-bold text-white">{title}</h3>
      <div className="mt-4 space-y-3">
        {entries.length ? (
          entries.map(([label, value]) => (
            <div key={label}>
              <div className="mb-1 flex items-center justify-between gap-3 text-xs">
                <span className="truncate text-[#cbd5e1]">{titleCase(label)}</span>
                <span className="font-mono font-bold text-white">{value}</span>
              </div>
              <div className="h-1.5 overflow-hidden rounded-full bg-[#181826]">
                <div className="h-full rounded-full bg-gradient-to-r from-[#00cfa8] to-[#00ffcc]" style={{ width: `${(value / max) * 100}%` }} />
              </div>
            </div>
          ))
        ) : (
          <p className="text-xs text-[#64748b]">{emptyLabel}</p>
        )}
      </div>
    </div>
  );
}

function SubsystemCard({ subsystem }: { subsystem: SubsystemHealth }) {
  return (
    <div className={`${GLASS} p-4`}>
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2 text-xs font-mono text-[#94a3b8]">
          <span className="text-[#cbd5e1]">{SUBSYSTEM_ICON[subsystem.key] ?? <Activity size={15} />}</span>
          <span className="truncate">{subsystem.label}</span>
        </div>
        <span className={`shrink-0 rounded-lg border px-2 py-0.5 text-[9px] font-mono font-bold uppercase ${STATUS_TONE[subsystem.status]}`}>
          {subsystem.status === "not_configured" ? "N/A" : subsystem.status}
        </span>
      </div>
      <div className="mt-3 text-2xl font-black tracking-tight text-white">{ms(subsystem.latency_ms)}</div>
      <p className="mt-1 line-clamp-2 text-[11px] leading-snug text-[#64748b]">{subsystem.detail}</p>
    </div>
  );
}

const EVENT_TONE: Record<OperationalEvent["status"], string> = {
  success: "border-[#00ffcc]/25 text-[#00ffcc]",
  warning: "border-[#ffe04a]/25 text-[#ffe04a]",
  error: "border-[#ff2d78]/25 text-[#ff2d78]",
  info: "border-blue-400/25 text-blue-400",
};

export default function ObservabilityPage() {
  const { activeTenantId, activeTenant } = useTenant();
  const [days, setDays] = useState<number>(7);
  const [testing, setTesting] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  const kpiQuery = useSWR<ObservabilityKPIs>(
    ["observability-kpis", activeTenantId, days],
    () => api.getObservabilityKPIs(activeTenantId, days),
    { refreshInterval: 30_000, revalidateOnFocus: true },
  );
  const healthQuery = useSWR<SystemHealthStatus>(
    ["observability-health", activeTenantId],
    () => api.getSystemHealth(activeTenantId),
    { refreshInterval: 15_000, revalidateOnFocus: true },
  );
  const eventsQuery = useSWR<OperationalEventsResponse>(
    ["observability-events", activeTenantId],
    () => api.getOperationalEvents(activeTenantId, 25),
    { refreshInterval: 20_000, revalidateOnFocus: true },
  );
  const alertsQuery = useSWR<ObservabilityAlertEvaluation>(
    ["observability-alerts", activeTenantId, days],
    () => api.getObservabilityAlerts(activeTenantId, days),
    { refreshInterval: 30_000, revalidateOnFocus: true },
  );

  const kpis = kpiQuery.data;
  const health = healthQuery.data;
  const alerts = alertsQuery.data;

  useEffect(() => {
    trackEvent("observability_dashboard_viewed", { surface: "dashboard", range_days: days });
  }, [days]);

  const fcrOnTarget = (kpis?.resolution_rate ?? 0) >= FCR_TARGET;
  const chartPoints = useMemo(() => kpis?.calls_over_time.slice(-30) ?? [], [kpis]);

  async function runTestAlert() {
    setActionError(null);
    setNotice(null);
    setTesting(true);
    try {
      const result = await api.triggerTestAlert(activeTenantId);
      trackEvent("observability_test_alert", {
        result: result.dispatch.queued ? "queued" : "skipped",
        alert_count: result.evaluation.alert_count,
      });
      setNotice(
        result.dispatch.queued
          ? `Test alert queued for durable delivery (job ${result.dispatch.job_id?.slice(0, 12)}…). Nothing was sent inline.`
          : `Alert dispatch skipped: ${titleCase(result.dispatch.reason)}.`,
      );
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "Unable to trigger a test alert.");
    } finally {
      setTesting(false);
    }
  }

  function refreshAll() {
    void kpiQuery.mutate();
    void healthQuery.mutate();
    void eventsQuery.mutate();
    void alertsQuery.mutate();
  }

  const loading = kpiQuery.isLoading && !kpis;
  const loadError = kpiQuery.error instanceof Error ? kpiQuery.error.message : null;

  return (
    <div className="mx-auto max-w-7xl space-y-6 pb-16">
      {/* Live Pulse Header */}
      <header className={`flex flex-col gap-4 rounded-2xl border border-[#242436] bg-gradient-to-br from-[#12121e] via-[#141422] to-[#12121e] p-6 shadow-sm lg:flex-row lg:items-center lg:justify-between`}>
        <div>
          <div className="flex flex-wrap items-center gap-2 text-xs font-mono text-[#94a3b8]">
            <span>Enterprise Observability</span>
            <span>/</span>
            <span className="font-bold text-[#00ffcc]">{activeTenant.name}</span>
            {alerts && alerts.alert_count > 0 && (
              <span className="inline-flex items-center gap-1 rounded-lg border border-[#ff2d78]/35 bg-[#ff2d78]/10 px-2 py-0.5 font-bold text-[#ff2d78]">
                <BellRing size={11} /> {alerts.alert_count} ALERT{alerts.alert_count === 1 ? "" : "S"}
              </span>
            )}
          </div>
          <h1 className="mt-2 text-2xl font-bold tracking-tight text-white">Call KPIs &amp; System Health</h1>
          <div className="mt-3 flex flex-wrap items-center gap-3">
            <PulseBadge status={health?.overall_status} />
            <span className="text-[11px] font-mono text-[#64748b]">
              Updated {relativeTime(health?.generated_at ?? kpis?.period.generated_at ?? null)}
            </span>
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <div className="flex rounded-xl border border-[#2c2c40] bg-[#181826] p-1">
            {RANGES.map((option) => (
              <button
                key={option.days}
                type="button"
                onClick={() => setDays(option.days)}
                className={`rounded-lg px-3 py-1.5 text-xs font-mono font-bold transition-colors ${days === option.days ? "bg-[#00ffcc] text-[#061313]" : "text-[#94a3b8] hover:text-white"}`}
              >
                {option.label}
              </button>
            ))}
          </div>
          <button
            type="button"
            onClick={refreshAll}
            className="inline-flex items-center gap-2 rounded-xl border border-[#2c2c40] bg-[#181826] px-3 py-2 text-xs font-medium text-[#cbd5e1] transition-colors hover:bg-[#202034] hover:text-white"
          >
            <RefreshCw size={14} /> Refresh
          </button>
          <button
            type="button"
            onClick={() => void runTestAlert()}
            disabled={testing}
            className="inline-flex items-center gap-2 rounded-xl bg-[#00ffcc] px-3 py-2 text-xs font-bold text-[#061313] transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-50"
          >
            <Send size={14} /> {testing ? "Queueing…" : "Test Alert"}
          </button>
        </div>
      </header>

      {loadError && (
        <div className="rounded-xl border border-[#ff2d78]/40 bg-[#ff2d78]/10 px-4 py-3 text-sm text-[#fecdd3]">
          Observability data could not be loaded: {loadError}
        </div>
      )}
      {actionError && (
        <div className="rounded-xl border border-[#ff2d78]/40 bg-[#ff2d78]/10 px-4 py-3 text-sm text-[#fecdd3]">{actionError}</div>
      )}
      {notice && (
        <div className="rounded-xl border border-[#00ffcc]/30 bg-[#00ffcc]/5 px-4 py-3 text-sm text-[#bfffee]">{notice}</div>
      )}

      {/* Alert feed */}
      {alerts && alerts.alerts.length > 0 && (
        <section className="space-y-2">
          {alerts.alerts.map((alert) => (
            <div
              key={alert.code}
              className={`flex gap-3 rounded-xl border p-3 text-sm ${alert.severity === "critical" ? "border-[#ff2d78]/30 bg-[#ff2d78]/10" : "border-[#ffe04a]/30 bg-[#ffe04a]/10"}`}
            >
              <AlertTriangle
                size={16}
                className={`mt-0.5 shrink-0 ${alert.severity === "critical" ? "text-[#ff2d78]" : "text-[#ffe04a]"}`}
              />
              <div className="min-w-0">
                <p className="font-mono text-[11px] font-bold uppercase text-white">{titleCase(alert.code)}</p>
                <p className="mt-1 text-xs text-[#cbd5e1]">{alert.message}</p>
              </div>
              <span className="ml-auto shrink-0 self-center font-mono text-[10px] text-[#94a3b8]">
                {alert.observed} / {alert.threshold}
              </span>
            </div>
          ))}
        </section>
      )}

      {loading ? (
        <div className={`${GLASS} p-12 text-center text-sm text-[#94a3b8]`}>Loading tenant observability…</div>
      ) : kpis ? (
        <>
          {/* 4 Key Scorecards */}
          <section className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <ScoreCard
              label="Total Inbound Calls"
              value={String(kpis.total_calls)}
              icon={<PhoneCall size={16} />}
              delta={kpis.deltas.total_calls_pct}
              footnote={`${kpis.total_minutes} voice minutes · ${kpis.deltas.prior_total_calls} prior period`}
            />
            <ScoreCard
              label="First-Contact Resolution"
              value={`${kpis.resolution_rate}%`}
              icon={fcrOnTarget ? <CheckCircle2 size={16} /> : <AlertTriangle size={16} />}
              delta={kpis.deltas.resolution_rate_pct}
              tone={fcrOnTarget ? "teal" : "amber"}
              footnote={`${kpis.resolved_calls} resolved · target ≥ ${FCR_TARGET}%`}
            />
            <ScoreCard
              label="Escalation Rate"
              value={`${kpis.escalation_rate}%`}
              icon={<ShieldCheck size={16} />}
              delta={kpis.deltas.escalation_rate_pct}
              invertDelta
              tone="rose"
              footnote={`${kpis.escalated_calls} escalated · ${kpis.sla_breached_count} past SLA`}
            />
            <ScoreCard
              label="Median Turn Latency"
              value={ms(kpis.median_turn_latency_ms)}
              icon={<Clock3 size={16} />}
              delta={kpis.deltas.median_turn_latency_pct}
              invertDelta
              tone="blue"
              footnote={`P90 ${ms(kpis.p90_turn_latency_ms)} · P99 ${ms(kpis.p99_turn_latency_ms)}`}
            />
          </section>

          {/* Charts */}
          <section className="grid grid-cols-1 gap-6 xl:grid-cols-3">
            <div className="xl:col-span-2">
              <VolumeChart points={chartPoints} />
            </div>
            <LatencyCurve kpis={kpis} />
          </section>

          {/* Subsystem Latency & Health Matrix */}
          <section>
            <div className="mb-3 flex items-center gap-2">
              <Gauge size={17} className="text-[#00ffcc]" />
              <h2 className="font-headline text-base font-bold text-white">Subsystem Latency &amp; Health</h2>
              {health && (
                <span className="ml-auto font-mono text-[10px] text-[#64748b]">
                  {health.calls_24h} calls / 24h · {health.error_rate_24h}% error rate
                </span>
              )}
            </div>
            {health ? (
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5">
                {health.subsystems.map((subsystem) => (
                  <SubsystemCard key={subsystem.key} subsystem={subsystem} />
                ))}
              </div>
            ) : (
              <div className={`${GLASS} p-6 text-xs text-[#64748b]`}>Loading subsystem diagnostics…</div>
            )}
          </section>

          {/* Breakdowns + Event Log */}
          <section className="grid grid-cols-1 gap-6 xl:grid-cols-3">
            <div className="space-y-6">
              <BreakdownBars title="Call Reason" values={kpis.breakdown.reasons} emptyLabel="No call intents in this period." />
              <BreakdownBars
                title="Resolution Category"
                values={kpis.breakdown.resolution_categories}
                emptyLabel="No categorized resolutions in this period."
              />
            </div>

            <div className={`${GLASS} p-6 xl:col-span-2`}>
              <div className="flex flex-wrap items-center justify-between gap-2 border-b border-[#242436] pb-4">
                <div className="flex items-center gap-2">
                  <Activity size={17} className="text-blue-400" />
                  <div>
                    <h2 className="font-headline text-base font-bold text-white">Operational Event Log</h2>
                    <p className="mt-1 text-xs text-[#94a3b8]">
                      Server-redacted stream. Caller numbers, PINs, names, and order payloads never reach this feed.
                    </p>
                  </div>
                </div>
                <span className="font-mono text-[10px] text-[#64748b]">Auto-refresh 20s</span>
              </div>
              <div className="mt-4 max-h-[28rem] space-y-1.5 overflow-y-auto pr-1">
                {eventsQuery.data?.events.length ? (
                  eventsQuery.data.events.map((event) => (
                    <div
                      key={event.id}
                      className="flex items-start gap-3 rounded-xl border border-[#242436] bg-[#181826]/60 px-3 py-2.5"
                    >
                      <span
                        className={`mt-0.5 shrink-0 rounded-lg border px-1.5 py-0.5 text-[9px] font-mono font-bold uppercase ${EVENT_TONE[event.status]}`}
                      >
                        {event.status}
                      </span>
                      <div className="min-w-0 flex-1">
                        <p className="truncate text-xs font-bold text-white">{event.label}</p>
                        <p className="mt-0.5 truncate font-mono text-[11px] text-[#94a3b8]">{event.detail}</p>
                      </div>
                      <span className="shrink-0 font-mono text-[10px] text-[#64748b]">{relativeTime(event.occurred_at)}</span>
                    </div>
                  ))
                ) : (
                  <p className="py-6 text-center text-xs text-[#64748b]">No operational events recorded for this tenant yet.</p>
                )}
              </div>
            </div>
          </section>

          {/* Alert routing */}
          {alerts && (
            <section className={`${GLASS} p-6`}>
              <div className="flex items-center gap-2 border-b border-[#242436] pb-4">
                <BellRing size={17} className="text-[#ffe04a]" />
                <div>
                  <h2 className="font-headline text-base font-bold text-white">Alert Routing &amp; Thresholds</h2>
                  <p className="mt-1 text-xs text-[#94a3b8]">
                    Notifications are queued for the durable worker. The API never sends mail or calls a webhook inline.
                  </p>
                </div>
              </div>
              <div className="mt-5 grid grid-cols-1 gap-4 lg:grid-cols-2">
                <div className="grid grid-cols-2 gap-3">
                  {(
                    [
                      ["Escalation rate", `> ${alerts.thresholds.escalation_rate_pct}%`],
                      ["SLA breaches", `> ${alerts.thresholds.sla_breach_count}`],
                      ["P90 latency", `> ${ms(alerts.thresholds.p90_latency_ms)}`],
                      ["Error rate 24h", `> ${alerts.thresholds.error_rate_pct}%`],
                    ] as const
                  ).map(([label, threshold]) => (
                    <div key={label} className="rounded-xl border border-[#2c2c40] bg-[#181826] p-3">
                      <p className="text-[10px] font-mono uppercase text-[#94a3b8]">{label}</p>
                      <p className="mt-1 font-mono text-sm font-bold text-white">{threshold}</p>
                    </div>
                  ))}
                </div>
                <div className="space-y-2">
                  {(["email", "webhook", "in_app"] as const).map((channel) => {
                    const config = alerts.channels?.[channel];
                    return (
                      <div
                        key={channel}
                        className="flex items-center justify-between gap-3 rounded-xl border border-[#2c2c40] bg-[#181826] px-3 py-2.5"
                      >
                        <span className="text-xs text-[#cbd5e1]">{titleCase(channel)}</span>
                        <span
                          className={`font-mono text-[10px] font-bold uppercase ${config?.configured ? "text-[#00ffcc]" : "text-[#94a3b8]"}`}
                        >
                          {config?.configured ? "Configured" : "Not configured"}
                        </span>
                      </div>
                    );
                  })}
                </div>
              </div>
            </section>
          )}
        </>
      ) : null}
    </div>
  );
}
