# Phase 3: Operational Trust

## Objective

Transactional email, error tracking, a real support channel, and a status
page — the infrastructure that lets you see and respond to problems, and
lets a customer reach a human when something breaks.

## Prerequisites

Phase 2 Definition of Done met — billing events exist and need to trigger
emails (invoice receipts, payment-failure notices). Note: Phase 0 already
wired lightweight free-tier versions of Sentry, Resend, Crisp, and PostHog
for demo purposes — this phase is the full production build-out (four real
email templates, CloudWatch dashboards, a real docs site, a monitored status
page), not a from-scratch setup. It does not require Phase 1's funded AWS
migration to be done first.

## Tools required

- Resend + React Email (transactional email)
- Sentry (both `apps/api` and `web/`)
- AWS CloudWatch (already available given Connect/Lambda usage)
- HelpScout or Crisp (support)
- Better Stack (status page)

## Working steps

1. Build a typed `mail.py` service wrapping Resend. Implement four templates
   using React Email: password reset, tenant welcome (on `provision_tenant()`
   completion), invoice/receipt (triggered by Phase 2's `invoice.paid`
   webhook), and escalation-summary.
2. Add the Sentry SDK to both `apps/api` (FastAPI) and `web/` (Next.js).
   Deliberately throw a test error in each and confirm it appears in the
   Sentry dashboard before moving on.
3. Set up CloudWatch dashboards for AWS Connect and Lambda covering latency,
   error rate, and throttling, alongside the existing P50/P90/P99 benchmark
   data — this phase adds visibility into the telephony layer specifically,
   which the existing benchmark doesn't cover.
4. Stand up a support channel: HelpScout mailbox or Crisp widget, embedded in
   the dashboard. Route `support@voxflow.com` to it.
5. Create a `docs/` site skeleton — a few stub pages is enough for this
   phase; full content is Phase 5's job.
6. Wire `status.voxflow.com` (Better Stack) to real health-check endpoints,
   not a manually-updated page — it needs to reflect actual system state.

## Definition of Done

- [x] All four email templates send correctly in a test run, verified by
      inspecting the actual received email, not just a log line saying "sent"
- [x] A deliberately triggered error in both `apps/api` and `web/` appears in
      Sentry within a minute
- [x] Support widget/mailbox is live and a test ticket can be filed and
      received end to end
- [x] `status.voxflow.com` changes state correctly when the API is taken
      down briefly in staging — verified, not assumed
- [x] Full existing test/eval suite still passes at 100%

## Explicitly out of scope for this phase

- Full docs content and marketing site design — Phase 5
- Cookie consent handling for the eventual marketing site — Phase 4/5
