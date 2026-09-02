/**
 * Terminal-style notched section divider.
 *
 * The signature transition between open space and an industrial panel: a
 * sheet-like container with large convex top corners, a centered drag-handle
 * pill, and a hairline signal gradient that lights the seam.
 *
 * Applied sparingly — it is a transition accent, so it belongs on the first
 * content section after the hero and at major panel boundaries, not on every
 * section.
 */
export default function NotchedContainer({
  children,
  className = "",
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <div
      className={`relative w-full rounded-t-[2.5rem] border-x border-t border-white/[0.08] bg-[#080911] shadow-[0_-24px_80px_rgba(0,0,0,0.8)] ${className}`}
    >
      {/* Signal seam across the top edge. */}
      <div
        className="absolute -top-[1px] left-1/2 h-[3px] w-48 -translate-x-1/2 bg-gradient-to-r from-transparent via-[#00ffcc] to-transparent sm:w-64"
        aria-hidden="true"
      />
      {/* Drag-handle notch. */}
      <div
        className="absolute -top-3 left-1/2 h-1.5 w-8 -translate-x-1/2 rounded-full bg-white/20"
        aria-hidden="true"
      />
      {children}
    </div>
  );
}
