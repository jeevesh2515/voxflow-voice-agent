"use client";

import { useMemo, useState } from "react";
import useSWR from "swr";
import {
  Activity,
  AlertTriangle,
  BarChart3,
  CheckCircle2,
  Clock3,
  Download,
  FileBarChart,
  Gauge,
  RefreshCw,
  ShieldCheck,
  Siren,
  UsersRound,
} from "lucide-react";
import { api } from "@/lib/api";
import { useTenant } from "@/lib/tenant-context";
import type { AnalyticsOverview } from "@/lib/types";

const PERIODS = [7, 30, 90] as const;

function durationLabel(seconds: number) {
  const minutes = Math.floor(seconds / 60);
  const remainder = seconds % 60;
  return minutes ? `${minutes}m ${remainder}s` : `${remainder}s`;
}

function ageLabel(seconds: number | null) {
  if (seconds === null) return "—";
  if (seconds < 60) return `${seconds}s`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m`;
  return `${Math.floor(seconds / 3600)}h ${Math.floor((seconds % 3600) / 60)}m`;
}

function titleCase(value: string) {
  return value.replace(/_/g, " ").replace(/\b\w/g, (character) => character.toUpperCase());
}

function MetricCard({
  label,
  value,
  caption,
  tone = "teal",
  icon,
}: {
  label: string;
  value: string | number;
  caption: string;
  tone?: "teal" | "amber" | "rose" | "blue";
  icon: React.ReactNode;
}) {
  const tones = {
    teal: "text-[#00ffcc] bg-[#00ffcc]/10 border-[#00ffcc]/25",
    amber: "text-[#ffe04a] bg-[#ffe04a]/10 border-[#ffe04a]/25",
    rose: "text-[#ff2d78] bg-[#ff2d78]/10 border-[#ff2d78]/25",
    blue: "text-blue-400 bg-blue-400/10 border-blue-400/25",
  };
  return (
    <div className="rounded-2xl border border-[#28283c] bg-[#141422] p-5 shadow-sm">
      <div className="mb-3 flex items-center justify-between text-xs font-mono text-[#94a3b8]">
        <span>{label}</span>
        <span className={`flex h-8 w-8 items-center justify-center rounded-xl border ${tones[tone]}`}>{icon}</span>
      </div>
      <div className="text-3xl font-black tracking-tight text-white">{value}</div>
      <p className="mt-1 text-[11px] text-[#64748b]">{caption}</p>
    </div>
  );
}

function DistributionList({ title, values, emptyLabel }: { title: string; values: Record<string, number>; emptyLabel: string }) {
  const entries = Object.entries(values).sort((a, b) => b[1] - a[1]);
  const max = Math.max(...entries.map(([, value]) => value), 1);
  return (
    <div className="rounded-2xl border border-[#28283c] bg-[#141422] p-5">
      <h3 className="font-headline text-sm font-bold text-white">{title}</h3>
      <div className="mt-4 space-y-3">
        {entries.length ? entries.slice(0, 5).map(([label, value]) => (
          <div key={label}>
            <div className="mb-1 flex items-center justify-between gap-3 text-xs">
              <span className="truncate text-[#cbd5e1]">{titleCase(label)}</span>
              <span className="font-mono font-bold text-white">{value}</span>
            </div>
            <div className="h-1.5 overflow-hidden rounded-full bg-[#181826]">
              <div className="h-full rounded-full bg-[#00ffcc]" style={{ width: `${(value / max) * 100}%` }} />
            </div>
          </div>
        )) : <p className="text-xs text-[#64748b]">{emptyLabel}</p>}
      </div>
    </div>
  );
}

function MonitoringBadge({ state }: { state: AnalyticsOverview["monitoring"]["state"] }) {
  const styles = {
    healthy: "border-[#00ffcc]/35 bg-[#00ffcc]/10 text-[#00ffcc]",
    attention: "border-[#ffe04a]/35 bg-[#ffe04a]/10 text-[#ffe04a]",
    critical: "border-[#ff2d78]/35 bg-[#ff2d78]/10 text-[#ff2d78]",
  };
  return <span className={`rounded-lg border px-2.5 py-1 text-xs font-mono font-bold uppercase ${styles[state]}`}>{state}</span>;
}

export default function AnalyticsPage() {
  const { activeTenantId, activeTenant } = useTenant();
  const [days, setDays] = useState<(typeof PERIODS)[number]>(30);
  const [exporting, setExporting] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const { data, error, isLoading, mutate } = useSWR(
    ["analytics-overview", activeTenantId, days],
    () => api.analyticsOverview(activeTenantId, days),
    { refreshInterval: 30_000, revalidateOnFocus: true },
  );

  const chartPoints = useMemo(() => data?.trends.slice(-14) || [], [data]);
  const chartMax = Math.max(...chartPoints.map((point) => point.calls), 1);

  async function exportReport() {
    setActionError(null);
    setExporting(true);
    try {
      await api.downloadAnalyticsReport(activeTenantId, days);
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "Unable to export the enterprise report.");
    } finally {
      setExporting(false);
    }
  }

  const loadingShell = isLoading && !data;
  const currentError = error instanceof Error ? error.message : actionError;

  return (
    <div className="mx-auto max-w-7xl space-y-6 pb-16">
      <header className="flex flex-col gap-4 rounded-2xl border border-[#242436] bg-[#12121e] p-6 shadow-sm lg:flex-row lg:items-center lg:justify-between">
        <div>
          <div className="flex items-center gap-2 text-xs font-mono text-[#94a3b8]">
            <span>Enterprise Operations Intelligence</span>
            <span>/</span>
            <span className="font-bold text-[#00ffcc]">{activeTenant.name}</span>
          </div>
          <h1 className="mt-2 text-2xl font-bold tracking-tight text-white">Advanced Analytics & Monitoring</h1>
          <p className="mt-1 max-w-2xl text-sm text-[#94a3b8]">
            Tenant-safe operational KPIs, durable-work health, campaign policy trends, and exportable reporting from persisted VoxFlow data.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <div className="flex rounded-xl border border-[#2c2c40] bg-[#181826] p-1">
            {PERIODS.map((option) => (
              <button
                key={option}
                type="button"
                onClick={() => setDays(option)}
                className={`rounded-lg px-3 py-1.5 text-xs font-mono font-bold transition-colors ${days === option ? "bg-[#00ffcc] text-[#061313]" : "text-[#94a3b8] hover:text-white"}`}
              >
                {option}D
              </button>
            ))}
          </div>
          <button
            type="button"
            onClick={() => void mutate()}
            className="inline-flex items-center gap-2 rounded-xl border border-[#2c2c40] bg-[#181826] px-3 py-2 text-xs font-medium text-[#cbd5e1] transition-colors hover:bg-[#202034] hover:text-white"
          >
            <RefreshCw size={14} /> Refresh
          </button>
          <button
            type="button"
            onClick={() => void exportReport()}
            disabled={exporting || loadingShell}
            className="inline-flex items-center gap-2 rounded-xl bg-[#00ffcc] px-3 py-2 text-xs font-bold text-[#061313] transition-opacity hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-50"
          >
            <Download size={14} /> {exporting ? "Preparing…" : "Export CSV"}
          </button>
        </div>
      </header>

      {currentError && (
        <div className="rounded-xl border border-[#ff2d78]/40 bg-[#ff2d78]/10 px-4 py-3 text-sm text-[#fecdd3]">
          Analytics data could not be loaded: {currentError}
        </div>
      )}

      {loadingShell ? (
        <div className="rounded-2xl border border-[#28283c] bg-[#141422] p-12 text-center text-sm text-[#94a3b8]">Loading tenant analytics…</div>
      ) : data ? (
        <>
          <section className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <MetricCard label="Resolution Rate" value={`${data.kpis.resolution_rate}%`} caption={`${data.kpis.resolved_calls} resolved calls`} icon={<CheckCircle2 size={16} />} />
            <MetricCard label="Avg Handle Time" value={durationLabel(data.kpis.average_handle_time_sec)} caption={`${data.kpis.total_minutes} voice minutes in period`} tone="amber" icon={<Clock3 size={16} />} />
            <MetricCard label="Escalation Rate" value={`${data.kpis.escalation_rate}%`} caption={`${data.kpis.escalated_calls} calls referred to staff`} tone="rose" icon={<UsersRound size={16} />} />
            <MetricCard label="Verified Calls" value={`${data.kpis.verified_call_rate}%`} caption={`${data.kpis.open_follow_ups} open follow-up items`} tone="blue" icon={<ShieldCheck size={16} />} />
          </section>

          <section className="grid grid-cols-1 gap-6 xl:grid-cols-3">
            <div className="rounded-2xl border border-[#28283c] bg-[#141422] p-6 xl:col-span-2">
              <div className="flex flex-wrap items-start justify-between gap-3 border-b border-[#242436] pb-4">
                <div>
                  <div className="flex items-center gap-2">
                    <BarChart3 size={18} className="text-[#00ffcc]" />
                    <h2 className="font-headline text-base font-bold text-white">Call Activity Trend</h2>
                  </div>
                  <p className="mt-1 text-xs text-[#94a3b8]">Daily persisted call volume over the selected reporting period.</p>
                </div>
                <span className="rounded-lg border border-[#2c2c40] bg-[#181826] px-2.5 py-1 text-xs font-mono text-[#94a3b8]">
                  {data.period.from} — {data.period.to}
                </span>
              </div>
              <div className="mt-6 flex h-48 items-end gap-2">
                {chartPoints.map((point) => (
                  <div key={point.date} className="group flex min-w-0 flex-1 flex-col items-center gap-2">
                    <div className="relative flex h-36 w-full items-end rounded-t-md bg-[#181826]">
                      <div
                        className="w-full rounded-t-md bg-gradient-to-t from-[#00cfa8] to-[#00ffcc] transition-opacity group-hover:opacity-80"
                        style={{ height: `${Math.max((point.calls / chartMax) * 100, point.calls ? 8 : 2)}%` }}
                        title={`${point.date}: ${point.calls} calls, ${point.resolved} resolved, ${point.escalated} escalated`}
                      />
                    </div>
                    <span className="text-[9px] font-mono text-[#64748b]">{point.date.slice(5)}</span>
                  </div>
                ))}
              </div>
              <div className="mt-4 grid grid-cols-3 gap-3 border-t border-[#242436] pt-4 text-xs">
                <div><span className="text-[#64748b]">Total calls</span><p className="mt-1 font-mono text-lg font-bold text-white">{data.kpis.total_calls}</p></div>
                <div><span className="text-[#64748b]">Resolved</span><p className="mt-1 font-mono text-lg font-bold text-[#00ffcc]">{data.kpis.resolved_calls}</p></div>
                <div><span className="text-[#64748b]">Open follow-ups</span><p className="mt-1 font-mono text-lg font-bold text-[#ffe04a]">{data.kpis.open_follow_ups}</p></div>
              </div>
            </div>

            <div className="rounded-2xl border border-[#28283c] bg-[#141422] p-6">
              <div className="flex items-center justify-between border-b border-[#242436] pb-4">
                <div className="flex items-center gap-2">
                  <Gauge size={18} className="text-[#00ffcc]" />
                  <h2 className="font-headline text-base font-bold text-white">Monitoring State</h2>
                </div>
                <MonitoringBadge state={data.monitoring.state} />
              </div>
              <div className="mt-5 grid grid-cols-2 gap-3">
                <div className="rounded-xl border border-[#2c2c40] bg-[#181826] p-3"><p className="text-[10px] font-mono text-[#94a3b8]">READY AGE</p><p className="mt-1 text-xl font-bold text-white">{ageLabel(data.monitoring.oldest_ready_age_sec)}</p></div>
                <div className="rounded-xl border border-[#2c2c40] bg-[#181826] p-3"><p className="text-[10px] font-mono text-[#94a3b8]">OUTBOX AGE</p><p className="mt-1 text-xl font-bold text-white">{ageLabel(data.monitoring.oldest_outbox_age_sec)}</p></div>
                <div className="rounded-xl border border-[#2c2c40] bg-[#181826] p-3"><p className="text-[10px] font-mono text-[#94a3b8]">ACTIVE JOBS</p><p className="mt-1 text-xl font-bold text-white">{data.monitoring.active_jobs}</p></div>
                <div className="rounded-xl border border-[#2c2c40] bg-[#181826] p-3"><p className="text-[10px] font-mono text-[#94a3b8]">DEAD LETTERS</p><p className="mt-1 text-xl font-bold text-[#ff2d78]">{data.monitoring.dead_lettered_jobs}</p></div>
              </div>
              <div className="mt-5 rounded-xl border border-[#00ffcc]/20 bg-[#00ffcc]/5 p-3 text-xs text-[#cbd5e1]">
                <span className="font-mono font-bold text-[#00ffcc]">{data.monitoring.rollout.activation_mode.toUpperCase()}</span>
                <span className="ml-2">Campaign dispatch remains {data.monitoring.rollout.dry_run ? "dry-run protected" : "feature-gated"}; analytics never invokes a provider.</span>
              </div>
            </div>
          </section>

          <section className="grid grid-cols-1 gap-6 lg:grid-cols-2 xl:grid-cols-4">
            <DistributionList title="Top Intents" values={data.distribution.intents} emptyLabel="No call intents in this period." />
            <DistributionList title="Call Outcomes" values={data.distribution.outcomes} emptyLabel="No call outcomes in this period." />
            <DistributionList title="Policy Decisions" values={data.campaigns.policy_decision_counts} emptyLabel="No durable policy decisions in this period." />
            <div className="rounded-2xl border border-[#28283c] bg-[#141422] p-5">
              <div className="flex items-center gap-2"><Activity size={18} className="text-blue-400" /><h3 className="font-headline text-sm font-bold text-white">Provider Lifecycle</h3></div>
              <p className="mt-2 text-xs text-[#94a3b8]">Signed callback observations owned by this tenant only.</p>
              <div className="mt-5 grid grid-cols-2 gap-3">
                <div className="rounded-xl border border-[#2c2c40] bg-[#181826] p-3"><p className="text-[10px] font-mono text-[#94a3b8]">EVENTS</p><p className="mt-1 text-xl font-bold text-white">{data.provider_lifecycle.event_count}</p></div>
                <div className="rounded-xl border border-[#2c2c40] bg-[#181826] p-3"><p className="text-[10px] font-mono text-[#94a3b8]">ANOMALIES</p><p className={`mt-1 text-xl font-bold ${data.provider_lifecycle.anomaly_count ? "text-[#ffe04a]" : "text-[#00ffcc]"}`}>{data.provider_lifecycle.anomaly_count}</p></div>
              </div>
              <div className="mt-4 text-xs text-[#cbd5e1]">Applied: <span className="font-mono font-bold text-white">{data.provider_lifecycle.apply_status_counts.applied || 0}</span> · Terminal ignored: <span className="font-mono font-bold text-white">{data.provider_lifecycle.apply_status_counts.ignored_terminal || 0}</span></div>
            </div>
          </section>

          <section className="grid grid-cols-1 gap-6 xl:grid-cols-5">
            <div className="rounded-2xl border border-[#28283c] bg-[#141422] p-6 xl:col-span-3">
              <div className="flex items-center justify-between border-b border-[#242436] pb-4">
                <div className="flex items-center gap-2">
                  <Siren size={18} className="text-[#ffe04a]" />
                  <div>
                    <h2 className="font-headline text-base font-bold text-white">Operational Attention Queue</h2>
                    <p className="mt-1 text-xs text-[#94a3b8]">Pull-based monitoring signals from persisted job, outbox, and call state.</p>
                  </div>
                </div>
                <span className="text-xs font-mono text-[#94a3b8]">Auto-refresh: 30s</span>
              </div>
              <div className="mt-4 space-y-2">
                {data.monitoring.alerts.length ? data.monitoring.alerts.map((alert) => (
                  <div key={`${alert.level}-${alert.code}`} className={`flex gap-3 rounded-xl border p-3 text-sm ${alert.level === "critical" ? "border-[#ff2d78]/30 bg-[#ff2d78]/10" : alert.level === "warning" ? "border-[#ffe04a]/30 bg-[#ffe04a]/10" : "border-blue-400/25 bg-blue-400/10"}`}>
                    <AlertTriangle size={16} className={alert.level === "critical" ? "mt-0.5 shrink-0 text-[#ff2d78]" : alert.level === "warning" ? "mt-0.5 shrink-0 text-[#ffe04a]" : "mt-0.5 shrink-0 text-blue-400"} />
                    <div><p className="font-mono text-[11px] font-bold uppercase text-white">{titleCase(alert.code)}</p><p className="mt-1 text-xs text-[#cbd5e1]">{alert.message}</p></div>
                  </div>
                )) : <div className="rounded-xl border border-[#00ffcc]/25 bg-[#00ffcc]/5 p-4 text-sm text-[#bfffee]"><CheckCircle2 size={16} className="mr-2 inline" />No current tenant-scoped operational attention signals.</div>}
              </div>
            </div>

            <div className="rounded-2xl border border-[#28283c] bg-[#141422] p-6 xl:col-span-2">
              <div className="flex items-center gap-2 border-b border-[#242436] pb-4">
                <FileBarChart size={18} className="text-[#00ffcc]" />
                <div><h2 className="font-headline text-base font-bold text-white">Enterprise Report</h2><p className="mt-1 text-xs text-[#94a3b8]">CSV is safe for spreadsheet export and excludes transcripts, raw job payloads, and policy evidence.</p></div>
              </div>
              <div className="mt-5 space-y-3 text-sm text-[#cbd5e1]">
                <p><span className="font-mono text-[#94a3b8]">TENANT</span><br />{data.tenant.name} · {data.tenant.plan.toUpperCase()}</p>
                <p><span className="font-mono text-[#94a3b8]">INCLUDED</span><br />KPIs, daily call trend, campaign policy totals, and monitoring alerts.</p>
                <p><span className="font-mono text-[#94a3b8]">EXCLUDED</span><br />Call transcript content, phone numbers, raw job payloads, and policy evidence JSON.</p>
                <button type="button" onClick={() => void exportReport()} disabled={exporting} className="mt-2 inline-flex w-full items-center justify-center gap-2 rounded-xl border border-[#00ffcc]/35 bg-[#00ffcc]/10 px-4 py-3 text-sm font-bold text-[#00ffcc] hover:bg-[#00ffcc]/20 disabled:opacity-50"><Download size={16} />{exporting ? "Preparing export…" : "Download Enterprise CSV"}</button>
              </div>
            </div>
          </section>
        </>
      ) : null}
    </div>
  );
}
