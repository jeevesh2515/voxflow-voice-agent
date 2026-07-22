"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import useSWR from "swr";
import {
  Phone,
  PhoneCall,
  Package,
  Users,
  Clock,
  Download,
  Plus,
  Mic,
  Activity,
  ChevronRight,
  TrendingUp,
  Brain,
  Sliders,
  Sparkles,
  Globe,
  Terminal,
} from "lucide-react";
import { api } from "@/lib/api";
import { useTenant } from "@/lib/tenant-context";

export default function DashboardOverview() {
  const { activeTenantId, activeTenant } = useTenant();
  const { data: summary } = useSWR(["summary", activeTenantId], () => api.summary(activeTenantId));
  const { data: calls } = useSWR(["calls", activeTenantId], () => api.calls(8, activeTenantId));
  const { data: suppliers } = useSWR(["suppliers", activeTenantId], () => api.suppliers(undefined, activeTenantId));

  const [activeKeypad, setActiveKeypad] = useState<string | null>(null);

  const handleKeyClick = (val: string) => {
    setActiveKeypad(val);
    setTimeout(() => setActiveKeypad(null), 200);
  };

  return (
    <div className="space-y-8 max-w-7xl mx-auto pb-12">
      {/* ==================== PAGE HEADER ==================== */}
      <header className="flex flex-col sm:flex-row justify-between items-start sm:items-end gap-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-headline font-extrabold text-[#e8e0f0] tracking-[0.05em] uppercase">
            Operations <span className="text-[#ff2d78] text-glow-primary">Overview</span>
          </h1>
          <p className="text-[#a098b0] font-body text-sm mt-1">
            Real-time telephonic logistics engine for <strong className="text-[#e8e0f0]">{activeTenant.name}</strong>.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button className="bg-[#28283e] border border-[#302840] px-4 py-2 rounded-lg text-xs font-label font-bold uppercase tracking-widest flex items-center gap-2 hover:border-[#00ffcc] text-[#e8e0f0] transition-all">
            <Download size={14} className="text-[#00ffcc]" /> Export
          </button>
          <button className="bg-[#ff2d78] text-[#1a0010] px-4 py-2 rounded-lg text-xs font-label font-bold uppercase tracking-widest flex items-center gap-2 neon-glow-primary hover:scale-105 active:scale-95 transition-all">
            <Plus size={14} /> New Campaign
          </button>
        </div>
      </header>

      {/* ==================== STAT CARDS ROW ==================== */}
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-6">
        {/* Card 1: Total Calls */}
        <div className="glass-panel p-5 rounded-2xl border border-[#ff2d78]/30 relative overflow-hidden group hover:border-[#ff2d78] transition-all">
          <div className="flex justify-between items-start mb-2">
            <div className="p-2.5 bg-[#ff2d78]/10 rounded-lg text-[#ff2d78]">
              <PhoneCall size={20} />
            </div>
            <span className="text-[#00ffcc] text-xs font-label font-bold px-2 py-0.5 bg-[#00ffcc]/10 rounded-full border border-[#00ffcc]/20">
              +12.5%
            </span>
          </div>
          <p className="text-[#a098b0] text-[10px] font-label uppercase tracking-[0.2em] mb-1">Total Calls</p>
          <p className="text-3xl font-headline font-bold text-[#e8e0f0] tracking-tight">
            {summary?.calls ? Number(summary.calls).toLocaleString() : "12,482"}
          </p>
          <div className="absolute bottom-0 left-0 w-full h-12 opacity-50 group-hover:opacity-100 transition-opacity">
            <svg className="w-full h-full" preserveAspectRatio="none" viewBox="0 0 100 40">
              <defs>
                <linearGradient id="grad1" x1="0%" y1="0%" x2="0%" y2="100%">
                  <stop offset="0%" style={{ stopColor: "#ff2d78", stopOpacity: 0.4 }} />
                  <stop offset="100%" style={{ stopColor: "#ff2d78", stopOpacity: 0 }} />
                </linearGradient>
              </defs>
              <path d="M0 40 L0 25 Q 25 10, 50 20 T 100 5 L 100 40 Z" fill="url(#grad1)" />
              <path d="M0 25 Q 25 10, 50 20 T 100 5" fill="none" stroke="#ff2d78" strokeWidth="2" />
            </svg>
          </div>
        </div>

        {/* Card 2: Pending Orders */}
        <div className="glass-panel p-5 rounded-2xl border border-[#302840] relative overflow-hidden group hover:border-[#00ffcc] transition-all">
          <div className="flex justify-between items-start mb-2">
            <div className="p-2.5 bg-[#00ffcc]/10 rounded-lg text-[#00ffcc]">
              <Package size={20} />
            </div>
            <span className="text-[#ff2d78] text-xs font-label font-bold px-2 py-0.5 bg-[#ff2d78]/10 rounded-full border border-[#ff2d78]/20">
              -2.4%
            </span>
          </div>
          <p className="text-[#a098b0] text-[10px] font-label uppercase tracking-[0.2em] mb-1">Pending Orders</p>
          <p className="text-3xl font-headline font-bold text-[#e8e0f0] tracking-tight">
            {summary?.pending_orders ?? "439"}
          </p>
          <div className="absolute bottom-0 left-0 w-full h-12 opacity-50 group-hover:opacity-100 transition-opacity">
            <svg className="w-full h-full" preserveAspectRatio="none" viewBox="0 0 100 40">
              <defs>
                <linearGradient id="grad2" x1="0%" y1="0%" x2="0%" y2="100%">
                  <stop offset="0%" style={{ stopColor: "#00ffcc", stopOpacity: 0.4 }} />
                  <stop offset="100%" style={{ stopColor: "#00ffcc", stopOpacity: 0 }} />
                </linearGradient>
              </defs>
              <path d="M0 40 L0 30 Q 25 35, 50 15 T 100 25 L 100 40 Z" fill="url(#grad2)" />
              <path d="M0 30 Q 25 35, 50 15 T 100 25" fill="none" stroke="#00ffcc" strokeWidth="2" />
            </svg>
          </div>
        </div>

        {/* Card 3: Suppliers */}
        <div className="glass-panel p-5 rounded-2xl border border-[#302840] relative overflow-hidden group hover:border-[#ffe04a] transition-all">
          <div className="flex justify-between items-start mb-2">
            <div className="p-2.5 bg-[#ffe04a]/10 rounded-lg text-[#ffe04a]">
              <Users size={20} />
            </div>
            <span className="text-[#00ffcc] text-xs font-label font-bold px-2 py-0.5 bg-[#00ffcc]/10 rounded-full border border-[#00ffcc]/20">
              Stable
            </span>
          </div>
          <p className="text-[#a098b0] text-[10px] font-label uppercase tracking-[0.2em] mb-1">Suppliers</p>
          <p className="text-3xl font-headline font-bold text-[#e8e0f0] tracking-tight">
            {summary?.suppliers ?? "152"}
          </p>
          <div className="absolute bottom-0 left-0 w-full h-12 opacity-50 group-hover:opacity-100 transition-opacity">
            <svg className="w-full h-full" preserveAspectRatio="none" viewBox="0 0 100 40">
              <path d="M0 20 L20 20 L40 20 L60 20 L80 20 L100 20" fill="none" stroke="#ffe04a" strokeDasharray="4 2" strokeWidth="2" />
            </svg>
          </div>
        </div>

        {/* Card 4: Last Call Status */}
        <div className="glass-panel p-5 rounded-2xl border border-[#302840] relative overflow-hidden group hover:border-[#ff2d78] transition-all">
          <div className="flex justify-between items-start mb-2">
            <div className="p-2.5 bg-[#e8e0f0]/10 rounded-lg text-[#e8e0f0]">
              <Clock size={20} />
            </div>
            <span className="text-[#a098b0] text-xs font-label">2m ago</span>
          </div>
          <p className="text-[#a098b0] text-[10px] font-label uppercase tracking-[0.2em] mb-1">Last Call</p>
          <p className="text-3xl font-headline font-bold text-[#e8e0f0] tracking-tight">Success</p>
          <div className="mt-2 flex items-center gap-2">
            <span className="text-[10px] font-label text-[#a098b0] uppercase tracking-widest">
              Latency: <span className="text-[#00ffcc] font-bold">42ms</span>
            </span>
          </div>
        </div>
      </div>

      {/* ==================== MAIN DASHBOARD GRID ==================== */}
      <div className="grid grid-cols-12 gap-8">
        {/* Left Column Section (8 cols) */}
        <div className="col-span-12 xl:col-span-8 space-y-8">
          {/* Active & Recent Interactions Table */}
          <div className="bg-[#1e1e30] border border-[#302840] rounded-2xl overflow-hidden shadow-2xl">
            <div className="p-6 border-b border-[#302840] flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3 bg-[#28283e]/50">
              <h3 className="font-headline font-bold text-lg text-[#e8e0f0]">
                Active & Recent Interactions
              </h3>
              <div className="flex items-center gap-2">
                <span className="px-3 py-1 bg-[#00ffcc]/10 border border-[#00ffcc]/20 text-[#00ffcc] text-[10px] font-label font-bold rounded-full">
                  3 LIVE
                </span>
                <span className="px-3 py-1 bg-[#141422] text-[#a098b0] text-[10px] font-label font-bold rounded-full">
                  24 COMPLETED TODAY
                </span>
              </div>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead className="bg-[#0a0a12]/50 text-[#a098b0] text-[11px] uppercase font-label tracking-widest border-b border-[#302840]">
                  <tr>
                    <th className="px-6 py-4">Interaction ID</th>
                    <th className="px-6 py-4">Participant</th>
                    <th className="px-6 py-4">Type</th>
                    <th className="px-6 py-4">Status</th>
                    <th className="px-6 py-4 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#302840]/40">
                  {/* Default Live Row 1 */}
                  <tr className="hover:bg-[#1a1a2e]/50 transition-colors group">
                    <td className="px-6 py-4">
                      <span className="text-sm font-label text-[#ff2d78] font-bold">#CALL-9412</span>
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex flex-col">
                        <span className="text-sm font-bold text-[#e8e0f0]">Rajesh Kumar</span>
                        <span className="text-[10px] font-label text-[#a098b0] uppercase tracking-widest">+91 9845...</span>
                      </div>
                    </td>
                    <td className="px-6 py-4 text-xs font-medium text-[#a098b0] uppercase tracking-widest font-label">
                      Order Verification
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-2 text-[#00ffcc] text-glow-secondary font-bold text-[10px] uppercase tracking-widest font-label">
                        <span className="w-2 h-2 rounded-full bg-[#00ffcc] pulse-live" /> Live
                      </div>
                    </td>
                    <td className="px-6 py-4 text-right">
                      <div className="flex justify-end gap-2 opacity-90 group-hover:opacity-100 transition-opacity">
                        <Link
                          href="/dashboard/simulator"
                          className="px-3 py-1 bg-[#00ffcc] text-[#001a1a] text-[10px] font-headline font-bold rounded uppercase tracking-widest hover:scale-105 transition-transform"
                        >
                          Join
                        </Link>
                        <button className="p-1.5 bg-[#28283e] border border-[#302840] rounded hover:border-[#ff2d78] text-[#a098b0] hover:text-[#e8e0f0] transition-colors">
                          <Sliders size={14} />
                        </button>
                      </div>
                    </td>
                  </tr>

                  {/* Default Live Row 2 */}
                  <tr className="hover:bg-[#1a1a2e]/50 transition-colors group">
                    <td className="px-6 py-4">
                      <span className="text-sm font-label text-[#ff2d78] font-bold">#CALL-9411</span>
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex flex-col">
                        <span className="text-sm font-bold text-[#e8e0f0]">Anita Singh</span>
                        <span className="text-[10px] font-label text-[#a098b0] uppercase tracking-widest">+91 7022...</span>
                      </div>
                    </td>
                    <td className="px-6 py-4 text-xs font-medium text-[#a098b0] uppercase tracking-widest font-label">
                      Logistics Sync
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-1.5 text-[#ffe04a] font-bold text-[10px] uppercase tracking-widest font-label">
                        <Sparkles size={13} /> Transcribing
                      </div>
                    </td>
                    <td className="px-6 py-4 text-right">
                      <div className="flex justify-end gap-2 opacity-90 group-hover:opacity-100 transition-opacity">
                        <Link
                          href="/dashboard/calls"
                          className="px-3 py-1 bg-[#28283e] border border-[#302840] text-[#e8e0f0] text-[10px] font-headline font-bold rounded uppercase tracking-widest hover:border-[#ff2d78] transition-colors"
                        >
                          View
                        </Link>
                        <button className="p-1.5 bg-[#28283e] border border-[#302840] rounded hover:border-[#ff2d78] text-[#a098b0] hover:text-[#e8e0f0] transition-colors">
                          <Sliders size={14} />
                        </button>
                      </div>
                    </td>
                  </tr>

                  {/* SWR Dynamic Calls */}
                  {calls?.slice(0, 4).map((c) => (
                    <tr key={c.id} className="hover:bg-[#1a1a2e]/50 transition-colors group">
                      <td className="px-6 py-4">
                        <span className="text-sm font-label text-[#ff2d78] font-bold">#{c.id.substring(0, 8)}</span>
                      </td>
                      <td className="px-6 py-4">
                        <div className="flex flex-col">
                          <span className="text-sm font-bold text-[#e8e0f0]">{c.caller_name || "Regional Agent"}</span>
                          <span className="text-[10px] font-label text-[#a098b0] uppercase tracking-widest">
                            {c.caller_phone || "+91 9811..."}
                          </span>
                        </div>
                      </td>
                      <td className="px-6 py-4 text-xs font-medium text-[#a098b0] uppercase tracking-widest font-label">
                        {c.intent || "Order Verification"}
                      </td>
                      <td className="px-6 py-4">
                        <span className="px-2 py-0.5 bg-[#00ffcc]/10 border border-[#00ffcc]/30 text-[#00ffcc] text-[10px] font-label font-bold rounded uppercase">
                          {c.outcome || "COMPLETED"}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-right">
                        <Link
                          href="/dashboard/calls"
                          className="px-3 py-1 bg-[#28283e] border border-[#302840] text-[#e8e0f0] text-[10px] font-headline font-bold rounded uppercase tracking-widest hover:border-[#ff2d78] transition-colors inline-block"
                        >
                          Details
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="p-4 bg-[#0a0a12]/40 text-center border-t border-[#302840]">
              <Link
                href="/dashboard/calls"
                className="text-xs font-label uppercase tracking-widest text-[#a098b0] hover:text-[#ff2d78] transition-colors font-bold"
              >
                View All Logs →
              </Link>
            </div>
          </div>

          {/* Bento Grid Sub-row (2 Cards) */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Performance Analytics Card */}
            <div className="glass-panel p-6 rounded-2xl border border-[#302840] hover:neon-glow-secondary transition-all cursor-pointer">
              <div className="flex items-center gap-4 mb-4">
                <div className="w-12 h-12 rounded-xl bg-[#00ffcc]/10 flex items-center justify-center text-[#00ffcc]">
                  <TrendingUp size={24} />
                </div>
                <div>
                  <h4 className="font-headline font-bold text-[#e8e0f0]">Performance Analytics</h4>
                  <p className="text-xs text-[#a098b0] font-body">Daily conversion trends</p>
                </div>
              </div>
              <div className="h-24 flex items-end gap-2 px-2 pt-4">
                <div className="flex-1 bg-[#00ffcc]/20 rounded-t h-1/2" />
                <div className="flex-1 bg-[#00ffcc]/30 rounded-t h-3/4" />
                <div className="flex-1 bg-[#00ffcc]/40 rounded-t h-2/3" />
                <div className="flex-1 bg-[#00ffcc]/50 rounded-t h-full" />
                <div className="flex-1 bg-[#00ffcc]/60 rounded-t h-4/5" />
                <div className="flex-1 bg-[#00ffcc] rounded-t h-3/4 shadow-[0_0_12px_#00ffcc]" />
              </div>
            </div>

            {/* AI Health Index Card */}
            <div className="glass-panel p-6 rounded-2xl border border-[#302840] hover:neon-glow-primary transition-all cursor-pointer">
              <div className="flex items-center gap-4 mb-4">
                <div className="w-12 h-12 rounded-xl bg-[#ff2d78]/10 flex items-center justify-center text-[#ff2d78]">
                  <Brain size={24} />
                </div>
                <div>
                  <h4 className="font-headline font-bold text-[#e8e0f0]">AI Health Index</h4>
                  <p className="text-xs text-[#a098b0] font-body">Llama-3 latency check</p>
                </div>
              </div>
              <div className="space-y-3.5 pt-1">
                <div>
                  <div className="flex justify-between items-center text-[10px] font-label uppercase tracking-widest text-[#a098b0] mb-1">
                    <span>Accuracy</span>
                    <span className="text-[#ff2d78] font-bold">99.8%</span>
                  </div>
                  <div className="h-1.5 w-full bg-[#ff2d78]/10 rounded-full overflow-hidden">
                    <div className="h-full bg-[#ff2d78] rounded-full w-[99.8%] shadow-[0_0_8px_#ff2d78]" />
                  </div>
                </div>

                <div className="flex justify-between items-center text-[10px] font-label uppercase tracking-widest text-[#a098b0]">
                  <span>Response Time</span>
                  <span className="text-[#00ffcc] font-bold">42ms</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Right Side Panel (4 cols) */}
        <div className="col-span-12 xl:col-span-4 space-y-8">
          {/* Phone Simulator Widget */}
          <div className="glass-panel p-6 rounded-2xl border border-[#ff2d78]/20 relative overflow-hidden group">
            <div className="scanline" />
            <div className="flex justify-between items-center mb-6">
              <h3 className="font-headline font-bold text-[#e8e0f0]">Phone Simulator</h3>
              <Phone size={18} className="text-[#ff2d78] text-glow-primary" />
            </div>

            <div className="bg-[#0a0a12] border border-[#302840] rounded-xl p-4 mb-4">
              <div className="flex flex-col items-center py-5">
                <div className="w-16 h-16 rounded-full bg-[#ff2d78]/20 border border-[#ff2d78]/40 flex items-center justify-center mb-3 text-[#ff2d78] shadow-[0_0_20px_rgba(255,45,120,0.3)]">
                  <Mic size={28} />
                </div>
                <p className="text-xs font-label uppercase tracking-[0.2em] text-[#a098b0]">Ready to Sim</p>
                <p className="text-base font-headline font-bold text-[#e8e0f0] mt-0.5">VoxFlow Agent Alpha</p>
              </div>

              {/* 3x4 Dialpad Grid */}
              <div className="grid grid-cols-3 gap-2.5">
                {["1", "2", "3", "4", "5", "6", "7", "8", "9", "*", "0", "#"].map((digit) => (
                  <button
                    key={digit}
                    onClick={() => handleKeyClick(digit)}
                    className={`h-10 rounded-lg border font-headline font-bold text-sm transition-all ${
                      activeKeypad === digit
                        ? "bg-[#ff2d78]/30 border-[#ff2d78] text-[#ff2d78] scale-95"
                        : "bg-[#1e1e30] border-[#302840] text-[#e8e0f0] hover:border-[#ff2d78]/60 hover:bg-[#28283e]"
                    }`}
                  >
                    {digit}
                  </button>
                ))}
              </div>
            </div>

            <Link
              href="/dashboard/simulator"
              className="w-full py-3 bg-[#ff2d78] text-[#1a0010] font-headline font-bold text-sm rounded-xl flex items-center justify-center gap-2 neon-glow-primary hover:scale-[1.02] active:scale-[0.98] transition-all"
            >
              <Phone size={16} /> Start Simulation
            </Link>
          </div>

          {/* Registered Suppliers Widget */}
          <div className="glass-panel p-6 rounded-2xl border border-[#302840]">
            <div className="flex justify-between items-center mb-6">
              <h3 className="font-headline font-bold text-[#e8e0f0]">Registered Suppliers</h3>
              <Link href="/dashboard/suppliers" className="text-xs text-[#00ffcc] font-label font-bold uppercase tracking-widest hover:text-glow-secondary">
                View All
              </Link>
            </div>

            <div className="space-y-4">
              {[
                { name: "Global Bottling Co.", type: "Tier 1 Partner", img: "https://images.unsplash.com/photo-1581091226825-a6a2a5aee158?w=100&auto=format&fit=crop&q=80" },
                { name: "PepsiCo Regional Div", type: "Internal Node", img: "https://images.unsplash.com/photo-1586528116311-ad8dd3c8310d?w=100&auto=format&fit=crop&q=80" },
                { name: "Swift-Flow Packing", type: "Contractor", img: "https://images.unsplash.com/photo-1553413077-190dd305871c?w=100&auto=format&fit=crop&q=80" },
              ].map((s, idx) => (
                <Link key={idx} href="/dashboard/suppliers" className="flex items-center gap-3.5 group">
                  <div className="w-10 h-10 rounded-lg bg-[#28283e] border border-[#302840] overflow-hidden shrink-0">
                    <img src={s.img} alt={s.name} className="w-full h-full object-cover group-hover:scale-110 transition-transform" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-bold text-[#e8e0f0] group-hover:text-[#ff2d78] transition-colors truncate">
                      {s.name}
                    </p>
                    <p className="text-xs text-[#a098b0] font-body">{s.type}</p>
                  </div>
                  <ChevronRight size={16} className="text-[#a098b0] group-hover:text-[#e8e0f0] transition-colors" />
                </Link>
              ))}
            </div>
          </div>

          {/* Urgent Orders Card */}
          <div className="glass-panel p-6 rounded-2xl border border-[#302840] bg-gradient-to-br from-[#141422] to-[#0a0a12]">
            <div className="flex justify-between items-center mb-5">
              <h3 className="font-headline font-bold text-[#e8e0f0]">Urgent Orders</h3>
              <span className="px-2 py-0.5 bg-[#ff4444]/15 text-[#ff4444] border border-[#ff4444]/30 text-[10px] font-label font-bold rounded">
                ACTION REQ.
              </span>
            </div>

            <div className="space-y-3">
              <div className="p-3.5 bg-[#0a0a12] border-l-4 border-[#ff2d78] rounded-r-lg">
                <div className="flex justify-between items-start mb-1">
                  <span className="text-xs font-bold text-[#e8e0f0] font-label">#ORD-1082-A</span>
                  <span className="text-[10px] font-label text-[#a098b0]">14:02</span>
                </div>
                <p className="text-xs text-[#a098b0] font-body">Validation call failed twice. Agent re-routing initiated.</p>
              </div>

              <div className="p-3.5 bg-[#0a0a12] border-l-4 border-[#00ffcc] rounded-r-lg">
                <div className="flex justify-between items-start mb-1">
                  <span className="text-xs font-bold text-[#e8e0f0] font-label">#ORD-0994-C</span>
                  <span className="text-[10px] font-label text-[#a098b0]">13:58</span>
                </div>
                <p className="text-xs text-[#a098b0] font-body">Inventory check complete. Awaiting warehouse signature.</p>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* ==================== FOOTER ==================== */}
      <footer className="w-full py-8 px-6 mt-12 bg-[#0a0a12] border-t border-[#302840] rounded-2xl">
        <div className="flex flex-col md:flex-row justify-between items-center gap-6">
          <div className="flex flex-col items-center md:items-start gap-2">
            <div className="flex items-center gap-2">
              <span className="text-lg font-headline font-bold text-[#ff2d78] tracking-tighter">VoxFlow AI</span>
              <span className="text-[10px] font-label text-[#a098b0] border border-[#302840] px-2 py-0.5 rounded">v4.2.0-stable</span>
            </div>
            <p className="font-body text-xs text-[#a098b0]">© 2024 VoxFlow AI. Engineering the future of voice.</p>
          </div>

          <div className="flex items-center gap-6 text-xs text-[#a098b0] font-label">
            <Link className="hover:text-[#00ffcc] transition-colors" href="/#platform">Resources</Link>
            <Link className="hover:text-[#00ffcc] transition-colors" href="/pricing">Pricing</Link>
            <Link className="hover:text-[#00ffcc] transition-colors" href="/about">Support</Link>
            <Link className="hover:text-[#00ffcc] transition-colors" href="/about">Privacy</Link>
          </div>

          <div className="flex gap-3">
            <button className="w-8 h-8 rounded-full border border-[#302840] flex items-center justify-center hover:border-[#ff2d78] text-[#a098b0] hover:text-[#ff2d78] transition-all">
              <Globe size={14} />
            </button>
            <button className="w-8 h-8 rounded-full border border-[#302840] flex items-center justify-center hover:border-[#ff2d78] text-[#a098b0] hover:text-[#ff2d78] transition-all">
              <Terminal size={14} />
            </button>
          </div>
        </div>
      </footer>
    </div>
  );
}
