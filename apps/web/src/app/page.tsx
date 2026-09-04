"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import CosmicStarfield from "@/components/CosmicStarfield";
import SmoothScroll from "@/components/SmoothScroll";
import HeroChoreography from "@/components/HeroChoreography";
import VoxPreloader from "@/components/VoxPreloader";
import AcousticBlackHoleCanvas from "@/components/AcousticBlackHoleCanvas";
import CosmicJourney from "@/components/CosmicJourney";
import HeroCursorFollower from "@/components/HeroCursorFollower";
import KineticScrollText from "@/components/KineticScrollText";
import SignalWires from "@/components/SignalWires";
import AmbientGradient from "@/components/AmbientGradient";
import StickyCapabilityShowcase from "@/components/StickyCapabilityShowcase";
import NotchedContainer from "@/components/NotchedContainer";
import ParallaxQuotes from "@/components/ParallaxQuotes";
import VoiceXray from "@/components/VoiceXray";
import DispatchSwitchboard from "@/components/DispatchSwitchboard";

export default function Home() {
  const [playing, setPlaying] = useState<VoiceKey | null>(null);
  const [roiCalls, setRoiCalls] = useState(1000);
  const [roiMins, setRoiMins] = useState(4);
  const [annualBilling, setAnnualBilling] = useState(true);
  const annualSavings = Math.max(0, Math.round((roiCalls * roiMins * (14 / 60 - 0.12) * 365 * 0.9) / 100) * 100);
  const monthlyHoursSaved = Math.round((roiCalls * roiMins * 30 * 0.9) / 60);
  const fteEquivalent = Math.max(1, Math.round((roiCalls * roiMins * 0.9) / 60 / 7));
  const paybackDays = Math.max(1, Math.min(14, Math.round((1500 / Math.max(annualSavings / 365, 1)) * 10) / 10));

  type VoiceKey = "en" | "hi" | "hinglish" | "us";
  const VOICE_META: Record<VoiceKey, { label: string; lang: string; pitch: number; freq: [number, number]; text: string; bubble: string }> = {
    en: {
      label: "English",
      lang: "en-GB",
      pitch: 1.05,
      freq: [440, 580],
      text: "Hello! I am your autonomous AI voice agent. I handle incoming customer inquiries, verify orders and shipments, check real-time stock levels, and synchronize all call records directly to your database with sub-second latency.",
      bubble: "“I handle incoming inquiries, verify orders and shipments, check real-time stock, and sync every record to your database — sub-second.”",
    },
    us: {
      label: "US English",
      lang: "en-US",
      pitch: 1.0,
      freq: [460, 600],
      text: "Hey there! This is your AI voice agent. I answer inbound calls, check live inventory, confirm delivery windows, and write every outcome straight back to your systems. No hold music required.",
      bubble: "“I answer inbound calls, check live inventory, confirm delivery windows, and write outcomes straight back to your systems.”",
    },
    hi: {
      label: "Hindi",
      lang: "hi-IN",
      pitch: 0.98,
      freq: [330, 390],
      text: "नमस्ते! मैं आपका एआई वॉइस असिस्टेंट हूँ। मैं ग्राहकों की कॉल्स का जवाब दे सकता हूँ, ऑर्डर और शिपमेंट की स्थिति बता सकता हूँ, और सभी कॉल्स का डेटा सीधे आपके सिस्टम में तुरंत अपडेट कर सकता हूँ।",
      bubble: "“मैं ग्राहकों की कॉल्स का जवाब दे सकता हूँ, ऑर्डर और शिपमेंट की स्थिति बता सकता हूँ, और सारा डेटा सीधे अपडेट कर सकता हूँ।”",
    },
    hinglish: {
      label: "Hinglish",
      lang: "hi-IN",
      pitch: 1.0,
      freq: [380, 480],
      text: "नमस्ते! आपका ऑर्डर verify हो गया है। 48 units dispatch हो चुके हैं, और delivery Friday सुबह 8 से 11 बजे confirm कर दी है। Sheet भी update कर दी है।",
      bubble: "“ऑर्डर verify हो गया — 48 units dispatched, delivery Friday 8–11 confirm. Sheet भी update कर दी।”",
    },
  };

  // Natural Lifelike Feature-Focused Voice Playback (No company names, pure capability showcase)
  const playSample = (lang: VoiceKey) => {
    if (typeof window === "undefined") return;

    if (playing) {
      if ("speechSynthesis" in window) {
        window.speechSynthesis.cancel();
      }
      setPlaying(null);
      return;
    }

    setPlaying(lang);
    window.dispatchEvent(new CustomEvent("voxflow:voice-play", { detail: { lang } }));
    const meta = VOICE_META[lang];

    // 1. Natural Spoken Audio via SpeechSynthesis
    if ("speechSynthesis" in window) {
      window.speechSynthesis.cancel();

      const utterance = new SpeechSynthesisUtterance(meta.text);
      utterance.lang = meta.lang;
      utterance.rate = 1.02;
      utterance.pitch = meta.pitch;

      utterance.onend = () => setPlaying(null);
      utterance.onerror = () => setPlaying(null);

      const voices = window.speechSynthesis.getVoices();
      const matchedVoice = voices.find((v) =>
        lang === "hi" || lang === "hinglish" ? v.lang.includes("hi") : v.lang.includes(meta.lang)
      );
      if (matchedVoice) utterance.voice = matchedVoice;

      window.speechSynthesis.speak(utterance);
    }

    // 2. Harmonic Acoustic Tone Accompaniment via Web Audio API
    try {
      const AudioCtx =
        window.AudioContext ||
        (window as unknown as { webkitAudioContext: typeof AudioContext }).webkitAudioContext;
      const ctx = new AudioCtx();
      if (ctx.state === "suspended") {
        ctx.resume();
      }
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      const filter = ctx.createBiquadFilter();
      filter.type = "lowpass";
      filter.frequency.value = 1600;

      osc.type = "sine";
      osc.frequency.setValueAtTime(meta.freq[0], ctx.currentTime);
      osc.frequency.exponentialRampToValueAtTime(meta.freq[1], ctx.currentTime + 0.3);

      gain.gain.setValueAtTime(0.001, ctx.currentTime);
      gain.gain.linearRampToValueAtTime(0.08, ctx.currentTime + 0.05);
      gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 4.2);

      osc.connect(filter).connect(gain).connect(ctx.destination);
      osc.start();
      osc.stop(ctx.currentTime + 4.4);

      setTimeout(() => {
        try {
          ctx.close();
        } catch {}
      }, 4500);
    } catch {}

    setTimeout(() => {
      setPlaying((curr) => (curr === lang ? null : curr));
    }, 6000);
  };

  useEffect(() => {
    // ── Reveal on intersect ──
    const els = document.querySelectorAll(
      ".reveal, .reveal-left, .reveal-right, .reveal-scale, .stagger-children"
    );
    const obs = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add("visible");
            obs.unobserve(entry.target);
          }
        });
      },
      { threshold: 0.08, rootMargin: "0px 0px -40px 0px" }
    );
    els.forEach((el) => obs.observe(el));

    // ── Kinetic scroll engine (rAF, class toggles only) ──
    const tele = document.getElementById("solutions");
    const pipe = document.getElementById("pipeline-section");
    const sheets = document.getElementById("sheets-section");
    const wordReveals = document.querySelectorAll<HTMLElement>("[data-word-reveal]");
    let ticking = false;

    const clamp01 = (v: number) => Math.min(1, Math.max(0, v));
    // Skip DOM reads/writes for sections nowhere near the viewport.
    const nearView = (r: DOMRect) => r.bottom > -150 && r.top < window.innerHeight + 150;
    // Pre-cache every queried node once: per-frame querySelectorAll across all
    // words/rows was forcing full layout on each scroll tick.
    const wordBlocks = Array.from(wordReveals).map((paragraph) => ({
      el: paragraph,
      words: Array.from(paragraph.querySelectorAll<HTMLElement>("[data-word-index]")),
    }));
    const teleSteps = tele ? Array.from(tele.querySelectorAll<HTMLElement>("[data-tele-step]")) : [];
    const teleBubbles = tele ? Array.from(tele.querySelectorAll<HTMLElement>("[data-bubble-step]")) : [];
    const pipeCards = pipe ? Array.from(pipe.querySelectorAll<HTMLElement>("[data-pipe-step]")) : [];
    const pipeRail = document.getElementById("pipe-rail-fill");
    const pipeBadge = document.getElementById("pipe-latency");
    const sheetRows = sheets ? Array.from(sheets.querySelectorAll<HTMLElement>("[data-sheet-row]")) : [];
    const sheetCommit = document.getElementById("sheet-commit-label");
    const prog = (el: HTMLElement) => {
      const r = el.getBoundingClientRect();
      return clamp01((window.innerHeight - r.top) / (window.innerHeight + r.height * 0.8));
    };

    const onScroll = () => {
      if (ticking) return;
      ticking = true;
      requestAnimationFrame(() => {
        ticking = false;

        // Word-level narrative illumination, driven by scroll position.
        wordBlocks.forEach(({ el: paragraph, words }) => {
          const r = paragraph.getBoundingClientRect();
          if (!nearView(r) || words.length === 0) return;
          const p = clamp01((window.innerHeight * 0.85 - r.top) / (r.height + window.innerHeight * 0.4));
          words.forEach((word, index) => {
            const reveal = clamp01(p * words.length - index + 0.35);
            word.style.opacity = `${0.16 + reveal * 0.84}`;
            word.style.transform = `translateY(${(1 - reveal) * 8}px)`;
          });
        });

        // Dual-POV sync
        if (tele) {
          const r = tele.getBoundingClientRect();
          if (nearView(r)) {
          const p = clamp01((window.innerHeight * 0.75 - r.top) / (r.height + window.innerHeight * 0.3));
          const step = Math.min(3, Math.floor(p * 4.5));
          teleSteps.forEach((n) => {
            n.classList.toggle("telemetry-hot", Number(n.dataset.teleStep) <= step);
          });
          teleBubbles.forEach((n) => {
            n.classList.toggle("bubble-pending", Number(n.dataset.bubbleStep) > step);
          });
          }
        }

        // 4-Hop Architecture Pipeline scroll sync
        if (pipe && pipeCards.length > 0) {
          const r = pipe.getBoundingClientRect();
          if (nearView(r)) {
          const viewportCenter = window.innerHeight * 0.55;
          const p = clamp01((viewportCenter - r.top) / (r.height * 0.85));
          const active = Math.min(pipeCards.length - 1, Math.max(0, Math.floor(p * pipeCards.length)));
          pipeCards.forEach((n, i) => {
            n.classList.toggle("pipe-active", i === active);
          });
          if (pipeRail) pipeRail.style.height = `${((active + 1) / pipeCards.length) * 100}%`;
          if (pipeBadge) {
            const lat = ["38ms", "84ms", "112ms", "196ms"][active];
            if (pipeBadge.textContent !== lat) pipeBadge.textContent = lat;
          }
          }
        }

        // Sheets mirror row flash
        if (sheets) {
          const r = sheets.getBoundingClientRect();
          if (nearView(r)) {
          const p = clamp01((window.innerHeight * 0.7 - r.top) / (r.height + window.innerHeight * 0.2));
          const litRows = Math.floor(p * 5);
          sheetRows.forEach((n) => {
            n.classList.toggle("sheet-flash", Number(n.dataset.sheetRow) < litRows);
          });
          if (sheetCommit) {
            const label = litRows === 0 ? "awaiting tool call…" : `commit ${Math.min(4, litRows)}/4 → Call Log tab`;
            if (sheetCommit.textContent !== label) sheetCommit.textContent = label;
          }
          }
        }
      });
    };
    window.addEventListener("scroll", onScroll, { passive: true });
    onScroll();
    // NOTE: `hero-stage-ready` is owned by HeroChoreography, which also drives
    // --hero-progress. Setting it here too would race its cleanup.

    return () => {
      obs.disconnect();
      window.removeEventListener("scroll", onScroll);
    };
  }, []);

  return (
    <>
      {/* Subtle, elegant ambient starfield */}
      <CosmicStarfield />
      <SmoothScroll />
      <HeroChoreography />
      <VoxPreloader />

      <main className="relative z-10 bg-transparent">
        {/* ==================== HERO SECTION ==================== */}
        <section id="hero-stage" className="hero-stage relative" aria-label="VoxFlow autonomous voice operations introduction">
          <div className="hero-stage-sticky min-h-[100svh] flex items-center overflow-hidden grid-bg pt-28 pb-16 sm:pt-32 sm:pb-24">
            {/* Keyframe 1 of the cosmic journey: the acoustic event horizon.
                Recedes to nothing across 0.10 → 0.18 as the starfield takes
                over. Carries 01-black-hole.webp as its own background, so a
                failed WebGL init degrades to the still rather than a void. */}
            <div className="hero-blackhole-layer">
              <AcousticBlackHoleCanvas />
            </div>

            {/* Keyframes 2-5 — starfield → solar system → telescope → Earth.
                Must follow the black hole layer in DOM order: both sit at
                z-index 0, so paint order is what puts the journey on top. */}
            <CosmicJourney />

            <div className="hero-vignette absolute inset-0 pointer-events-none" aria-hidden="true" />

            <HeroCursorFollower />

            {/* Stage B — diagnostic markers, in at 0.15, out by 0.9. */}
            <div className="hero-hud hero-hud-left" aria-hidden="true">
              <span>SIGNAL LOCK</span>
              <span>16kHz PCM · eu-west-2</span>
            </div>
            <div className="hero-hud hero-hud-right" aria-hidden="true">
              <span>GLASS-TO-GLASS TURN</span>
              <span>~200ms · UK edge</span>
            </div>

            {/* Journey copy — three quiet lines across keyframes 2-4.
                Arc: silence → a signal travelling → someone receiving it.
                Keyframe 5 (Earth) carries none: the docked h1 below is the
                payoff, and it hard-cuts in without overlap. */}
            <div className="hero-punchlines absolute inset-0 flex items-center justify-center pointer-events-none z-20 px-6">
              <p className="hero-punchline hero-punchline-j1 journey-line max-w-3xl text-center font-headline text-3xl sm:text-4xl lg:text-5xl">
                Out here, signals go quiet.
              </p>
              <p className="hero-punchline hero-punchline-j2 journey-line max-w-3xl text-center font-headline text-3xl sm:text-4xl lg:text-5xl">
                A signal, still moving.
              </p>
              <p className="hero-punchline hero-punchline-j3 journey-line max-w-3xl text-center font-headline text-3xl sm:text-4xl lg:text-5xl">
                Someone&rsquo;s listening now.
              </p>
            </div>

          {/* Ambient Glowing Nebula Orbs */}
          <div
            className="absolute top-1/4 left-1/4 w-[45vw] h-[45vw] max-w-[500px] max-h-[500px] bg-[#ff2d78]/10 blur-[130px] rounded-full pointer-events-none"
            aria-hidden="true"
          />
          <div
            className="absolute bottom-1/4 right-1/4 w-[40vw] h-[40vw] max-w-[450px] max-h-[450px] bg-[#c084fc]/10 blur-[130px] rounded-full pointer-events-none"
            aria-hidden="true"
          />

          <div className="relative z-10 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 grid lg:grid-cols-12 gap-12 lg:gap-16 items-center w-full">
            {/* Left Column: Headline, Value Proposition, Audio Previews & CTA */}
            <div className="hero-copy lg:col-span-7">
              <span className="font-label text-[#c084fc] tracking-[0.2em] uppercase text-xs sm:text-sm mb-4 sm:mb-6 block neon-text-sm">
                ✦ MULTILINGUAL FREIGHT VOICE OS
              </span>
              <h1 className="font-headline font-extrabold text-4xl sm:text-5xl lg:text-6xl xl:text-7xl leading-[1.1] tracking-tight mb-6 text-[#f8fafc]">
                We closed the{" "}
                <span className="hero-anomaly-pill inline-flex items-center px-2.5 sm:px-4 py-0.5 rounded-2xl bg-[#ff2d78]/15 border border-[#ff2d78]/40 text-[#ff2d78] shadow-[0_0_25px_rgba(255,45,120,0.3)] align-baseline">
                  black hole
                </span>
                <br />
                <span className="text-white/90">
                  on the dispatch line.
                </span>
              </h1>
              <p className="text-[#a098b0] text-base sm:text-lg lg:text-xl mb-8 max-w-xl font-body leading-relaxed">
                Voice agents that check stock, move docks, and write the sheet — while the driver is still talking.
              </p>

              {/* SLA Trust Badges */}
              <div className="flex flex-wrap gap-2.5 mb-8">
                {["~200ms Turn, UK Edge", "London eu-west-2", "UK GDPR Default", "Real-Time Sheets Sync"].map((b) => (
                  <span
                    key={b}
                    className="inline-flex items-center gap-2 rounded-full glass px-3.5 py-1.5 text-[11px] font-label text-[#e8e0f0] border border-white/[0.08] hover:border-[#ff2d78]/40 transition-colors"
                  >
                    <span className="w-1.5 h-1.5 rounded-full bg-[#ff2d78] signal-dot" aria-hidden="true" />
                    {b}
                  </span>
                ))}
              </div>

              {/* Audio Sample Pills (Sound-synced with top console) */}
              <div className="flex flex-wrap items-center gap-3 mb-8">
                <span className="w-full text-xs font-label text-[#a098b0] uppercase tracking-wider">
                  Test Voice Engine:
                </span>
                {(Object.keys(VOICE_META) as VoiceKey[]).map((lang) => {
                  const label = VOICE_META[lang].label;
                  return (
                  <button
                    key={lang}
                    type="button"
                    onClick={() => playSample(lang)}
                    className={`inline-flex items-center gap-2 rounded-full glass px-4 py-2 font-label text-xs transition-all duration-300 cursor-pointer ${
                      playing === lang
                        ? "bg-[#ff2d78]/20 border-[#ff2d78] text-white shadow-[0_0_20px_rgba(255,45,120,0.4)] scale-105"
                        : "border-white/[0.1] text-[#e8e0f0] hover:border-[#ff2d78]/60 hover:text-white"
                    }`}
                  >
                    {playing === lang ? (
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" className="text-[#ff2d78] animate-pulse">
                        <line x1="4" y1="9" x2="4" y2="15" />
                        <line x1="8" y1="6" x2="8" y2="18" />
                        <line x1="12" y1="3" x2="12" y2="21" />
                        <line x1="16" y1="7" x2="16" y2="17" />
                        <line x1="20" y1="10" x2="20" y2="14" />
                      </svg>
                    ) : (
                      <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor" className="text-[#ff2d78]">
                        <polygon points="5 3 19 12 5 21 5 3" />
                      </svg>
                    )}
                    {playing === lang ? `Speaking ${label}...` : `Play ${label}`}
                  </button>
                  );
                })}
              </div>

              {/* CTAs */}
              <div className="flex flex-wrap gap-3 sm:gap-4">
                <a
                  href="#voice-xray"
                  onClick={(e) => {
                    e.preventDefault();
                    const el = document.getElementById("voice-xray") || document.getElementById("solutions");
                    el?.scrollIntoView({ behavior: "smooth" });
                  }}
                  className="btn-ghost-obs inline-flex items-center gap-2 px-6 sm:px-8 py-3.5 sm:py-4 font-headline font-bold rounded-full text-sm sm:text-base border border-white/[0.1] hover:border-[#5EEAD4]/50 transition-all cursor-pointer"
                >
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor" className="text-[#5EEAD4]">
                    <polygon points="5 3 19 12 5 21 5 3" />
                  </svg>
                  Hear it live
                </a>
                <Link
                  href="/sign-up"
                  className="btn-signal inline-flex items-center gap-2 px-6 sm:px-8 py-3.5 sm:py-4 font-headline font-bold rounded-full text-sm sm:text-base hover:scale-[1.02] active:scale-95 transition-all shadow-[0_0_25px_rgba(255,45,120,0.4)]"
                >
                  Start free
                  <span className="cta-arrow-badge">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                      <line x1="5" y1="12" x2="19" y2="12" />
                      <polyline points="12 5 19 12 12 19" />
                    </svg>
                  </span>
                </Link>
              </div>
              <p className="mt-3 text-xs text-[#a098b0]">
                No credit card required • Cancel anytime in Stripe portal • 500 free minutes
              </p>
            </div>

            {/* Right Column: Live Operations Console Mockup Window (Sound-Synced!) */}
            <div className="hero-console lg:col-span-5 relative hero-console-shell">
              <div className="hero-console-core glass rounded-[1.25rem] border border-white/[0.12] shadow-[inset_0_1px_1px_rgba(255,255,255,0.12),0_20px_60px_rgba(0,0,0,0.7),0_0_35px_rgba(255,45,120,0.15)] overflow-hidden transition-all duration-400">
                {/* Console Window Top Bar */}
                <div className="bg-[#05050a]/90 px-4 py-3 border-b border-white/[0.08] flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div className="w-3 h-3 rounded-full bg-[#ff5f56]/80" />
                    <div className="w-3 h-3 rounded-full bg-[#ffbd2e]/80" />
                    <div className="w-3 h-3 rounded-full bg-[#27c93f]/80" />
                  </div>
                  <div className="flex items-center gap-2 font-label text-[11px] text-[#a098b0]">
                    <span className="w-2 h-2 rounded-full bg-[#10b981] motion-safe:animate-pulse" />
                    <span>Live Operations Console</span>
                  </div>
                  <span className="font-label text-[10px] text-[#ff2d78] font-bold">~200ms</span>
                </div>

                {/* Console Main Content */}
                <div className="p-4 sm:p-5 space-y-4 bg-[#0a0a14]/80">
                  {/* Top Stats Grid */}
                  <div className="grid grid-cols-3 gap-2 sm:gap-3">
                    <div className="glass rounded-xl p-3 border border-white/[0.06] text-center">
                      <p className="text-[9px] text-[#a098b0] uppercase tracking-wider font-label">Active Calls</p>
                      <p className="text-lg sm:text-xl font-headline font-extrabold text-[#f8fafc] mt-0.5">14</p>
                      {/* Animated 14-bar Soundwave Equalizer */}
                      <div className="h-4 flex items-end justify-center gap-[3px] mt-1.5 overflow-hidden">
                        {[0.4, 0.9, 0.6, 1.2, 0.7, 1.0, 0.5, 1.1, 0.65, 0.95, 0.45, 1.15, 0.8, 0.55].map((d, i) => (
                          <div
                            key={i}
                            className={`hero-eq-bar w-1 rounded-full ${
                              playing ? "bg-[#ff2d78] shadow-[0_0_8px_#ff2d78]" : "bg-[#c084fc]/60"
                            }`}
                            style={{
                              height: playing ? `${35 + (i % 4) * 20}%` : `${20 + (i % 3) * 15}%`,
                              animationDelay: playing ? `${i * 0.05}s` : "0s",
                            }}
                          />
                        ))}
                      </div>
                    </div>

                    <div className="glass rounded-xl p-3 border border-white/[0.06] text-center">
                      <p className="text-[9px] text-[#a098b0] uppercase tracking-wider font-label">Handled</p>
                      <p className="text-lg sm:text-xl font-headline font-extrabold text-[#ff2d78] mt-0.5">248</p>
                      <p className="text-[8px] text-[#10b981] font-label mt-1">+18% Today</p>
                    </div>

                    <div className="glass rounded-xl p-3 border border-white/[0.06] text-center">
                      <p className="text-[9px] text-[#a098b0] uppercase tracking-wider font-label">Orders</p>
                      <p className="text-lg sm:text-xl font-headline font-extrabold text-[#c084fc] mt-0.5">1,420</p>
                      <p data-tele-step="0" className="telemetry-line text-[8px] text-[#10b981] font-label mt-1">+24% Synced</p>
                    </div>
                  </div>

                  {/* Simulated Live Call Box (Dynamically Sound-Synced with Sample Speech!) */}
                  <div className="glass rounded-xl p-3.5 sm:p-4 border border-white/[0.08] relative overflow-hidden">
                    <div className="flex items-center justify-between mb-3">
                      <div className="flex items-center gap-2">
                        <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-[#ff2d78]">
                          <path d="M3 18v-6a9 9 0 0 1 18 0v6" />
                          <path d="M21 19a2 2 0 0 1-2 2h-1a2 2 0 0 1-2-2v-3a2 2 0 0 1 2-2h3zM3 19a2 2 0 0 0 2 2h1a2 2 0 0 0 2-2v-3a2 2 0 0 0-2-2H3z" />
                        </svg>
                        <span className="font-headline font-bold text-xs text-[#f8fafc]">
                          {playing ? `Speaking • ${VOICE_META[playing].label}` : "Live Agent Stream"}
                        </span>
                      </div>
                      <span className="bg-[#ff2d78]/20 text-[#ff2d78] text-[8px] px-2 py-0.5 rounded-full font-label font-bold uppercase tracking-wider">
                        {playing ? "AUDIO ACTIVE" : "ONLINE"}
                      </span>
                    </div>

                    <div className="space-y-2.5 font-body text-xs leading-relaxed">
                      <div className="bg-white/[0.04] p-2.5 rounded-xl text-[#a098b0]">
                        <span className="font-label text-[9px] text-[#c084fc] block mb-0.5">Caller (+44 20 7946 0821)</span>
                        &ldquo;Can you check if order #8841 is scheduled and update my delivery details?&rdquo;
                      </div>

                      <div className="bg-[#ff2d78]/10 p-2.5 rounded-xl border border-[#ff2d78]/30 text-[#f8fafc]">
                        <span className="font-label text-[9px] text-[#ff2d78] font-bold block mb-0.5">
                          Voxflow AI Agent (~200ms)
                        </span>
                        {playing ? (
                          <span className="text-[#ff2d78] font-medium motion-safe:animate-pulse">
                            {VOICE_META[playing].bubble}
                          </span>
                        ) : (
                          <span>
                            &ldquo;Order #8841 verified: 48 units dispatched. Your Google Sheet and inventory database have been updated live.&rdquo;
                          </span>
                        )}
                      </div>
                    </div>
                  </div>

                  {/* Telemetry Indicator */}
                  <div className="grid grid-cols-3 gap-2 text-center text-[10px] font-label text-[#a098b0] pt-1">
                    <span>Groq Whisper STT: <strong className="text-[#f8fafc]">84ms</strong></span>
                    <span>Llama 3 Reasoning: <strong className="text-[#f8fafc]">112ms</strong></span>
                    <span>Turn: <strong className="text-[#ff2d78]">196ms</strong></span>
                  </div>
                </div>
              </div>
            </div>
          </div>
          </div>
        </section>

        {/* ═══════════ TRUST METRICS STRIP ═══════════ */}
        <section className="relative">
          <NotchedContainer>
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="grid grid-cols-2 lg:grid-cols-4 stagger-children">
              {[
                ["99.8%", "Transcription Precision", "Fine-tuned UK & Hindi acoustics"],
                ["~200ms", "Telephony Latency", "London eu-west-2 edge cluster"],
                ["UK GDPR", "Data Residency", "Automated retention purge eu-west-2"],
                ["60% Saved", "Operational Efficiency", "Direct Google Sheets & DB 2-way sync"],
              ].map(([v, k, s], i) => (
                <div
                  key={k}
                  className={`glow-hover px-5 py-8 sm:px-8 sm:py-10 ${
                    i > 0 ? "border-l border-white/[0.08]" : ""
                  } ${i >= 2 ? "border-t lg:border-t-0 border-white/[0.08]" : ""}`}
                >
                  <p className="font-headline font-black text-3xl sm:text-4xl text-[#ff2d78] neon-text">{v}</p>
                  <p className="mt-2 font-headline font-bold text-xs sm:text-sm text-[#f8fafc]">{k}</p>
                  <p className="mt-1 font-body text-xs text-[#a098b0]">{s}</p>
                </div>
              ))}
            </div>
            </div>
          </NotchedContainer>
        </section>

        {/* ═══════════ KINETIC NARRATIVE ═══════════ */}
        <section className="kinetic-narrative relative py-28 sm:py-40 border-y border-white/[0.06]" id="narrative">
          {/* Live traffic flowing behind the narrative. */}
          <SignalWires className="opacity-70" />
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 grid lg:grid-cols-[0.62fr_1.38fr] gap-10 lg:gap-20 items-start">
            <div className="lg:sticky lg:top-36">
              <span className="font-label text-[#00ffcc] tracking-[0.24em] uppercase text-[10px] sm:text-xs">01 — Autonomous conversation layer</span>
              <p className="mt-5 max-w-xs font-body text-sm leading-6 text-[#94a3b8]">
                Built for the high-consequence moments between your customers, frontline team, and operational systems.
              </p>
              <div className="mt-8 flex items-center gap-3 text-[10px] font-label uppercase tracking-[0.16em] text-[#a098b0]">
                <span className="h-px w-10 bg-[#00ffcc]/70" />
                Scroll-led signal narrative
              </div>
            </div>
            {/* Letter-level scrub reveal. Retracts in the same order on the way
                back up — see KineticScrollText for why that symmetry is free. */}
            <KineticScrollText
              lines={[
                "Technology that turns chaotic phone traffic",
                "into one connected voice operating system.",
              ]}
              className="font-headline text-4xl leading-[1.05] tracking-[-0.045em] sm:text-6xl lg:text-7xl xl:text-8xl"
            />
          </div>
        </section>

        {/* ═══════════ PLATFORM FEATURES (3 PILLARS) ═══════════ */}
        <section className="py-20 sm:py-28 relative overflow-hidden" id="platform">
          <AmbientGradient />
          <div className="relative z-10 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="text-center mb-16 reveal">
              <span className="font-label text-[#c084fc] tracking-[0.2em] uppercase text-xs mb-3 block neon-text-sm">
                ✦ Enterprise Architecture
              </span>
              <h2 className="font-headline font-extrabold text-3xl sm:text-5xl tracking-tight text-[#f8fafc]">
                Three Pillars of Autonomous Voice
              </h2>
              <p className="text-[#a098b0] text-base sm:text-lg max-w-2xl mx-auto mt-4 font-body">
                Built from the ground up for mission-critical supply chains, freight dispatch, and customer operations.
              </p>
            </div>

            <div className="grid md:grid-cols-3 gap-6 sm:gap-8 stagger-children">
              {[
                {
                  step: "01",
                  title: "Dual-Engine Multilingual Voice",
                  desc: "Whisper STT combined with Llama 3 70B reasoning and low-latency Edge TTS. Flawless code-switching between British English and conversational Hindi.",
                  icon: (
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-[#c084fc]">
                      <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z" />
                      <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
                      <line x1="12" y1="19" x2="12" y2="23" />
                      <line x1="8" y1="23" x2="16" y2="23" />
                    </svg>
                  ),
                },
                {
                  step: "02",
                  title: "Live 2-Way CRM & Sheets Sync",
                  desc: "Every order confirmation, stock inquiry, and call outcome is written directly to your Google Sheets and CRM in real time with automated audit logging.",
                  icon: (
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-[#c084fc]">
                      <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
                      <line x1="3" y1="9" x2="21" y2="9" />
                      <line x1="3" y1="15" x2="21" y2="15" />
                      <line x1="9" y1="3" x2="9" y2="21" />
                      <line x1="15" y1="3" x2="15" y2="21" />
                    </svg>
                  ),
                },
                {
                  step: "03",
                  title: "Enterprise GDPR & eu-west-2",
                  desc: "UK and European data residency. PII redaction, automated transcript retention purge schedules, and exact DID routing with zero tenant leakage.",
                  icon: (
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-[#c084fc]">
                      <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
                    </svg>
                  ),
                },
              ].map((p) => (
                <div
                  key={p.step}
                  className="glass glow-hover rounded-2xl p-6 sm:p-8 border border-white/[0.08] hover:border-[#ff2d78]/50 transition-all duration-300 flex flex-col justify-between"
                >
                  <div>
                    <div className="flex items-center justify-between mb-6">
                      <span className="font-label text-xs font-bold text-[#ff2d78] px-2.5 py-1 rounded-full bg-[#ff2d78]/10 border border-[#ff2d78]/30">
                        {p.step}
                      </span>
                      {p.icon}
                    </div>
                    <h3 className="font-headline font-bold text-xl text-[#f8fafc] mb-3">{p.title}</h3>
                    <p className="font-body text-sm leading-relaxed text-[#a098b0]">{p.desc}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </section>

        <VoiceXray />

        {/* Sticky split capability showcase — pinned swap deck + notched stage. */}
        <StickyCapabilityShowcase />

        {/* ═══════════ DUAL-POV TELEMETRY REVEAL ═══════════ */}
        <section className="grid-horizon py-20 sm:py-28 relative overflow-hidden" id="solutions">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="mb-12 reveal">
              <span className="font-label text-[#c084fc] tracking-[0.25em] uppercase text-xs neon-text-sm">
                02 — Real-Time Telemetry
              </span>
              <h2 className="font-headline font-extrabold text-3xl sm:text-5xl mt-3 tracking-tight text-[#f8fafc]">
                Caller hears a human.
                <br />
                <span className="text-[#a098b0]">You see the machine.</span>
              </h2>
            </div>

            <div className="grid lg:grid-cols-2 gap-6">
              {/* Caller Chat Mockup */}
              <div className="glass rounded-2xl p-5 sm:p-7 border border-white/[0.08]">
                <div className="flex items-center justify-between mb-5">
                  <span className="font-label text-[10px] tracking-[0.2em] uppercase text-[#a098b0]">Caller POV</span>
                  <span className="flex items-center gap-1.5 font-label text-[10px] text-[#10b981]">
                    <span className="w-1.5 h-1.5 rounded-full bg-[#10b981] motion-safe:animate-pulse" /> LIVE • +44 20 7946 0821
                  </span>
                </div>
                <div className="space-y-3 font-body text-sm">
                  <div data-bubble-step="0" className="bubble max-w-[85%] rounded-2xl rounded-bl-sm bg-white/[0.04] border border-white/[0.08] p-3.5 text-[#f8fafc]">
                    &ldquo;Hi, I need to check the inventory status for item SKU-9941.&rdquo;
                    <span className="block mt-1 font-label text-[9px] text-[#a098b0]">English • caller</span>
                  </div>
                  <div data-bubble-step="1" className="bubble ml-auto max-w-[85%] rounded-2xl rounded-br-sm bg-[#ff2d78]/[0.12] border border-[#ff2d78]/40 p-3.5 text-[#f8fafc]">
                    &ldquo;SKU-9941 has 320 units available at Central Depot. Delivery window is open for Thursday.&rdquo;
                    <span className="block mt-1 font-label text-[9px] text-[#ff2d78] font-semibold">VoxFlow • 0.6s turn</span>
                  </div>
                  <div data-bubble-step="2" className="bubble max-w-[85%] rounded-2xl rounded-bl-sm bg-white/[0.04] border border-white/[0.08] p-3.5 text-[#f8fafc]">
                    &ldquo;कृपया 50 यूनिट्स बुक करके शुक्रवार सुबह का स्लॉट कन्फर्म कर दीजिए।&rdquo;
                    <span className="block mt-1 font-label text-[9px] text-[#a098b0]">Hindi • caller</span>
                  </div>
                  <div data-bubble-step="3" className="bubble ml-auto max-w-[85%] rounded-2xl rounded-br-sm bg-[#ff2d78]/[0.12] border border-[#ff2d78]/40 p-3.5 text-[#f8fafc]">
                    &ldquo;50 यूनिट्स बुक कर दी गई हैं। शुक्रवार 08:00–11:00 का स्लॉट लॉक हो गया है और एसएमएस भेज दिया गया है।&rdquo;
                    <span className="block mt-1 font-label text-[9px] text-[#ff2d78] font-semibold">VoxFlow • tool call ✓</span>
                  </div>
                </div>
              </div>

              {/* Engine Log Terminal */}
              <div className="glass glow-hover rounded-2xl p-5 sm:p-7 font-label text-xs sm:text-sm border border-white/[0.08]">
                <div className="flex items-center justify-between mb-5">
                  <span className="text-[10px] tracking-[0.2em] uppercase text-[#a098b0]">Engine POV</span>
                  <span className="text-[10px] text-[#c084fc]">voxflow-core • eu-west-2</span>
                </div>
                <div className="space-y-2.5 text-[#a098b0]">
                  <p data-tele-step="0" className="telemetry-line text-[#a098b0]"><span className="text-white/30">00:00.041</span> connect.stream → PCM 16kHz attached</p>
                  <p><span className="text-white/30">00:00.125</span> Groq Whisper STT ............ <span className="text-[#f8fafc]">84ms</span></p>
                  <p data-tele-step="1" className="telemetry-line text-[#a098b0]"><span className="text-white/30">00:00.237</span> Llama-3-70b tool call ....... <span className="text-[#f8fafc]">112ms</span></p>
                  <p data-tele-step="2" className="telemetry-line text-[#a098b0]"><span className="text-white/30">00:00.288</span> lang detect: hi → en bridge .. <span className="text-[#f8fafc]">51ms</span></p>
                  <p data-tele-step="3" className="telemetry-line text-[#a098b0]"><span className="text-white/30">00:00.391</span> sheets.mirror(commit) ....... <span className="text-[#f8fafc]">63ms</span></p>
                  <p data-tele-step="3" className="telemetry-line text-[#a098b0]"><span className="text-white/30">00:00.196</span> Total glass-to-glass turn ... <span className="text-[#ff2d78] font-bold">196ms</span></p>
                  <p className="term-caret pt-3 text-[#f8fafc]" />
                </div>
                <div className="mt-6 grid grid-cols-3 gap-3 text-center">
                  {[
                    ["STT", "84ms"],
                    ["LLM", "112ms"],
                    ["Turn", "196ms"],
                  ].map(([k, v]) => (
                    <div key={k} className="glass rounded-lg p-3 border border-white/[0.06]">
                      <p className="text-[#ff2d78] font-bold text-base sm:text-lg">{v}</p>
                      <p className="text-[9px] tracking-[0.2em] uppercase text-[#a098b0] mt-1">{k}</p>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* ═══════════ KINETIC 4-HOP PIPELINE ═══════════ */}
        <section id="pipeline-section" className="relative py-20 sm:py-28 border-t border-white/[0.06]">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 w-full grid lg:grid-cols-[1fr_1.2fr] gap-10 items-start">
            <div className="lg:sticky lg:top-28">
              <span className="font-label text-[#c084fc] tracking-[0.25em] uppercase text-xs neon-text-sm">03 — Architecture</span>
              <h2 className="font-headline font-extrabold text-3xl sm:text-5xl mt-3 tracking-tight text-[#f8fafc]">
                Four hops.
                <br />
                <span className="text-[#a098b0]">Zero humans until escalation.</span>
              </h2>
              <p className="mt-4 text-[#a098b0] max-w-sm text-sm sm:text-base leading-relaxed font-body">
                Every call flows through the same audited pipeline. From UK SIP stream ingestion to edge voice synthesis and live sheet commits.
              </p>
              <div className="mt-8 glass rounded-xl p-4 inline-flex items-baseline gap-3 border border-white/[0.08]">
                <span className="font-label text-[10px] tracking-[0.2em] uppercase text-[#a098b0]">Total Pipeline Turn</span>
                <span id="pipe-latency" className="font-label text-3xl font-bold text-[#00ffcc]">196ms</span>
              </div>
            </div>

            <div className="relative pl-8">
              <div className="absolute left-2 top-0 bottom-0 w-px bg-white/[0.08]" aria-hidden="true">
                <div id="pipe-rail-fill" className="pipe-rail w-px bg-gradient-to-b from-[#ff2d78] to-[#00ffcc]" style={{ height: "100%" }} />
              </div>
              <div className="space-y-4">
                {[
                  { step: "01", title: "Amazon Connect", desc: "UK SIP streams terminate, PCM 16kHz audio attached over TLS.", lat: "38ms" },
                  { step: "02", title: "Whisper STT + Llama 3 70B", desc: "Groq transcription → 70B reasoning → function calling.", lat: "84ms" },
                  { step: "03", title: "Tenant PostgreSQL + Sheets", desc: "Scoped tenant reads/writes, live Google Sheets mirror.", lat: "112ms" },
                  { step: "04", title: "Edge TTS + Audit Logging", desc: "Voice synthesized back; transcript, invoice & audit logged.", lat: "196ms" },
                ].map((s, i) => (
                  <div key={s.step} data-pipe-step={i} className="pipe-step glass rounded-2xl p-5 sm:p-6 border border-white/[0.08] hover:border-[#ff2d78]/40 transition-colors">
                    <div className="flex items-baseline justify-between gap-4">
                      <p className="font-label text-xs text-[#ff2d78] font-bold">{s.step}</p>
                      <p className="font-label text-xs text-[#00ffcc]">{s.lat}</p>
                    </div>
                    <h3 className="mt-1 font-headline font-bold text-lg text-[#f8fafc]">{s.title}</h3>
                    <p className="mt-1 text-sm leading-6 text-[#a098b0] font-body">{s.desc}</p>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </section>

        {/* ═══════════ 2-WAY GOOGLE SHEETS LIVE MIRROR ═══════════ */}
        <section id="sheets-section" className="relative py-20 sm:py-28 border-t border-white/[0.06]">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="mb-12 reveal">
              <span className="font-label text-[#c084fc] tracking-[0.25em] uppercase text-xs neon-text-sm">04 — Two-way live sync</span>
              <h2 className="font-headline font-extrabold text-3xl sm:text-5xl mt-3 tracking-tight text-[#f8fafc]">
                The call writes
                <br />
                <span className="text-[#a098b0]">your Google Sheet.</span>
              </h2>
            </div>

            <div className="grid lg:grid-cols-2 gap-6 items-stretch">
              {/* Transcript trigger */}
              <div className="glass glow-hover rounded-2xl p-5 sm:p-7 border border-white/[0.08] flex flex-col">
                <span className="font-label text-[10px] tracking-[0.2em] uppercase text-[#a098b0] mb-5">Transcript → tool calls</span>
                <div className="space-y-3 font-label text-xs sm:text-sm flex-1">
                  <p className="text-[#a098b0]"><span className="text-[#f8fafc]">caller:</span> &ldquo;move delivery to Friday morning&rdquo;</p>
                  <p className="text-[#00ffcc]">→ update_order(#8841, window=&quot;FRI 08–11&quot;)</p>
                  <p className="text-[#a098b0]"><span className="text-[#f8fafc]">agent:</span> &ldquo;Done — confirmation SMS sent.&rdquo;</p>
                  <p className="text-[#00ffcc]">→ log_call(outcome=&quot;rescheduled&quot;, pin_verified=true)</p>
                </div>
                <p id="sheet-commit-label" className="mt-6 font-label text-[11px] text-[#00ffcc]">awaiting tool call…</p>
              </div>

              {/* Frosted sheets UI */}
              <div className="sheets-shell glass rounded-[1.25rem] border border-white/[0.08] overflow-hidden">
                <div className="flex items-center gap-2 px-4 py-3 border-b border-white/[0.08] bg-white/[0.02]">
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-[#10b981]">
                    <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
                    <line x1="3" y1="9" x2="21" y2="9" />
                    <line x1="3" y1="15" x2="21" y2="15" />
                    <line x1="9" y1="3" x2="9" y2="21" />
                    <line x1="15" y1="3" x2="15" y2="21" />
                  </svg>
                  <span className="font-label text-xs text-[#f8fafc]">Voxflow — Call Log</span>
                  <span className="ml-auto inline-flex items-center gap-1.5 font-label text-[10px] text-[#10b981]">
                    <span className="w-1.5 h-1.5 rounded-full bg-[#10b981] motion-safe:animate-pulse" /> syncing
                  </span>
                </div>
                <div className="p-2 sm:p-3 text-[11px] sm:text-xs font-label">
                  <div className="grid grid-cols-4 gap-px text-[#a098b0] uppercase tracking-wider text-[9px] px-2 py-2">
                    <span>Time</span><span>Caller</span><span>Outcome</span><span>PIN</span>
                  </div>
                  {[
                    ["14:02:11", "+44 7700 9123", "rescheduled", "✓"],
                    ["14:02:09", "+44 161 496 002", "invoice sent", "✓"],
                    ["13:58:44", "+44 113 496 881", "stock check", "✓"],
                    ["13:51:02", "+44 20 7946 082", "escalated", "—"],
                  ].map((row, i) => (
                    <div key={i} data-sheet-row={i} className="sheet-row grid grid-cols-4 gap-px rounded-md px-2 py-2.5 text-[#f8fafc]">
                      {row.map((c, j) => <span key={j} className={j === 3 ? "text-[#00ffcc]" : ""}>{c}</span>)}
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </section>

        <DispatchSwitchboard />

        {/* Deep fixed-background parallax — Gargantua poster, gliding quotes. */}
        <ParallaxQuotes />

        {/* ═══════════ ROI & COST SAVINGS CALCULATOR ═══════════ */}
        <section className="py-20 sm:py-28 relative overflow-hidden border-t border-white/[0.06]" id="roi">
          <AmbientGradient />
          <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10">
            <div className="text-center mb-12 reveal">
              <span className="font-label text-[#ffe04a] tracking-[0.25em] uppercase text-xs neon-text-sm">05 — Prove the math</span>
              <h2 className="font-headline font-extrabold text-3xl sm:text-5xl mt-3 tracking-tight text-[#f8fafc]">
                Your ROI, <span className="text-[#ffe04a]">live.</span>
              </h2>
            </div>

            <div className="roi-shell rounded-[1.75rem] border border-white/[0.1] p-6 sm:p-10 grid lg:grid-cols-2 gap-10">
              {/* Sliders */}
              <div className="space-y-8">
                <div>
                  <div className="flex justify-between font-label text-xs mb-3">
                    <span className="text-[#a098b0] uppercase tracking-wider">Daily inbound calls</span>
                    <span className="text-[#f8fafc] font-bold">{roiCalls.toLocaleString()}</span>
                  </div>
                  <input
                    type="range"
                    min={1000}
                    max={50000}
                    step={50}
                    value={roiCalls}
                    onChange={(e) => setRoiCalls(Number(e.target.value))}
                    className="roi-slider w-full"
                    aria-label="Daily inbound calls"
                  />
                </div>
                <div>
                  <div className="flex justify-between font-label text-xs mb-3">
                    <span className="text-[#a098b0] uppercase tracking-wider">Avg call duration</span>
                    <span className="text-[#f8fafc] font-bold">{roiMins} min</span>
                  </div>
                  <input
                    type="range"
                    min={2}
                    max={10}
                    step={1}
                    value={roiMins}
                    onChange={(e) => setRoiMins(Number(e.target.value))}
                    className="roi-slider w-full"
                    aria-label="Average call duration"
                  />
                </div>
                    <p className="font-body text-xs text-[#a098b0] leading-relaxed">
                  Model: fully-loaded operator £14/h vs Voxflow ~£0.12/min. 90% automation containment.
                </p>
                <div className="mt-5 flex items-center justify-between border-t border-white/[0.08] pt-4 font-label text-[10px] uppercase tracking-[0.16em]">
                  <span className="text-[#71808a]">Payback period</span>
                  <span className="text-[#ffe04a]">{paybackDays} days</span>
                </div>
              </div>

              {/* Output */}
              <div className="grid grid-cols-2 gap-4 content-center">
                <div className="glass rounded-2xl p-5 border border-[#ffe04a]/25 col-span-2 text-center glow-hover">
                  <p className="font-headline font-black text-3xl sm:text-5xl text-[#ffe04a]">
                    £{annualSavings.toLocaleString()}
                  </p>
                  <p className="mt-2 font-label text-[10px] tracking-[0.2em] uppercase text-[#a098b0]">Net annual savings</p>
                </div>
                <div className="glass rounded-2xl p-4 border border-white/[0.08] text-center">
                  <p className="font-headline font-bold text-xl sm:text-2xl text-[#00ffcc]">
                    {monthlyHoursSaved.toLocaleString()}h
                  </p>
                  <p className="mt-1 font-label text-[9px] tracking-[0.2em] uppercase text-[#a098b0]">Hours saved / mo</p>
                </div>
                <div className="glass rounded-2xl p-4 border border-white/[0.08] text-center">
                  <p className="font-headline font-bold text-xl sm:text-2xl text-[#ff2d78]">
                    {fteEquivalent}
                  </p>
                  <p className="mt-1 font-label text-[9px] tracking-[0.2em] uppercase text-[#a098b0]">FTE equivalent</p>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* ═══════════ CONNECTED ECOSYSTEM ═══════════ */}
        <section className="py-20 sm:py-28 relative" id="network">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="text-center mb-14 reveal">
              <span className="font-label text-[#c084fc] tracking-[0.2em] uppercase text-xs mb-3 block neon-text-sm">
                ✦ Connected Ecosystem
              </span>
              <h2 className="font-headline font-bold text-3xl sm:text-5xl tracking-tight text-[#f8fafc]">
                Seamless Stack Connectivity
              </h2>
              <p className="text-[#a098b0] text-base sm:text-lg max-w-2xl mx-auto mt-4 font-body">
                Voxflow plugs directly into your existing communication, spreadsheet, and database tooling.
              </p>
            </div>

            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 sm:gap-6 stagger-children">
              {[
                {
                  name: "Amazon Connect",
                  desc: "UK Telephony SIP Streams",
                  icon: (
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-[#ff2d78]">
                      <path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z" />
                    </svg>
                  ),
                },
                {
                  name: "Google Sheets",
                  desc: "Live 2-Way Sheet Mirror",
                  icon: (
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-[#ff2d78]">
                      <rect x="3" y="3" width="18" height="18" rx="2" ry="2" />
                      <line x1="3" y1="9" x2="21" y2="9" />
                      <line x1="3" y1="15" x2="21" y2="15" />
                      <line x1="9" y1="3" x2="9" y2="21" />
                      <line x1="15" y1="3" x2="15" y2="21" />
                    </svg>
                  ),
                },
                {
                  name: "Twilio SMS",
                  desc: "Instant Dispatch Confirmations",
                  icon: (
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-[#ff2d78]">
                      <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
                    </svg>
                  ),
                },
                {
                  name: "PostgreSQL DB",
                  desc: "Isolated Tenant Schema",
                  icon: (
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-[#ff2d78]">
                      <ellipse cx="12" cy="5" rx="9" ry="3" />
                      <path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3" />
                      <path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5" />
                    </svg>
                  ),
                },
                {
                  name: "Stripe Billing",
                  desc: "Metered UK VAT Invoices",
                  icon: (
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-[#ff2d78]">
                      <rect x="1" y="4" width="22" height="16" rx="2" ry="2" />
                      <line x1="1" y1="10" x2="23" y2="10" />
                    </svg>
                  ),
                },
                {
                  name: "Salesforce CRM",
                  desc: "Automatic Contact Sync",
                  icon: (
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-[#ff2d78]">
                      <path d="M21.5 2v6h-6M21.34 15.57a10 10 0 1 1-.57-8.38l5.67-5.67" />
                    </svg>
                  ),
                },
                {
                  name: "Slack & Teams",
                  desc: "Instant Escalation Alerts",
                  icon: (
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-[#ff2d78]">
                      <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9" />
                      <path d="M13.73 21a2 2 0 0 1-3.46 0" />
                    </svg>
                  ),
                },
                {
                  name: "REST & Webhooks",
                  desc: "Custom Automation API",
                  icon: (
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-[#ff2d78]">
                      <polyline points="16 18 22 12 16 6" />
                      <polyline points="8 6 2 12 8 18" />
                    </svg>
                  ),
                },
              ].map((item) => (
                <div
                  key={item.name}
                  className="glass glow-hover rounded-2xl p-5 sm:p-6 border border-white/[0.08] hover:border-[#ff2d78]/50 transition-all duration-300"
                >
                  <div className="mb-3 block">
                    {item.icon}
                  </div>
                  <h3 className="font-headline font-bold text-base text-[#f8fafc]">{item.name}</h3>
                  <p className="font-body text-xs text-[#a098b0] mt-1">{item.desc}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* ═══════════ PRICING TIER MATRIX ═══════════ */}
        <section className="py-20 sm:py-28 relative border-t border-white/[0.06]" id="pricing-preview">
          <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="text-center mb-12 reveal">
              <span className="font-label text-[#c084fc] tracking-[0.25em] uppercase text-xs neon-text-sm">06 — Pricing</span>
              <h2 className="font-headline font-extrabold text-3xl sm:text-5xl mt-3 tracking-tight text-[#f8fafc]">
                Simple, metered, <span className="text-[#ff2d78]">VAT-ready.</span>
              </h2>

              {/* Billing toggle */}
              <div className="mt-6 inline-flex items-center gap-1 glass rounded-full p-1 border border-white/[0.1]">
                {([false, true] as const).map((annual) => (
                  <button
                    key={String(annual)}
                    type="button"
                    onClick={() => setAnnualBilling(annual)}
                    className={`px-5 py-2 rounded-full font-label text-xs transition-all duration-300 cursor-pointer ${
                      annualBilling === annual
                        ? "bg-[#ff2d78] text-white shadow-[0_0_16px_rgba(255,45,120,0.4)]"
                        : "text-[#a098b0] hover:text-white"
                    }`}
                  >
                    {annual ? "Annual −20%" : "Monthly"}
                  </button>
                ))}
              </div>
            </div>

            <div className="grid md:grid-cols-3 gap-5 stagger-children">
              {[
                {
                  name: "Starter",
                  monthly: 49,
                  tag: null,
                  features: ["1 voice line", "500 call mins / mo", "English + Hindi", "Email support"],
                  plan: "starter",
                },
                {
                  name: "Growth",
                  monthly: 149,
                  tag: "Most Popular",
                  features: ["3 voice lines", "2,500 call mins / mo", "PIN verification", "Live Sheet editing", "Priority support"],
                  plan: "growth",
                },
                {
                  name: "Enterprise",
                  monthly: 399,
                  tag: null,
                  features: ["Unlimited lines", "Unmetered minutes", "Dedicated UK DID", "24/7 SLA", "Custom retention & DSAR"],
                  plan: "enterprise",
                },
              ].map((t) => {
                const price = annualBilling ? Math.round(t.monthly * 0.8) : t.monthly;
                const popular = t.tag !== null;
                return (
                  <div
                    key={t.name}
                    className={`glass glow-hover rounded-2xl p-6 sm:p-8 flex flex-col justify-between transition-all duration-300 ${
                      popular
                        ? "border border-[#ff2d78]/50 shadow-[0_0_35px_rgba(255,45,120,0.18)] md:-translate-y-2"
                        : "border border-white/[0.08]"
                    }`}
                  >
                    <div>
                      {t.tag && (
                        <span className="self-start font-label text-[9px] font-bold uppercase tracking-widest bg-[#ff2d78] text-white px-2.5 py-1 rounded-full mb-4 inline-block">
                          {t.tag}
                        </span>
                      )}
                      <h3 className="font-headline font-bold text-lg text-[#f8fafc]">{t.name}</h3>
                      <p className="mt-3">
                        <span className="font-headline font-black text-4xl text-[#f8fafc]">£{price}</span>
                        <span className="font-body text-sm text-[#a098b0]">/mo{annualBilling ? " billed annually" : ""}</span>
                      </p>
                      <ul className="mt-6 space-y-2.5">
                        {t.features.map((f) => (
                          <li key={f} className="flex items-start gap-2 font-body text-sm text-[#a098b0]">
                            <span className="text-[#00ffcc] mt-0.5">✓</span>
                            {f}
                          </li>
                        ))}
                      </ul>
                    </div>
                    <Link
                      href={`/sign-up?plan=${t.plan}`}
                      className={`mt-8 inline-flex items-center justify-center gap-2 px-6 py-3 font-headline font-bold rounded-xl text-sm transition-all active:scale-95 ${
                        popular ? "btn-signal" : "btn-ghost-obs border border-white/[0.1]"
                      }`}
                    >
                      Start Free Trial
                    </Link>
                  </div>
                );
              })}
            </div>
            <p className="mt-6 text-center text-xs text-[#a098b0] font-body">
              Full comparison on <Link href="/pricing" className="text-[#00ffcc] hover:underline">/pricing</Link> • VAT receipts via Stripe • Cancel anytime
            </p>
          </div>
        </section>

        {/* ═══════════ PRODUCTION ARCHITECTURE SPECIFICATION ═══════════ */}
        <section className="py-16 sm:py-24 relative reveal" id="architecture-spec">
          <div className="max-w-5xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="glass rounded-3xl p-8 sm:p-12 border border-white/[0.1] relative overflow-hidden bg-gradient-to-br from-[#0c0d18]/90 via-[#030308]/95 to-[#0c0d18]/90 shadow-[0_20px_50px_rgba(0,0,0,0.8)]">
              <div className="absolute top-0 right-0 w-96 h-96 bg-[#5EEAD4]/5 blur-[120px] rounded-full pointer-events-none" />
              <div className="absolute bottom-0 left-0 w-96 h-96 bg-[#ff2d78]/5 blur-[120px] rounded-full pointer-events-none" />

              <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 border-b border-white/[0.08] pb-8 mb-8">
                <div>
                  <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-[#5EEAD4]/30 bg-[#5EEAD4]/10 text-xs font-mono tracking-widest text-[#5EEAD4] uppercase mb-3">
                    <span className="h-1.5 w-1.5 rounded-full bg-[#5EEAD4] animate-pulse" />
                    ENTERPRISE STACK SPECIFICATION
                  </div>
                  <h3 className="font-headline font-black text-2xl sm:text-3xl text-white tracking-tight">
                    Production-Ready Voice Agent Infrastructure
                  </h3>
                </div>
                <div className="font-mono text-xs text-white/50 border border-white/[0.08] rounded-xl px-4 py-2 bg-black/40">
                  <span className="text-[#5EEAD4]">CANONICAL SLA:</span> ~200ms turn, UK edge
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6 text-left">
                <div className="border-l border-[#5EEAD4]/30 pl-4">
                  <div className="font-mono text-[10px] uppercase tracking-widest text-[#5EEAD4] mb-1">VOICE &amp; STT ENGINE</div>
                  <div className="font-headline font-bold text-base text-white">Groq Whisper v3 Turbo</div>
                  <p className="font-sans text-xs text-white/60 mt-1 leading-relaxed">Streaming int16 audio with sub-100ms transcription turnarounds.</p>
                </div>
                <div className="border-l border-[#ff2d78]/30 pl-4">
                  <div className="font-mono text-[10px] uppercase tracking-widest text-[#ff2d78] mb-1">REASONING &amp; ROUTING</div>
                  <div className="font-headline font-bold text-base text-white">Llama 3.3 70B &amp; Qwen</div>
                  <p className="font-sans text-xs text-white/60 mt-1 leading-relaxed">Deterministic tool calls for stock queries, POs, and logistics updates.</p>
                </div>
                <div className="border-l border-[#00ffcc]/30 pl-4">
                  <div className="font-mono text-[10px] uppercase tracking-widest text-[#00ffcc] mb-1">DATA PLATFORM</div>
                  <div className="font-headline font-bold text-base text-white">PostgreSQL + Sheets Sync</div>
                  <p className="font-sans text-xs text-white/60 mt-1 leading-relaxed">Real-time two-way synchronization into dispatch operations workbooks.</p>
                </div>
                <div className="border-l border-white/20 pl-4">
                  <div className="font-mono text-[10px] uppercase tracking-widest text-white/40 mb-1">TELEPHONY BRIDGE</div>
                  <div className="font-headline font-bold text-base text-white">Amazon Connect SIP</div>
                  <p className="font-sans text-xs text-white/60 mt-1 leading-relaxed">Zero hardware changes with direct UK DID routing and failover.</p>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* ═══════════ FAQ ACCORDION ═══════════ */}
        <section className="py-16 sm:py-24 relative" id="faq">
          <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
            <h2 className="text-center font-headline font-extrabold text-2xl sm:text-4xl text-[#f8fafc] mb-10">
              Frequently Asked Questions
            </h2>
            <div className="space-y-3.5">
              {[
                {
                  q: "Will this work with my existing UK phone numbers?",
                  a: "Yes. Port your DID to Amazon Connect or use a Voxflow-issued UK DID (Enterprise). Exact DID routing guarantees zero cross-tenant leakage.",
                },
                {
                  q: "How does Google Sheets sync work?",
                  a: "Connect a sheet from Dashboard → Settings. Every call outcome and tool edit is mirrored live to your Call Log / Email Log tabs via a per-tenant service account.",
                },
                {
                  q: "What about GDPR & UK Data Residency?",
                  a: "All data stays in AWS London (eu-west-2). Transcripts auto-purge on your retention schedule (30/90 days by default), DSAR export/erasure is one click, and nightly purge runs are audited.",
                },
                {
                  q: "Can I try before purchasing?",
                  a: "Yes. Every account starts with a 14-day free trial with 500 included call minutes and instant access to the simulator.",
                },
              ].map((f) => (
                <details key={f.q} className="glass rounded-xl group border border-white/[0.08]">
                  <summary className="cursor-pointer list-none px-5 py-4 text-sm font-semibold text-[#f8fafc] flex justify-between items-center group-open:text-[#ff2d78] transition-colors">
                    {f.q}
                    <span className="text-[#a098b0] group-open:rotate-180 transition-transform duration-300">▾</span>
                  </summary>
                  <div className="faq-body">
                    <div>
                      <p className="px-5 pb-4 text-sm leading-6 text-[#a098b0] font-body">{f.a}</p>
                    </div>
                  </div>
                </details>
              ))}
            </div>
          </div>
        </section>

        {/* ═══════════ BOTTOM CONVERSION BANNER ═══════════ */}
        <section className="py-20 sm:py-28 relative overflow-hidden" id="cta">
          <AmbientGradient />
          <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 reveal-scale relative z-10">
            <div className="glass rounded-3xl p-8 sm:p-14 text-center relative overflow-hidden border border-[#ff2d78]/30 shadow-[0_0_50px_rgba(255,45,120,0.15)]">
              <div
                className="absolute -top-24 left-1/2 -translate-x-1/2 w-72 h-72 bg-[#ff2d78]/20 blur-[120px] rounded-full pointer-events-none"
                aria-hidden="true"
              />
              <h2 className="font-headline font-extrabold text-3xl sm:text-5xl tracking-tight text-[#f8fafc] relative z-10">
                Go live{" "}
                <span className="bg-gradient-to-r from-[#ff2d78] via-[#f43f5e] to-[#c084fc] bg-clip-text text-transparent neon-text">
                  this week.
                </span>
              </h2>
              <p className="text-[#a098b0] text-sm sm:text-lg mt-4 mb-10 max-w-xl mx-auto relative z-10 font-body">
                Deploy autonomous multilingual voice agents across your supply chain in under 3 minutes. Zero setup fees, 14-day unlimited trial.
              </p>
              <div className="flex flex-col sm:flex-row gap-3 sm:gap-4 justify-center relative z-10">
                <Link
                  href="/pricing"
                  className="btn-signal inline-flex items-center justify-center gap-2 px-8 sm:px-10 py-4 sm:py-5 font-headline font-bold rounded-xl text-sm sm:text-base"
                >
                  Start 14-Day Free Trial
                  <span className="cta-arrow-badge">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                      <line x1="5" y1="12" x2="19" y2="12" />
                      <polyline points="12 5 19 12 12 19" />
                    </svg>
                  </span>
                </Link>
                <Link
                  href="/dashboard/simulator"
                  className="btn-ghost-obs inline-flex items-center justify-center gap-2 px-8 sm:px-10 py-4 sm:py-5 font-headline font-bold rounded-xl text-sm sm:text-base"
                >
                  Live Simulator
                </Link>
              </div>
            </div>
          </div>
        </section>
      </main>
    </>
  );
}
