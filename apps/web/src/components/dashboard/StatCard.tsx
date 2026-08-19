"use client";

import { type ReactNode } from "react";

interface StatCardProps {
  title: string;
  value: string | number;
  icon: ReactNode;
  trend?: { value: string; positive: boolean };
  subtitle?: string;
  accent?: "primary" | "secondary" | "tertiary" | "neutral";
  className?: string;
}

export default function StatCard({ title, value, icon, trend, subtitle, accent = "neutral", className = "" }: StatCardProps) {
  const accentColors = {
    primary: { bg: "bg-[#ff2d78]/10", text: "text-[#ff2d78]", border: "border-[#ff2d78]/30", glow: "hover:shadow-[0_0_24px_rgba(255,45,120,0.15)]" },
    secondary: { bg: "bg-[#00ffcc]/10", text: "text-[#00ffcc]", border: "border-[#00ffcc]/30", glow: "hover:shadow-[0_0_24px_rgba(0,255,204,0.15)]" },
    tertiary: { bg: "bg-[#ffe04a]/10", text: "text-[#ffe04a]", border: "border-[#ffe04a]/30", glow: "hover:shadow-[0_0_24px_rgba(255,224,74,0.15)]" },
    neutral: { bg: "bg-[#e8e0f0]/10", text: "text-[#e8e0f0]", border: "border-[#e8e0f0]/30", glow: "hover:shadow-[0_0_24px_rgba(232,224,240,0.1)]" },
  };

  const colors = accentColors[accent];

  return (
    <div
      className={`
        relative overflow-hidden rounded-2xl border bg-[#141422]/60 p-5 transition-all duration-300
        ${colors.border} ${colors.glow} group
        ${className}
      `}
    >
      <div className="flex items-start justify-between mb-3">
        <div className={`p-2.5 rounded-xl ${colors.bg} ${colors.text}`}>
          {icon}
        </div>
        {trend && (
          <span
            className={`
              text-[11px] font-bold px-2.5 py-1 rounded-full border
              ${trend.positive ? "text-success-400 border-success-500/30 bg-success-500/10" : "text-danger-400 border-danger-500/30 bg-danger-500/10"}
            `}
          >
            {trend.positive ? "↑" : "↓"} {trend.value}
          </span>
        )}
      </div>

      <p className="text-[11px] font-medium text-[#a098b0] uppercase tracking-[0.15em] mb-1">{title}</p>
      <p className="text-3xl font-bold text-[#e8e0f0] tracking-tight">{value}</p>
      {subtitle && <p className="text-[10px] text-[#a098b0] font-mono mt-1">{subtitle}</p>}

      <div
        className="absolute -bottom-4 -right-4 w-24 h-24 rounded-full opacity-[0.03] group-hover:opacity-[0.07] transition-opacity"
        style={{ backgroundColor: colors.text.replace("text-", "bg-").replace("]", "").replace("[#", "#") }}
      />
    </div>
  );
}
