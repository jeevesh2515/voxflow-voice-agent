"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import CosmicStarfield from "@/components/CosmicStarfield";

export default function Home() {
  const [playing, setPlaying] = useState<"en" | "hi" | null>(null);

  // Natural Lifelike Feature-Focused Voice Playback (No company names, pure capability showcase)
  const playSample = (lang: "en" | "hi") => {
    if (typeof window === "undefined") return;

    if (playing) {
      if ("speechSynthesis" in window) {
        window.speechSynthesis.cancel();
      }
      setPlaying(null);
      return;
    }

    setPlaying(lang);

    // 1. Natural Spoken Audio via SpeechSynthesis
    if ("speechSynthesis" in window) {
      window.speechSynthesis.cancel();

      const text =
        lang === "en"
          ? "Hello! I am your autonomous AI voice agent. I handle incoming customer inquiries, verify orders and shipments, check real-time stock levels, and synchronize all call records directly to your database with sub-second latency. How can I assist your business today?"
          : "नमस्ते! मैं आपका एआई वॉइस असिस्टेंट हूँ। मैं ग्राहकों की कॉल्स का जवाब दे सकता हूँ, ऑर्डर और शिपमेंट की स्थिति बता सकता हूँ, और सभी कॉल्स का डेटा सीधे आपके सिस्टम में तुरंत अपडेट कर सकता हूँ। मैं आपकी क्या सहायता करूँ?";

      const utterance = new SpeechSynthesisUtterance(text);
      utterance.lang = lang === "en" ? "en-GB" : "hi-IN";
      utterance.rate = 1.02;
      utterance.pitch = lang === "en" ? 1.05 : 0.98;

      utterance.onend = () => setPlaying(null);
      utterance.onerror = () => setPlaying(null);

      const voices = window.speechSynthesis.getVoices();
      const matchedVoice = voices.find((v) =>
        lang === "en"
          ? v.lang.includes("en-GB") || v.lang.includes("en-US")
          : v.lang.includes("hi")
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
      osc.frequency.setValueAtTime(lang === "en" ? 440 : 330, ctx.currentTime);
      osc.frequency.exponentialRampToValueAtTime(lang === "en" ? 580 : 390, ctx.currentTime + 0.3);

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

    return () => {
      obs.disconnect();
    };
  }, []);

  return (
    <>
      {/* Subtle, elegant ambient starfield */}
      <CosmicStarfield />

      <main className="relative z-10 bg-transparent">
        {/* ==================== HERO SECTION ==================== */}
        <section
          id="hero"
          className="relative min-h-screen flex items-center pt-28 pb-16 sm:pt-32 sm:pb-24 overflow-hidden grid-bg"
        >
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
            <div className="lg:col-span-7 reveal stagger-children">
              <span className="font-label text-[#c084fc] tracking-[0.2em] uppercase text-xs sm:text-sm mb-4 sm:mb-6 block neon-text-sm">
                ✦ NEXT-GEN MULTILINGUAL VOICE AI
              </span>
              <h1 className="font-headline font-extrabold text-4xl sm:text-5xl lg:text-6xl xl:text-7xl leading-[1.1] tracking-tight mb-6 text-[#f8fafc]">
                Automate High-Volume
                <br />
                <span className="bg-gradient-to-r from-[#ff2d78] via-[#f43f5e] to-[#c084fc] bg-clip-text text-transparent neon-text">
                  Voice Operations
                </span>
              </h1>
              <p className="text-[#a098b0] text-base sm:text-lg lg:text-xl mb-8 max-w-xl font-body leading-relaxed">
                Autonomous voice agents for dispatch, customer service, and order capture. Sub-second response latency, fine-tuned English &amp; Hindi models, and live 2-way database synchronization.
              </p>

              {/* SLA Trust Badges */}
              <div className="flex flex-wrap gap-2.5 mb-8">
                {["Sub-200ms Turn Latency", "London eu-west-2", "UK GDPR Default", "Real-Time Sheets Sync"].map((b) => (
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
                <span className="text-xs font-label text-[#a098b0] uppercase tracking-wider">
                  Test Voice Engine:
                </span>
                {([["en", "English"], ["hi", "Hindi"]] as const).map(([lang, label]) => (
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
                    <span className="material-symbols-outlined text-sm text-[#ff2d78]">
                      {playing === lang ? "graphic_eq" : "play_arrow"}
                    </span>
                    {playing === lang ? `Speaking ${label}...` : `Play ${label} Sample`}
                  </button>
                ))}
              </div>

              {/* CTAs */}
              <div className="flex flex-wrap gap-3 sm:gap-4">
                <Link
                  href="/pricing"
                  className="btn-signal inline-flex items-center gap-2 px-6 sm:px-8 py-3.5 sm:py-4 font-headline font-bold rounded-xl text-sm sm:text-base hover:scale-[1.02] active:scale-95 transition-all shadow-[0_0_25px_rgba(255,45,120,0.4)]"
                >
                  Start 14-Day Free Trial
                  <span className="material-symbols-outlined">arrow_forward</span>
                </Link>
                <Link
                  href="/dashboard/simulator"
                  className="btn-ghost-obs inline-flex items-center gap-2 px-6 sm:px-8 py-3.5 sm:py-4 font-headline font-bold rounded-xl text-sm sm:text-base border border-white/[0.1] hover:border-white/30 transition-all"
                >
                  Live Simulator
                </Link>
              </div>
              <p className="mt-3 text-xs text-[#a098b0]">
                No credit card required • Cancel anytime in Stripe portal • 500 free minutes
              </p>
            </div>

            {/* Right Column: Live Operations Console Mockup Window (Sound-Synced!) */}
            <div className="lg:col-span-5 relative reveal-right">
              <div className="glass rounded-2xl border border-white/[0.12] shadow-[0_20px_60px_rgba(0,0,0,0.7),0_0_35px_rgba(255,45,120,0.15)] overflow-hidden transition-all duration-400">
                {/* Console Window Top Bar */}
                <div className="bg-[#05050a]/90 px-4 py-3 border-b border-white/[0.08] flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div className="w-3 h-3 rounded-full bg-[#ff5f56]/80" />
                    <div className="w-3 h-3 rounded-full bg-[#ffbd2e]/80" />
                    <div className="w-3 h-3 rounded-full bg-[#27c93f]/80" />
                  </div>
                  <div className="flex items-center gap-2 font-label text-[11px] text-[#a098b0]">
                    <span className="w-2 h-2 rounded-full bg-[#10b981] animate-pulse" />
                    <span>Live Operations Console</span>
                  </div>
                  <span className="font-label text-[10px] text-[#ff2d78] font-bold">98ms</span>
                </div>

                {/* Console Main Content */}
                <div className="p-4 sm:p-5 space-y-4 bg-[#0a0a14]/80">
                  {/* Top Stats Grid */}
                  <div className="grid grid-cols-3 gap-2 sm:gap-3">
                    <div className="glass rounded-xl p-3 border border-white/[0.06] text-center">
                      <p className="text-[9px] text-[#a098b0] uppercase tracking-wider font-label">Active Calls</p>
                      <p className="text-lg sm:text-xl font-headline font-extrabold text-[#f8fafc] mt-0.5">14</p>
                      {/* Animated Soundwave Equalizer */}
                      <div className="h-4 flex items-end justify-center gap-1 mt-1.5 overflow-hidden">
                        {[0.4, 0.9, 0.6, 1.2, 0.7, 1.0, 0.5].map((d, i) => (
                          <div
                            key={i}
                            className={`w-1 rounded-full ${
                              playing ? "bg-[#ff2d78] shadow-[0_0_8px_#ff2d78]" : "bg-[#c084fc]/60"
                            }`}
                            style={{
                              height: playing ? `${35 + (i % 4) * 20}%` : `${20 + (i % 3) * 15}%`,
                              animation: playing ? `pulse 0.3s ease-in-out infinite alternate ${i * 0.05}s` : "none",
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
                      <p className="text-[8px] text-[#10b981] font-label mt-1">+24% Synced</p>
                    </div>
                  </div>

                  {/* Simulated Live Call Box (Dynamically Sound-Synced with Sample Speech!) */}
                  <div className="glass rounded-xl p-3.5 sm:p-4 border border-white/[0.08] relative overflow-hidden">
                    <div className="flex items-center justify-between mb-3">
                      <div className="flex items-center gap-2">
                        <span className="material-symbols-outlined text-[#ff2d78] text-sm">support_agent</span>
                        <span className="font-headline font-bold text-xs text-[#f8fafc]">
                          {playing ? (playing === "en" ? "Speaking • English" : "Speaking • Hindi") : "Live Agent Stream"}
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
                          VoxFlow AI Agent (Sub-200ms)
                        </span>
                        {playing === "en" ? (
                          <span className="text-[#ff2d78] font-medium animate-pulse">
                            &ldquo;I handle incoming customer inquiries, verify orders and shipments, check real-time stock levels, and sync records to your database.&rdquo;
                          </span>
                        ) : playing === "hi" ? (
                          <span className="text-[#ff2d78] font-medium animate-pulse">
                            &ldquo;मैं ग्राहकों की कॉल्स का जवाब दे सकता हूँ, ऑर्डर और शिपमेंट की स्थिति बता सकता हूँ, और सारा डेटा सीधे अपडेट कर सकता हूँ।&rdquo;
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
                  <div className="flex items-center justify-between text-[10px] font-label text-[#a098b0] pt-1">
                    <span>Groq Whisper STT: <strong className="text-[#f8fafc]">84ms</strong></span>
                    <span>Llama 3 Reasoning: <strong className="text-[#f8fafc]">112ms</strong></span>
                    <span>Turn: <strong className="text-[#ff2d78]">196ms</strong></span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* ═══════════ TRUST METRICS STRIP ═══════════ */}
        <section className="relative border-y border-white/[0.08] bg-[#050508]/40 backdrop-blur-md">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="grid grid-cols-2 lg:grid-cols-4 stagger-children">
              {[
                ["99.8%", "Transcription Precision", "Fine-tuned UK & Hindi acoustics"],
                ["<100ms", "Telephony Latency", "London eu-west-2 edge cluster"],
                ["SOC 2", "Type II Enterprise", "UK GDPR automated retention purge"],
                ["10x ROI", "Operational Efficiency", "Direct Google Sheets & DB 2-way sync"],
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
        </section>

        {/* ═══════════ PLATFORM FEATURES (3 PILLARS) ═══════════ */}
        <section className="py-20 sm:py-28 relative" id="platform">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
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
                  icon: "record_voice_over",
                },
                {
                  step: "02",
                  title: "Live 2-Way CRM & Sheets Sync",
                  desc: "Every order confirmation, stock inquiry, and call outcome is written directly to your Google Sheets and CRM in real time with automated audit logging.",
                  icon: "table_chart",
                },
                {
                  step: "03",
                  title: "Enterprise GDPR & eu-west-2",
                  desc: "UK and European data residency. PII redaction, automated transcript retention purge schedules, and exact DID routing with zero tenant leakage.",
                  icon: "shield",
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
                      <span className="material-symbols-outlined text-[#c084fc] text-2xl" style={{ fontVariationSettings: "'FILL' 1" }}>
                        {p.icon}
                      </span>
                    </div>
                    <h3 className="font-headline font-bold text-xl text-[#f8fafc] mb-3">{p.title}</h3>
                    <p className="font-body text-sm leading-relaxed text-[#a098b0]">{p.desc}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* ═══════════ DUAL-POV TELEMETRY REVEAL ═══════════ */}
        <section className="py-20 sm:py-28 relative" id="solutions">
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
                    <span className="w-1.5 h-1.5 rounded-full bg-[#10b981] animate-pulse" /> LIVE • +44 20 7946 0821
                  </span>
                </div>
                <div className="space-y-3 font-body text-sm">
                  <div className="max-w-[85%] rounded-2xl rounded-bl-sm bg-white/[0.04] border border-white/[0.08] p-3.5 text-[#f8fafc]">
                    &ldquo;Hi, I need to check the inventory status for item SKU-9941.&rdquo;
                    <span className="block mt-1 font-label text-[9px] text-[#a098b0]">English • caller</span>
                  </div>
                  <div className="ml-auto max-w-[85%] rounded-2xl rounded-br-sm bg-[#ff2d78]/[0.12] border border-[#ff2d78]/40 p-3.5 text-[#f8fafc]">
                    &ldquo;SKU-9941 has 320 units available at Central Depot. Delivery window is open for Thursday.&rdquo;
                    <span className="block mt-1 font-label text-[9px] text-[#ff2d78] font-semibold">VoxFlow • 0.6s turn</span>
                  </div>
                  <div className="max-w-[85%] rounded-2xl rounded-bl-sm bg-white/[0.04] border border-white/[0.08] p-3.5 text-[#f8fafc]">
                    &ldquo;कृपया 50 यूनिट्स बुक करके शुक्रवार सुबह का स्लॉट कन्फर्म कर दीजिए।&rdquo;
                    <span className="block mt-1 font-label text-[9px] text-[#a098b0]">Hindi • caller</span>
                  </div>
                  <div className="ml-auto max-w-[85%] rounded-2xl rounded-br-sm bg-[#ff2d78]/[0.12] border border-[#ff2d78]/40 p-3.5 text-[#f8fafc]">
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
                  <p><span className="text-white/30">00:00.041</span> connect.stream → PCM 16kHz attached</p>
                  <p><span className="text-white/30">00:00.125</span> Groq Whisper STT ............ <span className="text-[#f8fafc]">84ms</span></p>
                  <p><span className="text-white/30">00:00.237</span> Llama-3-70b tool call ....... <span className="text-[#f8fafc]">112ms</span></p>
                  <p><span className="text-white/30">00:00.288</span> lang detect: hi → en bridge .. <span className="text-[#f8fafc]">51ms</span></p>
                  <p><span className="text-white/30">00:00.391</span> sheets.mirror(commit) ....... <span className="text-[#f8fafc]">63ms</span></p>
                  <p><span className="text-white/30">00:00.196</span> Total glass-to-glass turn ... <span className="text-[#ff2d78] font-bold">196ms</span></p>
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
                VoxFlow plugs directly into your existing communication, spreadsheet, and database tooling.
              </p>
            </div>

            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 sm:gap-6 stagger-children">
              {[
                { name: "Amazon Connect", desc: "UK Telephony SIP Streams", icon: "call" },
                { name: "Google Sheets", desc: "Live 2-Way Sheet Mirror", icon: "table_chart" },
                { name: "Twilio SMS", desc: "Instant Dispatch Confirmations", icon: "sms" },
                { name: "PostgreSQL DB", desc: "Isolated Tenant Schema", icon: "database" },
                { name: "Stripe Billing", desc: "Metered UK VAT Invoices", icon: "credit_card" },
                { name: "Salesforce CRM", desc: "Automatic Contact Sync", icon: "sync" },
                { name: "Slack & Teams", desc: "Instant Escalation Alerts", icon: "notifications" },
                { name: "REST & Webhooks", desc: "Custom Automation API", icon: "api" },
              ].map((item) => (
                <div
                  key={item.name}
                  className="glass glow-hover rounded-2xl p-5 sm:p-6 border border-white/[0.08] hover:border-[#ff2d78]/50 transition-all duration-300"
                >
                  <span className="material-symbols-outlined text-[#ff2d78] text-2xl mb-3 block" style={{ fontVariationSettings: "'FILL' 1" }}>
                    {item.icon}
                  </span>
                  <h3 className="font-headline font-bold text-base text-[#f8fafc]">{item.name}</h3>
                  <p className="font-body text-xs text-[#a098b0] mt-1">{item.desc}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* ═══════════ TESTIMONIAL / TRUST PROOF ═══════════ */}
        <section className="py-16 sm:py-24 relative reveal" id="testimonial">
          <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 text-center">
            <div className="glass rounded-3xl p-8 sm:p-14 border border-white/[0.1] relative overflow-hidden">
              <div className="absolute top-0 left-1/2 -translate-x-1/2 w-48 h-48 bg-[#ff2d78]/10 blur-[100px] rounded-full pointer-events-none" />
              <span className="material-symbols-outlined text-[#ff2d78]/30 text-5xl block mb-6" style={{ fontVariationSettings: "'FILL' 1" }}>
                format_quote
              </span>
              <blockquote className="text-lg sm:text-2xl font-body leading-relaxed text-[#f8fafc] mb-6 italic">
                &ldquo;VoxFlow transformed our dispatch operations overnight. We scaled from 50 to 2,500 daily driver calls without hiring extra operators. The English-Hindi multilingual accuracy is unreal.&rdquo;
              </blockquote>
              <p className="font-headline font-bold text-sm text-[#ff2d78]">Director of Logistics</p>
              <p className="font-body text-xs text-[#a098b0]">UK Beverage &amp; Freight Network</p>
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
                  a: "Yes. Port your DID to Amazon Connect or use a VoxFlow-issued UK DID (Enterprise). Exact DID routing guarantees zero cross-tenant leakage.",
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
        <section className="py-20 sm:py-28 relative" id="cta">
          <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 reveal-scale">
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
                  <span className="material-symbols-outlined">arrow_forward</span>
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
