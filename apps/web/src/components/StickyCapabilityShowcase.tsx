"use client";

import { useEffect, useRef, useState } from "react";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";

/**
 * Terminal-style sticky split showcase.
 *
 * Desktop: a 300vh section whose inner viewport pins (CSS sticky). A
 * ScrollTrigger scrub maps scroll progress to one of four capability steps.
 * The left column swaps cards (keyed, direction-aware); the right notched
 * stage cross-fades the matching technical display.
 *
 * The active step is DERIVED from continuous scroll progress on every update —
 * never latched — so scrolling back up walks the steps in exact reverse with
 * no stuck state. Mobile gets the same content as a static vertical stack
 * (no pin, no trap).
 */

type Step = {
  id: string;
  index: string;
  tab: string;
  title: string;
  body: string;
  points: string[];
  accent: string;
};

const STEPS: Step[] = [
  {
    id: "dispatch",
    index: "01",
    tab: "AT DISPATCH",
    title: "Automate & expedite driver check-ins",
    body: "Sub-second SIP stream response with automated POD capture and dock reassignment while the driver is still on the line.",
    points: ["Sub-second SIP response", "Automated POD capture", "Dock reassignment"],
    accent: "#00ffcc",
  },
  {
    id: "warehouse",
    index: "02",
    tab: "IN THE WAREHOUSE",
    title: "Real-time inventory reconciliation",
    body: "Voice-queried SKU lookups, pallet bay counts and dock congestion status — answered from the floor, not a terminal.",
    points: ["Voice SKU lookups", "Pallet bay counts", "Congestion status"],
    accent: "#ff2d78",
  },
  {
    id: "support",
    index: "03",
    tab: "CUSTOMER SUPPORT",
    title: "Zero-human order triage",
    body: "Automated rescheduling, delivery ETA verification and instant CRM commit — escalations arrive with context attached.",
    points: ["Automated rescheduling", "ETA verification", "Instant CRM commit"],
    accent: "#c6ff00",
  },
  {
    id: "erp",
    index: "04",
    tab: "ERP & SHEETS SYNC",
    title: "Bi-directional database writes",
    body: "Zero-human order updates committed live to Postgres and Google Sheets, each write carrying its transcript receipt.",
    points: ["Live Postgres commits", "Sheets 2-way mirror", "Transcript receipts"],
    accent: "#c084fc",
  },
];

/* ── Decorative right-stage displays (pure CSS/SVG, zero JS per frame) ── */

function RadarVisual({ accent }: { accent: string }) {
  return (
    <div className="showcase-visual-inner">
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img src="/lidar-blueprint.jpg" alt="" aria-hidden="true" className="showcase-visual-bg" />
      <svg viewBox="0 0 400 300" className="showcase-visual-fg" aria-hidden="true">
        <g fill="none" stroke={accent} strokeOpacity="0.5">
          <circle cx="200" cy="150" r="40" strokeWidth="1" />
          <circle cx="200" cy="150" r="75" strokeWidth="1" strokeDasharray="4 6" />
          <circle cx="200" cy="150" r="110" strokeWidth="1" />
        </g>
        <g fill={accent}>
          <circle cx="245" cy="105" r="3.5" />
          <circle cx="150" cy="190" r="3" opacity="0.7" />
          <circle cx="285" cy="185" r="2.6" />
          <circle cx="176" cy="96" r="2.4" opacity="0.75" />
        </g>
        <path d="M150 190 L176 96 L245 105 L285 185" fill="none" stroke={accent} strokeWidth="1" strokeOpacity="0.65" strokeDasharray="3 5" />
      </svg>
      <div className="showcase-radar-sweep" style={{ background: `conic-gradient(from 0deg, ${accent}30, transparent 72deg)` }} />
      
      {/* Realtime Telemetry Overlay */}
      <div className="absolute bottom-4 left-4 right-4 flex items-center justify-between rounded-lg border border-white/[0.08] bg-black/75 px-4 py-2.5 backdrop-blur-md font-mono text-[10px]">
        <div className="flex items-center gap-2">
          <span className="h-1.5 w-1.5 rounded-full animate-ping" style={{ backgroundColor: accent }} />
          <span className="text-[#d7e1e5]">RADAR NODE: UK-M6-DISPATCH</span>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-[#a098b0]">LAT: <span className="text-[#00ffcc]">53.4808</span></span>
          <span className="rounded px-1.5 py-0.5" style={{ background: `${accent}22`, color: accent }}>14 ACTIVE TRUCKS</span>
        </div>
      </div>
    </div>
  );
}

function WarehouseVisual({ accent }: { accent: string }) {
  return (
    <div className="showcase-visual-inner">
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img src="/warehouse-lidar.jpg" alt="" aria-hidden="true" className="showcase-visual-bg" />
      <div className="absolute inset-0 bg-gradient-to-t from-black/85 via-transparent to-black/30" />
      
      {/* Realtime Telemetry Overlay */}
      <div className="absolute bottom-4 left-4 right-4 flex items-center justify-between rounded-lg border border-white/[0.08] bg-black/75 px-4 py-2.5 backdrop-blur-md font-mono text-[10px]">
        <div className="flex items-center gap-2">
          <span className="h-1.5 w-1.5 rounded-full animate-ping" style={{ backgroundColor: accent }} />
          <span className="text-[#d7e1e5]">PALLET BAY #04-A</span>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-[#a098b0]">DENSITY: <span className="text-[#00ffcc]">98.4%</span></span>
          <span className="rounded px-1.5 py-0.5" style={{ background: `${accent}22`, color: accent }}>AGV-04 EN ROUTE</span>
        </div>
      </div>
    </div>
  );
}

function WaveformVisual({ accent }: { accent: string }) {
  return (
    <div className="showcase-visual-inner flex flex-col items-center justify-center gap-7 p-8">
      <div className="flex h-20 items-end gap-1.5" aria-hidden="true">
        {[0.5,0.9,0.65,1,0.45,0.8,0.55,0.95,0.7,0.4,0.85,0.6,1,0.5,0.75,0.45,0.9,0.55,0.8,0.65,0.95,0.5,0.7,0.6].map((v, i) => (
          <span
            key={i}
            className="showcase-wave-bar"
            style={{ height: `${v * 100}%`, backgroundColor: accent, animationDelay: `${i * 0.07}s` }}
          />
        ))}
      </div>
      <div className="flex flex-wrap items-center justify-center gap-2">
        {["intent: reschedule_order", "confidence 0.97", "ETA window Fri 08–11"].map((chip) => (
          <span
            key={chip}
            className="rounded-full border border-white/[0.1] bg-white/[0.04] px-3 py-1 font-label text-[9px] uppercase tracking-[0.16em] text-[#d7e1e5]"
          >
            {chip}
          </span>
        ))}
      </div>
    </div>
  );
}

function CommitFeedVisual({ accent }: { accent: string }) {
  const rows = [
    ["14:02:31", "orders", "UPDATE qty=48", "commit 9f3a"],
    ["14:02:29", "sheet!B7", "delivery_window", "commit 9f39"],
    ["14:02:24", "calls", "INSERT transcript", "commit 9f38"],
    ["14:02:19", "orders", "UPDATE status", "commit 9f37"],
    ["14:02:11", "sheet!C3", "stock_delta", "commit 9f36"],
  ];
  return (
    <div className="showcase-visual-inner flex flex-col justify-evenly gap-2 p-6 sm:p-8" aria-hidden="true">
      {rows.map(([t, table, action, badge], i) => (
        <div
          key={badge}
          className={`flex items-center justify-between gap-3 rounded-lg border px-3.5 py-2.5 font-mono text-[11px] ${
            i === 0 ? "showcase-commit-hot" : "border-white/[0.06] bg-white/[0.02] text-[#8c9aa2]"
          }`}
          style={i === 0 ? { borderColor: `${accent}55`, background: `${accent}0f`, color: "#e8e0f0" } : undefined}
        >
          <span className="text-[#71808a]">{t}</span>
          <span className="truncate">{table} · {action}</span>
          <span className="shrink-0 rounded px-1.5 py-0.5 text-[9px]" style={{ background: `${accent}22`, color: accent }}>{badge}</span>
        </div>
      ))}
    </div>
  );
}

function StepVisual({ step }: { step: Step }) {
  switch (step.id) {
    case "dispatch": return <RadarVisual accent={step.accent} />;
    case "warehouse": return <WarehouseVisual accent={step.accent} />;
    case "support": return <WaveformVisual accent={step.accent} />;
    default: return <CommitFeedVisual accent={step.accent} />;
  }
}

function StepCard({ step, total }: { step: Step; total: number }) {
  return (
    <div>
      <span className="font-label text-[10px] uppercase tracking-[0.24em]" style={{ color: step.accent }}>
        {step.index} / {step.tab}
      </span>
      <h3 className="mt-5 font-headline text-3xl font-extrabold leading-[1.08] tracking-[-0.03em] text-white sm:text-4xl lg:text-[2.6rem]">
        {step.title}
      </h3>
      <p className="mt-4 max-w-sm font-body text-sm leading-relaxed text-[#a098b0] sm:text-base">
        {step.body}
      </p>
      <ul className="mt-6 space-y-2.5">
        {step.points.map((p) => (
          <li key={p} className="flex items-center gap-2.5 font-label text-[11px] uppercase tracking-[0.14em] text-[#d7e1e5]">
            <span className="h-1 w-1 rounded-full" style={{ background: step.accent, boxShadow: `0 0 8px ${step.accent}` }} />
            {p}
          </li>
        ))}
      </ul>
      <p className="mt-8 font-label text-[10px] tracking-[0.2em] text-white/20">
        {step.index} — {String(total).padStart(2, "0")}
      </p>
    </div>
  );
}

export default function StickyCapabilityShowcase() {
  const sectionRef = useRef<HTMLElement | null>(null);
  const [active, setActive] = useState(0);
  const [direction, setDirection] = useState<1 | -1>(1);

  useEffect(() => {
    const section = sectionRef.current;
    if (!section) return;
    const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    const desktop = window.matchMedia("(min-width: 1024px)").matches;
    if (reduced || !desktop) return;

    gsap.registerPlugin(ScrollTrigger);

    const trigger = ScrollTrigger.create({
      trigger: section,
      start: "top top",
      end: "bottom bottom",
      scrub: true,
      onUpdate: (self) => {
        // Derived from continuous progress, never latched — exact reverse walk.
        const idx = Math.min(STEPS.length - 1, Math.floor(self.progress * STEPS.length));
        setActive((prev) => {
          if (prev === idx) return prev;
          setDirection(idx > prev ? 1 : -1);
          return idx;
        });
      },
    });

    return () => trigger.kill();
  }, []);

  const step = STEPS[active];

  return (
    <section
      ref={sectionRef}
      id="capabilities"
      className="capability-showcase relative border-y border-white/[0.06] lg:h-[300vh]"
      aria-label="VoxFlow capabilities"
    >
      {/* ── Desktop: pinned split ── */}
      <div className="capability-showcase-sticky sticky top-0 hidden h-screen items-center overflow-hidden lg:flex">
        <div className="mx-auto grid w-full max-w-7xl grid-cols-[40%_60%] items-center gap-12 px-6 lg:px-8">
          {/* Swapping card column. */}
          <div className="relative min-h-[26rem]">
            <div key={step.id} className={`deck-enter-${direction === 1 ? "forward" : "back"}`}>
              <StepCard step={step} total={STEPS.length} />
            </div>
            {/* Step rail. */}
            <div className="mt-10 flex gap-2" aria-hidden="true">
              {STEPS.map((s, i) => (
                <span
                  key={s.id}
                  className="h-0.5 rounded-full transition-all duration-500 ease-[cubic-bezier(0.32,0.72,0,1)]"
                  style={{
                    width: i === active ? 34 : 14,
                    background: i === active ? step.accent : "rgba(255,255,255,0.12)",
                  }}
                />
              ))}
            </div>
          </div>

          {/* Fixed notched visual stage with crossfading displays. */}
          <div className="showcase-stage">
            <div className="showcase-stage-core">
              {STEPS.map((s, i) => (
                <div
                  key={s.id}
                  className={`showcase-visual ${i === active ? "showcase-visual-active" : ""}`}
                  aria-hidden={i !== active}
                >
                  <StepVisual step={s} />
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* ── Mobile: static stack, no pin ── */}
      <div className="capability-showcase-static mx-auto max-w-2xl space-y-14 px-4 py-20 sm:px-6 lg:hidden">
        {STEPS.map((s) => (
          <div key={s.id}>
            <div className="showcase-stage mb-6">
              <div className="showcase-stage-core showcase-stage-core-static">
                <StepVisual step={s} />
              </div>
            </div>
            <StepCard step={s} total={STEPS.length} />
          </div>
        ))}
      </div>
    </section>
  );
}
