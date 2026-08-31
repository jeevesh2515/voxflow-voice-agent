"use client";
import { type ReactNode } from "react";
interface StatCardProps { title: string; value: string | number; icon: ReactNode; trend?: { value: string; positive: boolean }; subtitle?: string; accent?: "primary" | "secondary" | "tertiary" | "neutral"; className?: string; }
export default function StatCard({ title, value, icon, trend, subtitle, accent = "neutral", className = "" }: StatCardProps) {
  const m = {
    primary: { bg: "bg-[#ff2d78]/10", text: "text-[#ff2d78]", border: "border-[#ff2d78]/20", glow: "hover:shadow-[0_0_20px_rgba(255,45,120,0.12)]" },
    secondary: { bg: "bg-[#00ffcc]/10", text: "text-[#00ffcc]", border: "border-[#00ffcc]/20", glow: "hover:shadow-[0_0_20px_rgba(0,255,204,0.12)]" },
    tertiary: { bg: "bg-[#f59e0b]/10", text: "text-[#f59e0b]", border: "border-[#f59e0b]/20", glow: "hover:shadow-[0_0_20px_rgba(245,158,11,0.12)]" },
    neutral: { bg: "bg-white/[0.06]", text: "text-[#f8fafc]", border: "border-white/[0.06]", glow: "" },
  }[accent];
  return (
    <div className={`relative overflow-hidden rounded-2xl border bg-[#0f0f1c]/80 backdrop-blur-2xl p-4 transition-all duration-300 ${m.border} ${m.glow} ${className}`}>
      <div className="flex items-start justify-between mb-2.5">
        <div className={`p-2 rounded-xl ${m.bg} ${m.text} border border-white/[0.04]`}>{icon}</div>
        {trend && (<span className={`text-[11px] font-bold px-2 py-1 rounded-full border ${trend.positive ? "text-[#00ffcc] border-[#00ffcc]/20 bg-[#00ffcc]/10" : "text-[#ff2d78] border-[#ff2d78]/20 bg-[#ff2d78]/10"}`}>{trend.positive ? "↑" : "↓"} {trend.value}</span>)}
      </div>
      <p className="text-[11px] font-semibold tracking-[0.12em] uppercase text-[#64748b] mb-1">{title}</p>
      <p className="text-[22px] font-bold tracking-tight text-[#f8fafc] leading-none">{value}</p>
      {subtitle && <p className="text-[11px] font-mono text-[#94a3b8] mt-1">{subtitle}</p>}
    </div>
  );
}
