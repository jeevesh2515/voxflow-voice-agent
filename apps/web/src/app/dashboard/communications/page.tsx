"use client";

import { useState, useMemo } from "react";
import useSWR from "swr";
import { MessageSquare, Mail, Search } from "lucide-react";
import { api } from "@/lib/api";
import { useTenant } from "@/lib/tenant-context";
import SectionCard from "@/components/dashboard/SectionCard";
import DataTable from "@/components/dashboard/DataTable";

export default function CommunicationsPage() {
  const { activeTenantId, activeTenant } = useTenant();
  const { data: comms, error, isLoading } = useSWR(["communications", activeTenantId], () =>
    api.communications(activeTenantId),
  );

  const [search, setSearch] = useState("");
  const [channelFilter, setChannelFilter] = useState<string>("all");

  const filtered = useMemo(() => {
    if (!comms) return [];
    let result = comms;
    if (search.trim()) {
      const q = search.toLowerCase();
      result = result.filter((c) => c.recipient.toLowerCase().includes(q) || (c.subject || "").toLowerCase().includes(q));
    }
    if (channelFilter !== "all") {
      result = result.filter((c) => c.channel === channelFilter);
    }
    return result;
  }, [comms, search, channelFilter]);

  const columns = [
    {
      key: "channel",
      label: "Channel",
      render: (c: any) => (
        <span className={`inline-flex items-center gap-1.5 text-[10px] font-mono uppercase px-2 py-0.5 rounded border ${
          c.channel === "whatsapp" ? "text-emerald-400 border-emerald-500/30 bg-emerald-500/10" : "text-blue-400 border-blue-500/30 bg-blue-500/10"
        }`}>
          {c.channel === "whatsapp" ? "WA" : "Email"}
        </span>
      ),
    },
    {
      key: "recipient",
      label: "Recipient",
      render: (c: any) => <span className="text-[#e8e0f0] text-sm">{c.recipient}</span>,
    },
    {
      key: "subject",
      label: "Subject",
      render: (c: any) => <span className="text-[#a098b0] text-xs">{c.subject || "—"}</span>,
    },
    {
      key: "timestamp",
      label: "Sent At",
      render: (c: any) => (
        <span className="text-[#a098b0] text-xs font-mono">{new Date(c.timestamp).toLocaleString("en-IN")}</span>
      ),
    },
    {
      key: "status",
      label: "Status",
      render: (c: any) => (
        <span className="text-[10px] font-mono uppercase px-2 py-0.5 rounded border bg-success-500/10 text-success-400 border-success-500/30">
          {c.status}
        </span>
      ),
    },
  ];

  return (
    <div className="space-y-6">
      <SectionCard
        title="Outbound Communications Log"
        subtitle={`${activeTenant.name}`}
        icon={<MessageSquare size={18} className="text-[#00ffcc]" />}
        action={
          <div className="flex items-center gap-2">
            <div className="relative">
              <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-[#a098b0]" />
              <input
                type="text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search comms..."
                className="pl-9 pr-4 py-2 rounded-lg bg-[#0a0a12] border border-[#302840] text-xs text-[#e8e0f0] placeholder-[#5a5068] focus:outline-none focus:border-[#00ffcc]/50 w-48"
              />
            </div>
            <select
              value={channelFilter}
              onChange={(e) => setChannelFilter(e.target.value)}
              className="appearance-none bg-[#0a0a12] border border-[#302840] text-xs text-[#e8e0f0] rounded-lg px-3 py-2 pr-8 focus:outline-none focus:border-[#00ffcc]/50"
            >
              <option value="all">All Channels</option>
              <option value="whatsapp">WhatsApp</option>
              <option value="email">Email</option>
            </select>
          </div>
        }
      >
        {isLoading && <div className="text-center text-[#a098b0] py-12 text-sm">Loading communications...</div>}
        {error && <div className="rounded border border-danger-500/30 bg-danger-500/10 p-3 text-sm text-danger-500">Failed to load communications. Is the API running?</div>}
        {!isLoading && !error && (
          <DataTable
            columns={columns}
            data={filtered}
            keyExtractor={(c) => c.id}
            loading={isLoading}
            emptyState={
              <div className="px-4 py-12 text-center">
                <MessageSquare size={32} className="mx-auto text-[#5a5068] mb-3" />
                <div className="text-sm text-[#a098b0]">No outbound communications logged for {activeTenant.name}.</div>
              </div>
            }
          />
        )}
      </SectionCard>
    </div>
  );
}
