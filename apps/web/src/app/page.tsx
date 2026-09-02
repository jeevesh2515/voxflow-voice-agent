"use client";

import Link from "next/link";
import { useEffect, useRef } from "react";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import VoiceCoreCanvas from "@/components/VoiceCoreCanvas";
import VoiceXray from "@/components/VoiceXray";
import FourZones from "@/components/FourZones";
import RoiCalculator from "@/components/RoiCalculator";
import VoiceSamples from "@/components/VoiceSamples";
import ProofPricingTeaser from "@/components/ProofPricingTeaser";
import FaqAndContact from "@/components/FaqAndContact";

/**
 * Voxflow Homepage
 * - Section 01: Hero (verbatim H1, two-line focal anomaly, tight subhead, chip, dual CTAs)
 * - Section 02: Problem (IVR = clipboard, lost artifacts, "The driver is still on the line. The sheet is already updated.")
 * - Section 03: Dual Path (Dent/inlay cards: 01 FAST START & 02 CONTROL TOWER)
 * - Sections 04–08: Preserved wrappers in bible order
 */

export default function Home() {
  const heroRef = useRef<HTMLElement | null>(null);
  const problemRef = useRef<HTMLElement | null>(null);
  const dualPathRef = useRef<HTMLElement | null>(null);

  const headlineLine1 = "We closed the ";
  const anomalyWord = "black hole";
  const headlineLine2 = "on the dispatch line.";
  const fullHeadline = "We closed the black hole on the dispatch line.";

  const problemSplitLine = "The driver is still on the line. The sheet is already updated.";
  const problemWords = problemSplitLine.split(" ");

  useEffect(() => {
    if (typeof window === "undefined") return;

    gsap.registerPlugin(ScrollTrigger);

    const prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (prefersReducedMotion) return;

    const ctx = gsap.context(() => {
      // 1. Hero Entrance Animations (28ms stagger, expo.out)
      gsap.fromTo(
        ".hero-letter",
        {
          opacity: 0,
          y: 32,
          rotateX: -30,
        },
        {
          opacity: 1,
          y: 0,
          rotateX: 0,
          stagger: 0.028, // 28ms stagger
          duration: 0.85,
          ease: "expo.out",
          delay: 0.1,
        }
      );

      // Hero Focal Anomaly Pill (Suck & Release gravity feel)
      gsap.fromTo(
        ".hero-anomaly-pill",
        {
          opacity: 0,
          scale: 0.86,
          filter: "blur(4px)",
        },
        {
          opacity: 1,
          scale: 1,
          filter: "blur(0px)",
          duration: 0.9,
          delay: 0.28,
          ease: "expo.out",
        }
      );

      // Hero Fade Items
      gsap.fromTo(
        ".hero-fade",
        {
          opacity: 0,
          y: 20,
        },
        {
          opacity: 1,
          y: 0,
          duration: 0.8,
          delay: 0.45,
          stagger: 0.1,
          ease: "expo.out",
        }
      );

      // 2. Section 02 Problem SplitText Line
      if (problemRef.current) {
        gsap.fromTo(
          ".problem-word",
          {
            opacity: 0,
            y: 28,
          },
          {
            opacity: 1,
            y: 0,
            stagger: 0.045,
            duration: 0.75,
            ease: "expo.out",
            scrollTrigger: {
              trigger: problemRef.current,
              start: "top 75%",
            },
          }
        );

        // Problem Artifacts Floating In
        gsap.fromTo(
          ".problem-artifact",
          {
            opacity: 0,
            y: 40,
            scale: 0.96,
          },
          {
            opacity: 1,
            y: 0,
            scale: 1,
            duration: 0.85,
            stagger: 0.14,
            ease: "expo.out",
            scrollTrigger: {
              trigger: ".problem-artifacts-grid",
              start: "top 80%",
            },
          }
        );
      }

      // 3. Section 03 Dual Path Cards
      if (dualPathRef.current) {
        gsap.fromTo(
          ".dual-path-card",
          {
            opacity: 0,
            y: 45,
          },
          {
            opacity: 1,
            y: 0,
            duration: 0.85,
            stagger: 0.18,
            ease: "expo.out",
            scrollTrigger: {
              trigger: dualPathRef.current,
              start: "top 75%",
            },
          }
        );
      }
    });

    return () => ctx.revert();
  }, []);

  const handleHearItLive = (e: React.MouseEvent<HTMLAnchorElement>) => {
    e.preventDefault();
    const target = document.getElementById("section-04");
    if (target) {
      target.scrollIntoView({ behavior: "smooth" });
    }
  };

  return (
    <div className="relative w-full overflow-hidden text-white font-sans">
      {/* ========================================================================= */}
      {/* 01: HERO — pinned voice core morph (sphere → dispatch mesh)              */}
      {/* ========================================================================= */}
      <section
        ref={heroRef}
        id="hero-stage"
        data-section="01"
        aria-label="01 // Hero"
        className="hero-stage relative"
      >
        <span id="section-01" className="absolute top-0 pointer-events-none" aria-hidden="true" />
        <div className="hero-stage-sticky flex flex-col justify-center items-center px-4 sm:px-6 lg:px-8 text-center">
          {/* VoiceCoreCanvas: primary freight voice visual (sphere → routes → warehouse) */}
          <VoiceCoreCanvas />
          <div className="hero-vignette absolute inset-0 pointer-events-none" aria-hidden="true" />
          {/* quiet system metadata — product context never lost */}
          <div className="absolute top-24 left-4 sm:left-6 lg:left-8 hidden sm:flex flex-col gap-1 text-left pointer-events-none z-10" aria-hidden="true">
            <span className="font-mono text-[9px] tracking-[0.2em] uppercase text-white/30">VOXFLOW / VOICE OS</span>
            <span className="font-mono text-[9px] tracking-wider text-[#5EEAD4]/60">16kHz PCM · SIP · eu-west-2</span>
          </div>
          <div className="absolute top-24 right-4 sm:right-6 lg:right-8 hidden sm:flex flex-col items-end gap-1 text-right pointer-events-none z-10" aria-hidden="true">
            <span className="font-mono text-[9px] tracking-[0.2em] uppercase text-white/30">GLASS-TO-GLASS TURN</span>
            <span className="font-mono text-[9px] tracking-wider text-[#5EEAD4]">~200ms · UK edge</span>
          </div>
          <div className="hero-copy w-full max-w-5xl mx-auto flex flex-col items-center justify-center relative z-10">
          {/* Spec Chip */}
          <div className="hero-fade inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full border border-white/[0.1] bg-[#030308]/60 backdrop-blur-md text-xs font-mono tracking-wider text-[#5EEAD4] uppercase mb-8 shadow-[0_0_20px_rgba(94,234,212,0.12)]">
            <span className="h-1.5 w-1.5 rounded-full bg-[#5EEAD4] animate-pulse" />
            UK edge · ~200ms · EN + Hindi
          </div>

          {/* H1 Two-Line Focal Anomaly Lockup (Verbatim: We closed the black hole on the dispatch line.) */}
          <h1
            aria-label={fullHeadline}
            className="font-headline font-black text-4xl sm:text-6xl md:text-7xl lg:text-[5.1rem] tracking-[-0.04em] text-white max-w-4xl leading-[1.08] mb-6 [perspective:1000px]"
          >
            {/* Line 1: We closed the [black hole] */}
            <span className="block mb-1 sm:mb-2">
              {headlineLine1.split(" ").filter(Boolean).map((word, wIdx) => (
                <span key={wIdx} className="inline-block whitespace-nowrap mr-[0.28em]">
                  {word.split("").map((char, cIdx) => (
                    <span key={cIdx} aria-hidden="true" className="hero-letter inline-block will-change-transform">
                      {char}
                    </span>
                  ))}
                </span>
              ))}
              {" "}
              {/* Focal Anomaly Pill: black hole */}
              <span className="hero-anomaly-pill inline-flex items-center px-2.5 sm:px-4 py-0.5 sm:py-1 rounded-2xl bg-[#ff2d78]/10 border border-[#ff2d78]/35 text-[#ff2d78] shadow-[0_0_25px_rgba(255,45,120,0.25)] align-baseline">
                {anomalyWord.split(" ").map((w, wIdx) => (
                  <span key={wIdx} className="inline-block whitespace-nowrap mr-[0.24em] last:mr-0">
                    {w.split("").map((c, cIdx) => (
                      <span key={cIdx} aria-hidden="true" className="hero-letter inline-block will-change-transform">
                        {c}
                      </span>
                    ))}
                  </span>
                ))}
              </span>
            </span>

            {/* Line 2: on the dispatch line. */}
            <span className="block text-white/90">
              {headlineLine2.split(" ").map((word, wIdx) => (
                <span key={wIdx} className="inline-block whitespace-nowrap mr-[0.28em] last:mr-0">
                  {word.split("").map((char, cIdx) => (
                    <span key={cIdx} aria-hidden="true" className="hero-letter inline-block will-change-transform">
                      {char}
                    </span>
                  ))}
                </span>
              ))}
            </span>
          </h1>

          {/* Subheadline (12 words) */}
          <p className="hero-fade font-sans text-lg sm:text-xl md:text-2xl text-white/75 max-w-2xl font-normal leading-relaxed mb-10 text-balance">
            Voice agents check stock, move docks, write sheets — on the call.
          </p>

          {/* CTAs */}
          <div className="hero-fade flex flex-col sm:flex-row items-center justify-center gap-3.5 sm:gap-4 w-full sm:w-auto">
            <a
              href="#section-04"
              onClick={handleHearItLive}
              className="w-full sm:w-auto inline-flex items-center justify-center gap-2.5 px-6 py-3.5 rounded-full border border-white/[0.14] bg-white/[0.04] hover:bg-white/[0.08] text-white text-sm font-semibold tracking-wide transition-all hover:border-[#5EEAD4]/50 shadow-lg min-h-[46px]"
            >
              <svg
                width="14"
                height="14"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2.5"
                strokeLinecap="round"
                strokeLinejoin="round"
                className="text-[#5EEAD4]"
                aria-hidden="true"
              >
                <polygon points="5 3 19 12 5 21 5 3" />
              </svg>
              Hear it live
            </a>

            <Link
              href="/sign-up"
              className="w-full sm:w-auto inline-flex items-center justify-center gap-2 px-7 py-3.5 rounded-full bg-[#5EEAD4] text-[#030308] text-sm font-bold tracking-wide hover:shadow-[0_0_30px_rgba(94,234,212,0.5)] transition-all active:scale-95 min-h-[46px] font-headline"
            >
              Fix one workflow
              <svg
                width="14"
                height="14"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2.5"
                strokeLinecap="round"
                strokeLinejoin="round"
                aria-hidden="true"
              >
                <line x1="7" y1="17" x2="17" y2="7" />
                <polyline points="7 7 17 7 17 17" />
              </svg>
            </Link>
          </div>
        </div>
        </div>
      </section>

      {/* ========================================================================= */}
      {/* 02: PROBLEM                                                               */}
      {/* ========================================================================= */}
      <section
        ref={problemRef}
        id="section-02"
        data-section="02"
        aria-label="02 // Problem"
        className="relative min-h-[90vh] flex flex-col justify-center items-center px-4 sm:px-6 lg:px-8 py-28 border-t border-white/[0.06] bg-gradient-to-b from-transparent via-[#030308]/40 to-transparent"
      >
        <div className="w-full max-w-5xl mx-auto flex flex-col items-center text-center">
          {/* Section Marker */}
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-white/[0.08] bg-white/[0.02] text-xs font-mono tracking-widest text-[#5EEAD4] uppercase mb-6">
            02 / 08 • Problem // The Conversation Black Hole
          </div>

          <h2 className="font-headline font-extrabold text-3xl sm:text-5xl md:text-6xl tracking-tight text-white max-w-3xl leading-[1.12] mb-6">
            Traditional IVR is a clipboard with a phone wire.
          </h2>

          <p className="font-sans text-base sm:text-lg md:text-xl text-white/65 max-w-2xl leading-relaxed mb-12">
            Every dispatch call puts a driver on hold while an operator opens three browser tabs, checks a stock spreadsheet, and jots a note on paper. When call volume peaks, orders vanish.
          </p>

          {/* Drifting Artifact Cards: The 3 Lost Operations */}
          <div className="problem-artifacts-grid grid grid-cols-1 md:grid-cols-3 gap-4 sm:gap-6 w-full mb-14 text-left">
            {/* Artifact 1: Missed Driver Update */}
            <div className="problem-artifact relative p-6 rounded-2xl border border-white/[0.08] bg-[#030308]/80 backdrop-blur-xl shadow-[inset_0_1px_1px_rgba(255,255,255,0.06),0_15px_30px_rgba(0,0,0,0.6)]">
              <div className="flex items-center justify-between mb-4">
                <span className="font-mono text-[11px] uppercase tracking-wider text-rose-400/90 flex items-center gap-1.5">
                  <span className="h-1.5 w-1.5 rounded-full bg-rose-500 animate-pulse" />
                  Hold Time 4:18
                </span>
                <span className="text-white/30 font-mono text-xs">M4 Corridor</span>
              </div>
              <p className="font-headline font-bold text-white text-base mb-2">
                &ldquo;Are bays 4 and 5 clear for the 26-pallet drop?&rdquo;
              </p>
              <p className="text-xs text-white/50 leading-relaxed">
                Driver sitting in holding lane waiting for radio check while dock supervisor searches morning sheet.
              </p>
            </div>

            {/* Artifact 2: Stock Lockout */}
            <div className="problem-artifact relative p-6 rounded-2xl border border-white/[0.08] bg-[#030308]/80 backdrop-blur-xl shadow-[inset_0_1px_1px_rgba(255,255,255,0.06),0_15px_30px_rgba(0,0,0,0.6)]">
              <div className="flex items-center justify-between mb-4">
                <span className="font-mono text-[11px] uppercase tracking-wider text-amber-400/90 flex items-center gap-1.5">
                  <span className="h-1.5 w-1.5 rounded-full bg-amber-500" />
                  Manual ERP Lookup
                </span>
                <span className="text-white/30 font-mono text-xs">SKU-7729</span>
              </div>
              <p className="font-headline font-bold text-white text-base mb-2">
                &ldquo;Can we release 80 cases of Mango Pulp to Depot B?&rdquo;
              </p>
              <p className="text-xs text-white/50 leading-relaxed">
                Warehouse desk busy on phone. Allocation logged on scrap pad; sheet unupdated until shift end.
              </p>
            </div>

            {/* Artifact 3: Multilingual Misrouting */}
            <div className="problem-artifact relative p-6 rounded-2xl border border-white/[0.08] bg-[#030308]/80 backdrop-blur-xl shadow-[inset_0_1px_1px_rgba(255,255,255,0.06),0_15px_30px_rgba(0,0,0,0.6)]">
              <div className="flex items-center justify-between mb-4">
                <span className="font-mono text-[11px] uppercase tracking-wider text-cyan-400/90 flex items-center gap-1.5">
                  <span className="h-1.5 w-1.5 rounded-full bg-cyan-400" />
                  Language Barrier
                </span>
                <span className="text-white/30 font-mono text-xs">EN / Hinglish</span>
              </div>
              <p className="font-headline font-bold text-white text-base mb-2">
                &ldquo;Gate 2 band hai, delivery kahan utaaroon?&rdquo;
              </p>
              <p className="text-xs text-white/50 leading-relaxed">
                Standard UK telephony drops non-English calls or routes to voicemail with 3-hour turnaround.
              </p>
            </div>
          </div>

          {/* One Extra SplitText Line Max (Key Payoff) */}
          <div className="relative py-4 px-6 sm:px-8 rounded-2xl border border-[#5EEAD4]/20 bg-[#5EEAD4]/[0.03] backdrop-blur-sm max-w-3xl">
            <p className="font-headline font-bold text-xl sm:text-2xl md:text-3xl text-white leading-snug tracking-tight">
              {problemWords.map((word, idx) => (
                <span key={idx} className="problem-word inline-block mr-[0.28em] last:mr-0">
                  {word === "updated." ? (
                    <span className="text-[#5EEAD4] font-black underline decoration-[#5EEAD4]/40 underline-offset-4">
                      {word}
                    </span>
                  ) : (
                    word
                  )}
                  {" "}
                </span>
              ))}
            </p>
          </div>
        </div>
      </section>

      {/* ========================================================================= */}
      {/* 03: DUAL PATH                                                             */}
      {/* ========================================================================= */}
      <section
        ref={dualPathRef}
        id="section-03"
        data-section="03"
        aria-label="03 // Dual path"
        className="relative min-h-[90vh] flex flex-col justify-center items-center px-4 sm:px-6 lg:px-8 py-28 border-t border-white/[0.06]"
      >
        <div className="w-full max-w-6xl mx-auto flex flex-col items-center text-center">
          {/* Section Marker */}
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-white/[0.08] bg-white/[0.02] text-xs font-mono tracking-widest text-[#5EEAD4] uppercase mb-6">
            03 / 08 • Architecture // Dual Deployment Path
          </div>

          <h2 className="font-headline font-extrabold text-3xl sm:text-5xl md:text-6xl tracking-tight text-white max-w-3xl leading-[1.12] mb-6">
            One line to fix a bottleneck. Or one voice mesh for your whole fleet.
          </h2>

          <p className="font-sans text-base sm:text-lg md:text-xl text-white/65 max-w-2xl leading-relaxed mb-14">
            Start with the single telephone line bleeding the most operational time, then scale across every depot with zero infrastructure change.
          </p>

          {/* Dual Path Dent/Inlay Cards */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 sm:gap-8 w-full text-left">
            {/* Card 01: FAST START */}
            <div className="dual-path-card group relative p-8 sm:p-10 rounded-3xl border border-white/[0.09] bg-[#030308]/90 backdrop-blur-2xl shadow-[inset_0_1px_1px_rgba(255,255,255,0.08),0_25px_50px_rgba(0,0,0,0.85)] hover:border-[#5EEAD4]/40 transition-all duration-300">
              <div className="flex items-center justify-between mb-6 pb-4 border-b border-white/[0.06]">
                <span className="font-mono text-xs uppercase tracking-widest text-[#5EEAD4] font-bold">
                  01 // FAST START
                </span>
                <span className="font-mono text-xs text-white/40">1 Voice Line</span>
              </div>

              <h3 className="font-headline font-black text-2xl sm:text-3xl text-white tracking-tight mb-4 group-hover:text-[#5EEAD4] transition-colors">
                One depot number, live in days.
              </h3>

              <p className="text-white/70 text-base leading-relaxed mb-8">
                Plug a dedicated UK DID straight into your most congested inbound queue — warehouse gate, pallet collection, or stock verification. Pre-configured tools update Google Sheets &amp; dispatch rosters instantly.
              </p>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-4 border-t border-white/[0.06]">
                <div className="p-3 rounded-xl bg-white/[0.02] border border-white/[0.04]">
                  <span className="block font-mono text-[10px] text-white/40 uppercase tracking-wider mb-1">Setup Time</span>
                  <span className="font-headline font-bold text-sm text-white">&lt; 72 Hours</span>
                </div>
                <div className="p-3 rounded-xl bg-white/[0.02] border border-white/[0.04]">
                  <span className="block font-mono text-[10px] text-white/40 uppercase tracking-wider mb-1">Telephony</span>
                  <span className="font-headline font-bold text-sm text-white">UK DID / Connect</span>
                </div>
                <div className="p-3 rounded-xl bg-white/[0.02] border border-white/[0.04]">
                  <span className="block font-mono text-[10px] text-white/40 uppercase tracking-wider mb-1">State Sync</span>
                  <span className="font-headline font-bold text-sm text-[#5EEAD4]">Live Sheets</span>
                </div>
              </div>
            </div>

            {/* Card 02: CONTROL TOWER */}
            <div className="dual-path-card group relative p-8 sm:p-10 rounded-3xl border border-white/[0.09] bg-[#030308]/90 backdrop-blur-2xl shadow-[inset_0_1px_1px_rgba(255,255,255,0.08),0_25px_50px_rgba(0,0,0,0.85)] hover:border-[#5EEAD4]/40 transition-all duration-300">
              <div className="flex items-center justify-between mb-6 pb-4 border-b border-white/[0.06]">
                <span className="font-mono text-xs uppercase tracking-widest text-[#5EEAD4] font-bold">
                  02 // CONTROL TOWER
                </span>
                <span className="font-mono text-xs text-white/40">Fleet Mesh</span>
              </div>

              <h3 className="font-headline font-black text-2xl sm:text-3xl text-white tracking-tight mb-4 group-hover:text-[#5EEAD4] transition-colors">
                Mesh of depots, one memory.
              </h3>

              <p className="text-white/70 text-base leading-relaxed mb-8">
                Unify all regional logistics hubs into a single voice-activated state engine. Cross-depot inventory visibility, shared driver caller IDs, and automated failover escalation when a facility reaches capacity.
              </p>

              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-4 border-t border-white/[0.06]">
                <div className="p-3 rounded-xl bg-white/[0.02] border border-white/[0.04]">
                  <span className="block font-mono text-[10px] text-white/40 uppercase tracking-wider mb-1">Architecture</span>
                  <span className="font-headline font-bold text-sm text-white">Multi-Depot Mesh</span>
                </div>
                <div className="p-3 rounded-xl bg-white/[0.02] border border-white/[0.04]">
                  <span className="block font-mono text-[10px] text-white/40 uppercase tracking-wider mb-1">Intelligence</span>
                  <span className="font-headline font-bold text-sm text-white">Unified Memory</span>
                </div>
                <div className="p-3 rounded-xl bg-white/[0.02] border border-white/[0.04]">
                  <span className="block font-mono text-[10px] text-white/40 uppercase tracking-wider mb-1">Latency SLA</span>
                  <span className="font-headline font-bold text-sm text-[#5EEAD4]">~200ms Turn</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ========================================================================= */}
      {/* 04: VOICE X-RAY                                                           */}
      {/* ========================================================================= */}
      <VoiceXray />

      {/* ========================================================================= */}
      {/* 05: FOUR ZONES                                                            */}
      {/* ========================================================================= */}
      <FourZones />

      {/* ========================================================================= */}
      {/* 06: ROI CALCULATOR + SAMPLES                                              */}
      {/* ========================================================================= */}
      <section
        id="section-06"
        data-section="06"
        aria-label="06 // ROI calculator + samples"
        className="relative w-full border-t border-white/[0.06] bg-[#030308] text-white py-24 px-4 sm:px-6 lg:px-8"
      >
        <RoiCalculator />
        <VoiceSamples />
      </section>

      {/* ========================================================================= */}
      {/* 07: PROOF + PRICING TEASER                                                */}
      {/* ========================================================================= */}
      <section
        id="section-07"
        data-section="07"
        aria-label="07 // Proof + pricing teaser"
        className="relative w-full border-t border-white/[0.06] bg-[#030308] text-white py-24 px-4 sm:px-6 lg:px-8"
      >
        <ProofPricingTeaser />
      </section>

      {/* ========================================================================= */}
      {/* 08: FAQ + CONTACT                                                         */}
      {/* ========================================================================= */}
      <section
        id="section-08"
        data-section="08"
        aria-label="08 // FAQ + contact + footer"
        className="relative w-full border-t border-white/[0.06] bg-[#030308] text-white py-24 px-4 sm:px-6 lg:px-8 mb-12"
      >
        <FaqAndContact />
      </section>
    </div>
  );
}
