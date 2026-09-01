/**
 * Deep fixed-background parallax viewport.
 *
 * The starfield locks in place (sticky, not fixed — so it un-pins
 * naturally at the section boundary with no trap in either scroll direction)
 * while oversized typography glides over it under a heavy radial scrim.
 *
 * Pure CSS sticky + transform on the foreground. There is no scroll listener
 * here at all, which is exactly why reverse scrolling over it costs nothing.
 */
export default function ParallaxQuotes() {
  return (
    <section className="parallax-quotes relative min-h-[140svh] overflow-hidden border-y border-white/[0.08]" aria-label="Customer outcomes">
      {/* Signature Terminal Notched Header Seam */}
      <div className="absolute top-0 left-1/2 z-20 h-[3px] w-64 -translate-x-1/2 bg-gradient-to-r from-transparent via-[#00ffcc] to-transparent sm:w-96" aria-hidden="true" />
      <div className="absolute top-2 left-1/2 z-20 h-1.5 w-10 -translate-x-1/2 rounded-full bg-white/25 backdrop-blur-sm" aria-hidden="true" />

      {/* Locked background layer: Deep interstellar galaxy nebula backdrop */}
      <div className="parallax-quotes-backdrop sticky top-0 h-[100svh] overflow-hidden" aria-hidden="true">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src="/galaxy-nebula.jpg"
          alt=""
          className="absolute inset-0 h-full w-full object-cover opacity-75 transform scale-105 transition-transform duration-1000"
        />
        {/* Contrast scrim — dark obsidian vignette keeping text razor sharp */}
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,rgba(5,5,10,0.75)_0%,rgba(5,5,10,0.60)_50%,rgba(5,5,10,0.92)_100%)]" />
      </div>

      {/* Scrolling foreground. Negative top margin pulls it back over the bg. */}
      <div className="parallax-quotes-copy relative z-10 mx-auto -mt-[100svh] max-w-5xl space-y-48 px-6 py-[42svh]">
        <figure className="relative rounded-3xl border border-white/[0.08] bg-black/40 p-8 sm:p-12 backdrop-blur-md shadow-2xl">
          <div className="mb-4 inline-flex items-center gap-2 rounded-full border border-[#00ffcc]/30 bg-[#00ffcc]/10 px-3 py-1 font-mono text-[10px] uppercase tracking-widest text-[#00ffcc]">
            <span className="h-1.5 w-1.5 rounded-full bg-[#00ffcc] animate-pulse" />
            UK Logistics Deployment
          </div>
          <blockquote className="font-headline text-3xl font-extrabold leading-[1.15] tracking-tight text-white sm:text-5xl lg:text-6xl">
            &ldquo;We replaced 14 manual dispatcher queues with one autonomous
            voice signal.&rdquo;
          </blockquote>
          <figcaption className="mt-6 font-label text-xs uppercase tracking-[0.22em] text-[#a098b0]">
            — Fleet Operations, UK Logistics
          </figcaption>
        </figure>

        <figure className="relative rounded-3xl border border-white/[0.08] bg-black/40 p-8 sm:p-12 backdrop-blur-md shadow-2xl">
          <div className="mb-4 inline-flex items-center gap-2 rounded-full border border-[#ff2d78]/30 bg-[#ff2d78]/10 px-3 py-1 font-mono text-[10px] uppercase tracking-widest text-[#ff2d78]">
            <span className="h-1.5 w-1.5 rounded-full bg-[#ff2d78] animate-pulse" />
            Financial Return Velocity
          </div>
          <blockquote className="font-headline text-3xl font-extrabold leading-[1.15] tracking-tight text-white sm:text-5xl lg:text-6xl">
            &ldquo;Measurable payback in 14 days, without a capital
            infrastructure project.&rdquo;
          </blockquote>
          <figcaption className="mt-6 font-label text-xs uppercase tracking-[0.22em] text-[#a098b0]">
            — CFO, National Distribution Group
          </figcaption>
        </figure>
      </div>

      {/* Signature Terminal Bottom Notched Seam */}
      <div className="absolute bottom-0 left-1/2 z-20 h-[3px] w-64 -translate-x-1/2 bg-gradient-to-r from-transparent via-[#ff2d78] to-transparent sm:w-96" aria-hidden="true" />
      <div className="absolute bottom-2 left-1/2 z-20 h-1.5 w-10 -translate-x-1/2 rounded-full bg-white/25 backdrop-blur-sm" aria-hidden="true" />
    </section>
  );
}
