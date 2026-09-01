"use client";

import { useState } from "react";

/**
 * Terminal-pattern capability deck: category pills up top, circular prev/next
 * on the right, and a 58% primary + 42% preview card pair beneath.
 *
 * The preview card always shows the NEXT category, dimmed — clicking it is the
 * same as pressing Next. Card transitions animate transform + opacity only, so
 * switching tabs never repaints the surrounding page.
 *
 * Keyboard: pills and buttons are native <button>s (tab-focusable); the deck
 * itself needs no key handling beyond that.
 */

type Capability = {
  id: string;
  tab: string;
  title: string;
  body: string;
  points: string[];
  metric: string;
  metricLabel: string;
  accent: string;
};

const CAPABILITIES: Capability[] = [
  {
    id: "dispatch",
    tab: "AT DISPATCH",
    title: "Automate and expedite driver check-ins & routing",
    body: "Sub-second SIP stream response with automated POD capture and instant slot reallocation when plans change mid-call.",
    points: ["Sub-second SIP response", "Automated POD capture", "Instant slot reallocation"],
    metric: "196ms",
    metricLabel: "turn latency",
    accent: "#00ffcc",
  },
  {
    id: "warehouse",
    tab: "IN THE WAREHOUSE",
    title: "Real-time inventory reconciliation",
    body: "Live voice querying of SKU counts, pallet bay locations and dock congestion — answered from the floor, not a terminal.",
    points: ["SKU counts by voice", "Pallet bay lookups", "Dock congestion status"],
    metric: "Live",
    metricLabel: "stock truth",
    accent: "#ff2d78",
  },
  {
    id: "support",
    tab: "CUSTOMER SUPPORT",
    title: "Every call answered on the first ring",
    body: "English, Hindi or Hinglish — the caller's order history is loaded before the greeting finishes, so nobody repeats themselves.",
    points: ["Multilingual by default", "History pre-loaded", "Zero hold queues"],
    metric: "0",
    metricLabel: "calls abandoned",
    accent: "#c6ff00",
  },
  {
    id: "erp",
    tab: "ERP SYNC",
    title: "Bi-directional database writes",
    body: "Zero-human order updates committed directly to SAP, PostgreSQL and Google Sheets — every write carries its transcript receipt.",
    points: ["SAP & PostgreSQL", "Google Sheets mirror", "Transcript receipts"],
    metric: "100%",
    metricLabel: "writes logged",
    accent: "#c084fc",
  },
];

export default function AsymmetricCapabilitySlider() {
  const [active, setActive] = useState(0);
  const [direction, setDirection] = useState<1 | -1>(1);

  const go = (index: number) => {
    const next = (index + CAPABILITIES.length) % CAPABILITIES.length;
    if (next === active) return;
    setDirection(next > active || (active === CAPABILITIES.length - 1 && next === 0) ? 1 : -1);
    setActive(next);
  };

  const cap = CAPABILITIES[active];
  const preview = CAPABILITIES[(active + 1) % CAPABILITIES.length];

  return (
    <section
      id="capabilities"
      className="relative overflow-hidden border-y border-white/[0.06] py-24 sm:py-32"
      aria-label="VoxFlow capabilities"
    >
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        {/* Header: category pills left, pagination right. */}
        <div className="mb-10 flex flex-col gap-6 sm:mb-14 lg:flex-row lg:items-center lg:justify-between">
          <div
            role="tablist"
            aria-label="Capability categories"
            className="flex gap-2 overflow-x-auto pb-1 [-ms-overflow-style:none] [scrollbar-width:none] [&::-webkit-scrollbar]:hidden"
          >
            {CAPABILITIES.map((c, i) => (
              <button
                key={c.id}
                role="tab"
                aria-selected={i === active}
                type="button"
                onClick={() => go(i)}
                className={`shrink-0 rounded-full border px-4 py-2 font-label text-[10px] uppercase tracking-[0.18em] transition-all duration-500 ease-[cubic-bezier(0.32,0.72,0,1)] ${
                  i === active
                    ? "border-white/[0.2] bg-white/[0.07] text-white"
                    : "border-white/[0.08] bg-transparent text-[#8c9aa2] hover:border-white/[0.16] hover:text-[#e8e0f0]"
                }`}
              >
                {c.tab}
              </button>
            ))}
          </div>

          <div className="flex items-center gap-2.5">
            <button
              type="button"
              onClick={() => go(active - 1)}
              aria-label="Previous capability"
              className="group flex h-11 w-11 items-center justify-center rounded-full border border-white/[0.1] bg-white/[0.03] text-[#e8e0f0] transition-all duration-500 ease-[cubic-bezier(0.32,0.72,0,1)] hover:border-white/30 active:scale-95"
            >
              <span className="material-symbols-outlined text-lg transition-transform duration-500 ease-[cubic-bezier(0.32,0.72,0,1)] group-hover:-translate-x-0.5">
                arrow_back
              </span>
            </button>
            <button
              type="button"
              onClick={() => go(active + 1)}
              aria-label="Next capability"
              className="group flex h-11 w-11 items-center justify-center rounded-full border border-white/[0.1] bg-white/[0.03] text-[#e8e0f0] transition-all duration-500 ease-[cubic-bezier(0.32,0.72,0,1)] hover:border-white/30 active:scale-95"
            >
              <span className="material-symbols-outlined text-lg transition-transform duration-500 ease-[cubic-bezier(0.32,0.72,0,1)] group-hover:translate-x-0.5">
                arrow_forward
              </span>
            </button>
          </div>
        </div>

        {/* 58 / 42 asymmetric deck. Stacks on mobile. */}
        <div className="flex flex-col gap-5 sm:gap-6 lg:flex-row">
          {/* Primary card — keyed so tab changes retrigger the directional entry. */}
          <article
            key={cap.id}
            className={`deck-enter-${direction === 1 ? "forward" : "back"} relative w-full rounded-[2rem] border border-white/[0.12] bg-white/[0.04] p-1.5 lg:w-[58%]`}
            style={{ boxShadow: `0 0 60px ${cap.accent}14` }}
          >
            <div className="relative flex h-full flex-col justify-between overflow-hidden rounded-[calc(2rem-0.375rem)] border border-white/[0.05] bg-[#0d0e17] p-7 shadow-[inset_0_1px_1px_rgba(255,255,255,0.08)] sm:p-10">
              <div
                className="pointer-events-none absolute -right-20 -top-20 h-52 w-52 rounded-full blur-[90px]"
                style={{ background: cap.accent, opacity: 0.14 }}
                aria-hidden="true"
              />

              <div className="relative">
                <span
                  className="font-label text-[10px] uppercase tracking-[0.22em]"
                  style={{ color: cap.accent }}
                >
                  {String(active + 1).padStart(2, "0")} / {cap.tab}
                </span>
                <h3 className="mt-5 max-w-md font-headline text-2xl font-extrabold leading-[1.12] tracking-[-0.025em] text-[#f8fafc] sm:text-3xl lg:text-4xl">
                  {cap.title}
                </h3>
                <p className="mt-4 max-w-md font-body text-sm leading-relaxed text-[#a098b0] sm:text-base">
                  {cap.body}
                </p>

                <ul className="mt-6 space-y-2.5">
                  {cap.points.map((p) => (
                    <li
                      key={p}
                      className="flex items-center gap-2.5 font-label text-[11px] uppercase tracking-[0.14em] text-[#d7e1e5]"
                    >
                      <span
                        className="h-1 w-1 rounded-full"
                        style={{ background: cap.accent, boxShadow: `0 0 8px ${cap.accent}` }}
                      />
                      {p}
                    </li>
                  ))}
                </ul>
              </div>

              <div className="relative mt-10 flex items-end justify-between border-t border-white/[0.06] pt-6">
                <div>
                  <p
                    className="font-headline text-3xl font-extrabold tracking-[-0.03em] sm:text-4xl"
                    style={{ color: cap.accent }}
                  >
                    {cap.metric}
                  </p>
                  <p className="mt-1 font-label text-[10px] uppercase tracking-[0.16em] text-[#a098b0]">
                    {cap.metricLabel}
                  </p>
                </div>
                <span className="font-label text-[10px] tracking-[0.2em] text-white/20">
                  {String(active + 1).padStart(2, "0")} — {String(CAPABILITIES.length).padStart(2, "0")}
                </span>
              </div>
            </div>
          </article>

          {/* Preview card — next category, dimmed. Click advances. */}
          <button
            type="button"
            onClick={() => go(active + 1)}
            aria-label={`Next: ${preview.title}`}
            className="group relative w-full overflow-hidden rounded-[2rem] border border-white/[0.06] bg-[#080911]/60 p-7 text-left opacity-70 transition-all duration-700 ease-[cubic-bezier(0.32,0.72,0,1)] hover:border-white/[0.14] hover:opacity-100 sm:p-10 lg:w-[42%]"
          >
            <span
              className="font-label text-[10px] uppercase tracking-[0.22em] text-[#8c9aa2]"
            >
              NEXT / {preview.tab}
            </span>
            <h4 className="mt-5 font-headline text-xl font-bold leading-snug tracking-[-0.02em] text-[#a098b0] transition-colors duration-500 group-hover:text-[#e8e0f0] sm:text-2xl">
              {preview.title}
            </h4>
            <span className="mt-8 inline-flex items-center gap-2 font-label text-[10px] uppercase tracking-[0.2em] text-white/30 transition-colors duration-500 group-hover:text-white/60">
              Continue
              <span className="material-symbols-outlined text-sm transition-transform duration-500 ease-[cubic-bezier(0.32,0.72,0,1)] group-hover:translate-x-1">
                arrow_forward
              </span>
            </span>
          </button>
        </div>
      </div>
    </section>
  );
}
