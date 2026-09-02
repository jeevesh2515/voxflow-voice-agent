import assert from "node:assert/strict";
import { calcRoi, clampInputs, getRecommendedPlan, generateRoiCsv } from "./roi.js";

// Suite 1: baseline calculations (1000 calls, 4m AHT, £15/h, 8% missed)
{
  const r = calcRoi({ monthlyCalls: 1000, ahtMinutes: 4, hourlyRate: 15, missedPct: 8 });
  assert.equal(r.monthlyHoursSaved, 40); // 1000*4/60*0.6
  assert.equal(r.annualHoursSaved, 480);
  assert.equal(r.monthlySaving, 600); // 40*15
  assert.equal(r.annualSaving, 7200);
  assert.equal(r.missedCallsYear, 960); // 1000*12*0.08
  assert.equal(r.missedRevenueYear, 33600); // 960*35
}

// Suite 2: annual consistency (annual = monthly * 12)
{
  const r = calcRoi({ monthlyCalls: 2500, ahtMinutes: 6, hourlyRate: 22, missedPct: 12 });
  assert.equal(r.annualSaving, r.monthlySaving * 12);
  assert.equal(r.annualHoursSaved, r.monthlyHoursSaved * 12);
}

// Suite 3: boundary clamps
{
  const c = clampInputs({ monthlyCalls: 999999, ahtMinutes: 999, hourlyRate: 999, missedPct: 999 });
  assert.equal(c.monthlyCalls, 50000);
  assert.equal(c.ahtMinutes, 15);
  assert.equal(c.hourlyRate, 80);
  assert.equal(c.missedPct, 60);
}

// Suite 4: zero missed edge case & assumptions check (no 10x)
{
  const r = calcRoi({ monthlyCalls: 500, ahtMinutes: 3, hourlyRate: 12, missedPct: 0 });
  assert.equal(r.missedCallsYear, 0);
  assert.equal(r.missedRevenueYear, 0);
  assert.equal(r.assumptions.length, 3);
  assert.ok(!r.assumptions.join(" ").includes("10x"));
}

// Suite 5: plan recommendation & CSV export generation
{
  const planStarter = getRecommendedPlan(400, 5000);
  assert.equal(planStarter.id, "starter");
  assert.equal(planStarter.priceGBP, 49);

  const planGrowth = getRecommendedPlan(1500, 15000);
  assert.equal(planGrowth.id, "growth");
  assert.equal(planGrowth.priceGBP, 149);

  const planEnterprise = getRecommendedPlan(5000, 50000);
  assert.equal(planEnterprise.id, "enterprise");
  assert.equal(planEnterprise.priceGBP, 399);

  const inputs = { monthlyCalls: 1000, ahtMinutes: 4, hourlyRate: 15, missedPct: 8 };
  const outputs = calcRoi(inputs);
  const csv = generateRoiCsv(inputs, outputs);
  assert.ok(csv.includes("Voxflow Voice OS"));
  assert.ok(csv.includes("Monthly Inbound Calls"));
  assert.ok(csv.includes("Growth"));
}

console.log("roi: 5 suites pass");
