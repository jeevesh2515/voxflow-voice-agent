/**
 * Ambient rotating gradient wash for scroll sections below the hero.
 *
 * This implements the intent of a `background: linear-gradient(...)` +
 * `transform: rotate()` snippet — which, as commonly written, rotates the
 * element itself and spins its corners out of frame while repainting the
 * whole layer. The working version instead rotates an OVERSIZED conic layer
 * inside an overflow-hidden wrapper: rotation is compositor-only, the edges
 * never expose gaps, and content is never repainted.
 *
 * Palette honours the requested magenta pair (#c41271 / #a8005a) on the
 * obsidian base, kept dim so section copy stays pristine over it.
 */
export default function AmbientGradient({ className = "" }: { className?: string }) {
  return (
    <div
      className={`ambient-gradient pointer-events-none absolute inset-0 overflow-hidden ${className}`}
      aria-hidden="true"
    />
  );
}
