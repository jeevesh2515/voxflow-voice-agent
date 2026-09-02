// ponytail: pure ROI math, one formula set, assumptions visible in UI
export type RoiInputs = {
  monthlyCalls: number;
  ahtMinutes: number;
  hourlyRate: number;
  missedPct: number;
};

export type RoiOutputs = {
  monthlyHoursSaved: number;
  annualHoursSaved: number;
  monthlySaving: number;
  annualSaving: number;
  missedCallsYear: number;
  missedRevenueYear: number;
  monthlyMissedRevenue: number;
  assumptions: string[];
};

const AUTO_RATE = 0.6; // conservative: 60% of calls fully automated
const VALUE_PER_MISSED_CALL_GBP = 35; // avg cost of missed freight call (callback/redelivery). disclosed.

function clamp(n: number, lo: number, hi: number) {
  if (!Number.isFinite(n)) return lo;
  return Math.max(lo, Math.min(hi, n));
}

export function clampInputs(i: RoiInputs): RoiInputs {
  return {
    monthlyCalls: Math.round(clamp(i.monthlyCalls, 50, 50000)),
    ahtMinutes: clamp(i.ahtMinutes, 0.5, 15),
    hourlyRate: clamp(i.hourlyRate, 8, 80),
    missedPct: clamp(i.missedPct, 0, 60),
  };
}

export function calcRoi(raw: RoiInputs): RoiOutputs {
  const { monthlyCalls, ahtMinutes, hourlyRate, missedPct } = clampInputs(raw);
  const missedRate = missedPct / 100;

  const monthlyHoursTotal = (monthlyCalls * ahtMinutes) / 60;
  const monthlyHoursSaved = monthlyHoursTotal * AUTO_RATE;
  const annualHoursSaved = monthlyHoursSaved * 12;

  const monthlySaving = monthlyHoursSaved * hourlyRate;
  const annualSaving = monthlySaving * 12;

  const missedCallsYear = Math.round(monthlyCalls * 12 * missedRate);
  const missedRevenueYear = missedCallsYear * VALUE_PER_MISSED_CALL_GBP;

  return {
    monthlyHoursSaved: Math.round(monthlyHoursSaved * 10) / 10,
    annualHoursSaved: Math.round(annualHoursSaved * 10) / 10,
    monthlySaving: Math.round(monthlySaving),
    annualSaving: Math.round(annualSaving),
    missedCallsYear,
    missedRevenueYear: Math.round(missedRevenueYear),
    monthlyMissedRevenue: Math.round(missedRevenueYear / 12),
    assumptions: [
      `60% call automation at current AHT (conservative).`,
      `£${VALUE_PER_MISSED_CALL_GBP} per missed call (callback/re-booking cost). Adjust with your ops data.`,
      `Excludes Voxflow subscription; labour only.`,
    ],
  };
}

export function formatGBP(n: number): string {
  return `£${n.toLocaleString("en-GB")}`;
}
export function formatHours(n: number): string {
  return `${n.toLocaleString("en-GB")}h`;
}

export type RecommendedPlan = {
  id: "starter" | "growth" | "enterprise";
  name: string;
  priceGBP: number;
  annualCostGBP: number;
  netAnnualBenefitGBP: number;
  reason: string;
};

export function getRecommendedPlan(monthlyCalls: number, annualSaving: number): RecommendedPlan {
  if (monthlyCalls <= 500) {
    const priceGBP = 49;
    const annualCostGBP = priceGBP * 12;
    return {
      id: "starter",
      name: "Starter",
      priceGBP,
      annualCostGBP,
      netAnnualBenefitGBP: Math.max(0, annualSaving - annualCostGBP),
      reason: "Includes 500 monthly voice mins & Google Sheets mirror.",
    };
  }
  if (monthlyCalls <= 2500) {
    const priceGBP = 149;
    const annualCostGBP = priceGBP * 12;
    return {
      id: "growth",
      name: "Growth",
      priceGBP,
      annualCostGBP,
      netAnnualBenefitGBP: Math.max(0, annualSaving - annualCostGBP),
      reason: "Includes 2,500 monthly voice mins, caller PIN verification & 3 lines.",
    };
  }
  const priceGBP = 399;
  const annualCostGBP = priceGBP * 12;
  return {
    id: "enterprise",
    name: "Enterprise",
    priceGBP,
    annualCostGBP,
    netAnnualBenefitGBP: Math.max(0, annualSaving - annualCostGBP),
    reason: "Unlimited lines, dedicated UK DID & 24/7 SLA escalation.",
  };
}

export function generateRoiCsv(inputs: RoiInputs, outputs: RoiOutputs): string {
  const plan = getRecommendedPlan(inputs.monthlyCalls, outputs.annualSaving);
  const rows = [
    ["Voxflow Voice OS — Operational ROI & Savings Model"],
    ["Generated", new Date().toISOString().split("T")[0]],
    [""],
    ["INPUT PARAMETER", "VALUE", "UNIT"],
    ["Monthly Inbound Calls", inputs.monthlyCalls, "calls/month"],
    ["Average Handle Time (AHT)", inputs.ahtMinutes, "minutes/call"],
    ["Agent Cost Rate", `£${inputs.hourlyRate}`, "£/hour"],
    ["Missed Call Rate", `${inputs.missedPct}%`, "percentage"],
    [""],
    ["PROJECTED OPERATIONAL IMPACT", "VALUE", "UNIT"],
    ["Monthly Hours Saved", outputs.monthlyHoursSaved, "hours/month"],
    ["Annual Hours Recovered", outputs.annualHoursSaved, "hours/year"],
    ["Monthly Labour Savings", `£${outputs.monthlySaving}`, "£/month"],
    ["Annual Labour Savings", `£${outputs.annualSaving}`, "£/year"],
    ["Estimated Unanswered Calls", outputs.missedCallsYear, "calls/year"],
    ["Annual Missed Call Revenue Drag", `£${outputs.missedRevenueYear}`, "£/year"],
    [""],
    ["RECOMMENDED VOXFLOW TIER", "PLAN", "ANNUAL NET BENEFIT"],
    ["Matched Tier", `${plan.name} (£${plan.priceGBP}/mo)`, `£${plan.netAnnualBenefitGBP}/year net`],
    [""],
    ["ASSUMPTIONS & METHODOLOGY"],
    ...outputs.assumptions.map((a) => [a]),
    ["Disclaimer: Inputs clamped to operational ranges. Model is for estimation; actual results depend on depot call profiles."],
  ];

  return rows.map((r) => r.map((c) => `"${String(c).replace(/"/g, '""')}"`).join(",")).join("\n");
}
