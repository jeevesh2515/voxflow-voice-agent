"use client";

import useSWR from "swr";
import { MessageSquare, Mail } from "lucide-react";
import Topbar from "@/components/Topbar";
import { api } from "@/lib/api";
import { useTenant } from "@/lib/tenant-context";

export default function CommunicationsPage() {
  const { activeTenantId, activeTenant } = useTenant();
  const { data: comms, error, isLoading } = useSWR(["communications", activeTenantId], () =>
    api.communications(activeTenantId),
  );

  return (
    <>
      <Topbar title="Outbound Communications Log" subtitle={activeTenant.name} />

      <div className="p-6 space-y-6">
        <div className="rounded-lg border border-ink-700/60 bg-ink-900/40 overflow-hidden">
          <div className="px-5 py-4 border-b border-ink-700/60 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <MessageSquare className="text-vox-400" size={18} />
              <h2 className="text-sm font-semibold text-ink-50">Email & WhatsApp Logs</h2>
            </div>
            <span className="text-xs font-mono text-ink-400">{comms?.length ?? 0} dispatched</span>
          </div>

          {isLoading && <div className="px-5 py-12 text-center text-sm text-ink-500">Loading communications...</div>}
          {error && <div className="m-4 rounded border border-danger-500/30 bg-danger-500/10 p-3 text-sm text-danger-400">Failed to load communications. Is the API running?</div>}
          <div className="divide-y divide-ink-800/60">
            {comms?.map((c) => (
              <div key={c.id} className="p-5 space-y-2 hover:bg-ink-800/20 transition-colors">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span
                      className={`h-7 w-7 rounded grid place-items-center text-xs ${
                        c.channel === "whatsapp"
                          ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/30"
                          : "bg-blue-500/10 text-blue-400 border border-blue-500/30"
                      }`}
                    >
                      {c.channel === "whatsapp" ? <MessageSquare size={14} /> : <Mail size={14} />}
                    </span>
                    <div>
                      <div className="text-sm font-semibold text-ink-50">{c.recipient}</div>
                      <div className="text-[11px] font-mono text-ink-400 uppercase tracking-wider">
                        {c.channel} · {new Date(c.timestamp).toLocaleString("en-IN")}
                      </div>
                    </div>
                  </div>
                  <span className="text-[10px] font-mono uppercase px-2 py-0.5 rounded border bg-success-500/10 text-success-400 border-success-500/30">
                    {c.status}
                  </span>
                </div>

                {c.subject && <div className="text-xs font-medium text-ink-200 pl-9">{c.subject}</div>}
                <div className="text-xs text-ink-300 pl-9 font-mono bg-ink-950/40 p-3 rounded border border-ink-800/50 leading-relaxed">
                  {c.body}
                </div>
              </div>
            ))}

            {!isLoading && !error && (!comms || comms.length === 0) && (
              <div className="px-5 py-12 text-center text-sm text-ink-500">
                No outbound communications logged for {activeTenant.name}.
              </div>
            )}
          </div>
        </div>
      </div>
    </>
  );
}
