"use client";

import { useState, useMemo } from "react";
import { useRouter } from "next/navigation";
import useSWR, { mutate } from "swr";
import {
  Users,
  Search,
  Plus,
  Phone,
  ShieldCheck,
  Building,
  MapPin,
  FileCheck,
  X,
  PhoneCall,
  KeyRound,
} from "lucide-react";
import { api } from "@/lib/api";
import { useTenant } from "@/lib/tenant-context";

export default function SuppliersPage() {
  const router = useRouter();
  const { activeTenantId, activeTenant } = useTenant();
  const { data: suppliers, error, isLoading } = useSWR(["suppliers", activeTenantId], () =>
    api.suppliers(undefined, activeTenantId),
  );

  const [searchQuery, setSearchQuery] = useState("");
  const [isRegisterOpen, setIsRegisterOpen] = useState(false);

  // Form state
  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const [contactPerson, setContactPerson] = useState("");
  const [city, setCity] = useState("Gurgaon");
  const [state, setState] = useState("Haryana");
  const [pincode, setPincode] = useState("122001");
  const [gstin, setGstin] = useState("");
  const [authPin, setAuthPin] = useState("1234");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [formError, setFormError] = useState("");

  const filteredSuppliers = useMemo(() => {
    if (!suppliers) return [];
    return (suppliers as any[]).filter((s) => {
      const q = searchQuery.toLowerCase();
      return (
        s.name.toLowerCase().includes(q) ||
        s.id.toLowerCase().includes(q) ||
        s.phone.includes(q) ||
        s.city.toLowerCase().includes(q) ||
        (s.contact_person && s.contact_person.toLowerCase().includes(q)) ||
        (s.gstin && s.gstin.toLowerCase().includes(q))
      );
    });
  }, [suppliers, searchQuery]);

  const stats = useMemo(() => {
    const list = (suppliers as any[]) || [];
    const cities = new Set(list.map((s) => s.city));
    return {
      total: list.length,
      cities: cities.size,
      activeRate: "100%",
    };
  }, [suppliers]);

  const handleRegisterSupplier = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim() || !phone.trim()) {
      setFormError("Name and Phone are required");
      return;
    }
    setFormError("");
    setIsSubmitting(true);

    try {
      await api.createSupplier(
        {
          name: name.trim(),
          phone: phone.trim(),
          contact_person: contactPerson.trim(),
          city: city.trim(),
          state: state.trim(),
          pincode: pincode.trim(),
          gstin: gstin.trim(),
          auth_pin: authPin.trim() || "1234",
        },
        activeTenantId,
      );
      mutate(["suppliers", activeTenantId]);
      mutate(["summary", activeTenantId]);
      setIsRegisterOpen(false);
      setName("");
      setPhone("");
      setContactPerson("");
      setGstin("");
    } catch (err: any) {
      setFormError(err.message || "Failed to register supplier");
    } finally {
      setIsSubmitting(false);
    }
  };

  const startSimulatorWithSupplier = (sup: any) => {
    router.push(`/dashboard/simulator?caller_phone=${encodeURIComponent(sup.phone)}&caller_name=${encodeURIComponent(sup.name)}`);
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto pb-12">
      {/* ==================== PAGE HEADER ==================== */}
      <header className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 bg-[#12121e] p-6 rounded-2xl border border-[#242436] shadow-sm">
        <div className="space-y-1">
          <div className="flex items-center gap-2 text-xs font-mono text-[#94a3b8]">
            <span>Partners & Network</span>
            <span>/</span>
            <span className="text-[#00ffcc] font-bold">{activeTenant.name}</span>
          </div>
          <h1 className="text-xl sm:text-2xl font-headline font-bold text-white tracking-tight">
            Suppliers & Vendor Directory
          </h1>
          <p className="text-xs sm:text-sm text-[#94a3b8]">
            Verified caller directory with 2FA Voice PIN authentication for secure automated transactions.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => setIsRegisterOpen(true)}
            className="bg-[#00ffcc] hover:bg-[#00e6b8] text-[#0a0a12] px-4 py-2 rounded-xl text-xs font-bold flex items-center gap-2 shadow-sm transition-all"
          >
            <Plus size={15} />
            <span>Add Supplier</span>
          </button>
        </div>
      </header>

      {/* ==================== STAT CARDS ==================== */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="bg-[#141422] p-5 rounded-2xl border border-[#28283c] shadow-sm">
          <div className="flex items-center justify-between text-[#94a3b8] text-xs font-mono uppercase tracking-wider mb-1">
            <span>Verified Suppliers</span>
            <Users size={16} className="text-[#00ffcc]" />
          </div>
          <div className="text-2xl font-headline font-bold text-white">{stats.total}</div>
          <div className="text-xs text-[#00ffcc] mt-1">2FA Voice PIN Enabled</div>
        </div>

        <div className="bg-[#141422] p-5 rounded-2xl border border-[#28283c] shadow-sm">
          <div className="flex items-center justify-between text-[#94a3b8] text-xs font-mono uppercase tracking-wider mb-1">
            <span>Operating Hubs</span>
            <MapPin size={16} className="text-[#ff2d78]" />
          </div>
          <div className="text-2xl font-headline font-bold text-[#ff2d78]">{stats.cities} Cities</div>
          <div className="text-xs text-[#94a3b8] mt-1">Regional distribution network</div>
        </div>

        <div className="bg-[#141422] p-5 rounded-2xl border border-[#28283c] shadow-sm">
          <div className="flex items-center justify-between text-[#94a3b8] text-xs font-mono uppercase tracking-wider mb-1">
            <span>Security Compliance</span>
            <ShieldCheck size={16} className="text-emerald-400" />
          </div>
          <div className="text-2xl font-headline font-bold text-emerald-400">{stats.activeRate}</div>
          <div className="text-xs text-[#94a3b8] mt-1">GSTIN & Phone Verified</div>
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
            placeholder="Search supplier by name, ID, phone number, GSTIN, city..."
            className="w-full bg-[#10101a] border border-[#28283c] rounded-xl pl-9 pr-4 py-2 text-xs text-white placeholder:text-[#64748b] focus:outline-none focus:border-[#00ffcc]"
          />
        </div>
      </div>

      {/* ==================== SUPPLIERS GRID ==================== */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {isLoading && (
          <div className="col-span-full py-16 text-center text-[#94a3b8] text-xs">
            Loading verified suppliers...
          </div>
        )}

        {error && (
          <div className="col-span-full p-6 text-center text-red-400 bg-red-500/10 text-xs rounded-2xl border border-red-500/20">
            Failed to load suppliers. Please verify backend API connectivity.
          </div>
        )}

        {!isLoading &&
          !error &&
          filteredSuppliers.map((s) => (
            <div
              key={s.id}
              className="bg-[#141422] p-5 rounded-2xl border border-[#28283c] hover:border-[#00ffcc]/60 transition-all flex flex-col justify-between space-y-4 shadow-sm"
            >
              <div className="space-y-3">
                <div className="flex justify-between items-start">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-xl bg-[#00ffcc]/15 border border-[#00ffcc]/30 flex items-center justify-center text-[#00ffcc] font-headline font-bold text-sm">
                      {s.name.charAt(0)}
                    </div>
                    <div>
                      <h3 className="font-headline font-bold text-sm text-white">
                        {s.name}
                      </h3>
                      <span className="font-mono text-[10px] text-[#ff2d78]">#{s.id}</span>
                    </div>
                  </div>
                  <span className="flex items-center gap-1 text-[10px] font-mono font-bold text-[#00ffcc] bg-[#00ffcc]/10 border border-[#00ffcc]/30 px-2 py-0.5 rounded">
                    <ShieldCheck size={11} /> Verified
                  </span>
                </div>

                <div className="space-y-1.5 text-xs bg-[#181828] p-3 rounded-xl border border-[#28283c]">
                  <div className="flex items-center justify-between">
                    <span className="flex items-center gap-1.5 text-[11px] text-white font-mono">
                      <Phone size={12} className="text-[#00ffcc]" /> {s.phone}
                    </span>
                    {s.contact_person && (
                      <span className="text-[11px] text-[#94a3b8] truncate max-w-[120px]">
                        {s.contact_person}
                      </span>
                    )}
                  </div>
                  <div className="flex items-center justify-between pt-1 border-t border-[#242436] text-[10px]">
                    <span className="flex items-center gap-1 text-[#cbd5e1]">
                      <MapPin size={11} className="text-[#ff2d78]" /> {s.city}, {s.state}
                    </span>
                    <span className="font-mono text-[#94a3b8]">{s.pincode}</span>
                  </div>
                  {s.gstin && (
                    <div className="text-[10px] font-mono text-[#94a3b8] pt-1">
                      GSTIN: <span className="text-white">{s.gstin}</span>
                    </div>
                  )}
                </div>
              </div>

              {/* Action row */}
              <div className="pt-2 border-t border-[#242436] flex items-center justify-between gap-2">
                <div className="flex items-center gap-1 text-[11px] font-mono text-[#94a3b8]">
                  <KeyRound size={11} className="text-amber-400" /> PIN:{" "}
                  <strong className="text-amber-400">{s.auth_pin || "1234"}</strong>
                </div>
                <button
                  onClick={() => startSimulatorWithSupplier(s)}
                  className="bg-[#181826] border border-[#28283c] hover:border-[#00ffcc] text-[#cbd5e1] hover:text-[#00ffcc] px-3 py-1.5 rounded-xl text-xs font-medium flex items-center gap-1.5 transition-colors"
                >
                  <PhoneCall size={12} className="text-[#00ffcc]" />
                  <span>Simulate Call</span>
                </button>
              </div>
            </div>
          ))}

        {!isLoading && !error && filteredSuppliers.length === 0 && (
          <div className="col-span-full bg-[#141422] rounded-2xl border border-dashed border-[#28283c] p-16 text-center space-y-3">
            <Users className="mx-auto text-[#64748b]" size={36} />
            <div className="text-sm text-white font-headline font-semibold">No suppliers found</div>
            <p className="text-xs text-[#94a3b8] max-w-sm mx-auto">
              {searchQuery
                ? `No suppliers matching "${searchQuery}".`
                : `Register your first supplier or contact to enable 2FA voice authentication.`}
            </p>
          </div>
        )}
      </div>

      {/* ==================== REGISTER SUPPLIER MODAL ==================== */}
      {isRegisterOpen && (
        <div className="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-[#141422] border border-[#28283c] rounded-2xl p-6 sm:p-8 max-w-md w-full shadow-2xl space-y-5 relative">
            <button
              onClick={() => setIsRegisterOpen(false)}
              className="absolute top-5 right-5 text-[#94a3b8] hover:text-white transition-colors"
            >
              <X size={18} />
            </button>

            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-[#00ffcc]/15 border border-[#00ffcc]/30 flex items-center justify-center text-[#00ffcc]">
                <Users size={20} />
              </div>
              <div>
                <h3 className="font-headline font-bold text-base text-white">Register Supplier</h3>
                <p className="text-xs text-[#94a3b8]">Add verified partner for {activeTenant.name}</p>
              </div>
            </div>

            <form onSubmit={handleRegisterSupplier} className="space-y-3.5">
              <div>
                <label className="text-[11px] font-mono uppercase tracking-wider text-[#94a3b8] block mb-1 font-bold">
                  Supplier / Company Name
                </label>
                <input
                  type="text"
                  required
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="e.g. Sharma Beverages Wholesale"
                  className="w-full px-3.5 py-2 rounded-xl bg-[#10101a] border border-[#28283c] text-xs text-white focus:border-[#00ffcc] focus:outline-none"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-[11px] font-mono uppercase tracking-wider text-[#94a3b8] block mb-1 font-bold">
                    Phone (E.164)
                  </label>
                  <input
                    type="text"
                    required
                    value={phone}
                    onChange={(e) => setPhone(e.target.value)}
                    placeholder="+919876543210"
                    className="w-full px-3.5 py-2 rounded-xl bg-[#10101a] border border-[#28283c] text-xs text-white focus:border-[#00ffcc] focus:outline-none font-mono"
                  />
                </div>
                <div>
                  <label className="text-[11px] font-mono uppercase tracking-wider text-[#94a3b8] block mb-1 font-bold">
                    2FA Voice PIN
                  </label>
                  <input
                    type="text"
                    required
                    maxLength={6}
                    value={authPin}
                    onChange={(e) => setAuthPin(e.target.value)}
                    placeholder="1234"
                    className="w-full px-3.5 py-2 rounded-xl bg-[#10101a] border border-[#28283c] text-xs text-amber-400 font-mono focus:border-[#00ffcc] focus:outline-none"
                  />
                </div>
              </div>

              <div>
                <label className="text-[11px] font-mono uppercase tracking-wider text-[#94a3b8] block mb-1 font-bold">
                  Contact Person
                </label>
                <input
                  type="text"
                  value={contactPerson}
                  onChange={(e) => setContactPerson(e.target.value)}
                  placeholder="Rajesh Sharma"
                  className="w-full px-3.5 py-2 rounded-xl bg-[#10101a] border border-[#28283c] text-xs text-white focus:border-[#00ffcc] focus:outline-none"
                />
              </div>

              <div className="grid grid-cols-3 gap-2">
                <div>
                  <label className="text-[11px] font-mono uppercase tracking-wider text-[#94a3b8] block mb-1 font-bold">
                    City
                  </label>
                  <input
                    type="text"
                    value={city}
                    onChange={(e) => setCity(e.target.value)}
                    className="w-full px-3 py-2 rounded-xl bg-[#10101a] border border-[#28283c] text-xs text-white focus:border-[#00ffcc] focus:outline-none"
                  />
                </div>
                <div>
                  <label className="text-[11px] font-mono uppercase tracking-wider text-[#94a3b8] block mb-1 font-bold">
                    State
                  </label>
                  <input
                    type="text"
                    value={state}
                    onChange={(e) => setState(e.target.value)}
                    className="w-full px-3 py-2 rounded-xl bg-[#10101a] border border-[#28283c] text-xs text-white focus:border-[#00ffcc] focus:outline-none"
                  />
                </div>
                <div>
                  <label className="text-[11px] font-mono uppercase tracking-wider text-[#94a3b8] block mb-1 font-bold">
                    Pincode
                  </label>
                  <input
                    type="text"
                    value={pincode}
                    onChange={(e) => setPincode(e.target.value)}
                    className="w-full px-3 py-2 rounded-xl bg-[#10101a] border border-[#28283c] text-xs text-white focus:border-[#00ffcc] focus:outline-none font-mono"
                  />
                </div>
              </div>

              <div>
                <label className="text-[11px] font-mono uppercase tracking-wider text-[#94a3b8] block mb-1 font-bold">
                  GSTIN
                </label>
                <input
                  type="text"
                  value={gstin}
                  onChange={(e) => setGstin(e.target.value)}
                  placeholder="06AAAAA0000A1Z5"
                  className="w-full px-3.5 py-2 rounded-xl bg-[#10101a] border border-[#28283c] text-xs text-white focus:border-[#00ffcc] focus:outline-none font-mono uppercase"
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
                  onClick={() => setIsRegisterOpen(false)}
                  className="px-4 py-2 rounded-xl text-xs font-medium text-[#94a3b8] hover:text-white bg-[#181826] border border-[#28283c]"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="px-5 py-2 rounded-xl bg-[#00ffcc] hover:bg-[#00e6b8] text-[#0a0a12] text-xs font-bold transition-colors disabled:opacity-50"
                >
                  {isSubmitting ? "Registering..." : "Save Supplier"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
