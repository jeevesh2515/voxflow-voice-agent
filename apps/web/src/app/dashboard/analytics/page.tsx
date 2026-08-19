"use client";

import { useMemo } from "react";
import useSWR from "swr";
import {
  TrendingUp,
  Clock,
  CheckCircle2,
  AlertTriangle,
  Smile,
  Meh,
  Frown,
  Activity,
  BarChart3,
  ExternalLink,
  Flame,
  Zap,
  IndianRupee,
  Layers,
  Sparkles,
} from "lucide-react";
import { api } from "@/lib/api";
import { useTenant } from "@/lib/tenant-context";
import type { Call } from "@/lib/types";

export default function AnalyticsPage() {
  const { activeTenantId, activeTenant } = useTenant();
  const { data: calls, error, isLoading } = useSWR(
    ["calls-analytics", activeTenantId],
    () => api.calls(200, activeTenantId),
  );
  const { data: usage } = useSWR(["usage", activeTenantId], () =>
    api.getUsage(activeTenantId),
  );

  const metrics = useMemo(() => {
    const list = (calls as Call[]) || [];
    const total = list.length;
    if (total === 0) {
      return {
        total: 0,
        avgDuration: 0,
        fcrRate: 100,
        escalationRate: 0,
        happy: 0,
        neutral: 0,
        unhappy: 0,
        intents: { order: 0, stock_check: 0, shipment_status: 0, general: 0 },
      };
    }

    const totalDuration = list.reduce((sum, c) => sum + (c.duration_sec || 0), 0);
    const resolved = list.filter((c) => c.resolution_status === "resolved").length;
    const escalated = list.filter((c) => c.escalated).length;

    const happy = list.filter((c) => c.satisfaction === "happy").length;
    const neutral = list.filter((c) => c.satisfaction === "neutral" || !c.satisfaction).length;
    const unhappy = list.filter((c) => c.satisfaction === "unhappy").length;

    const intents = {
      order: list.filter((c) => c.intent === "order" || c.intent?.includes("order")).length,
      stock_check: list.filter((c) => c.intent === "stock_check" || c.intent?.includes("stock")).length,
      shipment_status: list.filter((c) => c.intent === "shipment_status" || c.intent?.includes("shipment")).length,
      general: list.filter((c) => !c.intent || c.intent === "general" || c.intent === "other").length,
    };

    return {
      total,
      avgDuration: Math.round(totalDuration / total),
      fcrRate: Math.round((resolved / total) * 100),
      escalationRate: Math.round((escalated / total) * 100),
      happy,
      neutral,
      unhappy,
      intents,
    };
  }, [calls]);

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-16">
      {/* ==================== PAGE HEADER ==================== */}
      <header className="flex flex-col sm:flex-row justify-between items-start sm:items-end gap-4">
        <div>
          <div className="flex items-center gap-2 text-xs font-label uppercase tracking-widest text-[#a098b0] mb-1">
            <span>Observability</span>
            <span>/</span>
            <span className="text-[#00ffcc] font-bold">{activeTenant.name}</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-headline font-extrabold text-[#e8e0f0] tracking-[0.05em] uppercase">
            Voice AI <span className="text-[#00ffcc] text-glow-secondary">Analytics</span>
          </h1>
          <p className="text-[#a098b0] font-body text-sm mt-1">
            First Call Resolution (FCR), caller sentiment telemetry, duration benchmarks, and LangSmith traces.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <a
            href="https://smith.langchain.com"
            target="_blank"
            rel="noreferrer"
            className="bg-[#1e1e30] border border-[#302840] hover:border-[#00ffcc] px-4 py-2 rounded-xl text-xs font-label font-bold uppercase tracking-widest flex items-center gap-2 text-[#e8e0f0] hover:text-[#00ffcc] transition-all shadow-sm"
          >
            <Sparkles size={14} className="text-[#00ffcc]" /> LangSmith Traces <ExternalLink size={12} />
          </a>
        </div>
      </header>

      {/* ==================== KPI CARDS ==================== */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="glass-panel p-5 rounded-2xl border border-[#00ffcc]/30">
          <div className="flex items-center justify-between text-[#a098b0] text-[10px] font-label uppercase tracking-wider mb-1">
            <span>First Call Resolution</span>
            <CheckCircle2 size={16} className="text-[#00ffcc]" />
          </div>
          <div className="text-3xl font-headline font-bold text-[#00ffcc]">{metrics.fcrRate}%</div>
          <div className="text-[10px] text-[#a098b0] mt-1">Direct agent closure</div>
        </div>

        <div className="glass-panel p-5 rounded-2xl border border-[#ffe04a]/30">
          <div className="flex items-center justify-between text-[#a098b0] text-[10px] font-label uppercase tracking-wider mb-1">
            <span>Avg Handle Time</span>
            <Clock size={16} className="text-[#ffe04a]" />
          </div>
          <div className="text-3xl font-headline font-bold text-[#ffe04a]">
            {Math.floor(metrics.avgDuration / 60)}m {metrics.avgDuration % 60}s
          </div>
          <div className="text-[10px] text-[#a098b0] mt-1">Per voice interaction</div>
        </div>

        <div className="glass-panel p-5 rounded-2xl border border-blue-500/30">
          <div className="flex items-center justify-between text-[#a098b0] text-[10px] font-label uppercase tracking-wider mb-1">
            <span>Total Calls Evaluated</span>
            <Activity size={16} className="text-blue-400" />
          </div>
          <div className="text-3xl font-headline font-bold text-[#e8e0f0]">{metrics.total}</div>
          <div className="text-[10px] text-[#a098b0] mt-1">Logged to Supabase</div>
        </div>

        <div className="glass-panel p-5 rounded-2xl border border-[#ff2d78]/30">
          <div className="flex items-center justify-between text-[#a098b0] text-[10px] font-label uppercase tracking-wider mb-1">
            <span>Escalation Rate</span>
            <AlertTriangle size={16} className="text-[#ff2d78]" />
          </div>
          <div className="text-3xl font-headline font-bold text-[#ff2d78]">{metrics.escalationRate}%</div>
          <div className="text-[10px] text-[#a098b0] mt-1">Sent to human desk</div>
        </div>
      </div>

      {/* ==================== CHARTS & BREAKDOWNS ==================== */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Sentiment breakdown */}
        <div className="glass-panel p-6 rounded-2xl border border-[#302840]/60 space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-[#302840]/40">
            <div className="flex items-center gap-2">
              <Smile size={18} className="text-[#00ffcc]" />
              <h3 className="font-headline font-bold text-sm text-[#e8e0f0]">Caller CSAT Sentiment</h3>
            </div>
            <span className="text-xs font-mono text-[#a098b0]">Voice Sentiment Analysis</span>
          </div>

          <div className="space-y-3 pt-2">
            <div>
              <div className="flex justify-between text-xs mb-1">
                <span className="text-[#00ffcc] flex items-center gap-1.5 font-medium">
                  <Smile size={14} /> Satisfied / Happy
                </span>
                <span className="text-[#e8e0f0] font-mono font-bold">
                  {metrics.happy} ({metrics.total ? Math.round((metrics.happy / metrics.total) * 100) : 0}%)
                </span>
              </div>
              <div className="h-2 rounded-full bg-[#181824] overflow-hidden">
                <div
                  className="h-full bg-[#00ffcc] rounded-full transition-all duration-500 shadow-[0_0_10px_#00ffcc]"
                  style={{ width: `${metrics.total ? (metrics.happy / metrics.total) * 100 : 0}%` }}
                />
              </div>
            </div>

            <div>
              <div className="flex justify-between text-xs mb-1">
                <span className="text-[#ffe04a] flex items-center gap-1.5 font-medium">
                  <Meh size={14} /> Neutral
                </span>
                <span className="text-[#e8e0f0] font-mono font-bold">
                  {metrics.neutral} ({metrics.total ? Math.round((metrics.neutral / metrics.total) * 100) : 0}%)
                </span>
              </div>
              <div className="h-2 rounded-full bg-[#181824] overflow-hidden">
                <div
                  className="h-full bg-[#ffe04a] rounded-full transition-all duration-500 shadow-[0_0_10px_#ffe04a]"
                  style={{ width: `${metrics.total ? (metrics.neutral / metrics.total) * 100 : 0}%` }}
                />
              </div>
            </div>

            <div>
              <div className="flex justify-between text-xs mb-1">
                <span className="text-[#ff2d78] flex items-center gap-1.5 font-medium">
                  <Frown size={14} /> Unhappy / Frustrated
                </span>
                <span className="text-[#e8e0f0] font-mono font-bold">
                  {metrics.unhappy} ({metrics.total ? Math.round((metrics.unhappy / metrics.total) * 100) : 0}%)
                </span>
              </div>
              <div className="h-2 rounded-full bg-[#181824] overflow-hidden">
                <div
                  className="h-full bg-[#ff2d78] rounded-full transition-all duration-500 shadow-[0_0_10px_#ff2d78]"
                  style={{ width: `${metrics.total ? (metrics.unhappy / metrics.total) * 100 : 0}%` }}
                />
              </div>
            </div>
          </div>
        </div>

        {/* Intent Breakdown */}
        <div className="glass-panel p-6 rounded-2xl border border-[#302840]/60 space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-[#302840]/40">
            <div className="flex items-center gap-2">
              <Layers size={18} className="text-[#ff2d78]" />
              <h3 className="font-headline font-bold text-sm text-[#e8e0f0]">Caller Intent Classification</h3>
            </div>
            <span className="text-xs font-mono text-[#a098b0]">Zero-Shot NLU</span>
          </div>

          <div className="grid grid-cols-2 gap-3 pt-2">
            <div className="bg-[#141422] p-4 rounded-xl border border-[#302840]/40 space-y-1">
              <span className="text-[10px] font-label uppercase tracking-widest text-[#a098b0]">
                Purchase Orders
              </span>
              <div className="text-xl font-headline font-bold text-[#ff2d78]">
                {metrics.intents.order}
              </div>
              <div className="text-[10px] text-[#a098b0]">2FA PIN Gated POs</div>
            </div>

            <div className="bg-[#141422] p-4 rounded-xl border border-[#302840]/40 space-y-1">
              <span className="text-[10px] font-label uppercase tracking-widest text-[#a098b0]">
                Stock Inquiries
              </span>
              <div className="text-xl font-headline font-bold text-[#ffe04a]">
                {metrics.intents.stock_check}
              </div>
              <div className="text-[10px] text-[#a098b0]">Real-time warehouse check</div>
            </div>

            <div className="bg-[#141422] p-4 rounded-xl border border-[#302840]/40 space-y-1">
              <span className="text-[10px] font-label uppercase tracking-widest text-[#a098b0]">
                Shipment Status
              </span>
              <div className="text-xl font-headline font-bold text-[#00ffcc]">
                {metrics.intents.shipment_status}
              </div>
              <div className="text-[10px] text-[#a098b0]">Carrier tracking ETA</div>
            </div>

            <div className="bg-[#141422] p-4 rounded-xl border border-[#302840]/40 space-y-1">
              <span className="text-[10px] font-label uppercase tracking-widest text-[#a098b0]">
                General & Support
              </span>
              <div className="text-xl font-headline font-bold text-blue-400">
                {metrics.intents.general}
              </div>
              <div className="text-[10px] text-[#a098b0]">Appointments & questions</div>
            </div>
          </div>
        </div>
      </div>

      {/* ==================== SAAS BILLING USAGE METER ==================== */}
      <div className="glass-panel p-6 sm:p-8 rounded-2xl border border-purple-500/30 space-y-4">
        <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-2 pb-3 border-b border-[#302840]/40">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-purple-500/15 border border-purple-500/30 flex items-center justify-center text-purple-400">
              <IndianRupee size={20} />
            </div>
            <div>
              <h3 className="font-headline font-bold text-base text-[#e8e0f0]">
                SaaS Usage & Voice Minute Metering
              </h3>
              <p className="text-xs text-[#a098b0]">
                Live billing breakdown for <strong className="text-[#e8e0f0]">{activeTenant.name}</strong>
              </p>
            </div>
          </div>
          <span className="text-xs font-label uppercase px-3 py-1 rounded-full bg-purple-500/10 text-purple-300 border border-purple-500/30 font-bold">
            Plan: {usage?.plan?.toUpperCase() || "PRO TIER"}
          </span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 pt-2">
          <div className="bg-[#141422] p-4 rounded-xl border border-[#302840]/60 space-y-1">
            <span className="text-[10px] font-label uppercase tracking-widest text-[#a098b0]">
              Total Telephony Minutes
            </span>
            <div className="text-2xl font-headline font-bold text-[#00ffcc]">
              {usage?.total_minutes || (metrics.total * 1.5).toFixed(1)} mins
            </div>
            <div className="text-[10px] text-[#a098b0]">Across all telephony sessions</div>
          </div>

          <div className="bg-[#141422] p-4 rounded-xl border border-[#302840]/60 space-y-1">
            <span className="text-[10px] font-label uppercase tracking-widest text-[#a098b0]">
              Rate Per Minute
            </span>
            <div className="text-2xl font-headline font-bold text-[#ffe04a]">
              ${usage?.rate_per_minute_usd || 0.15}/min
            </div>
            <div className="text-[10px] text-[#a098b0]">Includes STT, LLM & Cloud TTS</div>
          </div>

          <div className="bg-[#141422] p-4 rounded-xl border border-[#302840]/60 space-y-1">
            <span className="text-[10px] font-label uppercase tracking-widest text-[#a098b0]">
              Current Cycle Bill
            </span>
            <div className="text-2xl font-headline font-bold text-[#ff2d78]">
              ${usage?.estimated_bill_usd || ((metrics.total * 1.5) * 0.15).toFixed(2)} USD
            </div>
            <div className="text-[10px] text-[#a098b0]">Auto-billed at cycle end</div>
          </div>
        </div>
      </div>
    </div>
  );
}
