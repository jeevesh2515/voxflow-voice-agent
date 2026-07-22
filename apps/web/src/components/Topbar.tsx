"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowLeft, Building2, Circle, Plus, LogOut } from "lucide-react";
import { useTenant } from "@/lib/tenant-context";

export default function Topbar({ title, subtitle }: { title: string; subtitle?: string }) {
  const [now, setNow] = useState<string>("");
  const [isAddingTenant, setIsAddingTenant] = useState(false);
  const [newCompanyName, setNewCompanyName] = useState("");

  const router = useRouter();
  const { activeTenantId, tenants, setActiveTenantId, addTenant } = useTenant();

  useEffect(() => {
    const tick = () =>
      setNow(
        new Date().toLocaleTimeString("en-IN", {
          hour12: false,
          timeZone: "Asia/Kolkata",
        }),
      );
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, []);

  const handleAddCompanySubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!newCompanyName.trim()) return;
    const created = addTenant(newCompanyName);
    setNewCompanyName("");
    setIsAddingTenant(false);
    setActiveTenantId(created.id);
  };

  const handleLogout = () => {
    localStorage.removeItem("voxflow_session");
    router.push("/sign-in");
  };

  return (
    <header className="border-b border-ink-700/60 bg-ink-900/40 px-6 py-3 flex items-center justify-between">
      <div className="flex items-center gap-3">
        <button
          onClick={() => router.push("/dashboard")}
          className="text-ink-400 hover:text-ink-50 p-1 rounded hover:bg-ink-800/60 transition-colors"
          aria-label="Back"
        >
          <ArrowLeft size={16} />
        </button>
        <div>
          <h1 className="text-base font-semibold text-ink-50 tracking-tight">{title}</h1>
          {subtitle && <p className="text-[11px] font-mono text-ink-400 uppercase tracking-wider">{subtitle}</p>}
        </div>
      </div>

      <div className="flex items-center gap-4">
        {/* Company / Tenant Selector & Add Action */}
        <div className="flex items-center gap-2">
          {isAddingTenant ? (
            <form onSubmit={handleAddCompanySubmit} className="flex items-center gap-1">
              <input
                type="text"
                autoFocus
                value={newCompanyName}
                onChange={(e) => setNewCompanyName(e.target.value)}
                placeholder="Company Name..."
                className="bg-ink-900 border border-vox-500/80 rounded px-2.5 py-1 text-xs text-ink-100 placeholder:text-ink-400 focus:outline-none"
              />
              <button
                type="submit"
                className="bg-vox-500 hover:bg-vox-400 text-ink-950 font-bold px-2 py-1 rounded text-xs"
              >
                Add
              </button>
              <button
                type="button"
                onClick={() => setIsAddingTenant(false)}
                className="text-ink-400 hover:text-ink-200 px-1 text-xs"
              >
                ✕
              </button>
            </form>
          ) : (
            <div className="flex items-center gap-1.5 bg-ink-800/60 border border-ink-700/80 rounded-md px-3 py-1.5 text-xs text-ink-200">
              <Building2 size={14} className="text-vox-400 shrink-0" />
              <select
                value={activeTenantId}
                onChange={(e) => setActiveTenantId(e.target.value)}
                className="bg-transparent text-ink-100 font-medium focus:outline-none cursor-pointer pr-2 max-w-[200px] truncate"
              >
                {tenants.map((t) => (
                  <option key={t.id} value={t.id} className="bg-ink-900 text-ink-100">
                    {t.name}
                  </option>
                ))}
              </select>
              <button
                type="button"
                onClick={() => setIsAddingTenant(true)}
                title="Add New Company Workspace"
                className="text-vox-400 hover:text-vox-300 p-0.5 rounded hover:bg-ink-700/50"
              >
                <Plus size={14} />
              </button>
            </div>
          )}
        </div>

        <div className="flex items-center gap-3 text-[11px] font-mono text-ink-400">
          <span className="flex items-center gap-1.5">
            <Circle size={8} className="text-success-500 fill-success-500 pulse-dot" />
            LIVE
          </span>
          <span className="text-ink-500">·</span>
          <span>{now} IST</span>
          <span className="text-ink-500">·</span>
          <button
            onClick={handleLogout}
            title="Log Out"
            className="flex items-center gap-1 text-ink-400 hover:text-vox-400 transition-colors"
          >
            <LogOut size={13} />
            Exit
          </button>
        </div>
      </div>
    </header>
  );
}
