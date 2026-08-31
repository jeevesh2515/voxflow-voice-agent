"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

export default function Home() {
  const [playing, setPlaying] = useState<"en" | "hi" | null>(null);

  // 3s synthesized voice-formant sweep (Web Audio, no assets)
  const playSample = (lang: "en" | "hi") => {
    if (playing) return;
    setPlaying(lang);
    const ctx = new AudioContext();
    const base = lang === "en" ? 220 : 180; // hi: lower, more melismatic
    const steps = lang === "en" ? [1, 1.25, 1.1, 1.4, 1.2] : [1, 1.33, 1.19, 1.5, 1.12, 1.26];
    const dur = 3 / steps.length;
    steps.forEach((ratio, i) => {
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      const filt = ctx.createBiquadFilter();
      filt.type = "bandpass";
      filt.frequency.value = 900;
      filt.Q.value = 2;
      osc.type = "sawtooth";
      osc.frequency.value = base * ratio;
      const t0 = ctx.currentTime + i * dur;
      gain.gain.setValueAtTime(0.0001, t0);
      gain.gain.exponentialRampToValueAtTime(0.08, t0 + 0.05);
      gain.gain.exponentialRampToValueAtTime(0.0001, t0 + dur);
      osc.connect(filt).connect(gain).connect(ctx.destination);
      osc.start(t0);
      osc.stop(t0 + dur + 0.05);
    });
    setTimeout(() => {
      setPlaying(null);
      ctx.close();
    }, 3100);
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

    // ── Floating particles (obsidian emerald) ──
    const container = document.getElementById("particles-canvas");
    if (container && container.childElementCount === 0) {
      const count = window.innerWidth < 768 ? 12 : 24;
      const colors = ["#00ffcc", "#10b981", "rgba(255,255,255,0.6)"];
      for (let i = 0; i < count; i++) {
        const p = document.createElement("div");
        p.className = "particle";
        p.style.left = Math.random() * 100 + "%";
        p.style.top = Math.random() * 100 + "%";
        p.style.background = colors[i % 3];
        p.style.boxShadow = "0 0 6px " + colors[i % 3];
        const sz = 1 + Math.random() * 2 + "px";
        p.style.width = sz;
        p.style.height = sz;
        p.style.animation = `particle-float ${4 + Math.random() * 8}s ease-in-out ${Math.random() * 10}s infinite alternate`;
        container.appendChild(p);
      }
    }

    // ── Kinetic scroll engine (rAF, transform-only) ──
    const orb = document.getElementById("voice-orb");
    const hero = document.getElementById("hero");
    const tele = document.getElementById("telemetry-section");
    const pipe = document.getElementById("pipeline-section");
    const sheets = document.getElementById("sheets-section");
    let ticking = false;

    const clamp01 = (v: number) => Math.min(1, Math.max(0, v));
    // progress of scrolling through an element: 0 when its top enters viewport, 1 when past
    const prog = (el: HTMLElement) => {
      const r = el.getBoundingClientRect();
      return clamp01((window.innerHeight - r.top) / (window.innerHeight + r.height * 0.8));
    };

    const onScroll = () => {
      if (ticking) return;
      ticking = true;
      requestAnimationFrame(() => {
        ticking = false;

        // 1. Orb dock: scale + drift toward nav as hero scrolls away
        if (orb && hero) {
          const scrollY = window.scrollY || window.pageYOffset;
          const heroH = hero.offsetHeight || window.innerHeight;
          const heroP = clamp01(scrollY / heroH);
          const scale = 1 - heroP * 0.45;
          const ty = -heroP * 24;
          const tx = heroP * 12;
          orb.style.transform = `translate3d(${tx}vw, ${ty}px, 0) scale(${Math.max(scale, 0.55)})`;
          orb.style.opacity = String(1 - heroP * 0.4);
        }

        // 2. Dual-POV telemetry sync
        if (tele) {
          const p = prog(tele);
          const step = Math.min(3, Math.floor(p * 5) - 1); // -1..3
          tele.querySelectorAll<HTMLElement>("[data-tele-step]").forEach((n) => {
            const i = Number(n.dataset.teleStep);
            n.classList.toggle("telemetry-hot", i <= step);
          });
          tele.querySelectorAll<HTMLElement>("[data-bubble-step]").forEach((n) => {
            const i = Number(n.dataset.bubbleStep);
            n.classList.toggle("bubble-pending", i > step);
          });
        }

        // 3. Pinned pipeline highlight
        if (pipe) {
          const r = pipe.getBoundingClientRect();
          const total = r.height - window.innerHeight;
          const p = clamp01(-r.top / Math.max(total, 1));
          const active = Math.min(3, Math.floor(p * 4));
          pipe.querySelectorAll<HTMLElement>("[data-pipe-step]").forEach((n) => {
            n.classList.toggle("pipe-active", Number(n.dataset.pipeStep) === active);
          });
          const rail = document.getElementById("pipe-rail-fill");
          if (rail) rail.style.height = `${p * 100}%`;
          const badge = document.getElementById("pipe-latency");
          if (badge) {
            const lat = ["38ms", "84ms", "112ms", "196ms"][active];
            if (badge.textContent !== lat) badge.textContent = lat;
          }
        }

        // 4. Sheets mirror row flash
        if (sheets) {
          const p = prog(sheets);
          const litRows = Math.floor(clamp01((p - 0.25) / 0.5) * 4);
          sheets.querySelectorAll<HTMLElement>("[data-sheet-row]").forEach((n) => {
            n.classList.toggle("sheet-flash", Number(n.dataset.sheetRow) < litRows);
          });
          const commit = document.getElementById("sheet-commit-label");
          if (commit) {
            const label = litRows === 0 ? "awaiting tool call…" : `commit ${litRows}/4 → Call Log tab`;
            if (commit.textContent !== label) commit.textContent = label;
          }
        }
      });
    };
    window.addEventListener("scroll", onScroll, { passive: true });
    onScroll();

    // ── Hero mouse-follow spotlight (rAF-throttled, CSS vars) ──
    const spot = document.getElementById("hero-spot");
    let spotTick = false;
    const onMouse = (e: MouseEvent) => {
      if (!spot || spotTick) return;
      spotTick = true;
      requestAnimationFrame(() => {
        spotTick = false;
        const r = spot.getBoundingClientRect();
        spot.style.setProperty("--mx", `${e.clientX - r.left}px`);
        spot.style.setProperty("--my", `${e.clientY - r.top}px`);
      });
    };
    hero?.addEventListener("mousemove", onMouse);

    return () => {
      obs.disconnect();
      window.removeEventListener("scroll", onScroll);
      hero?.removeEventListener("mousemove", onMouse);
    };
  }, []);

  return (
    <>
      <div
        id="particles-canvas"
        className="fixed inset-0 pointer-events-none z-0 overflow-hidden"
        aria-hidden="true"
      />

      <main className="relative z-10 obs-bg">
        {/* ═══════════ SECTION 1 — HERO + VOICE ORB (0–20%) ═══════════ */}
        <section
          id="hero"
          className="relative min-h-screen flex items-center pt-24 pb-16 sm:pt-28 overflow-hidden obs-grid"
        >
          <div
            className="absolute top-1/3 left-1/2 -translate-x-1/2 w-[70vw] h-[70vw] max-w-[720px] max-h-[720px] bg-[#00ffcc]/[0.05] blur-[160px] rounded-full pointer-events-none"
            aria-hidden="true"
          />
          <div id="hero-spot" className="hero-spot absolute inset-0" aria-hidden="true" />

          <div className="relative z-10 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 grid lg:grid-cols-2 gap-12 lg:gap-16 items-center w-full">
            {/* Copy */}
            <div className="reveal stagger-children">
              <span className="font-mono text-[#00ffcc] tracking-[0.25em] uppercase text-xs mb-6 block">
                UK Supply Chain • Amazon Connect • eu-west-2
              </span>
              <h1 className="font-headline font-extrabold text-4xl sm:text-6xl lg:text-7xl leading-[1.05] tracking-tight mb-6 text-[#f8fafc]">
                The voice agent
                <br />
                UK operators
                <br />
                <span className="text-[#00ffcc]">actually trust.</span>
              </h1>
              <p className="text-[#94a3b8] text-base sm:text-lg lg:text-xl mb-8 max-w-md font-body leading-relaxed">
                Sub-second telephony turns, live Google Sheets sync, and UK GDPR by default — from £49/mo.
              </p>

              {/* SLA trust badges */}
              <div className="flex flex-wrap gap-2 mb-8">
                {["Sub-200ms Telephony SLA", "London eu-west-2", "UK GDPR Default"].map((b) => (
                  <span
                    key={b}
                    className="inline-flex items-center gap-2 rounded-full obs-panel px-3 py-1.5 text-[11px] font-mono text-[#94a3b8]"
                  >
                    <span className="w-1.5 h-1.5 rounded-full bg-[#00ffcc] signal-dot" aria-hidden="true" />
                    {b}
                  </span>
                ))}
              </div>

              <div className="flex flex-wrap gap-3 sm:gap-4">
                <Link
                  href="/pricing"
                  className="btn-signal inline-flex items-center gap-2 px-6 sm:px-8 py-3 sm:py-4 font-headline font-bold rounded-xl text-sm sm:text-base"
                >
                  Start 14-Day Free Trial
                  <span className="material-symbols-outlined">arrow_forward</span>
                </Link>
                <Link
                  href="/dashboard/simulator"
                  className="btn-ghost-obs inline-flex items-center gap-2 px-6 sm:px-8 py-3 sm:py-4 font-headline font-bold rounded-xl text-sm sm:text-base"
                >
                  Live Demo
                </Link>
              </div>
              <p className="mt-3 text-xs text-[#94a3b8]">
                No card required • Cancel in Stripe Customer Portal • VAT receipts included
              </p>
            </div>

            {/* Voice orb */}
            <div className="relative flex flex-col items-center justify-center gap-6 reveal-right">
              <div id="voice-orb" className="kinetic relative w-64 h-64 sm:w-80 sm:h-80">
                <div className={`orb-core absolute inset-0 rounded-full bg-[#0a0a12] border border-[#00ffcc]/30 ${playing ? "orb-playing" : ""}`} />
                {/* rotating dashed rings */}
                <svg className="orb-ring absolute inset-0 w-full h-full" viewBox="0 0 100 100" aria-hidden="true">
                  <circle cx="50" cy="50" r="46" fill="none" stroke="rgba(0,255,204,0.35)" strokeWidth="0.5" strokeDasharray="4 6" />
                </svg>
                <svg className="orb-ring-rev absolute inset-4" viewBox="0 0 100 100" aria-hidden="true">
                  <circle cx="50" cy="50" r="44" fill="none" stroke="rgba(16,185,129,0.3)" strokeWidth="0.6" strokeDasharray="2 8" />
                </svg>
                {/* equalizer bars */}
                <div className={`orb-bars absolute inset-0 flex items-center justify-center gap-1.5 ${playing ? "orb-playing" : ""}`} aria-hidden="true">
                  {[0.9, 0.5, 1.1, 0.7, 1.3, 0.6, 1.0, 0.8, 1.2, 0.55, 0.95, 0.7, 1.05].map((d, i) => (
                    <span
                      key={i}
                      className="w-1 rounded-full bg-[#00ffcc]"
                      style={{ height: `${18 + (i % 5) * 10}%`, animationDuration: `${d}s` }}
                    />
                  ))}
                </div>
                {/* center label */}
                <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
                  <span className="font-mono text-[10px] tracking-[0.3em] uppercase text-[#00ffcc]">
                    {playing ? (playing === "en" ? "Playing • EN" : "Playing • HI") : "VoxFlow Engine"}
                  </span>
                  <span className="font-mono text-[10px] text-[#94a3b8] mt-1">
                    {playing ? "3s sample" : "ACTIVE • 196ms"}
                  </span>
                </div>
              </div>

              {/* audio sample pills */}
              <div className="flex items-center gap-3 z-10">
                {([["en", "English"], ["hi", "Hindi"]] as const).map(([lang, label]) => (
                  <button
                    key={lang}
                    type="button"
                    onClick={() => playSample(lang)}
                    disabled={playing !== null}
                    className={`sample-pill inline-flex items-center gap-2 rounded-full obs-panel px-4 py-2 font-mono text-xs text-[#94a3b8] transition-all hover:text-[#f8fafc] hover:border-[#00ffcc]/40 disabled:opacity-60 cursor-pointer ${playing === lang ? "sample-active" : ""}`}
                  >
                    <span className="material-symbols-outlined text-sm text-[#00ffcc]">
                      {playing === lang ? "graphic_eq" : "play_arrow"}
                    </span>
                    Play {label} Sample
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* scroll cue */}
          <div className="absolute bottom-6 left-1/2 -translate-x-1/2 font-mono text-[10px] tracking-[0.3em] uppercase text-[#94a3b8]/60">
            Scroll — engine telemetry ↓
          </div>
        </section>

        {/* ═══════════ TRUST METRICS STRIP ═══════════ */}
        <section className="relative border-y border-white/[0.06] bg-white/[0.01]">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="grid grid-cols-2 lg:grid-cols-4 stagger-children">
              {[
                ["99.8%", "Transcription Accuracy", "Fine-tuned UK/Hindi acoustics"],
                ["<200ms", "Glass-to-Glass Turn", "London eu-west-2 edge"],
                ["SOC 2", "Type II Enterprise", "UK GDPR automated purge"],
                ["2-Way", "Google Sheets Mirror", "Zero-latency read/writes"],
              ].map(([v, k, s], i) => (
                <div
                  key={k}
                  className={`glow-hover px-5 py-8 sm:px-8 sm:py-10 ${i > 0 ? "border-l border-white/[0.06]" : ""} ${i >= 2 ? "border-t lg:border-t-0 border-white/[0.06]" : ""}`}
                >
                  <p className="font-mono font-bold text-2xl sm:text-4xl text-[#00ffcc]">{v}</p>
                  <p className="mt-2 font-headline font-bold text-xs sm:text-sm text-[#f8fafc]">{k}</p>
                  <p className="mt-1 font-mono text-[10px] text-[#94a3b8]">{s}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* ═══════════ SECTION 2 — DUAL-POV TELEMETRY (20–50%) ═══════════ */}
        <section id="solutions" className="relative py-20 sm:py-28 border-t border-white/[0.04]">
          <div id="telemetry-section" className="contents">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="mb-12 reveal">
              <span className="font-mono text-[#00ffcc] tracking-[0.25em] uppercase text-xs">01 — Live call, two points of view</span>
              <h2 className="font-headline font-extrabold text-3xl sm:text-5xl mt-3 tracking-tight text-[#f8fafc]">
                Caller hears a human.
                <br />
                <span className="text-[#94a3b8]">You see the machine.</span>
              </h2>
            </div>

            <div className="grid lg:grid-cols-2 gap-6">
              {/* Caller POV — phone mockup */}
              <div className="obs-panel rounded-2xl p-5 sm:p-7">
                <div className="flex items-center justify-between mb-5">
                  <span className="font-mono text-[10px] tracking-[0.2em] uppercase text-[#94a3b8]">Caller POV</span>
                  <span className="flex items-center gap-1.5 font-mono text-[10px] text-[#00ffcc]">
                    <span className="w-1.5 h-1.5 rounded-full bg-[#00ffcc] animate-pulse" /> LIVE • +44 20 7946 0821
                  </span>
                </div>
                <div className="space-y-3">
                  <div className="bubble max-w-[85%] rounded-2xl rounded-bl-sm bg-white/[0.04] border border-white/[0.06] p-3 text-sm text-[#f8fafc]" data-bubble-step="0">
                    &ldquo;Hi, Varun Beverages order verification — invoice #INV-4471 please.&rdquo;
                    <span className="block mt-1 font-mono text-[9px] text-[#94a3b8]">English • caller</span>
                  </div>
                  <div className="bubble ml-auto max-w-[85%] rounded-2xl rounded-br-sm bg-[#00ffcc]/[0.08] border border-[#00ffcc]/25 p-3 text-sm text-[#f8fafc]" data-bubble-step="1">
                    &ldquo;Invoice #INV-4471: 48 cases, dispatched Tuesday, POD signed at Leeds DC.&rdquo;
                    <span className="block mt-1 font-mono text-[9px] text-[#00ffcc]">VoxFlow • 0.6s turn</span>
                  </div>
                  <div className="bubble max-w-[85%] rounded-2xl rounded-bl-sm bg-white/[0.04] border border-white/[0.06] p-3 text-sm text-[#f8fafc]" data-bubble-step="2">
                    &ldquo;ठीक है, कृपया delivery window बदलकर शुक्रवार सुबह कर दें।&rdquo;
                    <span className="block mt-1 font-mono text-[9px] text-[#94a3b8]">Hindi • caller</span>
                  </div>
                  <div className="bubble ml-auto max-w-[85%] rounded-2xl rounded-br-sm bg-[#00ffcc]/[0.08] border border-[#00ffcc]/25 p-3 text-sm text-[#f8fafc]" data-bubble-step="3">
                    &ldquo;Done — Friday 08:00–11:00. Sheet updated, confirmation SMS sent.&rdquo;
                    <span className="block mt-1 font-mono text-[9px] text-[#00ffcc]">VoxFlow • tool call ✓</span>
                  </div>
                </div>
              </div>

              {/* Engine POV — terminal */}
              <div className="obs-panel glow-hover rounded-2xl p-5 sm:p-7 font-mono text-xs sm:text-sm">
                <div className="flex items-center justify-between mb-5">
                  <span className="text-[10px] tracking-[0.2em] uppercase text-[#94a3b8]">Engine POV</span>
                  <span className="text-[10px] text-[#94a3b8]">voxflow-core • eu-west-2</span>
                </div>
                <div className="space-y-2.5">
                  <p className="telemetry-line text-[#94a3b8]" data-tele-step="0">
                    <span className="text-white/30">00:00.041</span> connect.stream → PCM 16kHz attached
                  </p>
                  <p className="telemetry-line text-[#94a3b8]" data-tele-step="0">
                    <span className="text-white/30">00:00.125</span> Groq Whisper STT ............ <span className="text-[#f8fafc]">84ms</span>
                  </p>
                  <p className="telemetry-line text-[#94a3b8]" data-tele-step="1">
                    <span className="text-white/30">00:00.237</span> Llama-3-70b tool call ....... <span className="text-[#f8fafc]">112ms</span>
                  </p>
                  <p className="telemetry-line text-[#94a3b8]" data-tele-step="2">
                    <span className="text-white/30">00:00.288</span> lang detect: hi → en bridge .. <span className="text-[#f8fafc]">51ms</span>
                  </p>
                  <p className="telemetry-line text-[#94a3b8]" data-tele-step="3">
                    <span className="text-white/30">00:00.391</span> sheets.mirror(commit) ....... <span className="text-[#f8fafc]">63ms</span>
                  </p>
                  <p className="telemetry-line text-[#94a3b8]" data-tele-step="3">
                    <span className="text-white/30">00:00.196</span> Total glass-to-glass turn ... <span className="text-[#00ffcc]">196ms</span>
                  </p>
                  <p className="term-caret pt-3 text-[#f8fafc]" />
                </div>
                <div className="mt-6 grid grid-cols-3 gap-3 text-center">
                  {[
                    ["STT", "84ms"],
                    ["LLM", "112ms"],
                    ["Turn", "196ms"],
                  ].map(([k, v]) => (
                    <div key={k} className="obs-panel-faint rounded-lg p-3">
                      <p className="text-[#00ffcc] font-bold text-base sm:text-lg">{v}</p>
                      <p className="text-[9px] tracking-[0.2em] uppercase text-[#94a3b8] mt-1">{k}</p>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
          </div>
        </section>

        {/* ═══════════ SECTION 3 — PINNED 4-HOP PIPELINE (50–80%) ═══════════ */}
        <section id="pipeline-section" className="relative border-t border-white/[0.04]" style={{ height: "320vh" }}>
          <div className="sticky top-0 min-h-screen flex items-center overflow-hidden obs-grid">
            <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 w-full grid lg:grid-cols-[1fr_1.2fr] gap-10 items-center py-20">
              <div>
                <span className="font-mono text-[#00ffcc] tracking-[0.25em] uppercase text-xs">02 — Architecture</span>
                <h2 className="font-headline font-extrabold text-3xl sm:text-5xl mt-3 tracking-tight text-[#f8fafc]">
                  Four hops.
                  <br />
                  <span className="text-[#94a3b8]">Zero humans until escalation.</span>
                </h2>
                <p className="mt-4 text-[#94a3b8] max-w-sm text-sm sm:text-base leading-relaxed">
                  Every call flows through the same audited pipeline. Scroll to trace a packet from ring to resolution.
                </p>
                <div className="mt-8 obs-panel rounded-xl p-4 inline-flex items-baseline gap-3">
                  <span className="font-mono text-[10px] tracking-[0.2em] uppercase text-[#94a3b8]">Hop latency</span>
                  <span id="pipe-latency" className="font-mono text-3xl font-bold text-[#00ffcc]">38ms</span>
                </div>
              </div>

              <div className="relative pl-8">
                {/* rail */}
                <div className="absolute left-2 top-0 bottom-0 w-px bg-white/[0.06]" aria-hidden="true">
                  <div id="pipe-rail-fill" className="pipe-rail w-px" style={{ height: "0%" }} />
                </div>
                <div className="space-y-4">
                  {[
                    { step: "01", title: "Amazon Connect", desc: "UK DID answers, streams PCM audio to VoxFlow over TLS.", lat: "38ms" },
                    { step: "02", title: "Whisper + LLM", desc: "Groq STT → Llama-3-70b reasoning → tool calls.", lat: "84ms" },
                    { step: "03", title: "Tenant DB + Google Sheets", desc: "Scoped reads/writes, live sheet mirror per tenant.", lat: "112ms" },
                    { step: "04", title: "Voice back + logs", desc: "Edge TTS reply; transcript, invoice & audit logged.", lat: "196ms" },
                  ].map((s, i) => (
                    <div key={s.step} data-pipe-step={i} className="pipe-step obs-surface rounded-2xl p-5 sm:p-6">
                      <div className="flex items-baseline justify-between gap-4">
                        <p className="font-mono text-xs text-[#00ffcc]">{s.step}</p>
                        <p className="font-mono text-xs text-[#94a3b8]">{s.lat}</p>
                      </div>
                      <h3 className="mt-1 font-headline font-bold text-lg text-[#f8fafc]">{s.title}</h3>
                      <p className="mt-1 text-sm leading-6 text-[#94a3b8]">{s.desc}</p>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* ═══════════ SECTION 4 — SHEETS MIRROR (80–100%) ═══════════ */}
        <section id="sheets-section" className="relative py-20 sm:py-28 border-t border-white/[0.04]">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="mb-12 reveal">
              <span className="font-mono text-[#00ffcc] tracking-[0.25em] uppercase text-xs">03 — Two-way live sync</span>
              <h2 className="font-headline font-extrabold text-3xl sm:text-5xl mt-3 tracking-tight text-[#f8fafc]">
                The call writes
                <br />
                <span className="text-[#94a3b8]">your Google Sheet.</span>
              </h2>
            </div>

            <div className="grid lg:grid-cols-2 gap-6 items-stretch">
              {/* Transcript trigger */}
              <div className="obs-panel rounded-2xl p-5 sm:p-7 flex flex-col">
                <span className="font-mono text-[10px] tracking-[0.2em] uppercase text-[#94a3b8] mb-5">Transcript → tool calls</span>
                <div className="space-y-3 font-mono text-xs sm:text-sm flex-1">
                  <p className="text-[#94a3b8]"><span className="text-[#f8fafc]">caller:</span> &ldquo;move delivery to Friday morning&rdquo;</p>
                  <p className="text-[#00ffcc]">→ update_order(INV-4471, window=&quot;FRI 08–11&quot;)</p>
                  <p className="text-[#94a3b8]"><span className="text-[#f8fafc]">agent:</span> &ldquo;Done — confirmation SMS sent.&rdquo;</p>
                  <p className="text-[#00ffcc]">→ log_call(outcome=&quot;rescheduled&quot;, pin_verified=true)</p>
                </div>
                <p id="sheet-commit-label" className="mt-6 font-mono text-[11px] text-[#00ffcc]">awaiting tool call…</p>
              </div>

              {/* Frosted sheets UI */}
              <div className="glass rounded-2xl border border-white/[0.08] overflow-hidden">
                <div className="flex items-center gap-2 px-4 py-3 border-b border-white/[0.06] bg-white/[0.02]">
                  <span className="material-symbols-outlined text-[#10b981] text-lg">table</span>
                  <span className="font-mono text-xs text-[#f8fafc]">VoxFlow — Call Log</span>
                  <span className="ml-auto font-mono text-[10px] text-[#00ffcc]">● syncing</span>
                </div>
                <div className="p-2 sm:p-3 text-[11px] sm:text-xs font-mono">
                  <div className="grid grid-cols-4 gap-px text-[#94a3b8] uppercase tracking-wider text-[9px] px-2 py-2">
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

        {/* ═══════════ SECTION 5 — BENTO + FAQ + CTA ═══════════ */}
        <section className="py-20 sm:py-28 border-t border-white/[0.04]" id="platform">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="mb-12 reveal">
              <span className="font-mono text-[#00ffcc] tracking-[0.25em] uppercase text-xs">04 — Enterprise surface</span>
              <h2 className="font-headline font-extrabold text-3xl sm:text-5xl mt-3 tracking-tight text-[#f8fafc]">
                Built for UK operations.
              </h2>
            </div>

            {/* 6-item bento */}
            <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4 stagger-children">
              {[
                { icon: "record_voice_over", t: "Dual-Engine Voice", d: "Whisper STT + Llama-3-70b reasoning, hot-swapped per tenant. Hindi & English native." },
                { icon: "pin", t: "PIN Verification", d: "Caller identity verified against tenant DB before any order data is spoken aloud." },
                { icon: "shield_lock", t: "GDPR Auto-Purge", d: "eu-west-2 residency. Transcripts purge on your retention schedule; DSAR in one click." },
                { icon: "table", t: "Google Sheets Mirror", d: "Every tool call commits live to your Call Log tab. Ops team never leaves Sheets." },
                { icon: "group", t: "RBAC Isolation", d: "3-tier roles, exact DID routing, zero cross-tenant leakage — verified every release." },
                { icon: "credit_card", t: "Stripe Billing", d: "Metered minutes, VAT receipts, self-serve customer portal. Cancel anytime." },
              ].map((f) => (
                <div key={f.t} className="bento-card glow-hover obs-panel rounded-2xl p-6 sm:p-7">
                  <span className="material-symbols-outlined text-[#00ffcc] text-2xl" style={{ fontVariationSettings: "'FILL' 1" }}>
                    {f.icon}
                  </span>
                  <h3 className="mt-4 font-headline font-bold text-lg text-[#f8fafc]">{f.t}</h3>
                  <p className="mt-2 text-sm leading-6 text-[#94a3b8]">{f.d}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* FAQ */}
        <section className="py-14 sm:py-20 border-t border-white/[0.04]" id="faq">
          <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
            <h2 className="text-center font-headline font-extrabold text-2xl sm:text-3xl text-[#f8fafc] mb-8">FAQ</h2>
            <div className="space-y-3">
              {[
                {
                  q: "Will this work with my existing UK phone numbers?",
                  a: "Yes. Port your DID to Amazon Connect or use a VoxFlow-issued UK DID (Enterprise). Exact DID routing guarantees zero cross-tenant leakage.",
                },
                {
                  q: "How does Google Sheets sync work?",
                  a: "Connect a sheet from Dashboard → Settings. Every call outcome and tool edit is mirrored live to your Call Log / Email Log tabs via a per-tenant service account.",
                },
                {
                  q: "What about GDPR?",
                  a: "All data stays in eu-west-2. Transcripts auto-purge on your retention schedule (30/90 days by default), DSAR export/erasure is one click, and the nightly purge runner is audited.",
                },
              ].map((f) => (
                <details key={f.q} className="obs-panel rounded-xl group">
                  <summary className="cursor-pointer list-none px-5 py-4 text-sm font-semibold text-[#f8fafc] flex justify-between items-center group-open:text-[#00ffcc]">
                    {f.q}
                    <span className="text-[#94a3b8] group-open:rotate-180 transition-transform duration-300">▾</span>
                  </summary>
                  <div className="faq-body">
                    <div>
                      <p className="px-5 pb-4 text-sm leading-6 text-[#94a3b8]">{f.a}</p>
                    </div>
                  </div>
                </details>
              ))}
            </div>
          </div>
        </section>

        {/* Conversion banner */}
        <section className="py-20 sm:py-28 border-t border-white/[0.04] obs-grid" id="cta">
          <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 reveal-scale">
            <div className="obs-panel rounded-3xl p-8 sm:p-14 text-center relative overflow-hidden">
              <div
                className="absolute -top-24 left-1/2 -translate-x-1/2 w-72 h-72 bg-[#00ffcc]/10 blur-[120px] rounded-full pointer-events-none"
                aria-hidden="true"
              />
              <h2 className="font-headline font-extrabold text-3xl sm:text-5xl tracking-tight text-[#f8fafc] relative z-10">
                Go live <span className="text-[#00ffcc]">this week.</span>
              </h2>
              <p className="text-[#94a3b8] text-sm sm:text-lg mt-4 mb-10 max-w-xl mx-auto relative z-10">
                Deploy autonomous multilingual voice agents across your supply chain in under 3 minutes. Zero setup fees, 14-day unlimited trial.
              </p>
              <div className="flex flex-col sm:flex-row gap-3 sm:gap-4 justify-center relative z-10">
                <Link
                  href="/pricing"
                  className="btn-signal inline-flex items-center justify-center gap-2 px-8 sm:px-10 py-4 sm:py-5 font-headline font-bold rounded-xl text-sm sm:text-base"
                >
                  Start 14-Day Free Trial
                  <span className="material-symbols-outlined">arrow_forward</span>
                </Link>
                <Link
                  href="/dashboard/simulator"
                  className="btn-ghost-obs inline-flex items-center justify-center gap-2 px-8 sm:px-10 py-4 sm:py-5 font-headline font-bold rounded-xl text-sm sm:text-base"
                >
                  Live Demo
                </Link>
              </div>
            </div>
          </div>
        </section>
      </main>
    </>
  );
}
