"use client";

import { useState } from "react";
import useSWR from "swr";
import {
  Activity,
  AlertOctagon,
  AlertTriangle,
  Bot,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  Clock,
  Filter,
  Flame,
  Gauge,
  Play,
  RefreshCw,
  RotateCcw,
  ShieldAlert,
  ShieldCheck,
  Sparkles,
  Volume2,
  Wrench,
  XCircle,
} from "lucide-react";
import { api } from "@/lib/api";
import type { EvalCategoryScore, EvalReport, EvalScenarioResult, EvalThreshold } from "@/lib/types";

interface Props {
  tenantId?: string;
  tenantName?: string;
}

export function VoiceEvalScorecard({ tenantId, tenantName }: Props) {
  const [isRunning, setIsRunning] = useState(false);
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);
  const [showFailedOnly, setShowFailedOnly] = useState(false);
  const [showHardGateOnly, setShowHardGateOnly] = useState(false);
  const [expandedScenarios, setExpandedScenarios] = useState<Record<string, boolean>>({});
  const [runError, setRunError] = useState<string | null>(null);

  const { data: report, error, isLoading, mutate } = useSWR<EvalReport>(
    tenantId ? ["voice-eval-scorecard", tenantId] : ["voice-eval-scorecard", "all"],
    () => (tenantId ? api.evals.getTenantScorecard(tenantId) : api.evals.getScorecard()),
    { revalidateOnFocus: false, revalidateOnReconnect: false }
  );

  const handleRunEval = async () => {
    try {
      setIsRunning(true);
      setRunError(null);
      const newReport = await api.evals.runEval({
        tenant_id: tenantId,
        category_filter: selectedCategory || undefined,
      });
      await mutate(newReport, false);
    } catch (err: any) {
      setRunError(err?.message || "Failed to execute evaluation harness");
    } finally {
      setIsRunning(false);
    }
  };

  const toggleScenario = (id: string) => {
    setExpandedScenarios((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  const toggleAllScenarios = (expand: boolean) => {
    if (!report?.scenarios) return;
    const next: Record<string, boolean> = {};
    for (const sc of report.scenarios) {
      next[sc.scenario_id] = expand;
    }
    setExpandedScenarios(next);
  };

  if (isLoading && !report) {
    return (
      <div className="rounded-2xl border border-[#28283c] bg-[#141422] p-8 text-center">
        <RefreshCw className="mx-auto h-8 w-8 animate-spin text-[#00ffcc]" />
        <p className="mt-3 text-sm font-medium text-white">Running voice evaluation baseline harness…</p>
        <p className="mt-1 text-xs text-[#94a3b8]">Simulating 23 multi-turn scenarios across safety, accuracy, and brevity</p>
      </div>
    );
  }

  if (error && !report) {
    return (
      <div className="rounded-2xl border border-[#ff2d78]/30 bg-[#ff2d78]/10 p-6 text-[#fecdd3]">
        <div className="flex items-center gap-2">
          <AlertOctagon size={20} className="text-[#ff2d78]" />
          <h3 className="font-bold">Evaluation Harness Unavailable</h3>
        </div>
        <p className="mt-2 text-sm text-[#fda4af]">
          Could not retrieve voice scorecard: {error?.message || "Internal server error"}
        </p>
        <button
          onClick={() => mutate()}
          className="mt-4 inline-flex items-center gap-1.5 rounded-lg border border-[#ff2d78]/40 bg-[#ff2d78]/20 px-3 py-1.5 text-xs font-semibold text-white transition hover:bg-[#ff2d78]/30"
        >
          <RotateCcw size={14} /> Retry Baseline
        </button>
      </div>
    );
  }

  const filteredScenarios = (report?.scenarios || []).filter((sc) => {
    if (selectedCategory && sc.category !== selectedCategory) return false;
    if (showFailedOnly && sc.passed) return false;
    if (showHardGateOnly && !sc.hard_gate) return false;
    return true;
  });

  return (
    <div className="space-y-6">
      {/* Header Banner */}
      <section className="relative overflow-hidden rounded-2xl border border-[#28283c] bg-[#141422] p-6 shadow-xl">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-start gap-3.5">
            <div className={`rounded-xl border p-2.5 ${
              report?.release_ready
                ? "border-[#00ffcc]/30 bg-[#00ffcc]/10 text-[#00ffcc]"
                : "border-[#ff2d78]/30 bg-[#ff2d78]/10 text-[#ff2d78]"
            }`}>
              {report?.release_ready ? <ShieldCheck size={24} /> : <ShieldAlert size={24} />}
            </div>
            <div>
              <div className="flex flex-wrap items-center gap-2">
                <span className="font-mono text-xs font-semibold uppercase tracking-wider text-[#94a3b8]">
                  Release Gate #5 — Voice Harness
                </span>
                <span className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-[11px] font-bold uppercase tracking-wider ${
                  report?.release_ready
                    ? "bg-[#00ffcc]/15 text-[#00ffcc] border border-[#00ffcc]/30"
                    : "bg-[#ff2d78]/15 text-[#ff9bbd] border border-[#ff2d78]/30"
                }`}>
                  {report?.release_ready ? "🚀 Ready for Release" : "🛑 Gate Blocked"}
                </span>
                {report?.hard_gate_passed ? (
                  <span className="rounded-md border border-[#00ffcc]/20 bg-[#00ffcc]/5 px-2 py-0.5 text-[10px] font-mono text-[#00ffcc]">
                    Zero Data Leaks (100% Safe)
                  </span>
                ) : (
                  <span className="rounded-md border border-[#ff2d78]/30 bg-[#ff2d78]/10 px-2 py-0.5 text-[10px] font-mono text-[#ff9bbd]">
                    Hard Gate Leak Detected
                  </span>
                )}
              </div>
              <h2 className="mt-1.5 text-xl font-bold text-white">
                Voice Agent Evaluation & Safety Scorecard
              </h2>
              <p className="mt-1 text-xs text-[#94a3b8]">
                Deterministic benchmark testing 23 scenarios for data leakage, accuracy, spoken brevity, and tool adherence.
                {tenantName ? ` Scoped to ${tenantName}.` : " Scoped across all multi-tenant profiles."}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={handleRunEval}
              disabled={isRunning}
              className={`inline-flex items-center gap-2 rounded-xl px-4 py-2.5 min-h-[44px] text-xs font-semibold shadow-lg transition-all ${
                isRunning
                  ? "cursor-not-allowed border border-[#302840] bg-[#1a1a2e] text-[#64748b]"
                  : "border border-[#00ffcc]/40 bg-[#00ffcc]/15 text-[#00ffcc] hover:bg-[#00ffcc]/25 active:scale-95"
              }`}
            >
              {isRunning ? (
                <>
                  <RefreshCw size={14} className="animate-spin" /> Running Evals…
                </>
              ) : (
                <>
                  <Play size={14} className="fill-current" /> Run Harness Now
                </>
              )}
            </button>
          </div>
        </div>

        {runError && (
          <div className="mt-4 rounded-xl border border-[#ff2d78]/30 bg-[#ff2d78]/10 p-3 text-xs text-[#fecdd3]">
            {runError}
          </div>
        )}

        <div className="mt-4 flex flex-wrap items-center gap-4 text-[11px] text-[#64748b] border-t border-[#202035] pt-3">
          <span>Run ID: <code className="text-[#a098b0]">{report?.run_id}</code></span>
          <span>Last Executed: <strong className="text-[#a098b0]">{report?.timestamp ? new Date(report.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }) : "Just now"}</strong></span>
          <span>Tested Scenarios: <strong className="text-white">{report?.total_scenarios}</strong></span>
        </div>
      </section>

      {/* KPI Cards */}
      <section className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
        <MetricCard
          label="Security Pass Rate"
          value={`${((report?.security_pass_rate || 0) * 100).toFixed(0)}%`}
          target="100%"
          passed={report?.security_pass_rate === 1.0}
          isHardGate
          icon={<ShieldCheck size={16} />}
        />
        <MetricCard
          label="Overall Pass Rate"
          value={`${((report?.overall_pass_rate || 0) * 100).toFixed(1)}%`}
          target=">= 90%"
          passed={(report?.overall_pass_rate || 0) >= 0.9}
          icon={<CheckCircle2 size={16} />}
        />
        <MetricCard
          label="Verification Accuracy"
          value={`${((report?.verification_accuracy || 0) * 100).toFixed(0)}%`}
          target=">= 90%"
          passed={(report?.verification_accuracy || 0) >= 0.9}
          icon={<Bot size={16} />}
        />
        <MetricCard
          label="Tool Accuracy"
          value={`${((report?.tool_accuracy || 0) * 100).toFixed(0)}%`}
          target=">= 85%"
          passed={(report?.tool_accuracy || 0) >= 0.85}
          icon={<Wrench size={16} />}
        />
        <MetricCard
          label="Avg Brevity"
          value={`${report?.avg_brevity_words || 0} w`}
          target="<= 35 w"
          passed={(report?.avg_brevity_words || 0) <= 35}
          icon={<Volume2 size={16} />}
        />
        <MetricCard
          label="P95 Latency"
          value={`${Math.round(report?.p95_latency_ms || 0)} ms`}
          target="<= 3500ms"
          passed={(report?.p95_latency_ms || 0) <= 3500}
          icon={<Clock size={16} />}
        />
      </section>

      {/* Thresholds & Category Scorecard */}
      <div className="grid gap-6 lg:grid-cols-2">
        {/* Release Thresholds Table */}
        <section className="rounded-2xl border border-[#28283c] bg-[#141422] p-5 shadow-lg">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Gauge size={18} className="text-[#00ffcc]" />
              <h3 className="font-headline text-sm font-bold text-white">Release Gate Threshold Ledger</h3>
            </div>
            <span className="text-[10px] font-mono text-[#94a3b8]">6 Gated Checks</span>
          </div>

          <div className="mt-4 overflow-hidden rounded-xl border border-[#28283c]/60">
            <table className="w-full text-left text-xs">
              <thead className="border-b border-[#28283c] bg-[#10101c] font-mono text-[10px] uppercase text-[#64748b]">
                <tr>
                  <th className="px-3 py-2.5">Gate / Metric</th>
                  <th className="px-3 py-2.5">Target</th>
                  <th className="px-3 py-2.5">Actual</th>
                  <th className="px-3 py-2.5 text-right">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#202035] bg-[#141422]">
                {report?.thresholds?.map((th) => (
                  <tr key={th.name} className="hover:bg-[#18182a]/50">
                    <td className="px-3 py-2.5">
                      <div className="font-medium text-white flex items-center gap-1.5">
                        {th.name}
                        {th.is_hard_gate && (
                          <span className="rounded bg-[#ffe04a]/10 px-1.5 py-0.2 text-[9px] font-mono font-bold text-[#ffe04a]">
                            HARD GATE
                          </span>
                        )}
                      </div>
                    </td>
                    <td className="px-3 py-2.5 font-mono text-[#94a3b8]">
                      {th.comparator} {th.target}
                    </td>
                    <td className="px-3 py-2.5 font-mono font-semibold text-white">
                      {th.actual}
                    </td>
                    <td className="px-3 py-2.5 text-right">
                      {th.passed ? (
                        <span className="inline-flex items-center gap-1 rounded-full bg-[#00ffcc]/10 px-2 py-0.5 text-[10px] font-semibold text-[#00ffcc]">
                          <CheckCircle2 size={11} /> Pass
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 rounded-full bg-[#ff2d78]/15 px-2 py-0.5 text-[10px] font-semibold text-[#ff9bbd]">
                          <XCircle size={11} /> Blocked
                        </span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        {/* Category Breakdown Progress */}
        <section className="rounded-2xl border border-[#28283c] bg-[#141422] p-5 shadow-lg">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Sparkles size={18} className="text-[#ffe04a]" />
              <h3 className="font-headline text-sm font-bold text-white">Category Breakdown</h3>
            </div>
            <span className="text-[10px] font-mono text-[#94a3b8]">7 Domain Areas</span>
          </div>

          <div className="mt-4 space-y-3">
            {report?.category_scores?.map((cs) => {
              const pct = Math.round(cs.pass_rate * 100);
              const isSelected = selectedCategory === cs.category;
              return (
                <div
                  key={cs.category}
                  onClick={() => setSelectedCategory(isSelected ? null : cs.category)}
                  className={`group cursor-pointer rounded-xl border p-3 transition-all ${
                    isSelected
                      ? "border-[#00ffcc]/60 bg-[#00ffcc]/10 shadow-md"
                      : "border-[#28283c]/60 bg-[#181826] hover:border-[#383850]"
                  }`}
                >
                  <div className="flex items-center justify-between text-xs">
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-xs font-semibold capitalize text-white group-hover:text-[#00ffcc]">
                        {cs.category.replace(/_/g, " ")}
                      </span>
                      {cs.hard_gate_failures > 0 && (
                        <span className="rounded bg-[#ff2d78]/20 px-1.5 py-0.2 text-[9px] font-bold text-[#ff9bbd]">
                          {cs.hard_gate_failures} LEAK
                        </span>
                      )}
                    </div>
                    <div className="font-mono text-[11px] text-[#94a3b8]">
                      <span className="font-semibold text-white">{cs.passed}</span>/{cs.total} ({pct}%)
                    </div>
                  </div>

                  <div className="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-[#10101c]">
                    <div
                      className={`h-full rounded-full transition-all ${
                        cs.hard_gate_failures > 0
                          ? "bg-[#ff2d78]"
                          : pct >= 90
                          ? "bg-[#00ffcc]"
                          : pct >= 70
                          ? "bg-[#ffe04a]"
                          : "bg-[#ff2d78]"
                      }`}
                      style={{ width: `${pct}%` }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </section>
      </div>

      {/* Scenario Explorer */}
      <section className="rounded-2xl border border-[#28283c] bg-[#141422] p-5 shadow-lg">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between border-b border-[#202035] pb-4">
          <div className="flex items-center gap-2">
            <Filter size={18} className="text-[#00ffcc]" />
            <h3 className="font-headline text-sm font-bold text-white">
              Scenario Drilldown Explorer ({filteredScenarios.length} tests)
            </h3>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            {selectedCategory && (
              <button
                onClick={() => setSelectedCategory(null)}
                className="rounded-lg border border-[#00ffcc]/30 bg-[#00ffcc]/15 px-2.5 py-1 text-[11px] font-medium text-[#00ffcc] hover:bg-[#00ffcc]/25"
              >
                Clear Category: {selectedCategory.replace(/_/g, " ")} ✕
              </button>
            )}

            <button
              onClick={() => setShowHardGateOnly(!showHardGateOnly)}
              className={`rounded-lg border px-2.5 py-1 text-[11px] font-medium transition ${
                showHardGateOnly
                  ? "border-[#ffe04a]/40 bg-[#ffe04a]/15 text-[#ffe04a]"
                  : "border-[#28283c] bg-[#181826] text-[#94a3b8] hover:text-white"
              }`}
            >
              Hard Gate Only
            </button>

            <button
              onClick={() => setShowFailedOnly(!showFailedOnly)}
              className={`rounded-lg border px-2.5 py-1 text-[11px] font-medium transition ${
                showFailedOnly
                  ? "border-[#ff2d78]/40 bg-[#ff2d78]/15 text-[#ff9bbd]"
                  : "border-[#28283c] bg-[#181826] text-[#94a3b8] hover:text-white"
              }`}
            >
              Failed Only
            </button>

            <button
              onClick={() => toggleAllScenarios(true)}
              className="rounded-lg border border-[#28283c] bg-[#181826] px-2.5 py-1 text-[11px] text-[#94a3b8] hover:text-white"
            >
              Expand All
            </button>

            <button
              onClick={() => toggleAllScenarios(false)}
              className="rounded-lg border border-[#28283c] bg-[#181826] px-2.5 py-1 text-[11px] text-[#94a3b8] hover:text-white"
            >
              Collapse
            </button>
          </div>
        </div>

        {/* Scenario List */}
        <div className="mt-4 space-y-3">
          {filteredScenarios.map((sc) => {
            const isExpanded = !!expandedScenarios[sc.scenario_id];
            return (
              <div
                key={sc.scenario_id}
                className={`overflow-hidden rounded-xl border transition-all ${
                  sc.hard_gate_violation
                    ? "border-[#ff2d78]/50 bg-[#ff2d78]/5"
                    : sc.passed
                    ? "border-[#28283c]/70 bg-[#161624]"
                    : "border-[#ff2d78]/30 bg-[#181826]"
                }`}
              >
                <div
                  onClick={() => toggleScenario(sc.scenario_id)}
                  className="flex cursor-pointer items-center justify-between p-3.5 hover:bg-[#1c1c2e]/50"
                >
                  <div className="flex items-center gap-3">
                    <button className="text-[#94a3b8]">
                      {isExpanded ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
                    </button>
                    <div>
                      <div className="flex flex-wrap items-center gap-2">
                        <span className={`inline-flex items-center gap-1 rounded-md px-2 py-0.5 text-[10px] font-mono font-bold uppercase ${
                          sc.passed
                            ? "bg-[#00ffcc]/10 text-[#00ffcc]"
                            : "bg-[#ff2d78]/15 text-[#ff9bbd]"
                        }`}>
                          {sc.passed ? "PASS" : "FAIL"}
                        </span>
                        {sc.hard_gate && (
                          <span className="rounded bg-[#ffe04a]/10 px-1.5 py-0.5 text-[9px] font-mono font-bold text-[#ffe04a]">
                            HARD GATE #5
                          </span>
                        )}
                        <span className="font-semibold text-white text-xs">{sc.name}</span>
                        <span className="font-mono text-[10px] text-[#64748b]">({sc.scenario_id})</span>
                      </div>
                      <p className="mt-0.5 text-[11px] text-[#94a3b8]">{sc.description}</p>
                    </div>
                  </div>

                  <div className="flex items-center gap-4 text-xs font-mono text-[#94a3b8]">
                    <span>{sc.avg_words} words</span>
                    <span>{Math.round(sc.total_latency_ms)}ms</span>
                  </div>
                </div>

                {isExpanded && (
                  <div className="border-t border-[#202035] bg-[#10101c] p-4 space-y-3 text-xs">
                    {sc.violations.length > 0 && (
                      <div className="rounded-lg border border-[#ff2d78]/40 bg-[#ff2d78]/10 p-3 text-[#fecdd3]">
                        <p className="font-semibold flex items-center gap-1.5 text-xs text-[#ff9bbd]">
                          <AlertTriangle size={14} /> Violations Found:
                        </p>
                        <ul className="mt-1 list-disc pl-5 space-y-0.5 text-[11px]">
                          {sc.violations.map((v, idx) => (
                            <li key={idx}>{v}</li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {sc.turns.map((turn, tIdx) => (
                      <div key={tIdx} className="space-y-2 rounded-lg border border-[#28283c]/50 bg-[#141422] p-3">
                        <div className="flex items-start gap-2">
                          <span className="rounded bg-[#00ffcc]/10 px-1.5 py-0.5 font-mono text-[10px] text-[#00ffcc]">
                            USER
                          </span>
                          <p className="text-white text-xs font-medium">&ldquo;{turn.user_text}&rdquo;</p>
                        </div>

                        <div className="flex items-start gap-2">
                          <span className="rounded bg-[#7928ca]/20 px-1.5 py-0.5 font-mono text-[10px] text-[#c084fc]">
                            AGENT
                          </span>
                          <p className="text-[#cbd5e1] text-xs">&ldquo;{turn.reply_text}&rdquo;</p>
                        </div>

                        <div className="flex flex-wrap items-center gap-4 text-[10px] font-mono text-[#64748b] pt-1">
                          <span>Length: <strong className="text-[#a098b0]">{turn.word_count} words</strong></span>
                          <span>Latency: <strong className="text-[#a098b0]">{Math.round(turn.latency_ms)}ms</strong></span>
                          {turn.tool_calls.length > 0 && (
                            <span className="text-[#ffe04a]">
                              Tools Called: <strong>{turn.tool_calls.join(", ")}</strong>
                            </span>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </section>
    </div>
  );
}

function MetricCard({
  label,
  value,
  target,
  passed,
  isHardGate,
  icon,
}: {
  label: string;
  value: string;
  target: string;
  passed: boolean;
  isHardGate?: boolean;
  icon: React.ReactNode;
}) {
  return (
    <div
      className={`rounded-2xl border p-4 shadow-md transition ${
        isHardGate && !passed
          ? "border-[#ff2d78] bg-[#ff2d78]/10"
          : passed
          ? "border-[#28283c] bg-[#141422]"
          : "border-[#ff2d78]/40 bg-[#141422]"
      }`}
    >
      <div className="flex items-center justify-between text-[#94a3b8]">
        <span className="text-[10px] font-mono uppercase tracking-wider">{label}</span>
        <div className={passed ? "text-[#00ffcc]" : "text-[#ff9bbd]"}>{icon}</div>
      </div>
      <p className="mt-2 text-xl font-bold font-mono text-white">{value}</p>
      <div className="mt-1.5 flex items-center justify-between text-[10px] font-mono">
        <span className="text-[#64748b]">Target: {target}</span>
        <span className={passed ? "text-[#00ffcc] font-semibold" : "text-[#ff9bbd] font-semibold"}>
          {passed ? "✓ Pass" : "✗ Fail"}
        </span>
      </div>
    </div>
  );
}
