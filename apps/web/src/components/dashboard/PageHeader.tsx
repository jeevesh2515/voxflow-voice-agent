"use client";

import { type ReactNode } from "react";

interface PageHeaderProps {
  title: string;
  subtitle?: string;
  action?: ReactNode;
  badge?: { label: string; color?: "primary" | "secondary" | "danger" | "warn" };
}

export default function PageHeader({ title, subtitle, action, badge }: PageHeaderProps) {
  const badgeColors = {
    primary: "text-[#ff2d78] border-[#ff2d78]/30 bg-[#ff2d78]/10",
    secondary: "text-[#00ffcc] border-[#00ffcc]/30 bg-[#00ffcc]/10",
    danger: "text-[#ff4444] border-[#ff4444]/30 bg-[#ff4444]/10",
    warn: "text-[#ffe04a] border-[#ffe04a]/30 bg-[#ffe04a]/10",
  };

  return (
    <div className="px-6 pt-6 pb-4 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
      <div className="flex items-center gap-3">
        <div>
          <div className="flex items-center gap-3 flex-wrap">
            <h1 className="text-xl font-bold text-[#e8e0f0]">{title}</h1>
            {badge && (
              <span className={`text-[10px] font-bold px-2.5 py-1 rounded-full border ${badgeColors[badge.color || "secondary"]}`}>
                {badge.label}
              </span>
            )}
          </div>
          {subtitle && <p className="text-xs text-[#a098b0] mt-1">{subtitle}</p>}
        </div>
      </div>
      {action && <div className="shrink-0">{action}</div>}
    </div>
  );
}
