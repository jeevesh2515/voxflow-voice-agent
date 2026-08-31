"use client";
import { type ReactNode, useState } from "react";
import clsx from "clsx";
interface DataTableProps<T> {
  columns: { key: string; label: string; render?: (item: T) => ReactNode; className?: string }[];
  data: T[];
  keyExtractor: (item: T) => string;
  emptyState?: ReactNode;
  loading?: boolean;
  loadingRows?: number;
  onRowClick?: (item: T) => void;
  headerClassName?: string;
  rowClassName?: string;
}
export default function DataTable<T>({ columns, data, keyExtractor, emptyState, loading = false, loadingRows = 5, onRowClick, headerClassName = "", rowClassName = "" }: DataTableProps<T>) {
  const [copied, setCopied] = useState<string | null>(null);
  const doCopy = (v: string) => {
    navigator.clipboard?.writeText(v);
    setCopied(v);
    setTimeout(() => setCopied(null), 1200);
  };
  const defaultEmpty = (
    <div className="px-4 py-12 text-center text-sm text-[#64748b]">No data found</div>
  );
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-left border-collapse">
        <thead className="sticky top-0 z-10">
          <tr className={clsx("bg-[#07070e]/80 backdrop-blur-xl text-[11px] font-semibold tracking-[0.12em] uppercase text-[#64748b] border-b border-white/[0.06]", headerClassName)}>
            {columns.map((col) => (<th key={col.key} className={clsx("px-3 py-2.5 font-semibold whitespace-nowrap", col.className)}>{col.label}</th>))}
          </tr>
        </thead>
        <tbody className="divide-y divide-white/[0.04]">
          {loading ? Array.from({ length: loadingRows }).map((_, i) => (
            <tr key={i} className={rowClassName}>{columns.map((col) => (<td key={col.key} className="px-3 py-2.5"><div className="h-3.5 bg-white/[0.06] rounded animate-pulse w-full max-w-[110px]" /></td>))}</tr>
          )) : data.map((item) => (
            <tr key={keyExtractor(item)} onClick={() => onRowClick?.(item)} className={clsx("transition-colors group", onRowClick ? "cursor-pointer hover:bg-white/[0.04]" : "hover:bg-white/[0.03]", rowClassName)}>
              {columns.map((col) => (<td key={col.key} className={clsx("px-3 py-2.5 text-[13px] align-middle", col.className)}>{col.render ? col.render(item) : (item as any)[col.key]}</td>))}
            </tr>
          ))}
          {!loading && data.length === 0 && (
            <tr>
              <td colSpan={columns.length}>
                {emptyState || defaultEmpty}
              </td>
            </tr>
          )}
        </tbody>
      </table>
      {copied && <div className="fixed bottom-4 left-1/2 -translate-x-1/2 bg-[#0f0f1c] border border-white/[0.07] text-xs text-[#f8fafc] px-3 py-1.5 rounded-full shadow-lg z-50">Copied {copied.slice(0,12)}…</div>}
    </div>
  );
}
