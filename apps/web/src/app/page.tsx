"use client";
import Link from "next/link";
import { useEffect, useState } from "react";

// Simple voice orb component - CSS/SVG pulsing waveform
function VoiceOrb({ lang, setLang }: { lang: "en" | "hi"; setLang: (l: "en" | "hi") => void }) {
  const [playing, setPlaying] = useState(false);
  const phrases: Record<string, { en: string; hi: string }> = {
    en: { en: "Verifying caller PIN — checking order 9921 now.", hi: "कॉलर पिन सत्यापित — ऑर्डर 9921 देख रहा हूँ।" },
    hi: { en: "Namaste! Order 9921 is in transit, arriving Tuesday.", hi: "नमस्ते! ऑर्डर 9921 रास्ते में है, मंगलवार पहुँचेगा।" },
  };
  const text = lang === "en" ? phrases[lang].en : phrases[lang].hi;
  return (
    <div className="relative flex flex-col items-center">
      {/* Orb */}
      <div className="relative">
        <div className="absolute -inset-6 bg-gradient-to-br from-[#ff2d78]/20 to-[#00ffcc]/15 blur-2xl rounded-full" />
        <button
          onClick={() => setPlaying((p) => !p)}
          aria-label="Play voice preview"
          className="relative w-[220px] h-[220px] sm:w-[260px] sm:h-[260px] rounded-full glass flex flex-col items-center justify-center gap-3 hover:border-[#ff2d78]/40 transition-all duration-300 group overflow-hidden"
        >
          <div className="absolute inset-0 bg-gradient-to-br from-[#ff2d78]/5 to-[#00ffcc]/5 opacity-0 group-hover:opacity-100 transition-opacity" />
          {/* Concentric rings */}
          <div className={`absolute inset-4 rounded-full border border-[#ff2d78]/20 ${playing ? "animate-pulse" : ""}`} />
          <div className={`absolute inset-8 rounded-full border border-[#00ffcc]/15 ${playing ? "animate-pulse" : ""}`} style={{ animationDelay: "0.3s" }} />
          {/* Center icon */}
          <div className={`w-14 h-14 rounded-full bg-gradient-to-br from-[#ff2d78] to-[#ff5996] flex items-center justify-center text-white shadow-[0_0_25px_rgba(255,45,120,0.35)] transition-transform ${playing ? "scale-105" : "group-hover:scale-105"}`}>
            <span className="material-symbols-outlined text-[28px]" style={{ fontVariationSettings: "'FILL' 1" }}>{playing ? "pause" : "graphic_eq"}</span>
          </div>
          {/* Waveform bars */}
          <div className="flex items-end gap-[3px] h-7">
            {[5, 9, 6, 11, 8, 10, 4, 7].map((_, i) => (
              <div key={i} className={`w-[3px] rounded-full bg-gradient-to-t from-[#ff2d78] to-[#00ffcc] ${playing ? "eq-bar" : "opacity-40"}`} style={{ height: playing ? undefined : `${6 + i * 2}px`, animationDelay: `${i * 0.08}s` }} />
            ))}
          </div>
          <span className="text-[10px] font-mono uppercase tracking-[0.15em] text-[#94a3b8]">Live Audio Preview</span>
        </button>
        {/* Floating badge */}
        <div className="absolute -bottom-2 left-1/2 -translate-x-1/2 flex items-center gap-1 rounded-full bg-[#0f0f1c] border border-white/[0.07] px-3 py-1.5 shadow-lg">
          <span className="w-1.5 h-1.5 rounded-full bg-[#00ffcc] animate-pulse" />
          <span className="text-[10px] font-semibold tracking-[0.12em] uppercase text-[#f8fafc] whitespace-nowrap">Sub-300ms First-Byte Audio</span>
        </div>
      </div>
      {/* Lang toggle */}
      <div className="mt-8 flex items-center gap-2">
        <div className="inline-flex rounded-full border border-white/[0.07] bg-[#0f0f1c]/80 p-1">
          {(["en", "hi"] as const).map((l) => (
            <button key={l} onClick={() => setLang(l)} className={`rounded-full px-4 py-1.5 text-xs font-bold transition ${lang === l ? "bg-[#ff2d78] text-white shadow" : "text-[#94a3b8] hover:text-white"}`}>{l === "en" ? "English" : "हिन्दी"}</button>
          ))}
        </div>
        <span className="text-xs text-[#94a3b8] hidden sm:inline">· Tap orb to {playing ? "pause" : "preview"}</span>
      </div>
      <p className="mt-3 max-w-[280px] text-center text-xs leading-5 text-[#94a3b8] italic">&ldquo;{text}&rdquo;</p>
    </div>
  );
}

export default function Home() {
  const [lang, setLang] = useState<"en" | "hi">("en");
  useEffect(() => {
    const els = document.querySelectorAll(".reveal, .reveal-left, .reveal-right, .reveal-scale, .stagger-children");
    if (els.length) {
      const obs = new IntersectionObserver((entries) => entries.forEach((e) => { if (e.isIntersecting) { e.target.classList.add("visible"); obs.unobserve(e.target); } }), { threshold: 0.08, rootMargin: "0px 0px -40px 0px" });
      els.forEach((el) => obs.observe(el));
    }
    const c = document.getElementById("particles-canvas");
    if (c && c.childElementCount === 0) {
      const count = window.innerWidth < 768 ? 18 : 32;
      const colors = ["var(--neon-primary)", "var(--neon-secondary)", "var(--neon-tertiary)"];
      for (let i = 0; i < count; i++) {
        const p = document.createElement("div");
        p.className = "particle";
        p.style.left = Math.random() * 100 + "%";
        p.style.top = Math.random() * 100 + "%";
        p.style.background = colors[i % 3];
        p.style.boxShadow = "0 0 6px " + colors[i % 3];
        const sz = 1 + Math.random() * 2.5 + "px";
        p.style.width = sz; p.style.height = sz;
        p.style.animation = `particle-float ${5 + Math.random() * 7}s ease-in-out ${Math.random() * 8}s infinite alternate`;
        c.appendChild(p);
      }
    }
  }, []);

  return (
    <>
      <div id="particles-canvas" className="fixed inset-0 pointer-events-none z-0 overflow-hidden" aria-hidden="true" />
      <main className="relative z-10">
        {/* HERO */}
        <section className="relative pt-24 pb-10 sm:pt-28 sm:pb-12 overflow-hidden" id="hero">
          <div className="absolute top-1/4 left-[10%] w-[480px] h-[480px] bg-[#ff2d78]/[0.07] blur-[120px] rounded-full pointer-events-none" />
          <div className="absolute bottom-0 right-[15%] w-[400px] h-[400px] bg-[#00ffcc]/[0.05] blur-[120px] rounded-full pointer-events-none" />
          <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="grid lg:grid-cols-[1.15fr_0.85fr] gap-10 lg:gap-8 items-center py-8 sm:py-12">
              <div className="reveal stagger-children">
                <div>
                  <span className="inline-flex items-center gap-2 rounded-full border border-white/[0.07] bg-white/[0.04] px-3 py-1 text-[11px] font-semibold tracking-[0.12em] uppercase text-[#00ffcc] mb-5">
                    <span className="w-1.5 h-1.5 rounded-full bg-[#00ffcc] animate-pulse" /> UK Supply Chain • Amazon Connect • Sub-Second Voice
                  </span>
                  <h1 className="font-headline font-extrabold text-[32px] sm:text-5xl lg:text-[52px] xl:text-[56px] leading-[1.05] tracking-tight text-[#f8fafc]">
                    Autonomous Voice<br />Operations for<br /><span className="text-[#ff2d78] neon-text">Modern Supply Chains</span>
                  </h1>
                  <p className="mt-4 max-w-xl text-[15px] sm:text-[17px] leading-7 text-[#94a3b8]">
                    Deploy intelligent Hindi & English AI agents that verify callers, look up live inventory, mirror to Google Sheets, and resolve logistics escalations in <span className="text-[#f8fafc] font-semibold">sub-300ms</span>.
                  </p>
                  <div className="mt-7 flex flex-wrap gap-3">
                    <Link href="/sign-up" className="inline-flex items-center gap-2 rounded-xl bg-[#ff2d78] px-7 py-3.5 text-sm font-bold text-white shadow-[0_0_25px_rgba(255,45,120,0.35)] hover:shadow-[0_0_30px_rgba(255,45,120,0.5)] hover:scale-[1.02] active:scale-95 transition-all">
                      Start 14-Day Free Trial <span className="material-symbols-outlined text-[18px]">arrow_forward</span>
                    </Link>
                    <Link href="/dashboard/simulator" className="inline-flex items-center gap-2 rounded-xl border border-white/[0.07] bg-white/[0.04] px-7 py-3.5 text-sm font-bold text-[#f8fafc] hover:bg-white/[0.08] hover:border-[#ff2d78]/30 transition-all">
                      Open Live Simulator
                    </Link>
                  </div>
                  <p className="mt-3 text-xs text-[#64748b]">No card required • Cancel in Stripe Portal • VAT receipts included</p>
                  {/* Trust pills - horizontal strip */}
                  <div className="mt-6 flex flex-wrap gap-2">
                    {["99.9% Telephony SLA", "UK eu-west-2 Hosted (London)", "Sub-300ms First-Byte Audio", "Zero-Leak RLS Isolated"].map((t) => (
                      <span key={t} className="inline-flex items-center gap-1.5 rounded-full border border-white/[0.06] bg-[#0f0f1c]/60 px-3 py-1.5 text-[11px] font-medium text-[#94a3b8]">
                        <span className="w-1 h-1 rounded-full bg-[#00ffcc]" /> {t}
                      </span>
                    ))}
                  </div>
                </div>
              </div>
              <div className="reveal-right flex justify-center lg:justify-end">
                <VoiceOrb lang={lang} setLang={setLang} />
              </div>
            </div>
          </div>
          <div className="border-t border-white/[0.06] mt-4" />
        </section>

        {/* TRUSTED STRIP - compact */}
        <section className="py-6 border-b border-white/[0.06] relative overflow-hidden reveal">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-wrap items-center justify-center gap-6 sm:gap-10 text-xs font-semibold tracking-widest uppercase text-[#64748b]">
            <span className="text-[11px] tracking-[0.15em]">Trusted automation for</span>
            <span className="flex items-center gap-6">
              {["ZENITH-TECH", "NEXUS_AI", "CORP_CORE", "PLATFORM_X"].map((b) => (
                <span key={b} className="inline-flex items-center gap-1.5 text-[#94a3b8] opacity-60"><span className="material-symbols-outlined text-[16px]">token</span>{b}</span>
              ))}
            </span>
          </div>
        </section>

        {/* BENTO GRID - 6 items */}
        <section className="py-16 sm:py-20 relative" id="platform">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="reveal mb-8 flex flex-col sm:flex-row sm:items-end justify-between gap-4">
              <div>
                <p className="text-[11px] font-semibold tracking-[0.15em] uppercase text-[#64748b] mb-2">Platform Architecture</p>
                <h2 className="font-headline font-bold text-2xl sm:text-3xl tracking-tight text-[#f8fafc]">Everything supply chains need — no gaps.</h2>
              </div>
              <p className="max-w-md text-sm leading-6 text-[#94a3b8]">Live inventory, caller verification, Sheets mirroring, SLA escalation, GDPR purge, and billing — wired to your existing stack.</p>
            </div>
            <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4 stagger-children">
              {[
                { icon: "record_voice_over", color: "#ff2d78", title: "Multilingual Dual-Engine Voice", body: "Instant EN↔HI switching with emotion-aware VAD. UK English + हिन्दी out of the box, 50+ languages on Enterprise." },
                { icon: "table_chart", color: "#00ffcc", title: "Google Sheets Live Mirror", body: "Two-way sync, zero latency. Sheet edits trigger voice updates; every tool call writes back to your Call / Email tabs." },
                { icon: "shield_lock", color: "#f59e0b", title: "Tier-2 Caller PIN Verification", body: "Automated security gate. 4-digit PIN per supplier, rotation reminders, lockout after N failures — no unauthorised lookups." },
                { icon: "alarm", color: "#f59e0b", title: "Autonomous SLA Escalations", body: "Auto-assignment to staff with countdown timers, fallback SMS, breach alerts, and closed-loop resolution drawer." },
                { icon: "delete_sweep", color: "#94a3b8", title: "Nightly GDPR Purge Runner", body: "Immutable audit logs, 30/90-day retention, DSAR export/erasure, and eu-west-2 residency — UK GDPR by default." },
                { icon: "credit_card", color: "#00ffcc", title: "Self-Serve Stripe Billing", body: "Instant checkout, VAT invoices, tier gating, and Stripe Customer Portal. No card stored on VoxFlow." },
              ].map((f) => (
                <div key={f.title} className="bento-card glass rounded-2xl p-5 sm:p-6 relative overflow-hidden group">
                  <div className="absolute -top-8 -right-8 w-24 h-24 rounded-full blur-2xl opacity-10 group-hover:opacity-20 transition-opacity" style={{ background: f.color }} />
                  <div className="w-10 h-10 rounded-xl bg-white/[0.06] border border-white/[0.07] grid place-items-center mb-4">
                    <span className="material-symbols-outlined text-[20px]" style={{ color: f.color }}>{f.icon}</span>
                  </div>
                  <h3 className="font-headline font-bold text-sm text-[#f8fafc] mb-1.5">{f.title}</h3>
                  <p className="text-xs leading-5 text-[#94a3b8]">{f.body}</p>
                </div>
              ))}
            </div>
            <div className="mt-4 grid sm:grid-cols-2 gap-4 reveal">
              <div className="rounded-2xl border border-white/[0.06] bg-[#0f0f1c]/40 p-5 flex items-center justify-between">
                <div>
                  <p className="text-xs font-bold text-[#f8fafc]">Amazon Connect telephony</p>
                  <p className="text-xs text-[#94a3b8]">UK DID, exact-DID routing, zero cross-tenant leak</p>
                </div>
                <span className="material-symbols-outlined text-[#00ffcc]">call</span>
              </div>
              <div className="rounded-2xl border border-white/[0.06] bg-[#0f0f1c]/40 p-5 flex items-center justify-between">
                <div>
                  <p className="text-xs font-bold text-[#f8fafc]">Sub-second LLM turns</p>
                  <p className="text-xs text-[#94a3b8]">Groq Whisper + gpt-oss-20b, &lt;200ms per turn</p>
                </div>
                <span className="material-symbols-outlined text-[#ff2d78]">bolt</span>
              </div>
            </div>
          </div>
        </section>

        {/* HOW IT WORKS - 4 hops compact */}
        <section className="py-10 sm:py-12 border-y border-white/[0.06] bg-[#0f0f1c]/30" id="architecture">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex items-center justify-between mb-6">
              <h2 className="font-headline font-bold text-lg text-[#f8fafc]">How it works <span className="font-mono text-xs font-normal tracking-widest uppercase text-[#64748b]">— 4 hops, no human until escalation</span></h2>
              <Link href="/dashboard/simulator" className="text-xs font-bold text-[#00ffcc] hover:underline hidden sm:inline">Try simulator →</Link>
            </div>
            <div className="grid sm:grid-cols-4 gap-3">
              {[
                { n: "01", t: "Amazon Connect", d: "UK DID answers, streams PCM to VoxFlow" },
                { n: "02", t: "Whisper + LLM", d: "Groq STT → gpt-oss-20b → tool calls" },
                { n: "03", t: "Tenant DB + Sheets", d: "Scoped reads/writes + live sheet mirror" },
                { n: "04", t: "Voice back + logs", d: "Edge TTS reply, transcript & invoice logged" },
              ].map((s) => (
                <div key={s.n} className="rounded-xl border border-white/[0.06] bg-[#07070e]/60 p-4">
                  <p className="text-[11px] font-mono tracking-widest text-[#00ffcc]">{s.n}</p>
                  <p className="mt-1 text-sm font-bold text-[#f8fafc]">{s.t}</p>
                  <p className="mt-1 text-xs leading-5 text-[#94a3b8]">{s.d}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* STATS STRIP - dense */}
        <section className="py-10 sm:py-12 border-b border-white/[0.06] reveal" id="stats">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 grid grid-cols-2 lg:grid-cols-4 gap-4">
            {[
              { v: "99.8%", l: "Transcription Accuracy" },
              { v: "<100ms", l: "Global Latency" },
              { v: "SOC 2", l: "Type II Security" },
              { v: "50+", l: "Languages Supported" },
            ].map((s) => (
              <div key={s.l} className="rounded-2xl border border-white/[0.06] bg-[#0f0f1c]/40 p-5 text-center">
                <p className="text-2xl sm:text-3xl font-black tracking-tight text-[#f8fafc]">{s.v}</p>
                <p className="mt-1 text-[11px] font-semibold tracking-[0.14em] uppercase text-[#64748b]">{s.l}</p>
              </div>
            ))}
          </div>
        </section>

        {/* INTEGRATIONS - 4 cards dense */}
        <section className="py-16 sm:py-20" id="network">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="text-center mb-8 reveal">
              <p className="text-[11px] font-semibold tracking-[0.15em] uppercase text-[#64748b] mb-2">Integrations</p>
              <h2 className="font-headline font-bold text-2xl sm:text-3xl text-[#f8fafc]">Seamless Connectivity</h2>
              <p className="mt-2 text-sm text-[#94a3b8]">Plugs into your stack. No rip-and-replace.</p>
            </div>
            <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4 stagger-children">
              {[
                { icon: "hub", title: "CRM Sync", desc: "Real-time contact & deal updates" },
                { icon: "chat", title: "Slack & Teams", desc: "Dispatch alerts & summaries" },
                { icon: "database", title: "Data Warehouses", desc: "Snowflake, BigQuery, Redshift" },
                { icon: "api", title: "REST & Webhook", desc: "Custom integrations API" },
              ].map((c) => (
                <div key={c.title} className="glass rounded-2xl p-6 text-center bento-card">
                  <div className="w-12 h-12 rounded-xl bg-white/[0.06] border border-white/[0.07] grid place-items-center mx-auto mb-3">
                    <span className="material-symbols-outlined text-[#00ffcc]">{c.icon}</span>
                  </div>
                  <p className="text-sm font-bold text-[#f8fafc]">{c.title}</p>
                  <p className="text-xs text-[#94a3b8] mt-1">{c.desc}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* TESTIMONIAL + FAQ compact */}
        <section className="py-10 sm:py-14 border-y border-white/[0.06] bg-[#0f0f1c]/20">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 grid lg:grid-cols-2 gap-8">
            <div className="glass rounded-2xl p-6 sm:p-8">
              <span className="material-symbols-outlined text-[#ff2d78]/40 text-3xl">format_quote</span>
              <p className="text-sm sm:text-base leading-6 text-[#f8fafc] italic">&ldquo;VoxFlow transformed our call centre overnight. We scaled from 50 to 5,000 daily calls without adding a single agent.&rdquo;</p>
              <div className="mt-4 flex items-center gap-3">
                <div className="w-8 h-8 rounded-full bg-gradient-to-br from-[#ff2d78] to-[#00ffcc] grid place-items-center text-white text-xs font-bold">S</div>
                <div><p className="text-xs font-bold text-[#f8fafc]">Sarah Chen</p><p className="text-[11px] text-[#94a3b8]">VP Operations, ZenithTech</p></div>
              </div>
            </div>
            <div>
              <h3 className="font-headline font-bold text-lg text-[#f8fafc] mb-4">FAQ</h3>
              <div className="space-y-2">
                {[
                  { q: "Will this work with my existing UK phone numbers?", a: "Yes — port your DID to Amazon Connect or use a VoxFlow-issued UK DID (Enterprise). Exact DID routing guarantees zero cross-tenant leakage." },
                  { q: "How does Google Sheets sync work?", a: "Connect a sheet in Settings. Every call outcome is mirrored live to Call Log / Email Log tabs via a per-tenant service account." },
                  { q: "What about GDPR?", a: "All data stays in eu-west-2. Transcripts auto-purge on your schedule, DSAR export/erasure is one click." },
                ].map((f) => (
                  <details key={f.q} className="rounded-xl border border-white/[0.06] bg-[#0f0f1c]/40 group">
                    <summary className="cursor-pointer list-none px-4 py-3 text-xs font-semibold text-[#f8fafc] flex justify-between group-open:text-[#ff2d78]">{f.q}<span className="text-[#64748b] group-open:rotate-180 transition">▾</span></summary>
                    <div className="px-4 pb-3 text-xs leading-5 text-[#94a3b8]">{f.a}</div>
                  </details>
                ))}
              </div>
            </div>
          </div>
        </section>

        {/* PRICING PREVIEW compact */}
        <section className="py-10 sm:py-14 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-baseline justify-between mb-6">
            <h2 className="font-headline font-bold text-lg text-[#f8fafc]">Transparent pricing — £ GBP billed</h2>
            <Link href="/pricing" className="text-xs font-bold text-[#00ffcc] hover:underline">Full comparison →</Link>
          </div>
          <div className="overflow-hidden rounded-2xl border border-white/[0.06]">
            <div className="grid grid-cols-4 gap-px bg-white/[0.06] text-xs">
              <div className="bg-[#0f0f1c] p-3 font-bold text-[#f8fafc]">Capability</div>
              <div className="bg-[#0f0f1c] p-3 text-center font-bold text-[#f8fafc]">Starter £49</div>
              <div className="bg-[#07070e] p-3 text-center font-bold text-[#ff2d78] border-x border-[#ff2d78]/20">Growth £149 · Popular</div>
              <div className="bg-[#0f0f1c] p-3 text-center font-bold text-[#f8fafc]">Enterprise £399</div>
              {[
                ["Voice lines", "1", "3", "Unlimited"],
                ["Call mins / mo", "500", "2,500", "Unmetered"],
                ["PIN verification", "—", "✓", "✓"],
                ["Dedicated UK DID", "—", "—", "✓"],
              ].map(([cap, a, b, c]) => (
                <div key={cap} className="contents">
                  <div className="bg-[#0a0a12] p-3 text-[#94a3b8]">{cap}</div>
                  <div className="bg-[#0a0a12] p-3 text-center text-[#f8fafc]">{a}</div>
                  <div className="bg-[#07070e] p-3 text-center text-[#f8fafc] border-x border-[#ff2d78]/10">{b}</div>
                  <div className="bg-[#0a0a12] p-3 text-center text-[#f8fafc]">{c}</div>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* COMPACT CTA - anchored, glowing corners */}
        <section className="py-16 sm:py-20" id="cta">
          <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="relative overflow-hidden rounded-3xl border border-white/[0.07] bg-[#0f0f1c]/80 backdrop-blur-2xl p-8 sm:p-10 text-center">
              <div className="absolute -top-16 -left-16 w-40 h-40 bg-[#ff2d78]/15 blur-[40px] rounded-full pointer-events-none" />
              <div className="absolute -bottom-16 -right-16 w-40 h-40 bg-[#00ffcc]/10 blur-[40px] rounded-full pointer-events-none" />
              <div className="absolute top-0 left-0 w-12 h-12 border-t-2 border-l-2 border-[#ff2d78]/30 rounded-tl-3xl" />
              <div className="absolute bottom-0 right-0 w-12 h-12 border-b-2 border-r-2 border-[#00ffcc]/20 rounded-br-3xl" />
              <h2 className="relative font-headline font-extrabold text-2xl sm:text-3xl tracking-tight text-[#f8fafc]">Go live <span className="text-[#ff2d78] neon-text">this week.</span></h2>
              <p className="relative mt-3 text-sm leading-6 text-[#94a3b8] max-w-xl mx-auto">Multilingual voice agents across your supply chain in under 3 minutes. Zero setup fees, 14-day trial, enterprise SLA.</p>
              <div className="relative mt-6 flex flex-col sm:flex-row gap-3 justify-center">
                <Link href="/sign-up" className="inline-flex items-center justify-center gap-2 rounded-xl bg-[#ff2d78] px-8 py-3.5 text-sm font-bold text-white shadow-[0_0_25px_rgba(255,45,120,0.35)] hover:scale-[1.02] active:scale-95 transition-all">Start 14-Day Free Trial <span className="material-symbols-outlined text-[18px]">arrow_forward</span></Link>
                <Link href="/dashboard/simulator" className="inline-flex items-center justify-center gap-2 rounded-xl border border-white/[0.07] bg-white/[0.04] px-8 py-3.5 text-sm font-bold text-[#f8fafc] hover:bg-white/[0.08] transition-all">Open Live Simulator</Link>
              </div>
            </div>
          </div>
        </section>
      </main>
    </>
  );
}
