"use client";

import { useState, useMemo } from "react";
import useSWR from "swr";
import { Calendar, Clock, Search } from "lucide-react";
import { api } from "@/lib/api";
import { useTenant } from "@/lib/tenant-context";
import SectionCard from "@/components/dashboard/SectionCard";
import DataTable from "@/components/dashboard/DataTable";

export default function AppointmentsPage() {
  const { activeTenantId, activeTenant } = useTenant();
  const { data: appointments, error, isLoading } = useSWR(["appointments", activeTenantId], () =>
    api.appointments(activeTenantId),
  );

  const [search, setSearch] = useState("");

  const filtered = useMemo(() => {
    if (!appointments) return [];
    if (!search.trim()) return appointments;
    const q = search.toLowerCase();
    return appointments.filter((a) =>
      a.id.toLowerCase().includes(q) ||
      (a.purpose || "").toLowerCase().includes(q) ||
      (a.supplier_id || "").toLowerCase().includes(q)
    );
  }, [appointments, search]);

  const columns = [
    {
      key: "id",
      label: "ID",
      render: (a: any) => <span className="font-mono text-[#ff2d78] text-xs font-bold">{a.id}</span>,
    },
    {
      key: "status",
      label: "Status",
      render: (a: any) => (
        <span className={`text-[10px] font-mono uppercase px-2 py-0.5 rounded border ${
          a.status === "confirmed" ? "text-success-400 border-success-500/30 bg-success-500/10" : "text-warn-400 border-warn-500/30 bg-warn-500/10"
        }`}>
          {a.status}
        </span>
      ),
    },
    {
      key: "purpose",
      label: "Purpose",
      render: (a: any) => <span className="text-[#e8e0f0] text-xs">{a.purpose || "General supplier meeting"}</span>,
    },
    {
      key: "datetime",
      label: "Date & Time",
      render: (a: any) => (
        <span className="text-[#a098b0] text-xs font-mono">{new Date(a.datetime).toLocaleString("en-IN")}</span>
      ),
    },
    {
      key: "supplier",
      label: "Supplier",
      render: (a: any) => <span className="text-[#a098b0] text-xs">{a.supplier_id || "Unspecified"}</span>,
    },
  ];

  return (
    <div className="space-y-6">
      <SectionCard
        title="Supplier Appointments"
        subtitle={`${activeTenant.name}`}
        icon={<Calendar size={18} className="text-[#00ffcc]" />}
        action={
          <div className="relative">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-[#a098b0]" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search appointments..."
              className="pl-9 pr-4 py-2 rounded-lg bg-[#0a0a12] border border-[#302840] text-xs text-[#e8e0f0] placeholder-[#5a5068] focus:outline-none focus:border-[#00ffcc]/50 w-48"
            />
          </div>
        }
      >
        {isLoading && <div className="text-center text-[#a098b0] py-12 text-sm">Loading appointments...</div>}
        {error && <div className="rounded border border-danger-500/30 bg-danger-500/10 p-3 text-sm text-danger-500">Failed to load appointments. Is the API running?</div>}
        {!isLoading && !error && (
          <DataTable
            columns={columns}
            data={filtered}
            keyExtractor={(a) => a.id}
            loading={isLoading}
            emptyState={
              <div className="px-4 py-12 text-center">
                <Calendar size={32} className="mx-auto text-[#5a5068] mb-3" />
                <div className="text-sm text-[#a098b0]">No appointments booked for {activeTenant.name}.</div>
              </div>
            }
          />
        )}
      </SectionCard>
    </div>
  );
}
