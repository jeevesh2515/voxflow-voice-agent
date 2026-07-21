"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowLeft, Circle } from "lucide-react";

export default function Topbar({ title, subtitle }: { title: string; subtitle?: string }) {
  const [now, setNow] = useState<string>("");
  const router = useRouter();

  useEffect(() => {
    const tick = () =>
      setNow(
        new Date().toLocaleTimeString("en-IN", {
          hour12: false, timeZone: "Asia/Kolkata",
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
          className="text-ink-400 hover:text-ink-50"
          aria-label="Back"
        >
          <ArrowLeft size={16} />
        </button>
        <div>
          <h1 className="text-base font-semibold text-ink-50 tracking-tight">{title}</h1>
          {subtitle && <p className="text-[11px] font-mono text-ink-400 uppercase tracking-wider">{subtitle}</p>}
        </div>
      </div>
      <div className="flex items-center gap-3 text-[11px] font-mono text-ink-400">
        <span className="flex items-center gap-1.5">
          <Circle size={8} className="text-success-500 fill-success-500 pulse-dot" />
          LIVE
        </span>
        <span className="text-ink-500">·</span>
        <span>{now} IST</span>
      </div>
    </header>
  );
}
