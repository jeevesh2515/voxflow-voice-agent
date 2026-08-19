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
  const accentBorder = accent === "primary" ? "border-[#ff2d78]/20" : accent === "secondary" ? "border-[#00ffcc]/20" : "border-[#302840]/60";

  return (
    <div className={`rounded-2xl border bg-[#141422]/40 overflow-hidden ${accentBorder} ${className}`}>
      {(title || action) && (
        <div className="px-6 py-4 border-b border-[#302840]/40 flex items-center justify-between gap-4 bg-[#0f0f1a]/60">
          <div className="flex items-center gap-3">
            {icon && <span className="text-[#a098b0]">{icon}</span>}
            <div>
              {title && <h3 className="font-bold text-[#e8e0f0] text-base">{title}</h3>}
              {subtitle && <p className="text-xs text-[#a098b0] mt-0.5">{subtitle}</p>}
            </div>
          </div>
          {action && <div className="shrink-0">{action}</div>}
        </div>
      )}
      <div className="p-6">{children}</div>
    </div>
  );
}
