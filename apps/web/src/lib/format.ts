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
  if (["delivered", "shipped", "resolved", "confirmed", "completed"].includes(s)) return "text-[#00ffcc]";
  if (["in_transit", "out_for_delivery", "in_progress"].includes(s)) return "text-[#00ffcc]";
  if (["pending", "escalated"].includes(s)) return "text-[#f59e0b]";
  if (["past_due", "breached", "cancelled", "delayed", "abandoned", "error"].includes(s)) return "text-[#ef4444]";
  return "text-[#94a3b8]";
}
export function statusBg(status: string): string {
  const s = status.toLowerCase();
  if (["delivered", "shipped", "resolved", "confirmed", "completed"].includes(s)) return "bg-[#00ffcc]/10 border-[#00ffcc]/20";
  if (["in_transit", "out_for_delivery", "in_progress"].includes(s)) return "bg-[#00ffcc]/10 border-[#00ffcc]/20";
  if (["pending", "escalated"].includes(s)) return "bg-[#f59e0b]/10 border-[#f59e0b]/20";
  if (["past_due", "breached", "cancelled", "delayed", "abandoned", "error"].includes(s)) return "bg-[#ef4444]/10 border-[#ef4444]/20";
  return "bg-white/[0.04] border-white/[0.06]";
}
export function copyId(id: string) {
  if (typeof navigator !== "undefined" && navigator.clipboard) navigator.clipboard.writeText(id);
}
