"use client";

/**
 * Terminal Industries Inspired Editorial Quotes Section.
 *
 * Implements:
 * - Seamless interstellar cosmic backdrop with edge-to-edge gradient integration
 * - Mechanical crosshair markers (+) on grid junctions (Terminal Industries pattern)
 * - Large editorial typography with high contrast monospace telemetry badges
 * - Balanced multi-quote grid layout without awkward image voids or header clipping
 * - Scooped notched accent seams
 */
export default function ParallaxQuotes() {
  return (
    <section className="parallax-quotes relative overflow-hidden border-y border-white/[0.08] bg-[#04060c] py-28 sm:py-36 lg:py-44" aria-label="Production architecture specification">
      {/* Signature Terminal Notched Top Seam */}
      <div className="absolute top-0 left-1/2 z-20 h-[3px] w-64 -translate-x-1/2 bg-gradient-to-r from-transparent via-[#00ffcc] to-transparent sm:w-96" aria-hidden="true" />
      <div className="absolute top-2.5 left-1/2 z-20 h-1.5 w-10 -translate-x-1/2 rounded-full bg-white/20 backdrop-blur-sm" aria-hidden="true" />

      {/* Deep Interstellar Galaxy Backdrop */}
      <div className="absolute inset-0 pointer-events-none overflow-hidden" aria-hidden="true">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src="/galaxy-nebula.webp"
          alt=""
          loading="lazy"
          decoding="async"
          className="absolute inset-0 h-full w-full object-cover opacity-35 scale-105"
        />
        {/* Dark Obsidian Radial Scrim */}
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,rgba(4,6,12,0.65)_0%,rgba(4,6,12,0.92)_70%,rgba(4,6,12,1)_100%)]" />
        {/* Fine Technical Grid Lines */}
        <div className="absolute inset-0 bg-[linear-gradient(to_right,rgba(255,255,255,0.03)_1px,transparent_1px),linear-gradient(to_bottom,rgba(255,255,255,0.03)_1px,transparent_1px)] bg-[size:4rem_4rem]" />
      </div>

      <div className="relative z-10 mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        {/* Section Header with Crosshair Accent */}
        <div className="relative mb-20 max-w-3xl">
          <div className="mb-4 inline-flex items-center gap-2 rounded-full border border-[#00ffcc]/30 bg-black/60 px-4 py-1 font-mono text-[11px] uppercase tracking-[0.2em] text-[#00ffcc] backdrop-blur-md">
            <span className="h-1.5 w-1.5 rounded-full bg-[#00ffcc] animate-ping" />
            ENGINEERING // PRODUCTION ARCHITECTURE
          </div>
          <h2 className="font-headline text-3xl sm:text-5xl lg:text-6xl font-extrabold tracking-tight text-white leading-[1.08]">
            Engineered for mission-critical voice operations.
          </h2>
        </div>

        {/* 2-Column High-Impact Editorial Grid */}
        <div className="grid gap-12 lg:grid-cols-2 lg:gap-16 items-stretch">
          {/* Architecture Pillar 1 with Terminal Crosshairs */}
          <div className="relative flex flex-col justify-between rounded-3xl border border-white/[0.08] bg-black/50 p-8 sm:p-12 backdrop-blur-xl shadow-2xl transition-all duration-300 hover:border-[#00ffcc]/40">
            {/* Terminal Industries Mechanical Corner Crosshairs */}
            <div className="absolute -top-2 -left-2 text-sm font-mono text-[#00ffcc]/60 select-none" aria-hidden="true">+</div>
            <div className="absolute -top-2 -right-2 text-sm font-mono text-[#00ffcc]/60 select-none" aria-hidden="true">+</div>
            <div className="absolute -bottom-2 -left-2 text-sm font-mono text-[#00ffcc]/60 select-none" aria-hidden="true">+</div>
            <div className="absolute -bottom-2 -right-2 text-sm font-mono text-[#00ffcc]/60 select-none" aria-hidden="true">+</div>

            <div>
              <div className="mb-6 flex items-center justify-between border-b border-white/[0.08] pb-4">
                <span className="font-mono text-[11px] uppercase tracking-widest text-[#00ffcc]">
                  PIPELINE 01 // SUB-200MS AUDIO STREAM
                </span>
                <span className="font-mono text-[11px] text-white/40">SLA: 99.98%</span>
              </div>
              <div className="font-headline text-xl sm:text-2xl lg:text-3xl font-bold leading-snug tracking-tight text-white">
                Streaming int16 PCM audio directly to Groq Whisper v3 Turbo with speculative tool reasoning and neural edge TTS synthesis.
              </div>
              <p className="mt-4 font-body text-sm sm:text-base text-[#a098b0] leading-relaxed">
                Deterministic order routing, warehouse lookup, and inventory dispatch executed in real time without human intervention.
              </p>
            </div>

            <div className="mt-8 border-t border-white/[0.08] pt-4 flex items-center justify-between font-label text-xs uppercase tracking-[0.2em] text-[#00ffcc]/90">
              <span>GROQ WHISPER V3 TURBO • LLAMA 3.3</span>
              <span className="font-mono text-[10px] text-white/40">~200ms turn, UK edge</span>
            </div>
          </div>

          {/* Architecture Pillar 2 with Terminal Crosshairs */}
          <div className="relative flex flex-col justify-between rounded-3xl border border-white/[0.08] bg-black/50 p-8 sm:p-12 backdrop-blur-xl shadow-2xl transition-all duration-300 hover:border-[#ff2d78]/40">
            {/* Terminal Industries Mechanical Corner Crosshairs */}
            <div className="absolute -top-2 -left-2 text-sm font-mono text-[#ff2d78]/60 select-none" aria-hidden="true">+</div>
            <div className="absolute -top-2 -right-2 text-sm font-mono text-[#ff2d78]/60 select-none" aria-hidden="true">+</div>
            <div className="absolute -bottom-2 -left-2 text-sm font-mono text-[#ff2d78]/60 select-none" aria-hidden="true">+</div>
            <div className="absolute -bottom-2 -right-2 text-sm font-mono text-[#ff2d78]/60 select-none" aria-hidden="true">+</div>

            <div>
              <div className="mb-6 flex items-center justify-between border-b border-white/[0.08] pb-4">
                <span className="font-mono text-[11px] uppercase tracking-widest text-[#ff2d78]">
                  SECURITY 02 // ZERO-LEAKAGE ENTERPRISE ISOLATION
                </span>
                <span className="font-mono text-[11px] text-white/40">AWS EU-WEST-2</span>
              </div>
              <div className="font-headline text-xl sm:text-2xl lg:text-3xl font-bold leading-snug tracking-tight text-white">
                Row-level PostgreSQL multi-tenancy, SHA-256 caller PIN verification, and bidirectional Google Sheets synchronization.
              </div>
              <p className="mt-4 font-body text-sm sm:text-base text-[#a098b0] leading-relaxed">
                Automated GDPR DSAR lifecycle management, HMAC signature verified Stripe billing, and Amazon Connect SIP telephony.
              </p>
            </div>

            <div className="mt-8 border-t border-white/[0.08] pt-4 flex items-center justify-between font-label text-xs uppercase tracking-[0.2em] text-[#ff2d78]/90">
              <span>POSTGRESQL • SHEETS 2-WAY SYNC</span>
              <span className="font-mono text-[10px] text-white/40">100% TENANT ISOLATION</span>
            </div>
          </div>
        </div>
      </div>

      {/* Signature Terminal Notched Bottom Seam */}
      <div className="absolute bottom-0 left-1/2 z-20 h-[3px] w-64 -translate-x-1/2 bg-gradient-to-r from-transparent via-[#ff2d78] to-transparent sm:w-96" aria-hidden="true" />
      <div className="absolute bottom-2.5 left-1/2 z-20 h-1.5 w-10 -translate-x-1/2 rounded-full bg-white/20 backdrop-blur-sm" aria-hidden="true" />
    </section>
  );
}
