"use client";

import useSWR from "swr";
import { PhoneCall, Phone, Package, Users, Activity, Mic } from "lucide-react";
import Link from "next/link";
import Topbar from "@/components/Topbar";
import { api } from "@/lib/api";
import { fmtRelative, statusBg, statusColor } from "@/lib/format";

export default function DashboardOverview() {
  const { data: summary } = useSWR("summary", () => api.summary());
  const { data: calls }   = useSWR("calls", () => api.calls(8));
  const { data: orders }  = useSWR("orders", () => api.orders({ status: "pending" }));
  const { data: suppliers } = useSWR("suppliers", () => api.suppliers());

  return (
    <>
      <Topbar title="Operations overview" subtitle="Live · IST" />

      <div className="p-6 space-y-6">
        {/* Stat row */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <Stat icon={PhoneCall} label="Total calls"     value={summary?.calls ?? "—"} accent="vox" />
          <Stat icon={Package}   label="Pending orders"  value={summary?.pending_orders ?? "—"} accent="warn" />
          <Stat icon={Users}     label="Suppliers"       value={summary?.suppliers ?? "—"} accent="vox" />
          <Stat icon={Activity}  label="Last call"       value={fmtRelative(summary?.last_call_at)} accent="success" />
        </div>

        {/* Two columns */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          {/* Recent calls */}
          <div className="lg:col-span-2 rounded-lg border border-ink-700/60 bg-ink-900/40">
            <div className="px-5 py-3 border-b border-ink-700/60 flex items-center justify-between">
              <h2 className="text-sm font-semibold text-ink-50">Recent calls</h2>
              <Link href="/dashboard/calls" className="text-xs text-vox-400 hover:text-vox-300">View all →</Link>
            </div>
            <div className="divide-y divide-ink-800/60">
              {calls?.slice(0, 6).map((c) => (
                <div key={c.id} className="px-5 py-3 flex items-center gap-3">
                  <div className={`h-8 w-8 rounded-full grid place-items-center text-xs font-mono ${
                    c.language === "hi" ? "bg-amber-500/10 text-amber-400" : "bg-vox-500/10 text-vox-300"
                  }`}>
                    {c.language.toUpperCase()}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="text-sm text-ink-50 truncate">{c.caller_name || c.caller_phone || "Unknown"}</div>
                    <div className="text-[11px] font-mono text-ink-400 uppercase tracking-wider">
                      {c.intent || "general"} · {fmtRelative(c.started_at)}
                    </div>
                  </div>
                  <span className={`text-[10px] font-mono uppercase px-2 py-0.5 rounded border ${statusBg(c.outcome)} ${statusColor(c.outcome)}`}>
                    {c.outcome}
                  </span>
                </div>
              ))}
              {(!calls || calls.length === 0) && (
                <div className="px-5 py-8 text-center text-sm text-ink-500">No calls yet — try the phone simulator.</div>
              )}
            </div>
          </div>

          {/* Quick actions + suppliers */}
          <div className="space-y-4">
            <div className="rounded-lg border border-vox-500/30 bg-vox-500/5 p-5">
              <div className="flex items-center gap-2 mb-2">
                <Mic size={16} className="text-vox-400" />
                <h3 className="text-sm font-semibold text-ink-50">Phone simulator</h3>
              </div>
              <p className="text-xs text-ink-300 mb-3">Talk to Vaani in your browser. Hindi or English.</p>
              <Link
                href="/dashboard/simulator"
                className="inline-flex items-center gap-2 text-xs px-3 py-1.5 rounded-md bg-vox-500 hover:bg-vox-600 text-white font-medium"
              >
                <Phone size={14} /> Open simulator
              </Link>
            </div>

            <div className="rounded-lg border border-ink-700/60 bg-ink-900/40">
              <div className="px-5 py-3 border-b border-ink-700/60">
                <h3 className="text-sm font-semibold text-ink-50">Suppliers</h3>
              </div>
              <div className="divide-y divide-ink-800/60 max-h-72 overflow-y-auto">
                {suppliers?.map((s) => (
                  <div key={s.id} className="px-5 py-2.5 flex items-center justify-between">
                    <div>
                      <div className="text-sm text-ink-50">{s.name}</div>
                      <div className="text-[11px] font-mono text-ink-400">{s.city} · {s.phone}</div>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div className="rounded-lg border border-ink-700/60 bg-ink-900/40">
              <div className="px-5 py-3 border-b border-ink-700/60 flex items-center justify-between">
                <h3 className="text-sm font-semibold text-ink-50">Pending orders</h3>
                <Link href="/dashboard/orders" className="text-xs text-vox-400 hover:text-vox-300">All →</Link>
              </div>
              <div className="divide-y divide-ink-800/60">
                {orders?.slice(0, 5).map((o) => (
                  <div key={o.id} className="px-5 py-2.5">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-mono text-vox-300">{o.id}</span>
                      <span className={`text-[10px] font-mono uppercase px-2 py-0.5 rounded border ${statusBg(o.status)} ${statusColor(o.status)}`}>
                        {o.status}
                      </span>
                    </div>
                    <div className="text-[11px] text-ink-400 mt-0.5">
                      {o.total_qty} cases · {fmtRelative(o.created_at)}
                    </div>
                  </div>
                ))}
                {(!orders || orders.length === 0) && (
                  <div className="px-5 py-4 text-center text-xs text-ink-500">No pending orders.</div>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}

function Stat({ icon: Icon, label, value, accent }: { icon: any; label: string; value: any; accent: "vox" | "warn" | "success" }) {
  const colors = {
    vox: "text-vox-400 bg-vox-500/10 border-vox-500/30",
    warn: "text-warn-500 bg-warn-500/10 border-warn-500/30",
    success: "text-success-500 bg-success-500/10 border-success-500/30",
  }[accent];
  return (
    <div className="rounded-lg border border-ink-700/60 bg-ink-900/40 p-4">
      <div className="flex items-center gap-2 text-[11px] font-mono uppercase tracking-wider text-ink-400 mb-2">
        <span className={`h-6 w-6 rounded grid place-items-center border ${colors}`}>
          <Icon size={12} />
        </span>
        {label}
      </div>
      <div className="text-2xl font-semibold text-ink-50">{value}</div>
    </div>
  );
}
