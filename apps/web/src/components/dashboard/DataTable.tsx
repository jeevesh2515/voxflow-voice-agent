"use client";

import { type ReactNode } from "react";
import clsx from "clsx";

interface DataTableProps<T> {
  columns: {
    key: string;
    label: string;
    render?: (item: T) => ReactNode;
    className?: string;
  }[];
  data: T[];
  keyExtractor: (item: T) => string;
  emptyState?: ReactNode;
  loading?: boolean;
  loadingRows?: number;
  onRowClick?: (item: T) => void;
  headerClassName?: string;
  rowClassName?: string;
}

export default function DataTable<T>({
  columns,
  data,
  keyExtractor,
  emptyState,
  loading = false,
  loadingRows = 5,
  onRowClick,
  headerClassName = "",
  rowClassName = "",
}: DataTableProps<T>) {
  const defaultEmpty = (
    <tr>
      <td colSpan={columns.length} className="px-4 py-12 text-center text-sm text-[#5a5068]">
        No data found
      </td>
    </tr>
  );

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-left border-collapse">
        <thead>
          <tr className={clsx("bg-[#0a0a12]/60 text-[10px] font-mono uppercase tracking-widest text-[#a098b0] border-b border-[#302840]/60", headerClassName)}>
            {columns.map((col) => (
              <th key={col.key} className={clsx("px-4 py-3 font-medium", col.className)}>
                {col.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-[#302840]/30">
          {loading
            ? Array.from({ length: loadingRows }).map((_, i) => (
                <tr key={i} className={rowClassName}>
                  {columns.map((col) => (
                    <td key={col.key} className="px-4 py-3">
                      <div className="h-4 bg-[#302840]/30 rounded animate-pulse w-full max-w-[120px]" />
                    </td>
                  ))}
                </tr>
              ))
            : data.map((item) => (
                <tr
                  key={keyExtractor(item)}
                  onClick={() => onRowClick?.(item)}
                  className={clsx(
                    "transition-colors",
                    onRowClick ? "cursor-pointer hover:bg-[#1e1e30]/40" : "hover:bg-[#1e1e30]/20",
                    rowClassName
                  )}
                >
                  {columns.map((col) => (
                    <td key={col.key} className={clsx("px-4 py-3 text-sm align-middle", col.className)}>
                      {col.render ? col.render(item) : (item as any)[col.key]}
                    </td>
                  ))}
                </tr>
              ))}
          {!loading && data.length === 0 && (emptyState || defaultEmpty)}
        </tbody>
      </table>
    </div>
  );
}
