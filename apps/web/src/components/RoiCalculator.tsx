"use client";

import { useEffect, useState } from "react";
import {
  calcRoi,
  formatGBP,
  formatHours,
  getRecommendedPlan,
  generateRoiCsv,
  type RoiInputs,
} from "@/lib/roi";

const STORAGE_KEY = "voxflow_roi_inputs";
const EMAIL_KEY = "voxflow_roi_email";

const DEFAULTS: RoiInputs = {
  monthlyCalls: 2200,
  ahtMinutes: 4.5,
  hourlyRate: 18,
  missedPct: 8,
};

function Field({
  label,
  unit,
  hint,
  children,
}: {
  label: string;
  unit: string;
  hint: string;
  children: React.ReactNode;
}) {
  return (
    <label className="flex flex-col gap-2">
      <span className="flex items-baseline justify-between">
        <span className="font-mono text-[11px] uppercase tracking-widest text-white/70">{label}</span>
        <span className="font-mono text-[10px] text-white/40">{unit}</span>
      </span>
      {children}
      <span className="font-mono text-[10px] text-white/35 leading-tight">{hint}</span>
    </label>
  );
}

export default function RoiCalculator() {
  const [inputs, setInputs] = useState<RoiInputs>(DEFAULTS);
  const [email, setEmail] = useState("");
  const [saved, setSaved] = useState(false);

  // hydrate from localStorage
  useEffect(() => {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (raw) {
        const p = JSON.parse(raw) as Partial<RoiInputs>;
        setInputs((prev) => ({
          monthlyCalls: Number.isFinite(p.monthlyCalls as number) ? (p.monthlyCalls as number) : prev.monthlyCalls,
          ahtMinutes: Number.isFinite(p.ahtMinutes as number) ? (p.ahtMinutes as number) : prev.ahtMinutes,
          hourlyRate: Number.isFinite(p.hourlyRate as number) ? (p.hourlyRate as number) : prev.hourlyRate,
          missedPct: Number.isFinite(p.missedPct as number) ? (p.missedPct as number) : prev.missedPct,
        }));
      }
      const e = localStorage.getItem(EMAIL_KEY);
      if (e) setEmail(e);
    } catch {}
  }, []);

  // persist (inputs + optional email)
  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(inputs));
    } catch {}
  }, [inputs]);

  useEffect(() => {
    try {
      if (email) localStorage.setItem(EMAIL_KEY, email);
      else localStorage.removeItem(EMAIL_KEY);
    } catch {}
  }, [email]);

  const r = calcRoi(inputs);
  const plan = getRecommendedPlan(inputs.monthlyCalls, r.annualSaving);
  const emailValid = !email || /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);

  const update =
    (k: keyof RoiInputs) =>
    (v: string | number): void => {
      const n = typeof v === "string" ? Number(v) : v;
      setInputs((prev) => ({ ...prev, [k]: n }));
      setSaved(false);
    };

  const handleExportCsv = () => {
    const csvContent = generateRoiCsv(inputs, r);
    const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.setAttribute("href", url);
    link.setAttribute("download", `voxflow-roi-estimate-${inputs.monthlyCalls}-calls.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  return (
    <div className="w-full max-w-6xl mx-auto">
      {/* Section Header */}
      <div className="text-center mb-10">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-white/[0.08] bg-white/[0.02] text-xs font-mono tracking-widest text-[#5EEAD4] uppercase mb-4">
          <span className="h-1.5 w-1.5 rounded-full bg-[#5EEAD4] animate-pulse" />
          06 / 08 • Economics // Operational ROI Calculator
        </div>
        <h2 className="font-headline font-black text-3xl sm:text-5xl lg:text-6xl tracking-tight text-white leading-[1.08]">
          The sheet updates. <br />
          <span className="text-white/60">Labour and capacity return.</span>
        </h2>
        <p className="font-sans text-sm sm:text-base text-white/70 max-w-2xl mx-auto mt-4 leading-relaxed">
          Model recovered operator hours and missed-call revenue drag directly from your own depot numbers.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        {/* Left Column: Inputs (Dent Card Inlay) */}
        <div className="lg:col-span-5 rounded-3xl border border-white/[0.09] bg-[#030308]/95 backdrop-blur-2xl shadow-[inset_0_1px_1px_rgba(255,255,255,0.08),0_25px_50px_rgba(0,0,0,0.85)] p-6 sm:p-8">
          <div className="flex items-center justify-between mb-6 pb-3 border-b border-white/[0.06]">
            <span className="font-mono text-xs uppercase tracking-widest text-white font-bold">
              Depot Parameters
            </span>
            <span className="font-mono text-[10px] text-[#5EEAD4]">UK EDGE ~200MS</span>
          </div>

          <div className="space-y-6">
            <Field label="Monthly Inbound Calls" unit="50 – 50,000" hint="Total monthly driver & supplier calls.">
              <div className="flex gap-3 items-center">
                <input
                  type="range"
                  min={50}
                  max={50000}
                  step={50}
                  value={inputs.monthlyCalls}
                  onChange={(e) => update("monthlyCalls")(e.target.value)}
                  aria-label="Monthly inbound calls"
                  className="flex-1 accent-[#5EEAD4] h-2 bg-white/[0.08] rounded-lg appearance-none cursor-pointer"
                />
                <input
                  type="number"
                  inputMode="numeric"
                  min={50}
                  max={50000}
                  value={inputs.monthlyCalls}
                  onChange={(e) => update("monthlyCalls")(e.target.value)}
                  className="w-28 rounded-xl border border-white/[0.08] bg-white/[0.03] px-3 py-2 font-mono text-sm text-white focus:outline-none focus:ring-2 focus:ring-[#5EEAD4]/40 text-right"
                />
              </div>
            </Field>

            <Field label="Average Handle Time (AHT)" unit="0.5 – 15 mins" hint="Average human duration per inbound call.">
              <div className="flex gap-3 items-center">
                <input
                  type="range"
                  min={0.5}
                  max={15}
                  step={0.5}
                  value={inputs.ahtMinutes}
                  onChange={(e) => update("ahtMinutes")(e.target.value)}
                  aria-label="Average handle time in minutes"
                  className="flex-1 accent-[#5EEAD4] h-2 bg-white/[0.08] rounded-lg appearance-none cursor-pointer"
                />
                <input
                  type="number"
                  inputMode="decimal"
                  min={0.5}
                  max={15}
                  step={0.5}
                  value={inputs.ahtMinutes}
                  onChange={(e) => update("ahtMinutes")(e.target.value)}
                  className="w-28 rounded-xl border border-white/[0.08] bg-white/[0.03] px-3 py-2 font-mono text-sm text-white focus:outline-none focus:ring-2 focus:ring-[#5EEAD4]/40 text-right"
                />
              </div>
            </Field>

            <Field label="Loaded Agent Cost" unit="£8 – £80 / hr" hint="Fully loaded operator cost per hour.">
              <div className="flex gap-3 items-center">
                <input
                  type="range"
                  min={8}
                  max={80}
                  step={1}
                  value={inputs.hourlyRate}
                  onChange={(e) => update("hourlyRate")(e.target.value)}
                  aria-label="Loaded agent cost per hour"
                  className="flex-1 accent-[#5EEAD4] h-2 bg-white/[0.08] rounded-lg appearance-none cursor-pointer"
                />
                <input
                  type="number"
                  inputMode="numeric"
                  min={8}
                  max={80}
                  value={inputs.hourlyRate}
                  onChange={(e) => update("hourlyRate")(e.target.value)}
                  className="w-28 rounded-xl border border-white/[0.08] bg-white/[0.03] px-3 py-2 font-mono text-sm text-white focus:outline-none focus:ring-2 focus:ring-[#5EEAD4]/40 text-right"
                />
              </div>
            </Field>

            <Field label="Missed Call Rate" unit="0% – 60%" hint="Share of inbound calls abandoned or unanswered.">
              <div className="flex gap-3 items-center">
                <input
                  type="range"
                  min={0}
                  max={60}
                  step={1}
                  value={inputs.missedPct}
                  onChange={(e) => update("missedPct")(e.target.value)}
                  aria-label="Missed call rate percentage"
                  className="flex-1 accent-[#5EEAD4] h-2 bg-white/[0.08] rounded-lg appearance-none cursor-pointer"
                />
                <input
                  type="number"
                  inputMode="numeric"
                  min={0}
                  max={60}
                  value={inputs.missedPct}
                  onChange={(e) => update("missedPct")(e.target.value)}
                  className="w-28 rounded-xl border border-white/[0.08] bg-white/[0.03] px-3 py-2 font-mono text-sm text-white focus:outline-none focus:ring-2 focus:ring-[#5EEAD4]/40 text-right"
                />
              </div>
            </Field>

            {/* Optional Email Capture */}
            <div className="pt-4 border-t border-white/[0.06]">
              <label className="flex flex-col gap-1.5">
                <span className="font-mono text-[11px] uppercase tracking-widest text-white/70">
                  Email <span className="text-white/40 font-normal normal-case">(optional)</span>
                </span>
                <input
                  type="email"
                  inputMode="email"
                  autoComplete="email"
                  placeholder="operations@depot.co.uk"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  aria-invalid={!emailValid}
                  className={`rounded-xl border bg-white/[0.03] px-3.5 py-2.5 font-mono text-sm text-white placeholder:text-white/30 focus:outline-none focus:ring-2 ${
                    emailValid ? "border-white/[0.08] focus:ring-[#5EEAD4]/40" : "border-rose-400/50 focus:ring-rose-400/30"
                  }`}
                />
                {!emailValid && (
                  <span className="font-mono text-[10px] text-rose-300">Enter a valid email or leave blank.</span>
                )}
                <span className="font-mono text-[10px] text-white/35">
                  Saved locally to pre-fill your workspace setup.
                </span>
              </label>
              <div className="flex gap-2.5 mt-3">
                <button
                  type="button"
                  onClick={() => setSaved(true)}
                  disabled={!emailValid}
                  className="inline-flex items-center rounded-xl border border-[#5EEAD4]/30 bg-[#5EEAD4]/10 px-4 py-2 font-mono text-xs font-bold text-[#5EEAD4] hover:bg-[#5EEAD4]/20 disabled:opacity-40 disabled:cursor-not-allowed transition"
                >
                  {saved ? "Saved locally ✓" : "Save inputs"}
                </button>
                <button
                  type="button"
                  onClick={handleExportCsv}
                  className="inline-flex items-center rounded-xl border border-white/[0.08] bg-white/[0.02] px-3.5 py-2 font-mono text-xs text-white/70 hover:text-white hover:bg-white/[0.05] transition"
                >
                  Export CSV ↓
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* Right Column: Output Metrics & Tier Recommendations */}
        <div className="lg:col-span-7 space-y-5">
          {/* Key Metric Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div className="rounded-2xl border border-white/[0.08] bg-white/[0.02] p-5 flex flex-col justify-between">
              <span className="font-mono text-[10px] uppercase tracking-widest text-white/40 mb-1">
                Annual Labour Saving
              </span>
              <div className="font-headline font-black text-2xl sm:text-3xl text-white tracking-tight">
                {formatGBP(r.annualSaving)}
              </div>
              <div className="font-mono text-[11px] text-[#5EEAD4] mt-1">
                {formatGBP(r.monthlySaving)} / month
              </div>
            </div>

            <div className="rounded-2xl border border-[#5EEAD4]/20 bg-[#5EEAD4]/[0.06] p-5 flex flex-col justify-between shadow-[0_0_20px_rgba(94,234,212,0.08)]">
              <span className="font-mono text-[10px] uppercase tracking-widest text-[#5EEAD4]/80 mb-1">
                Hours Recovered
              </span>
              <div className="font-headline font-black text-2xl sm:text-3xl text-white tracking-tight">
                {formatHours(r.annualHoursSaved)}
                <span className="text-white/40 text-sm font-normal"> / yr</span>
              </div>
              <div className="font-mono text-[11px] text-white/60 mt-1">
                {formatHours(r.monthlyHoursSaved)} / month
              </div>
            </div>

            <div className="rounded-2xl border border-white/[0.08] bg-white/[0.02] p-5 flex flex-col justify-between">
              <span className="font-mono text-[10px] uppercase tracking-widest text-white/40 mb-1">
                Missed-Call Drag
              </span>
              <div className="font-headline font-black text-2xl sm:text-3xl text-white tracking-tight">
                {formatGBP(r.missedRevenueYear)}
                <span className="text-white/40 text-sm font-normal"> / yr</span>
              </div>
              <div className="font-mono text-[11px] text-white/50 mt-1">
                {r.missedCallsYear.toLocaleString("en-GB")} calls · {formatGBP(r.monthlyMissedRevenue)}/mo
              </div>
            </div>
          </div>

          {/* Recommended Plan & Net ROI Inlay */}
          <div className="rounded-2xl border border-white/[0.08] bg-[#030308]/80 p-5">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-3 mb-3 border-b border-white/[0.06]">
              <div className="flex items-center gap-2">
                <span className="font-mono text-xs uppercase tracking-wider text-white/60 font-bold">
                  Matched Tier:
                </span>
                <span className="px-2.5 py-0.5 rounded-full font-mono text-xs font-bold bg-[#5EEAD4]/15 border border-[#5EEAD4]/40 text-[#5EEAD4]">
                  {plan.name} (£{plan.priceGBP}/mo)
                </span>
              </div>
              <span className="font-mono text-xs text-white/80">
                Net Benefit: <span className="text-emerald-400 font-bold">+{formatGBP(plan.netAnnualBenefitGBP)}/yr</span>
              </span>
            </div>
            <p className="font-mono text-xs text-white/60 leading-relaxed">
              {plan.reason}
            </p>
          </div>

          {/* Disclosed Methodology & Assumptions */}
          <div className="rounded-2xl border border-white/[0.08] bg-[#030308]/60 p-5">
            <div className="font-mono text-xs uppercase tracking-widest text-white/60 mb-3 font-bold">
              Model Assumptions & Methodology
            </div>
            <ul className="space-y-2">
              {r.assumptions.map((a, i) => (
                <li key={i} className="font-mono text-xs leading-relaxed text-white/50 flex gap-2.5">
                  <span className="text-[#5EEAD4]">—</span>
                  <span>{a}</span>
                </li>
              ))}
            </ul>
            <p className="font-mono text-[10px] text-white/35 mt-4 leading-relaxed border-t border-white/[0.04] pt-3">
              Inputs clamped to realistic UK logistics ranges. Hours rounded to 0.1h; currency rounded to nearest pound. No financial guarantee implied; evaluate against your depot ledger.
            </p>
          </div>

          {/* Action Footer */}
          <div className="rounded-2xl border border-[#5EEAD4]/30 bg-[#5EEAD4]/[0.05] p-5 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
            <div>
              <div className="font-headline font-bold text-sm text-white">
                Ready to eliminate missed calls and reclaims hours?
              </div>
              <div className="font-mono text-xs text-white/60 mt-0.5">
                Start on 500 free minutes with our 14-day trial.
              </div>
            </div>
            <a
              href={`/sign-up?plan=${plan.id}`}
              className="inline-flex items-center justify-center rounded-xl bg-[#5EEAD4] px-5 py-2.5 font-headline text-xs font-bold text-[#030308] hover:shadow-[0_0_22px_rgba(94,234,212,0.4)] transition active:scale-95 whitespace-nowrap"
            >
              Start with one workflow →
            </a>
          </div>
        </div>
      </div>
    </div>
  );
}
