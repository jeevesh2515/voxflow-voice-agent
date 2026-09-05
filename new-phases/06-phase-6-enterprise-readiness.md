# Phase 6: Enterprise Readiness

## Objective

SSO/SAML, SOC 2 Type I, a formally tested DR process, load testing, and
application-layer rate limiting — what unblocks a $50K+ enterprise contract.

## Prerequisites

SSO, load testing, and rate limiting depend on Phases 1-5 being done. SOC 2
is different: evidence-collection depends only on Phase 1 (backups, secrets
management, access logging) and can start in parallel with Phases 2-5 rather
than waiting for all of them — don't delay engaging Drata/Vanta just because
this is numbered Phase 6.

## Timeline correction

The original assessment scheduled SOC 2 Type I to start "week 6-8" and take
8-12 weeks, which cannot finish inside a claimed 90-day window. Start SOC 2
whenever Phase 1's controls are actually in place and evidenced, not on a
fixed calendar week — budget for it to run past the 90-day mark of the
overall roadmap.

## Tools required

- `boxyhq/saml-jackson` (open-source SSO middleware)
- Drata or Vanta (SOC 2 readiness)
- k6 or Locust (load testing)

## Working steps

1. Integrate `boxyhq/saml-jackson` into the existing `/api/auth/signup`
   flow. Test against at least one real Identity Provider sandbox — Okta or
   Google Workspace SAML — not just an internal mock.
2. Connect Drata or Vanta to the controls already built in Phase 1 (backups,
   secrets management, access logging). This phase is largely evidence
   collection on top of earlier engineering work, not new build-out — if it
   feels like you're building major new infrastructure here, something from
   Phase 1 was skipped.
3. Formalize Phase 1's DR runbook stub: run an actual timed restore and
   record the real RTO, don't estimate it. Update the runbook with the
   measured number.
4. Load test: a k6 or Locust script simulating 100 concurrent tenants
   against the voice pipeline. Record the actual concurrency ceiling the
   system holds up to — don't guess or extrapolate from the single-turn
   latency benchmark alone.
5. Add application-layer rate limiting across the API, protecting both the
   existing routes and any future programmatic API surface.

## Definition of Done

- [ ] SSO tested end-to-end against a real IdP sandbox, not internal mock
      auth only
- [ ] SOC 2 Type I readiness assessment shows every Phase-1-derived control
      mapped and evidenced in Drata/Vanta
- [ ] DR runbook contains a real measured restore time, not an estimate
- [ ] Load test report states the actual concurrency ceiling in calls/minute
      or simultaneous tenants, from a real test run
- [ ] Rate limiting verified by deliberately exceeding it in a test and
      confirming the correct 429 response
- [ ] Full existing test/eval suite still passes at 100%

## Explicitly out of scope for this phase

- Webhooks, product analytics, i18n, mobile audit — Phase 7
