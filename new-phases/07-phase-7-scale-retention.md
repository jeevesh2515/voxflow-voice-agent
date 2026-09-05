# Phase 7: Scale & Retention

## Objective

The nice-to-have tier from the original assessment: webhooks, product
analytics, mobile responsiveness, additional localization, a referral loop,
and integration marketplace stubs. Lower priority than every phase before
this — sequence within this phase is flexible.

## Prerequisites

Phases 1-6 Definitions of Done met. This phase assumes a working, sellable,
enterprise-ready product already exists.

## Tools required

- PostHog or Mixpanel (product analytics, distinct from Phase 5's marketing
  funnel analytics)
- `svix` or a self-built webhook delivery system
- `next-intl` (or equivalent) for localization
- Real iOS and Android devices for testing (not devtools emulation alone)

## Working steps

1. Build product analytics dashboards covering in-app funnel and retention,
   beyond Phase 5's marketing-site traffic analytics.
2. Build a webhook system letting customers subscribe to events (starting
   with `call.escalated`), with signed payloads and retry/backoff on
   delivery failure.
3. Audit mobile responsiveness specifically for the in-call and dashboard
   experience on real iOS Safari and Android Chrome — drivers receive calls
   on phones, per the original assessment's own note, so this isn't
   optional polish for this user group specifically.
4. Localize the dashboard chrome beyond English/Hindi for European buyers,
   using `next-intl` or equivalent.
5. Build a referral loop: `?ref=` tracking plus a credit applied to the
   referrer's invoice, wired into Phase 2's billing tables.
6. Document intended integration points (Slack, Teams, ERP systems) even if
   not built yet, so sales has a real roadmap to point to rather than a
   vague promise.

## Definition of Done

- [ ] Product analytics dashboard shows real funnel/retention data, not
      placeholder metrics
- [ ] At least one webhook event type fully implemented and verified against
      a real subscriber endpoint
- [ ] In-call/dashboard experience verified on real iOS and Android
      hardware, not emulation only
- [ ] At least one additional locale live and switchable in the dashboard
- [ ] Referral tracking verified end to end with an actual test signup and
      confirmed credit applied to the referrer's invoice
- [ ] Full existing test/eval suite still passes at 100%

## Explicitly out of scope

- Nothing further — this is the last phase in this roadmap. Anything beyond
  this is a new roadmap, not an extension of this one.
