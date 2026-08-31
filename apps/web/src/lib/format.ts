export function fmtTime(iso: string | null | undefined): string {
  if (!iso) return "—";
  const d = new Date(iso);
  return d.toLocaleString("en-IN", { timeZone: "Asia/Kolkata", hour12: false });
}

export function fmtRelative(iso: string | null | undefined): string {
  if (!iso) return "—";
  const ms = Date.now() - new Date(iso).getTime();
  const s = Math.floor(ms / 1000);
  if (s < 60) return `${s}s ago`;
  const m = Math.floor(s / 60);
  if (m < 60) return `${m}m ago`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h}h ago`;
  const d = Math.floor(h / 24);
  return `${d}d ago`;
}

export function fmtDuration(sec: number): string {
  const m = Math.floor(sec / 60);
  const s = sec % 60;
  return `${m}:${s.toString().padStart(2, "0")}`;
}

export function statusColor(status: string): string {
  const s = status.toLowerCase();
  if (["shipped", "delivered", "resolved", "confirmed"].includes(s)) return "text-success-500";
  if (["in_transit", "out_for_delivery", "in_progress", "pending"].includes(s)) return "text-warn-500";
  if (["cancelled", "delayed", "escalated", "abandoned", "error"].includes(s)) return "text-danger-500";
  return "text-ink-300";
}

export function statusBg(status: string): string {
  const s = status.toLowerCase();
  if (["shipped", "delivered", "resolved", "confirmed"].includes(s)) return "bg-success-500/10 border-success-500/30";
  if (["in_transit", "out_for_delivery", "in_progress", "pending"].includes(s)) return "bg-warn-500/10 border-warn-500/30";
  if (["cancelled", "delayed", "escalated", "abandoned", "error"].includes(s)) return "bg-danger-500/10 border-danger-500/30";
  return "bg-ink-700/40 border-ink-600/40";
}
