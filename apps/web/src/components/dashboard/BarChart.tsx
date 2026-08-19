"use client";

interface BarChartProps {
  data: { label: string; value: number; max?: number }[];
  height?: number;
  color?: string;
  showLabels?: boolean;
}

export default function BarChart({ data, height = 120, color = "#00ffcc", showLabels = true }: BarChartProps) {
  const maxVal = Math.max(...data.map((d) => d.value), 1);

  return (
    <div className="w-full">
      <div className="flex items-end gap-1.5" style={{ height }}>
        {data.map((item, idx) => {
          const pct = (item.value / maxVal) * 100;
          return (
            <div key={idx} className="flex-1 flex flex-col items-center gap-1.5 group">
              <div className="relative w-full flex items-end justify-center">
                <div
                  className="w-full max-w-[32px] rounded-t-md transition-all duration-500 group-hover:opacity-80"
                  style={{
                    height: `${pct}%`,
                    backgroundColor: color,
                    opacity: 0.3 + (pct / 100) * 0.7,
                    boxShadow: pct > 80 ? `0 0 12px ${color}40` : "none",
                  }}
                />
                {showLabels && (
                  <span className="absolute -top-6 text-[10px] font-mono text-[#a098b0] opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap">
                    {item.value}
                  </span>
                )}
              </div>
              {showLabels && (
                <span className="text-[9px] font-mono text-[#a098b0] uppercase tracking-wider truncate w-full text-center">
                  {item.label}
                </span>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
