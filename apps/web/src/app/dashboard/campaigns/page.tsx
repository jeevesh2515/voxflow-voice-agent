"use client";

import { useState, useMemo } from "react";
import useSWR, { mutate } from "swr";
import {
  Megaphone,
  PhoneCall,
  Play,
  Plus,
  Search,
  CheckCircle2,
  AlertTriangle,
  Clock,
  Users,
  RefreshCw,
  X,
  Layers,
  ArrowRight,
  ShieldCheck,
  Radio,
  Activity,
  Database,
} from "lucide-react";
import { api } from "@/lib/api";
import { useTenant } from "@/lib/tenant-context";
import { fmtRelative } from "@/lib/format";
import type { OutboundCampaign, CampaignQueueItem, JobHealth } from "@/lib/types";

export default function CampaignsPage() {
  const { activeTenantId, activeTenant } = useTenant();
  const { data: campaigns, error, isLoading, mutate: refreshCampaigns } = useSWR(
    ["campaigns", activeTenantId],
    () => api.campaigns(activeTenantId),
  );
  const { data: suppliers } = useSWR(["suppliers", activeTenantId], () =>
    api.suppliers(undefined, activeTenantId),
  );
  const { data: jobHealth, mutate: refreshJobHealth } = useSWR(
    ["job-health", activeTenantId],
    () => api.jobHealth(activeTenantId),
    { refreshInterval: 15000 },
  );

  const [searchQuery, setSearchQuery] = useState("");
  const [filterType, setFilterType] = useState("all");
  const [selectedCampaignId, setSelectedCampaignId] = useState<string | null>(null);
  const [isCreateOpen, setIsCreateOpen] = useState(false);

  // Form state
  const [campaignName, setCampaignName] = useState("North Hub Urgent PO Verification");
  const [campaignType, setCampaignType] = useState("po_confirmation");
  const [targetPhones, setTargetPhones] = useState("+919876543210\n+919811122233");
  const [autoStart, setAutoStart] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [runningCampaignId, setRunningCampaignId] = useState<string | null>(null);
  const [formError, setFormError] = useState("");

  // Selected Campaign Queue details
  const { data: queueItems, mutate: refreshQueue } = useSWR(
    selectedCampaignId ? ["campaign-queue", activeTenantId, selectedCampaignId] : null,
    () => (selectedCampaignId ? api.getCampaignQueue(selectedCampaignId, activeTenantId) : null),
  );

  const filteredCampaigns = useMemo(() => {
    if (!campaigns) return [];
    return (campaigns as OutboundCampaign[]).filter((c) => {
      const q = searchQuery.toLowerCase().trim();
      const matchSearch =
        !q ||
        c.name.toLowerCase().includes(q) ||
        c.id.toLowerCase().includes(q) ||
        c.campaign_type.toLowerCase().includes(q);
      const matchType = filterType === "all" || c.campaign_type === filterType;
      return matchSearch && matchType;
    });
  }, [campaigns, searchQuery, filterType]);

  const stats = useMemo(() => {
    const list = (campaigns as OutboundCampaign[]) || [];
    const totalTargets = list.reduce((sum, c) => sum + (c.total_targets || 0), 0);
    const successful = list.reduce((sum, c) => sum + (c.successful_calls || 0), 0);
    const activeCount = list.filter((c) => c.status === "running" || c.status === "active").length;
    const successRate = totalTargets > 0 ? Math.round((successful / totalTargets) * 100) : 100;

    return {
      total: list.length,
      activeCount,
      totalTargets,
      successful,
      successRate,
    };
  }, [campaigns]);

  const handleCreateCampaign = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!campaignName.trim()) {
      setFormError("Campaign Name is required");
      return;
    }
    const lines = targetPhones
      .split("\n")
      .map((l) => l.trim())
      .filter(Boolean);

    if (lines.length === 0) {
      setFormError("Please enter at least one target phone number");
      return;
    }

    setFormError("");
    setIsSubmitting(true);

    try {
      const targets = lines.map((phone, i) => ({
        phone,
        name: `Supplier Contact ${i + 1}`,
        context: {
          po_id: `PO-${8000 + i}`,
          carrier: "BlueDart",
          revised_eta: "Tomorrow 11:00 AM",
        },
      }));

      const res = await api.createCampaign(
        {
          name: campaignName.trim(),
          campaign_type: campaignType,
          targets,
          auto_start: autoStart,
        },
        activeTenantId,
      );

      mutate(["campaigns", activeTenantId]);
      setIsCreateOpen(false);
      setSelectedCampaignId(res.id);
    } catch (err: any) {
      setFormError(err.message || "Failed to launch outbound campaign");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleRunCampaign = async (id: string) => {
    setRunningCampaignId(id);
    try {
      await api.runCampaign(id, 5, activeTenantId);
      mutate(["campaigns", activeTenantId]);
      if (selectedCampaignId === id) {
        mutate(["campaign-queue", activeTenantId, id]);
      }
    } catch (err) {
      console.error("Failed to run campaign batch:", err);
    } finally {
      setRunningCampaignId(null);
    }
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-16">
      {/* ==================== PAGE HEADER ==================== */}
      <header className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 bg-[#12121e] p-6 rounded-2xl border border-[#242436] shadow-sm">
        <div className="space-y-1">
          <div className="flex items-center gap-2 text-xs font-mono text-[#94a3b8]">
            <span>Day 24 • Autonomous Telephony</span>
            <span>/</span>
            <span className="text-[#00ffcc] font-bold">{activeTenant.name}</span>
          </div>
          <h1 className="text-xl sm:text-2xl font-headline font-bold text-white tracking-tight">
            Outbound Voice Campaigns & SIP Dialer
          </h1>
          <p className="text-xs sm:text-sm text-[#94a3b8]">
            Proactive automated voice dispatch for delayed shipments, PO confirmations, and dock appointments.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => refreshCampaigns()}
            className="bg-[#181826] hover:bg-[#202034] border border-[#2c2c40] px-4 py-2 rounded-xl text-xs font-medium flex items-center gap-2 text-[#cbd5e1] hover:text-white transition-colors"
          >
            <RefreshCw size={14} className="text-[#00ffcc]" />
            <span>Refresh</span>
          </button>
          <button
            onClick={() => setIsCreateOpen(true)}
            className="bg-[#ff2d78] hover:bg-[#e02669] text-white px-4 py-2 rounded-xl text-xs font-bold flex items-center gap-2 shadow-sm transition-colors"
          >
            <Plus size={15} />
            <span>Launch Campaign</span>
          </button>
        </div>
      </header>

      {/* ==================== STAT CARDS ==================== */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-[#141422] p-5 rounded-2xl border border-[#28283c] shadow-sm">
          <div className="flex items-center justify-between text-[#94a3b8] text-xs font-mono uppercase tracking-wider mb-1">
            <span>Total Campaigns</span>
            <Megaphone size={16} className="text-[#ff2d78]" />
          </div>
          <div className="text-2xl font-headline font-bold text-white">{stats.total}</div>
          <div className="text-xs text-[#94a3b8] mt-1">Configured for {activeTenant.name}</div>
        </div>

        <div className="bg-[#141422] p-5 rounded-2xl border border-[#28283c] shadow-sm">
          <div className="flex items-center justify-between text-[#94a3b8] text-xs font-mono uppercase tracking-wider mb-1">
            <span>Active Trunks</span>
            <Radio size={16} className="text-[#00ffcc]" />
          </div>
          <div className="text-2xl font-headline font-bold text-[#00ffcc]">
            {stats.activeCount > 0 ? `${stats.activeCount} Running` : "Amazon Connect"}
          </div>
          <div className="text-xs text-[#94a3b8] mt-1">Enterprise AWS voice routing</div>
        </div>

        <div className="bg-[#141422] p-5 rounded-2xl border border-[#28283c] shadow-sm">
          <div className="flex items-center justify-between text-[#94a3b8] text-xs font-mono uppercase tracking-wider mb-1">
            <span>Dispatched Calls</span>
            <PhoneCall size={16} className="text-blue-400" />
          </div>
          <div className="text-2xl font-headline font-bold text-blue-400">{stats.successful}</div>
          <div className="text-xs text-[#94a3b8] mt-1">of {stats.totalTargets} total target queued</div>
        </div>

        <div className="bg-[#141422] p-5 rounded-2xl border border-[#28283c] shadow-sm">
          <div className="flex items-center justify-between text-[#94a3b8] text-xs font-mono uppercase tracking-wider mb-1">
            <span>Delivery SLA</span>
            <ShieldCheck size={16} className="text-emerald-400" />
          </div>
          <div className="text-2xl font-headline font-bold text-emerald-400">{stats.successRate}%</div>
          <div className="text-xs text-[#94a3b8] mt-1">9am-8pm window enforced</div>
        </div>
      </div>

      {/* ==================== SEARCH & FILTERS ==================== */}
      <div className="flex flex-col sm:flex-row gap-3 items-stretch sm:items-center justify-between bg-[#141422] p-3 rounded-2xl border border-[#28283c]">
        <div className="relative flex-1">
          <Search size={15} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-[#64748b]" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search campaigns by name, type, or ID..."
            className="w-full bg-[#10101a] border border-[#28283c] rounded-xl pl-9 pr-4 py-2 text-xs text-white placeholder:text-[#64748b] focus:outline-none focus:border-[#ff2d78]"
          />
        </div>
        <div className="flex items-center bg-[#10101a] p-1 rounded-xl border border-[#28283c] overflow-x-auto">
          {["all", "delayed_shipment", "po_confirmation", "dock_reminder", "generic"].map((t) => (
            <button
              key={t}
              onClick={() => setFilterType(t)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium uppercase tracking-wider transition-colors shrink-0 ${
                filterType === t ? "bg-[#ff2d78] text-white" : "text-[#94a3b8] hover:text-white"
              }`}
            >
              {t.replace("_", " ")}
            </button>
          ))}
        </div>
      </div>

      {/* ==================== CAMPAIGNS GRID & QUEUE INSPECTOR ==================== */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left 2 Cols: Campaign List */}
        <div className="lg:col-span-2 space-y-4">
          {isLoading && (
            <div className="py-16 text-center text-[#94a3b8] text-xs font-mono">
              Loading outbound campaigns...
            </div>
          )}

          {error && (
            <div className="p-6 text-center text-red-400 bg-red-500/10 text-xs rounded-2xl border border-red-500/20">
              Failed to load campaigns. Please verify backend API connectivity.
            </div>
          )}

          {!isLoading &&
            !error &&
            filteredCampaigns.map((c) => {
              const isSelected = selectedCampaignId === c.id;
              const isRunning = runningCampaignId === c.id;

              return (
                <div
                  key={c.id}
                  onClick={() => setSelectedCampaignId(c.id)}
                  className={`bg-[#141422] p-5 rounded-2xl border transition-all cursor-pointer space-y-4 shadow-sm ${
                    isSelected ? "border-[#ff2d78] bg-[#181828]" : "border-[#28283c] hover:border-[#ff2d78]/40"
                  }`}
                >
                  <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-xl bg-[#ff2d78]/15 border border-[#ff2d78]/30 flex items-center justify-center text-[#ff2d78]">
                        <Megaphone size={18} />
                      </div>
                      <div>
                        <div className="flex items-center gap-2">
                          <h3 className="font-headline font-bold text-sm text-white">{c.name}</h3>
                          <span className="text-[10px] font-mono font-bold uppercase px-2 py-0.5 rounded bg-[#10101a] text-[#00ffcc] border border-[#00ffcc]/30">
                            {c.campaign_type.replace("_", " ")}
                          </span>
                        </div>
                        <div className="text-xs text-[#94a3b8] font-mono mt-0.5">
                          ID: <strong className="text-white">{c.id}</strong> • Created {fmtRelative(c.created_at)}
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center gap-2">
                      <span
                        className={`text-[10px] font-mono font-bold uppercase px-2.5 py-1 rounded-md border ${
                          c.status === "completed"
                            ? "bg-emerald-500/15 text-emerald-400 border-emerald-500/30"
                            : c.status === "running"
                            ? "bg-[#00ffcc]/15 text-[#00ffcc] border-[#00ffcc]/30 animate-pulse"
                            : "bg-amber-500/15 text-amber-400 border-amber-500/30"
                        }`}
                      >
                        {c.status}
                      </span>

                      {c.status !== "completed" && (
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            handleRunCampaign(c.id);
                          }}
                          disabled={isRunning}
                          className="px-3 py-1 bg-[#00ffcc] hover:bg-[#00e6b8] text-black rounded-lg text-xs font-bold flex items-center gap-1.5 transition-colors disabled:opacity-50"
                        >
                          <Play size={12} fill="currentColor" />
                          <span>{isRunning ? "Staging..." : "Stage Queue"}</span>
                        </button>
                      )}
                    </div>
                  </div>

                  {/* Progress Bar */}
                  <div className="space-y-1.5">
                    <div className="flex justify-between text-xs font-mono text-[#94a3b8]">
                      <span>Progress</span>
                      <span>
                        {c.successful_calls} / {c.total_targets} Calls ({c.total_targets > 0 ? Math.round((c.successful_calls / c.total_targets) * 100) : 0}%)
                      </span>
                    </div>
                    <div className="w-full h-2 bg-[#10101a] rounded-full overflow-hidden border border-[#28283c]">
                      <div
                        className="h-full bg-gradient-to-r from-[#ff2d78] to-[#00ffcc] transition-all duration-300"
                        style={{
                          width: `${c.total_targets > 0 ? Math.round((c.successful_calls / c.total_targets) * 100) : 0}%`,
                        }}
                      />
                    </div>
                  </div>
                </div>
              );
            })}

          {!isLoading && !error && filteredCampaigns.length === 0 && (
            <div className="bg-[#141422] rounded-2xl border border-dashed border-[#28283c] p-16 text-center space-y-3">
              <Megaphone className="mx-auto text-[#64748b]" size={36} />
              <div className="text-sm text-white font-headline font-semibold">No campaigns launched</div>
              <p className="text-xs text-[#94a3b8] max-w-sm mx-auto">
                {searchQuery
                  ? `No campaigns matching "${searchQuery}".`
                  : `Launch an autonomous outbound campaign to ring suppliers or distributors with AI-generated voice updates.`}
              </p>
            </div>
          )}
        </div>

        {/* Right 1 Col: Durable Job Health + Queue Inspector */}
        <div className="space-y-4">
          <div className="bg-[#141422] p-5 rounded-2xl border border-[#28283c] shadow-sm space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-[#242436]">
              <div className="flex items-center gap-2">
                <Activity size={16} className="text-[#00ffcc]" />
                <h3 className="font-headline font-bold text-sm text-white">Durable Dispatch Health</h3>
              </div>
              <button
                onClick={() => refreshJobHealth()}
                className="text-xs text-[#00ffcc] hover:underline font-mono"
              >
                Refresh
              </button>
            </div>
            {jobHealth ? (() => {
              const health = jobHealth as JobHealth;
              return (
                <>
                  <div className="flex items-center gap-2 text-[10px] font-mono uppercase">
                    <span className={`px-2 py-1 rounded border ${health.activation_mode === "canary" ? "text-emerald-400 border-emerald-500/30 bg-emerald-500/10" : health.activation_mode === "dry_run" ? "text-blue-400 border-blue-500/30 bg-blue-500/10" : "text-amber-400 border-amber-500/30 bg-amber-500/10"}`}>
                      {health.activation_mode === "canary" ? "Canary enabled" : health.activation_mode === "dry_run" ? "Canary dry run" : "Safe staging"}
                    </span>
                    <span className="text-[#94a3b8]">{health.rollout?.canary_allowed ? "Tenant approved" : "No inline dialling"}</span>
                  </div>
                  <div className="grid grid-cols-2 gap-2 text-xs">
                    <div className="rounded-lg bg-[#10101a] p-2.5 border border-[#28283c]"><span className="text-[#94a3b8] block text-[10px] font-mono uppercase">Ready</span><strong className="text-white text-base">{health.status_counts.ready || 0}</strong></div>
                    <div className="rounded-lg bg-[#10101a] p-2.5 border border-[#28283c]"><span className="text-[#94a3b8] block text-[10px] font-mono uppercase">Running</span><strong className="text-[#00ffcc] text-base">{health.status_counts.running || 0}</strong></div>
                    <div className="rounded-lg bg-[#10101a] p-2.5 border border-[#28283c]"><span className="text-[#94a3b8] block text-[10px] font-mono uppercase">Retrying</span><strong className="text-amber-400 text-base">{health.status_counts.retry_scheduled || 0}</strong></div>
                    <div className="rounded-lg bg-[#10101a] p-2.5 border border-[#28283c]"><span className="text-[#94a3b8] block text-[10px] font-mono uppercase">Review</span><strong className="text-red-400 text-base">{health.status_counts.dead_lettered || 0}</strong></div>
                  </div>
                  <div className="flex items-center gap-2 text-[11px] text-[#94a3b8]">
                    <Database size={13} className="text-blue-400" />
                    <span>{health.outbox.unpublished} unpublished event{health.outbox.unpublished === 1 ? "" : "s"}</span>
                    {(health.status_counts.cancelled || 0) > 0 && <span className="text-violet-300">• {health.status_counts.cancelled} policy stop{health.status_counts.cancelled === 1 ? "" : "s"}</span>}
                    {health.expired_leases > 0 && <span className="text-red-400">• {health.expired_leases} expired lease{health.expired_leases === 1 ? "" : "s"}</span>}
                  </div>
                </>
              );
            })() : <div className="text-xs text-[#94a3b8] py-2">Loading durable queue health…</div>}
          </div>
          <div className="bg-[#141422] p-5 rounded-2xl border border-[#28283c] shadow-sm space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-[#242436]">
              <div className="flex items-center gap-2">
                <Layers size={16} className="text-[#00ffcc]" />
                <h3 className="font-headline font-bold text-sm text-white">Target Call Queue</h3>
              </div>
              {selectedCampaignId && (
                <button
                  onClick={() => refreshQueue()}
                  className="text-xs text-[#00ffcc] hover:underline font-mono"
                >
                  Refresh
                </button>
              )}
            </div>

            {!selectedCampaignId && (
              <div className="py-12 text-center text-xs text-[#94a3b8]">
                Select a campaign from the list to inspect individual call targets and live transcripts.
              </div>
            )}

            {selectedCampaignId && queueItems && (
              <div className="space-y-3 max-h-[500px] overflow-y-auto pr-1">
                {queueItems.map((item: CampaignQueueItem) => (
                  <div
                    key={item.id}
                    className="p-3 bg-[#10101a] rounded-xl border border-[#28283c] space-y-1.5"
                  >
                    <div className="flex justify-between items-center text-xs">
                      <span className="font-bold text-white font-mono">{item.recipient_phone}</span>
                      <span
                        className={`text-[9px] font-mono uppercase px-2 py-0.5 rounded border ${
                          item.status === "completed"
                            ? "bg-emerald-500/15 text-emerald-400 border-emerald-500/30"
                            : item.status === "dialing"
                            ? "bg-[#00ffcc]/15 text-[#00ffcc] border-[#00ffcc]/30 animate-pulse"
                            : item.status === "failed"
                            ? "bg-red-500/15 text-red-400 border-red-500/30"
                            : item.status === "cancelled"
                            ? "bg-violet-500/15 text-violet-300 border-violet-500/30"
                            : "bg-amber-500/15 text-amber-400 border-amber-500/30"
                        }`}
                      >
                        {item.status}
                      </span>
                    </div>
                    {item.recipient_name && (
                      <div className="text-[11px] text-[#94a3b8]">{item.recipient_name}</div>
                    )}
                    {item.transcript_summary && (
                      <div className="text-[10px] text-[#cbd5e1] bg-[#181828] p-2 rounded-lg font-mono border border-[#242436]">
                        {item.transcript_summary}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* ==================== CREATE CAMPAIGN MODAL ==================== */}
      {isCreateOpen && (
        <div className="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-[#141422] border border-[#28283c] rounded-2xl p-6 sm:p-8 max-w-md w-full shadow-2xl space-y-5 relative">
            <button
              onClick={() => setIsCreateOpen(false)}
              className="absolute top-5 right-5 text-[#94a3b8] hover:text-white transition-colors"
            >
              <X size={18} />
            </button>

            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-[#ff2d78]/15 border border-[#ff2d78]/30 flex items-center justify-center text-[#ff2d78]">
                <Megaphone size={20} />
              </div>
              <div>
                <h3 className="font-headline font-bold text-base text-white">Launch Voice Campaign</h3>
                <p className="text-xs text-[#94a3b8]">Trigger automated outbound calls for {activeTenant.name}</p>
              </div>
            </div>

            <form onSubmit={handleCreateCampaign} className="space-y-4">
              <div>
                <label className="text-[11px] font-mono uppercase tracking-wider text-[#94a3b8] block mb-1.5 font-bold">
                  Campaign Title
                </label>
                <input
                  type="text"
                  required
                  value={campaignName}
                  onChange={(e) => setCampaignName(e.target.value)}
                  placeholder="e.g. Delayed Shipment Flash Notification"
                  className="w-full px-3.5 py-2 rounded-xl bg-[#10101a] border border-[#28283c] text-xs text-white focus:border-[#ff2d78] focus:outline-none"
                />
              </div>

              <div>
                <label className="text-[11px] font-mono uppercase tracking-wider text-[#94a3b8] block mb-1.5 font-bold">
                  Campaign Goal / Scenario
                </label>
                <select
                  value={campaignType}
                  onChange={(e) => setCampaignType(e.target.value)}
                  className="w-full px-3.5 py-2 rounded-xl bg-[#10101a] border border-[#28283c] text-xs text-white focus:border-[#ff2d78] focus:outline-none"
                >
                  <option value="delayed_shipment">Delayed Shipment ETA Update (Hindi/English)</option>
                  <option value="po_confirmation">Unconfirmed PO Verification & Slot Booking</option>
                  <option value="dock_reminder">Warehouse Dock Visit 24H Reminder</option>
                  <option value="generic">General Operations Voice Alert</option>
                </select>
              </div>

              <div>
                <label className="text-[11px] font-mono uppercase tracking-wider text-[#94a3b8] block mb-1.5 font-bold">
                  Recipient Phone Numbers (One E.164 number per line)
                </label>
                <textarea
                  rows={4}
                  required
                  value={targetPhones}
                  onChange={(e) => setTargetPhones(e.target.value)}
                  placeholder="+919876543210&#10;+919811122233"
                  className="w-full p-3 rounded-xl bg-[#10101a] border border-[#28283c] text-xs text-white focus:border-[#ff2d78] focus:outline-none font-mono leading-relaxed"
                />
              </div>

              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="autostart"
                  checked={autoStart}
                  onChange={(e) => setAutoStart(e.target.checked)}
                  className="rounded border-[#28283c] bg-[#10101a] text-[#ff2d78] focus:ring-0"
                />
                <label htmlFor="autostart" className="text-xs text-[#cbd5e1] cursor-pointer">
                  Mark active on creation; calls remain safely staged until worker rollout approval
                </label>
              </div>

              {formError && (
                <div className="text-xs text-red-400 bg-red-500/10 border border-red-500/30 rounded-xl p-2.5">
                  {formError}
                </div>
              )}

              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setIsCreateOpen(false)}
                  className="px-4 py-2 rounded-xl text-xs font-medium text-[#94a3b8] hover:text-white bg-[#181826] border border-[#28283c]"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="px-5 py-2 rounded-xl bg-[#ff2d78] hover:bg-[#e02669] text-white text-xs font-bold transition-colors disabled:opacity-50"
                >
                  {isSubmitting ? "Launching..." : "Launch Campaign"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
