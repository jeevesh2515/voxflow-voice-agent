"use client";

import { useState, useEffect, useRef } from "react";
import Image from "next/image";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";

export interface ZoneModule {
  id: string;
  index: string;
  tabLabel: string;
  title: string;
  subtitle: string;
  body: string;
  tags: string[];
  imageSrc: string;
}

const ZONES: ZoneModule[] = [
  {
    id: "dispatch",
    index: "01",
    tabLabel: "01 // AT DISPATCH",
    title: "Automate & expedite driver check-ins",
    subtitle: "SIP, POD, dock",
    body: "Sub-second SIP stream response with automated POD capture and dock reassignment while the driver is still on the line.",
    tags: ["Sub-second SIP response", "Automated POD capture", "Dock reassignment"],
    imageSrc: "/lidar-blueprint.jpg",
  },
  {
    id: "warehouse",
    index: "02",
    tabLabel: "02 // IN THE WAREHOUSE",
    title: "Real-time inventory reconciliation",
    subtitle: "SKU, bay, congestion",
    body: "Voice-queried SKU lookups, pallet bay counts and dock congestion status — answered directly from the floor, not a terminal.",
    tags: ["Voice SKU lookups", "Pallet bay counts", "Congestion status"],
    imageSrc: "/warehouse-lidar.jpg",
  },
  {
    id: "support",
    index: "03",
    tabLabel: "03 // CUSTOMER SUPPORT",
    title: "Zero-human order triage",
    subtitle: "reschedule, ETA, CRM",
    body: "Automated rescheduling, delivery ETA verification and instant CRM commit — escalations arrive with complete context attached.",
    tags: ["Automated rescheduling", "ETA verification", "Instant CRM commit"],
    imageSrc: "/voice-core-env.jpg",
  },
  {
    id: "erp",
    index: "04",
    tabLabel: "04 // ERP & SHEETS",
    title: "Bi-directional database writes",
    subtitle: "two-way write",
    body: "Zero-human order updates committed live to Postgres and Google Sheets, each write carrying its transcript receipt.",
    tags: ["Live Postgres commits", "Sheets 2-way mirror", "Transcript receipts"],
    imageSrc: "/space-starfield.jpg",
  },
];

/* ── Compact Inset Visuals per Zone ── */

function RadarCompactInset() {
  return (
    <div className="absolute bottom-4 right-4 sm:bottom-6 sm:right-6 w-48 sm:w-56 rounded-2xl border border-white/[0.12] bg-[#030308]/90 backdrop-blur-xl p-3.5 shadow-2xl z-20">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <span className="h-2 w-2 rounded-full bg-[#5EEAD4] animate-ping" />
          <span className="font-mono text-[9px] uppercase tracking-wider text-white font-bold">
            RADAR NODE
          </span>
        </div>
        <span className="font-mono text-[9px] text-[#5EEAD4] bg-[#5EEAD4]/10 px-1.5 py-0.5 rounded border border-[#5EEAD4]/20">
          UK-M6
        </span>
      </div>

      <div className="relative h-20 w-full rounded-xl bg-black/60 border border-white/[0.06] overflow-hidden flex items-center justify-center">
        {/* Radar Rings */}
        <div className="absolute h-16 w-16 rounded-full border border-[#5EEAD4]/20" />
        <div className="absolute h-10 w-10 rounded-full border border-[#5EEAD4]/30" />
        <div className="absolute h-4 w-4 rounded-full border border-[#5EEAD4]/40" />

        {/* Blip dots */}
        <span className="absolute top-3 right-6 h-1.5 w-1.5 rounded-full bg-[#5EEAD4] shadow-[0_0_6px_#5EEAD4]" />
        <span className="absolute bottom-4 left-7 h-1.5 w-1.5 rounded-full bg-[#5EEAD4]/80 shadow-[0_0_6px_#5EEAD4]" />
        <span className="absolute top-6 left-5 h-1 w-1 rounded-full bg-white/70" />

        {/* Radar Sweep Line */}
        <div
          className="absolute inset-0 origin-center animate-spin"
          style={{
            animationDuration: "4s",
            background: "conic-gradient(from 0deg, rgba(94,234,212,0.25) 0deg, transparent 60deg, transparent 360deg)",
          }}
        />
      </div>

      <div className="flex items-center justify-between font-mono text-[9px] text-white/50 mt-2">
        <span>LAT: 53.4808</span>
        <span className="text-[#5EEAD4] font-bold">14 ACTIVE TRUCKS</span>
      </div>
    </div>
  );
}

function WarehouseCompactInset() {
  return (
    <div className="absolute bottom-4 right-4 sm:bottom-6 sm:right-6 w-52 sm:w-60 rounded-2xl border border-white/[0.12] bg-[#030308]/90 backdrop-blur-xl p-4 shadow-2xl z-20">
      <div className="flex items-center justify-between mb-3 border-b border-white/[0.06] pb-2">
        <span className="font-mono text-[10px] uppercase text-[#5EEAD4] font-bold">
          BAY DENSITY #04-A
        </span>
        <span className="font-mono text-[10px] text-emerald-400">98.4%</span>
      </div>
      <div className="space-y-1.5 font-mono text-[10px] text-white/70">
        <div className="flex justify-between">
          <span className="text-white/40">Pallets In Queue</span>
          <span className="text-white font-bold">48 Units</span>
        </div>
        <div className="flex justify-between">
          <span className="text-white/40">AGV Status</span>
          <span className="text-[#5EEAD4]">AGV-04 EN ROUTE</span>
        </div>
        <div className="flex justify-between">
          <span className="text-white/40">Turnaround</span>
          <span className="text-white">3.2 Mins</span>
        </div>
      </div>
    </div>
  );
}

function SupportCompactInset() {
  return (
    <div className="absolute bottom-4 right-4 sm:bottom-6 sm:right-6 w-56 sm:w-64 rounded-2xl border border-white/[0.12] bg-[#030308]/90 backdrop-blur-xl p-4 shadow-2xl z-20">
      <div className="flex items-center justify-between mb-2">
        <span className="font-mono text-[10px] uppercase text-[#5EEAD4] font-bold">
          TRIAGE INTENT
        </span>
        <span className="font-mono text-[10px] text-white/40">CONF 0.98</span>
      </div>
      <div className="p-2.5 rounded-xl bg-white/[0.03] border border-white/[0.06] font-mono text-[10px] text-[#5EEAD4] mb-2">
        intent: reschedule_order
      </div>
      <div className="flex items-center justify-between font-mono text-[9px] text-white/60">
        <span>ETA Window:</span>
        <span className="text-white font-bold">Fri 08:00–11:00</span>
      </div>
    </div>
  );
}

function ERPCommitFeedVisual() {
  const rows = [
    { time: "14:02:31", target: "orders", action: "UPDATE qty=48", badge: "commit 9f3a" },
    { time: "14:02:29", target: "sheet!B7", action: "delivery_window", badge: "commit 9f39" },
    { time: "14:02:24", target: "calls", action: "INSERT transcript", badge: "commit 9f38" },
    { time: "14:02:19", target: "orders", action: "UPDATE status", badge: "commit 9f37" },
  ];

  return (
    <div className="absolute inset-x-4 bottom-4 sm:inset-x-6 sm:bottom-6 rounded-2xl border border-white/[0.12] bg-[#030308]/95 backdrop-blur-xl p-4 shadow-2xl z-20">
      <div className="flex items-center justify-between mb-3 border-b border-white/[0.06] pb-2 font-mono text-[10px]">
        <div className="flex items-center gap-2">
          <span className="h-1.5 w-1.5 rounded-full bg-[#5EEAD4] animate-pulse" />
          <span className="text-white font-bold uppercase">LIVE TWO-WAY WRITE LOG</span>
        </div>
        <span className="text-[#5EEAD4]">200 OK</span>
      </div>
      <div className="space-y-1.5">
        {rows.map((r, i) => (
          <div
            key={i}
            className={`flex items-center justify-between gap-3 px-3 py-1.5 rounded-lg border font-mono text-[10px] ${
              i === 0
                ? "border-[#5EEAD4]/40 bg-[#5EEAD4]/10 text-white"
                : "border-white/[0.04] bg-white/[0.01] text-white/60"
            }`}
          >
            <span className="text-white/40">{r.time}</span>
            <span className="truncate">{r.target} · {r.action}</span>
            <span className="text-[#5EEAD4] font-bold">{r.badge}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

export default function FourZones() {
  const [activeZone, setActiveZone] = useState<number>(0);
  const sectionRef = useRef<HTMLElement | null>(null);

  useEffect(() => {
    if (typeof window === "undefined") return;
    gsap.registerPlugin(ScrollTrigger);

    const prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (prefersReducedMotion || !sectionRef.current) return;

    const ctx = gsap.context(() => {
      gsap.fromTo(
        ".zone-card-item",
        { opacity: 0, y: 35 },
        {
          opacity: 1,
          y: 0,
          duration: 0.85,
          stagger: 0.15,
          ease: "expo.out",
          scrollTrigger: {
            trigger: sectionRef.current,
            start: "top 75%",
          },
        }
      );
    }, sectionRef);

    return () => ctx.revert();
  }, []);

  const currentZone = ZONES[activeZone];

  return (
    <section
      ref={sectionRef}
      id="section-05"
      data-section="05"
      aria-label="05 // Four zones"
      className="relative w-full border-t border-white/[0.06] bg-[#030308] text-white py-28 px-4 sm:px-6 lg:px-8"
    >
      <div className="w-full max-w-7xl mx-auto">
        {/* Section Header */}
        <div className="max-w-3xl mb-14">
          <div className="inline-flex items-center gap-2 px-3.5 py-1 rounded-full border border-white/[0.1] bg-white/[0.02] text-xs font-mono tracking-widest text-[#5EEAD4] uppercase mb-4">
            <span className="h-1.5 w-1.5 rounded-full bg-[#5EEAD4] animate-pulse" />
            05 / 08 • Operations // Four Operating Zones
          </div>
          <h2 className="font-headline font-black text-3xl sm:text-5xl lg:text-6xl tracking-tight text-white leading-[1.08] mb-4">
            One voice OS. <br />
            <span className="text-white/60">Four critical logistics zones.</span>
          </h2>
          <p className="font-sans text-base sm:text-lg text-white/70 max-w-2xl leading-relaxed">
            From driver dock check-ins to automated Google Sheets write-backs, Voxflow connects the voice line directly to physical execution.
          </p>
        </div>

        {/* Tab Selector (Terminal Rhythm Navigation) */}
        <div
          role="tablist"
          aria-label="Four Operating Zones"
          className="grid grid-cols-2 md:grid-cols-4 gap-2 sm:gap-3 p-1.5 rounded-2xl border border-white/[0.08] bg-white/[0.02] backdrop-blur-xl mb-10"
        >
          {ZONES.map((z, idx) => {
            const isSelected = idx === activeZone;
            return (
              <button
                key={z.id}
                type="button"
                role="tab"
                id={`tab-${z.id}`}
                aria-selected={isSelected}
                aria-controls={`panel-${z.id}`}
                tabIndex={isSelected ? 0 : -1}
                onClick={() => setActiveZone(idx)}
                onKeyDown={(e) => {
                  if (e.key === "ArrowRight") {
                    e.preventDefault();
                    const next = (idx + 1) % ZONES.length;
                    setActiveZone(next);
                    document.getElementById(`tab-${ZONES[next].id}`)?.focus();
                  } else if (e.key === "ArrowLeft") {
                    e.preventDefault();
                    const prev = (idx - 1 + ZONES.length) % ZONES.length;
                    setActiveZone(prev);
                    document.getElementById(`tab-${ZONES[prev].id}`)?.focus();
                  } else if (e.key === "Home") {
                    e.preventDefault();
                    setActiveZone(0);
                    document.getElementById(`tab-${ZONES[0].id}`)?.focus();
                  } else if (e.key === "End") {
                    e.preventDefault();
                    setActiveZone(ZONES.length - 1);
                    document.getElementById(`tab-${ZONES[ZONES.length - 1].id}`)?.focus();
                  }
                }}
                className={`flex flex-col items-start p-3.5 sm:p-4 rounded-xl text-left transition-all duration-200 cursor-pointer ${
                  isSelected
                    ? "bg-[#5EEAD4]/15 border border-[#5EEAD4]/40 shadow-[0_0_20px_rgba(94,234,212,0.15)] text-white"
                    : "border border-transparent text-white/50 hover:text-white hover:bg-white/[0.03]"
                }`}
              >
                <span className="font-mono text-[10px] uppercase tracking-wider text-[#5EEAD4] font-bold mb-1">
                  {z.index} // {z.subtitle}
                </span>
                <span className="font-headline font-bold text-xs sm:text-sm text-white tracking-wide truncate w-full">
                  {z.tabLabel.replace(/^\d+\s*\/\/\s*/, "")}
                </span>
              </button>
            );
          })}
        </div>

        {/* Active Zone Display (Desktop: Split Layout with Mask Reveal / Mobile: Full View) */}
        <div
          id={`panel-${currentZone.id}`}
          role="tabpanel"
          data-active-zone={currentZone.id}
          data-zone-index={currentZone.index}
          aria-labelledby={`tab-${currentZone.id}`}
          className="zone-card-item grid grid-cols-1 lg:grid-cols-12 gap-8 items-center rounded-3xl border border-white/[0.1] bg-[#030308]/90 backdrop-blur-2xl p-6 sm:p-10 shadow-[inset_0_1px_1px_rgba(255,255,255,0.08),0_25px_50px_rgba(0,0,0,0.85)]"
        >
          {/* Left Column: Zone Content & Specifications (5 Cols) */}
          <div className="lg:col-span-5 flex flex-col justify-between space-y-6">
            <div>
              <div className="flex items-center gap-2 mb-4">
                <span className="px-2.5 py-0.5 rounded-full font-mono text-[10px] font-bold bg-[#5EEAD4]/10 border border-[#5EEAD4]/30 text-[#5EEAD4]">
                  ZONE {currentZone.index}
                </span>
                <span className="font-mono text-xs text-white/40 uppercase tracking-wider">
                  {currentZone.subtitle}
                </span>
              </div>

              <h3 className="font-headline font-black text-2xl sm:text-4xl text-white tracking-tight leading-tight mb-4">
                {currentZone.title}
              </h3>

              <p className="font-sans text-base text-white/70 leading-relaxed mb-8">
                {currentZone.body}
              </p>

              {/* Feature Points / Badges */}
              <ul className="space-y-3 pt-4 border-t border-white/[0.06]">
                {currentZone.tags.map((tag, i) => (
                  <li key={i} className="flex items-center gap-3 font-mono text-xs text-white/80">
                    <span className="h-1.5 w-1.5 rounded-full bg-[#5EEAD4] shadow-[0_0_8px_#5EEAD4]" />
                    {tag}
                  </li>
                ))}
              </ul>
            </div>

            <div className="pt-6 border-t border-white/[0.06] flex items-center justify-between font-mono text-xs text-white/40">
              <span>VOXFLOW DISPATCH ENGINE</span>
              <span className="text-[#5EEAD4]">UK EDGE ~200MS</span>
            </div>
          </div>

          {/* Right Column: Masked Still Visual + Compact Inset Widget (7 Cols) */}
          <div className="lg:col-span-7 relative h-72 sm:h-96 md:h-[420px] w-full rounded-2xl border border-white/[0.08] overflow-hidden bg-black/60 shadow-inner">
            {/* Visual Still with Soft Mask */}
            <Image
              src={currentZone.imageSrc}
              alt={`${currentZone.title} illustration`}
              fill
              className="object-cover opacity-60 mix-blend-luminosity filter brightness-90 contrast-125"
              priority
            />
            <div className="absolute inset-0 bg-gradient-to-t from-[#030308] via-transparent to-[#030308]/40 pointer-events-none" />
            <div className="absolute inset-0 bg-radial-gradient from-transparent via-[#030308]/30 to-[#030308] pointer-events-none" />

            {/* Zone-Specific Inset Overlay */}
            {currentZone.id === "dispatch" && <RadarCompactInset />}
            {currentZone.id === "warehouse" && <WarehouseCompactInset />}
            {currentZone.id === "support" && <SupportCompactInset />}
            {currentZone.id === "erp" && <ERPCommitFeedVisual />}
          </div>
        </div>
      </div>
    </section>
  );
}
