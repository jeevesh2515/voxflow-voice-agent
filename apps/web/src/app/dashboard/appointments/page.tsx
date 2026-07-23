"use client";

import useSWR from "swr";
import { Calendar, Clock } from "lucide-react";
import Topbar from "@/components/Topbar";
import { api } from "@/lib/api";
import { useTenant } from "@/lib/tenant-context";

export default function AppointmentsPage() {
  const { activeTenantId, activeTenant } = useTenant();
  const { data: appointments, error, isLoading } = useSWR(["appointments", activeTenantId], () =>
    api.appointments(activeTenantId),
  );

  return (
    <>
      <Topbar title="Supplier Appointments" subtitle={activeTenant.name} />

      <div className="p-6 space-y-6">
        <div className="rounded-lg border border-ink-700/60 bg-ink-900/40 overflow-hidden">
          <div className="px-5 py-4 border-b border-ink-700/60 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Calendar className="text-vox-400" size={18} />
              <h2 className="text-sm font-semibold text-ink-50">Scheduled Appointments</h2>
            </div>
            <span className="text-xs font-mono text-ink-400">
              {appointments?.length ?? 0} booked
            </span>
          </div>

          {isLoading && <div className="px-5 py-12 text-center text-sm text-ink-500">Loading appointments...</div>}
          {error && <div className="m-4 rounded border border-danger-500/30 bg-danger-500/10 p-3 text-sm text-danger-400">Failed to load appointments. Is the API running?</div>}
          <div className="divide-y divide-ink-800/60">
            {appointments?.map((app) => (
              <div key={app.id} className="p-5 flex items-start justify-between gap-4 hover:bg-ink-800/20 transition-colors">
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-semibold text-ink-50">{app.id}</span>
                    <span
                      className={`text-[10px] font-mono uppercase px-2 py-0.5 rounded border ${
                        app.status === "confirmed"
                          ? "bg-success-500/10 text-success-400 border-success-500/30"
                          : "bg-warn-500/10 text-warn-400 border-warn-500/30"
                      }`}
                    >
                      {app.status}
                    </span>
                  </div>
                  <p className="text-xs text-ink-300">{app.purpose || "General supplier meeting"}</p>
                  <div className="flex items-center gap-4 text-[11px] font-mono text-ink-400 pt-1">
                    <span className="flex items-center gap-1">
                      <Clock size={12} /> {new Date(app.datetime).toLocaleString("en-IN")}
                    </span>
                    <span>Supplier ID: {app.supplier_id || "Unspecified"}</span>
                  </div>
                </div>
              </div>
            ))}

            {!isLoading && !error && (!appointments || appointments.length === 0) && (
              <div className="px-5 py-12 text-center text-sm text-ink-500">
                No appointments booked for {activeTenant.name}.
              </div>
            )}
          </div>
        </div>
      </div>
    </>
  );
}
