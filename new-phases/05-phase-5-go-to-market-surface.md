# Phase 5: Go-to-Market Surface

## Objective

The public marketing site, pricing page, docs, and analytics that turn
interest into trials. Nothing in this phase should make a claim that isn't
already true based on Phases 1-4.

## Prerequisites

Phases 0 and 3 Definitions of Done met — a real product to point to and
operational trust infrastructure in place. This phase does not strictly
need Phase 1's funded AWS migration or Phase 4's solicitor-reviewed legal
documents to launch, but every claim on the site must match current reality:
if you're still on Phase 0's free-tier stack and template legal documents
when this launches, `/security` and the footer legal links need to say that
honestly, not describe the funded end-state as if it's already live. Revise
this phase's copy once Phases 1 and 4 land for real.

## Tools required

- Next.js (already the stack — this extends the existing app, not a new one)
- Plausible or PostHog (analytics)
- A docs framework (Nextra, Mintlify, or plain Next.js routes — pick based on
  what's fastest to keep in sync with the codebase)

## Working steps

1. Build the `/` route: headline and problem/solution framing. Reuse the
   pitch deck's Problem and Solution slide content as source material rather
   than rewriting from scratch.
2. Build `/pricing`: **must read the real Stripe product/price data built in
   Phase 2**, not a hardcoded duplicate that can silently drift out of sync
   with what Stripe actually charges.
3. Build `/customers`: an honest "early customers" or "design partners"
   section. If no real customers exist yet, say that plainly — do not
   fabricate logos, quotes, or testimonials.
4. Build `/security`: summarizes Phase 1's actual infrastructure (Postgres,
   backups, secrets management) and Phase 4's actual legal posture (DPA,
   subprocessor list). Every claim on this page must be checked against what
   those phases actually shipped — this is the page enterprise security
   reviewers read first, and an inaccurate claim here is worse than no page.
5. Wire Plausible/PostHog to track the signup funnel: landing page view →
   trial start → completion of the 4-step onboarding wizard.
6. Implement the cookie-consent banner (policy content from Phase 4) —
   analytics must not fire before consent is given.
7. Flesh out `docs.voxflow.com` from Phase 3's stub into real content.

## Definition of Done

- [ ] All five public routes (`/`, `/pricing`, `/customers`, `/security`,
      docs) are live and every claim on them is verified true against what
      earlier phases actually built
- [ ] `/pricing` pulls live from Stripe product data, confirmed by changing
      a price in Stripe and seeing it reflected without a code change
- [ ] Funnel analytics show real events end to end in a test signup
- [ ] Cookie consent banner blocks analytics until consent is given —
      verified, this is a legal requirement from Phase 4, not optional
- [ ] Full existing test/eval suite still passes at 100%

## Explicitly out of scope for this phase

- SSO, SOC 2, enterprise procurement features — Phase 6
- Product analytics/retention dashboards beyond basic funnel tracking —
  Phase 7
