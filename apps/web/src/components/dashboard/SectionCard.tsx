"use client";
import { type ReactNode } from "react";
interface SectionCardProps {
  title: string;
  subtitle?: string;
  icon?: ReactNode;
  action?: ReactNode;
  children: ReactNode;
  className?: string;
  accent?: "primary" | "secondary" | "neutral";
}
export default function SectionCard({ title, subtitle, icon, action, children, className = "", accent = "neutral" }: SectionCardProps) {
  const accentBorder = accent === "primary" ? "border-[#ff2d78]/15" : accent === "secondary" ? "border-[#00ffcc]/15" : "border-white/[0.06]";
  const isTable = className.includes("no-pad");
  return (
    <div className={`rounded-2xl border bg-[#0f0f1c]/80 backdrop-blur-2xl overflow-hidden ${accentBorder} ${className.replace("no-pad","")}`}>
      {(title || action) && (
        <div className="px-4 sm:px-5 py-3.5 border-b border-white/[0.06] flex items-center justify-between gap-4 bg-[#07070e]/40">
          <div className="flex items-center gap-2.5 min-w-0">
            {icon && <span className="shrink-0 text-[#94a3b8]">{icon}</span>}
            <div className="min-w-0">
              {title && <h3 className="font-bold text-[#f8fafc] text-[13px] tracking-tight truncate">{title}</h3>}
              {subtitle && <p className="text-[11px] text-[#94a3b8] truncate">{subtitle}</p>}
            </div>
          </div>
          {action && <div className="shrink-0 flex items-center gap-2">{action}</div>}
        </div>
      )}
      <div className={isTable ? "p-0" : "p-4 sm:p-5"}>{children}</div>
    </div>
  );
}
