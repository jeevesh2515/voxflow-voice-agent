"use client";

/**
 * Continuous editorial parallax quotes section.
 *
 * Quotes glide over a deep cosmic galaxy nebula background with
 * generous vertical breathing room, high contrast typography,
 * and signature Terminal Industries notched accent seams.
 */
export default function ParallaxQuotes() {
  return (
    <section className="parallax-quotes relative min-h-[160vh] overflow-hidden border-y border-white/[0.08]" aria-label="Customer outcomes">
      {/* Signature Terminal Notched Header Seam */}
      <div className="absolute top-0 left-1/2 z-20 h-[3px] w-64 -translate-x-1/2 bg-gradient-to-r from-transparent via-[#00ffcc] to-transparent sm:w-96" aria-hidden="true" />
      <div className="absolute top-2.5 left-1/2 z-20 h-1.5 w-10 -translate-x-1/2 rounded-full bg-white/20 backdrop-blur-sm" aria-hidden="true" />

      {/* Locked background layer: Deep interstellar galaxy nebula backdrop */}
      <div className="parallax-quotes-backdrop sticky top-0 h-screen w-full overflow-hidden" aria-hidden="true">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src="/galaxy-nebula.jpg"
          alt=""
          className="absolute inset-0 h-full w-full object-cover opacity-80 scale-105"
        />
        {/* Contrast scrim — dark obsidian vignette keeping text razor sharp */}
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,rgba(4,6,12,0.82)_0%,rgba(4,6,12,0.65)_50%,rgba(4,6,12,0.95)_100%)]" />
      </div>

      {/* Scrolling foreground text with generous clearance below fixed header */}
      <div className="parallax-quotes-copy relative z-10 mx-auto -mt-[100vh] max-w-5xl px-6 pt-72 pb-64 space-y-64">
        <figure className="max-w-4xl">
          <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-[#00ffcc]/30 bg-black/60 px-3.5 py-1 font-mono text-[11px] uppercase tracking-widest text-[#00ffcc] backdrop-blur-md">
            <span className="h-1.5 w-1.5 rounded-full bg-[#00ffcc] animate-pulse" />
            UK Logistics Deployment
          </div>
          <blockquote className="font-headline text-3xl font-extrabold leading-[1.12] tracking-tight text-white sm:text-5xl lg:text-6xl drop-shadow-2xl">
            &ldquo;We replaced 14 manual dispatcher queues with one autonomous
            voice signal.&rdquo;
          </blockquote>
          <figcaption className="mt-8 font-label text-xs uppercase tracking-[0.24em] text-[#00ffcc]/90">
            — Fleet Operations, UK Logistics
          </figcaption>
        </figure>

        <figure className="max-w-4xl">
          <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-[#ff2d78]/30 bg-black/60 px-3.5 py-1 font-mono text-[11px] uppercase tracking-widest text-[#ff2d78] backdrop-blur-md">
            <span className="h-1.5 w-1.5 rounded-full bg-[#ff2d78] animate-pulse" />
            Financial Return Velocity
          </div>
          <blockquote className="font-headline text-3xl font-extrabold leading-[1.12] tracking-tight text-white sm:text-5xl lg:text-6xl drop-shadow-2xl">
            &ldquo;Measurable payback in 14 days, without a capital
            infrastructure project.&rdquo;
          </blockquote>
          <figcaption className="mt-8 font-label text-xs uppercase tracking-[0.24em] text-[#ff2d78]/90">
            — CFO, National Distribution Group
          </figcaption>
        </figure>
      </div>

      {/* Signature Terminal Bottom Notched Seam */}
      <div className="absolute bottom-0 left-1/2 z-20 h-[3px] w-64 -translate-x-1/2 bg-gradient-to-r from-transparent via-[#ff2d78] to-transparent sm:w-96" aria-hidden="true" />
      <div className="absolute bottom-2.5 left-1/2 z-20 h-1.5 w-10 -translate-x-1/2 rounded-full bg-white/20 backdrop-blur-sm" aria-hidden="true" />
    </section>
  );
}
