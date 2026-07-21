"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowLeft, Building2, Circle, ChevronDown } from "lucide-react";
import { useTenant } from "@/lib/tenant-context";

export default function Topbar({ title, subtitle }: { title: string; subtitle?: string }) {
  const [now, setNow] = useState<string>("");
  const router = useRouter();
  const { activeTenantId, activeTenant, tenants, setActiveTenantId } = useTenant();

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
        {/* Company / Tenant Selector */}
        <div className="relative flex items-center gap-2 bg-ink-800/60 border border-ink-700/80 rounded-md px-3 py-1.5 text-xs text-ink-200">
          <Building2 size={14} className="text-vox-400" />
          <select
            value={activeTenantId}
            onChange={(e) => setActiveTenantId(e.target.value)}
            className="bg-transparent text-ink-100 font-medium focus:outline-none cursor-pointer pr-4"
          >
            {tenants.map((t) => (
              <option key={t.id} value={t.id} className="bg-ink-900 text-ink-100">
                {t.name}
              </option>
            ))}
          </select>
        </div>

        <div className="flex items-center gap-3 text-[11px] font-mono text-ink-400">
          <span className="flex items-center gap-1.5">
            <Circle size={8} className="text-success-500 fill-success-500 pulse-dot" />
            LIVE
          </span>
          <span className="text-ink-500">·</span>
          <span>{now} IST</span>
        </div>
      </div>
    </header>
  );
}
