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
      <header className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 bg-[#12121e] p-6 rounded-2xl border border-[#242436] shadow-sm">
        <div className="space-y-1">
          <div className="flex items-center gap-2 text-xs font-mono text-[#94a3b8]">
            <span>Operations & Scheduling</span>
            <span>/</span>
            <span className="text-[#00ffcc] font-bold">{activeTenant.name}</span>
          </div>
          <h1 className="text-xl sm:text-2xl font-headline font-bold text-white tracking-tight">
            Supplier & Dock Appointments
          </h1>
          <p className="text-xs sm:text-sm text-[#94a3b8]">
            Scheduled warehouse dock appointments, physical quality inspections, and supplier onboarding slots.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => {
              if (suppliers && suppliers.length > 0) setSupplierId(suppliers[0].id);
              setIsScheduleOpen(true);
            }}
            className="bg-amber-500 hover:bg-amber-400 text-black px-4 py-2 rounded-xl text-xs font-bold flex items-center gap-2 shadow-sm transition-all"
          >
            <Plus size={15} />
            <span>Book Slot</span>
          </button>
        </div>
      </header>

      {/* ==================== STAT CARDS ==================== */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="bg-[#141422] p-5 rounded-2xl border border-[#28283c] shadow-sm">
          <div className="flex items-center justify-between text-[#94a3b8] text-xs font-mono uppercase tracking-wider mb-1">
            <span>Total Appointments</span>
            <Calendar size={16} className="text-amber-400" />
          </div>
          <div className="text-2xl font-headline font-bold text-white">{stats.total}</div>
          <div className="text-xs text-amber-400 mt-1">Dock visits recorded</div>
        </div>

        <div className="bg-[#141422] p-5 rounded-2xl border border-[#28283c] shadow-sm">
          <div className="flex items-center justify-between text-[#94a3b8] text-xs font-mono uppercase tracking-wider mb-1">
            <span>Confirmed Slots</span>
            <CheckCircle2 size={16} className="text-[#00ffcc]" />
          </div>
          <div className="text-2xl font-headline font-bold text-[#00ffcc]">{stats.confirmed}</div>
          <div className="text-xs text-[#94a3b8] mt-1">Automated voice confirmation</div>
        </div>

        <div className="bg-[#141422] p-5 rounded-2xl border border-[#28283c] shadow-sm">
          <div className="flex items-center justify-between text-[#94a3b8] text-xs font-mono uppercase tracking-wider mb-1">
            <span>Warehouse Capacity</span>
            <CalendarCheck size={16} className="text-blue-400" />
          </div>
          <div className="text-2xl font-headline font-bold text-blue-400">Available</div>
          <div className="text-xs text-[#94a3b8] mt-1">Slots open for this week</div>
        </div>
      </div>

      {/* ==================== SEARCH BAR ==================== */}
      <div className="bg-[#141422] p-3 rounded-2xl border border-[#28283c]">
        <div className="relative">
          <Search size={15} className="absolute left-3.5 top-1/2 -translate-y-1/2 text-[#64748b]" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search appointments by ID, supplier, purpose, or status..."
            className="w-full bg-[#10101a] border border-[#28283c] rounded-xl pl-9 pr-4 py-2 text-xs text-white placeholder:text-[#64748b] focus:outline-none focus:border-amber-400"
          />
        </div>
      </div>

      {/* ==================== APPOINTMENTS FEED ==================== */}
      <div className="space-y-4">
        {isLoading && (
          <div className="py-16 text-center text-[#94a3b8] text-xs">
            Loading appointment slots...
          </div>
        )}

        {error && (
          <div className="p-6 text-center text-red-400 bg-red-500/10 text-xs rounded-2xl border border-red-500/20">
            Failed to load appointments. Please verify backend API connectivity.
          </div>
        )}

        {!isLoading &&
          !error &&
          filteredAppointments.map((app) => (
            <div
              key={app.id}
              className="bg-[#141422] p-5 rounded-2xl border border-[#28283c] hover:border-amber-400/50 transition-all flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 shadow-sm"
            >
              <div className="flex items-start gap-4">
                <div className="w-12 h-12 rounded-2xl bg-amber-500/15 border border-amber-500/30 flex flex-col items-center justify-center text-amber-400 shrink-0">
                  <Calendar size={18} />
                  <span className="text-[10px] font-bold font-mono mt-0.5">
                    {new Date(app.datetime).getDate()}
                  </span>
                </div>
                <div>
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="font-headline font-bold text-sm text-white">
                      {app.purpose || "Supplier Dock Meeting"}
                    </span>
                    <span
                      className={`text-[10px] font-mono font-bold uppercase px-2.5 py-0.5 rounded-md border ${
                        app.status === "confirmed"
                          ? "bg-[#00ffcc]/15 text-[#00ffcc] border-[#00ffcc]/30"
                          : "bg-amber-500/15 text-amber-400 border-amber-500/30"
                      }`}
                    >
                      {app.status}
                    </span>
                  </div>

                  <div className="text-xs text-[#94a3b8] flex items-center gap-3 mt-1.5 flex-wrap">
                    <span className="flex items-center gap-1 text-white font-mono">
                      <Clock size={12} className="text-amber-400" />{" "}
                      {new Date(app.datetime).toLocaleTimeString("en-IN", {
                        hour: "2-digit",
                        minute: "2-digit",
                      })}
                    </span>
                    <span className="text-[#cbd5e1]">
                      Supplier: <strong className="text-white">{app.supplier_id || "Direct Caller"}</strong>
                    </span>
                    <span className="font-mono text-[10px] text-[#ff2d78]">#{app.id.slice(0, 10)}</span>
                  </div>
                </div>
              </div>

              <div className="text-right shrink-0 text-xs font-mono text-[#94a3b8]">
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
          <div className="bg-[#141422] rounded-2xl border border-dashed border-[#28283c] p-16 text-center space-y-3">
            <Calendar className="mx-auto text-[#64748b]" size={36} />
            <div className="text-sm text-white font-headline font-semibold">No scheduled appointments</div>
            <p className="text-xs text-[#94a3b8] max-w-sm mx-auto">
              {searchQuery
                ? `No appointments matching "${searchQuery}".`
                : `Book a dock appointment or let the AI voice agent schedule slots during caller inquiries.`}
            </p>
          </div>
        )}
      </div>

      {/* ==================== SCHEDULE APPOINTMENT MODAL ==================== */}
      {isScheduleOpen && (
        <div className="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-[#141422] border border-[#28283c] rounded-2xl p-6 sm:p-8 max-w-md w-full shadow-2xl space-y-5 relative">
            <button
              onClick={() => setIsScheduleOpen(false)}
              className="absolute top-5 right-5 text-[#94a3b8] hover:text-white transition-colors"
            >
              <X size={18} />
            </button>

            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-amber-500/15 border border-amber-500/30 flex items-center justify-center text-amber-400">
                <Calendar size={20} />
              </div>
              <div>
                <h3 className="font-headline font-bold text-base text-white">Book Appointment</h3>
                <p className="text-xs text-[#94a3b8]">Schedule dock visit for {activeTenant.name}</p>
              </div>
            </div>

            <form onSubmit={handleScheduleAppointment} className="space-y-4">
              <div>
                <label className="text-[11px] font-mono uppercase tracking-wider text-[#94a3b8] block mb-1.5 font-bold">
                  Supplier Partner
                </label>
                <select
                  value={supplierId}
                  onChange={(e) => setSupplierId(e.target.value)}
                  className="w-full px-3.5 py-2 rounded-xl bg-[#10101a] border border-[#28283c] text-xs text-white focus:border-amber-400 focus:outline-none"
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
                <label className="text-[11px] font-mono uppercase tracking-wider text-[#94a3b8] block mb-1.5 font-bold">
                  Date & Time Slot
                </label>
                <input
                  type="datetime-local"
                  required
                  value={appointmentDate}
                  onChange={(e) => setAppointmentDate(e.target.value)}
                  className="w-full px-3.5 py-2 rounded-xl bg-[#10101a] border border-[#28283c] text-xs text-white focus:border-amber-400 focus:outline-none"
                />
              </div>

              <div>
                <label className="text-[11px] font-mono uppercase tracking-wider text-[#94a3b8] block mb-1.5 font-bold">
                  Meeting Purpose / Dock Task
                </label>
                <input
                  type="text"
                  required
                  value={purpose}
                  onChange={(e) => setPurpose(e.target.value)}
                  placeholder="e.g. Stock delivery verification & quality testing"
                  className="w-full px-3.5 py-2 rounded-xl bg-[#10101a] border border-[#28283c] text-xs text-white focus:border-amber-400 focus:outline-none"
                />
              </div>

              {formError && (
                <div className="text-xs text-red-400 bg-red-500/10 border border-red-500/30 rounded-xl p-2.5">
                  {formError}
                </div>
              )}

              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setIsScheduleOpen(false)}
                  className="px-4 py-2 rounded-xl text-xs font-medium text-[#94a3b8] hover:text-white bg-[#181826] border border-[#28283c]"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="px-5 py-2 rounded-xl bg-amber-500 hover:bg-amber-400 text-black text-xs font-bold transition-colors disabled:opacity-50"
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
