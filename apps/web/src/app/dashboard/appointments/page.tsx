"use client";

import { useState, useMemo } from "react";
import useSWR, { mutate } from "swr";
import {
  Calendar,
  Clock,
  Plus,
  Users,
  Search,
  CheckCircle2,
  AlertCircle,
  MapPin,
  X,
  CalendarCheck,
} from "lucide-react";
import { api } from "@/lib/api";
import { useTenant } from "@/lib/tenant-context";

export default function AppointmentsPage() {
  const { activeTenantId, activeTenant } = useTenant();
  const { data: appointments, error, isLoading } = useSWR(
    ["appointments", activeTenantId],
    () => api.appointments(activeTenantId),
  );
  const { data: suppliers } = useSWR(["suppliers", activeTenantId], () =>
    api.suppliers(undefined, activeTenantId),
  );

  const [searchQuery, setSearchQuery] = useState("");
  const [isScheduleOpen, setIsScheduleOpen] = useState(false);

  // Form state
  const [supplierId, setSupplierId] = useState("");
  const [appointmentDate, setAppointmentDate] = useState("");
  const [purpose, setPurpose] = useState("Dock Delivery & Physical Verification");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [formError, setFormError] = useState("");

  const filteredAppointments = useMemo(() => {
    if (!appointments) return [];
    return (appointments as any[]).filter((a) => {
      const q = searchQuery.toLowerCase();
      return (
        a.id.toLowerCase().includes(q) ||
        (a.supplier_id && a.supplier_id.toLowerCase().includes(q)) ||
        (a.purpose && a.purpose.toLowerCase().includes(q)) ||
        a.status.toLowerCase().includes(q)
      );
    });
  }, [appointments, searchQuery]);

  const stats = useMemo(() => {
    const list = (appointments as any[]) || [];
    return {
      total: list.length,
      confirmed: list.filter((a) => a.status === "confirmed").length,
      pending: list.filter((a) => a.status === "pending").length,
    };
  }, [appointments]);

  const handleScheduleAppointment = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!appointmentDate) {
      setFormError("Please select a date and time");
      return;
    }
    setFormError("");
    setIsSubmitting(true);

    try {
      await api.createAppointment(
        {
          supplier_id: supplierId || undefined,
          datetime: new Date(appointmentDate).toISOString(),
          purpose: purpose.trim(),
        },
        activeTenantId,
      );
      mutate(["appointments", activeTenantId]);
      setIsScheduleOpen(false);
      setAppointmentDate("");
    } catch (err: any) {
      setFormError(err.message || "Failed to schedule appointment");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-12">
      {/* ==================== PAGE HEADER ==================== */}
      <header className="flex flex-col sm:flex-row justify-between items-start sm:items-end gap-4">
        <div>
          <div className="flex items-center gap-2 text-xs font-label uppercase tracking-widest text-[#a098b0] mb-1">
            <span>Operations</span>
            <span>/</span>
            <span className="text-[#00ffcc] font-bold">{activeTenant.name}</span>
          </div>
          <h1 className="text-2xl sm:text-3xl font-headline font-extrabold text-[#e8e0f0] tracking-[0.05em] uppercase">
            Supplier <span className="text-[#ffe04a] text-glow-accent">Appointments</span>
          </h1>
          <p className="text-[#a098b0] font-body text-sm mt-1">
            Scheduled warehouse dock appointments, physical quality inspections, and supplier onboarding slots.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => {
              if (suppliers && suppliers.length > 0) setSupplierId(suppliers[0].id);
              setIsScheduleOpen(true);
            }}
            className="bg-[#ffe04a] text-[#1a0010] px-4 py-2 rounded-xl text-xs font-headline font-bold uppercase tracking-widest flex items-center gap-2 shadow-[0_0_20px_rgba(255,224,74,0.4)] hover:scale-105 active:scale-95 transition-all"
          >
            <Plus size={15} /> Book Slot
          </button>
        </div>
      </header>

      {/* ==================== STAT CARDS ==================== */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="glass-panel p-4 rounded-2xl border border-[#ffe04a]/30">
          <div className="flex items-center justify-between text-[#a098b0] text-[10px] font-label uppercase tracking-wider mb-1">
            <span>Total Appointments</span>
            <Calendar size={16} className="text-[#ffe04a]" />
          </div>
          <div className="text-2xl font-headline font-bold text-[#e8e0f0]">{stats.total}</div>
          <div className="text-[10px] text-[#ffe04a] mt-1">Dock visits recorded</div>
        </div>

        <div className="glass-panel p-4 rounded-2xl border border-[#00ffcc]/30">
          <div className="flex items-center justify-between text-[#a098b0] text-[10px] font-label uppercase tracking-wider mb-1">
            <span>Confirmed Slots</span>
            <CheckCircle2 size={16} className="text-[#00ffcc]" />
          </div>
          <div className="text-2xl font-headline font-bold text-[#00ffcc]">{stats.confirmed}</div>
          <div className="text-[10px] text-[#a098b0] mt-1">Automated voice confirmation</div>
        </div>

        <div className="glass-panel p-4 rounded-2xl border border-blue-500/30">
          <div className="flex items-center justify-between text-[#a098b0] text-[10px] font-label uppercase tracking-wider mb-1">
            <span>Warehouse Capacity</span>
            <CalendarCheck size={16} className="text-blue-400" />
          </div>
          <div className="text-2xl font-headline font-bold text-blue-400">Available</div>
          <div className="text-[10px] text-[#a098b0] mt-1">Slots open for this week</div>
        </div>
      </div>

      {/* ==================== SEARCH BAR ==================== */}
      <div className="relative bg-[#111118]/80 p-3 rounded-2xl border border-[#302840]/60">
        <Search size={15} className="absolute left-6 top-1/2 -translate-y-1/2 text-[#a098b0]" />
        <input
          type="text"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          placeholder="Search appointments by ID, supplier, purpose, or status..."
          className="w-full bg-[#181824] border border-[#302840]/60 rounded-xl pl-9 pr-4 py-2 text-xs text-[#e8e0f0] placeholder:text-[#a098b0]/50 focus:outline-none focus:border-[#ffe04a] transition-all font-body"
        />
      </div>

      {/* ==================== APPOINTMENTS FEED ==================== */}
      <div className="space-y-4">
        {isLoading && (
          <div className="py-16 text-center text-[#a098b0] text-xs font-label uppercase tracking-widest flex items-center justify-center gap-2">
            <span className="w-2 h-2 rounded-full bg-[#ffe04a] animate-ping" /> Loading appointment slots...
          </div>
        )}

        {error && (
          <div className="p-6 text-center text-[#ff2d78] bg-[#ff2d78]/5 text-xs font-body rounded-2xl border border-[#ff2d78]/20">
            Failed to load appointments. Please verify backend API connectivity.
          </div>
        )}

        {!isLoading &&
          !error &&
          filteredAppointments.map((app) => (
            <div
              key={app.id}
              className="glass-panel p-5 rounded-2xl border border-[#302840]/60 hover:border-[#ffe04a]/60 transition-all flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 shadow-lg group"
            >
              <div className="flex items-start gap-4">
                <div className="w-12 h-12 rounded-2xl bg-[#ffe04a]/10 border border-[#ffe04a]/30 flex flex-col items-center justify-center text-[#ffe04a] shrink-0">
                  <Calendar size={18} />
                  <span className="text-[9px] font-bold font-mono mt-0.5">
                    {new Date(app.datetime).getDate()}
                  </span>
                </div>
                <div>
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="font-headline font-bold text-sm text-[#e8e0f0] group-hover:text-glow-accent transition-all">
                      {app.purpose || "Supplier Dock Meeting"}
                    </span>
                    <span
                      className={`text-[10px] font-label font-bold uppercase px-2.5 py-0.5 rounded-full border ${
                        app.status === "confirmed"
                          ? "bg-[#00ffcc]/10 text-[#00ffcc] border-[#00ffcc]/30"
                          : "bg-[#ffe04a]/10 text-[#ffe04a] border-[#ffe04a]/30"
                      }`}
                    >
                      {app.status}
                    </span>
                  </div>

                  <div className="text-xs text-[#a098b0] flex items-center gap-3 mt-1.5 flex-wrap">
                    <span className="flex items-center gap-1 text-[#e8e0f0]">
                      <Clock size={12} className="text-[#ffe04a]" />{" "}
                      {new Date(app.datetime).toLocaleTimeString("en-IN", {
                        hour: "2-digit",
                        minute: "2-digit",
                      })}
                    </span>
                    <span className="font-mono text-[11px] text-[#a098b0]">
                      Supplier: <strong className="text-[#e8e0f0]">{app.supplier_id || "Direct Caller"}</strong>
                    </span>
                    <span className="font-mono text-[10px] text-[#5a5068]">{app.id}</span>
                  </div>
                </div>
              </div>

              <div className="text-right shrink-0 text-xs font-mono text-[#a098b0]">
                <div>
                  {new Date(app.datetime).toLocaleDateString("en-IN", {
                    weekday: "short",
                    month: "short",
                    day: "numeric",
                    year: "numeric",
                  })}
                </div>
              </div>
            </div>
          ))}

        {!isLoading && !error && filteredAppointments.length === 0 && (
          <div className="glass-panel rounded-2xl border border-dashed border-[#302840]/60 p-16 text-center space-y-3">
            <Calendar className="mx-auto text-[#5a5068]" size={36} />
            <div className="text-sm text-[#e8e0f0] font-headline font-semibold">No scheduled appointments</div>
            <p className="text-xs text-[#a098b0] max-w-sm mx-auto">
              {searchQuery
                ? `No appointments matching "${searchQuery}".`
                : `Book a dock appointment or let the AI voice agent schedule slots during caller inquiries.`}
            </p>
          </div>
        )}
      </div>

      {/* ==================== SCHEDULE APPOINTMENT MODAL ==================== */}
      {isScheduleOpen && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-md flex items-center justify-center p-4">
          <div className="bg-[#111118] border border-[#ffe04a]/40 rounded-2xl p-6 sm:p-8 max-w-md w-full shadow-[0_0_50px_rgba(255,224,74,0.2)] space-y-5 relative">
            <button
              onClick={() => setIsScheduleOpen(false)}
              className="absolute top-5 right-5 text-[#a098b0] hover:text-[#e8e0f0] transition-colors"
            >
              <X size={18} />
            </button>

            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-[#ffe04a]/15 border border-[#ffe04a]/40 flex items-center justify-center text-[#ffe04a]">
                <Calendar size={20} />
              </div>
              <div>
                <h3 className="font-headline font-bold text-lg text-[#e8e0f0]">Book Appointment</h3>
                <p className="text-xs text-[#a098b0] font-body">Schedule dock visit for {activeTenant.name}</p>
              </div>
            </div>

            <form onSubmit={handleScheduleAppointment} className="space-y-4">
              <div>
                <label className="text-[10px] font-label uppercase tracking-widest text-[#e8e0f0] block mb-1.5">
                  Supplier Partner
                </label>
                <select
                  value={supplierId}
                  onChange={(e) => setSupplierId(e.target.value)}
                  className="w-full px-3.5 py-2.5 rounded-xl bg-[#181824] border border-[#302840] text-xs text-[#e8e0f0] focus:border-[#ffe04a] focus:outline-none"
                >
                  <option value="">General Supplier Meeting...</option>
                  {(suppliers || []).map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.name} ({s.id})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="text-[10px] font-label uppercase tracking-widest text-[#e8e0f0] block mb-1.5">
                  Date & Time Slot
                </label>
                <input
                  type="datetime-local"
                  required
                  value={appointmentDate}
                  onChange={(e) => setAppointmentDate(e.target.value)}
                  className="w-full px-3.5 py-2.5 rounded-xl bg-[#181824] border border-[#302840] text-xs text-[#e8e0f0] focus:border-[#ffe04a] focus:outline-none"
                />
              </div>

              <div>
                <label className="text-[10px] font-label uppercase tracking-widest text-[#e8e0f0] block mb-1.5">
                  Meeting Purpose / Dock Task
                </label>
                <input
                  type="text"
                  required
                  value={purpose}
                  onChange={(e) => setPurpose(e.target.value)}
                  placeholder="e.g. Stock delivery verification & quality testing"
                  className="w-full px-3.5 py-2.5 rounded-xl bg-[#181824] border border-[#302840] text-xs text-[#e8e0f0] focus:border-[#ffe04a] focus:outline-none font-body"
                />
              </div>

              {formError && (
                <div className="text-xs text-[#ff2d78] bg-[#ff2d78]/10 border border-[#ff2d78]/30 rounded-xl p-2.5">
                  {formError}
                </div>
              )}

              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setIsScheduleOpen(false)}
                  className="px-4 py-2.5 rounded-xl text-xs font-label uppercase font-bold text-[#a098b0] hover:text-[#e8e0f0] bg-[#181824]"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="px-5 py-2.5 rounded-xl bg-[#ffe04a] text-[#1a0010] text-xs font-headline font-bold uppercase tracking-wider shadow-[0_0_15px_rgba(255,224,74,0.4)] hover:scale-105 active:scale-95 disabled:opacity-50"
                >
                  {isSubmitting ? "Booking..." : "Confirm Schedule"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
