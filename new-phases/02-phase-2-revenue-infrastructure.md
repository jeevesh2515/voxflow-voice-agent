# Phase 2: Revenue Infrastructure

## Objective

Real billing: Stripe subscriptions, usage metering off actual call data,
invoicing, and dunning for failed payments.

## Prerequisites

Phase 0 Definition of Done met — Supabase live (real Postgres), `/superadmin`
exists. **This phase does not need to wait for Phase 1's funded AWS
migration.** Supabase is genuine Postgres, so Stripe's subscription/invoice
tables can be built now and will migrate cleanly to RDS later via Phase 1's
`pg_dump`/`pg_restore` step. This is what actually lets your first design
partners get billed without waiting on a cloud migration.

## Tools required

- Stripe (Billing product + Webhooks)
- A background task runner for webhook processing (a FastAPI background task
  is sufficient at this stage — don't introduce a separate queue system yet)

## Working steps

0. **Design partners don't have to wait for this phase.** The first pilots
   can be invoiced manually (bank transfer or a plain invoice) before Stripe
   automation exists — that's normal for early customers. When this phase
   ships, reconcile any manually-invoiced pilots into the real
   `subscriptions`/`invoices` tables so they aren't left in a spreadsheet
   permanently.
1. Create Stripe Products/Prices for the three tiers already defined in the
   pitch deck: Starter $499, Growth $1,499, Enterprise from $4,500. Confirm
   these are the actual final prices with the founder before wiring them in —
   don't invent or adjust pricing during implementation.
2. Build `subscriptions` and `invoices` tables in Postgres, populated from
   Stripe webhook events: `checkout.session.completed`, `invoice.paid`,
   `invoice.payment_failed`, `customer.subscription.updated`,
   `customer.subscription.deleted`.
3. Meter voice-minutes: aggregate call duration from the existing calls log
   (the same data behind the `calls.latency_ms` benchmark) into a daily usage
   record, reported to Stripe via its usage-based billing API.
4. Dunning: on `invoice.payment_failed`, flag the tenant into a grace-period
   status. After Stripe's configured retry schedule is exhausted, auto-suspend
   the tenant. Suspension status must be visible in `/superadmin`.
5. Verify Stripe webhook signatures on every incoming event. Handle
   duplicate delivery idempotently — Stripe resends events, and a
   non-idempotent handler will double-charge or double-suspend a tenant.
6. Run a full sandbox test in Stripe test mode: trial → paid → simulated
   failed card → dunning → suspension. Confirm each state transition is
   correct and visible in `/superadmin` before treating this as done.

## Definition of Done

- [x] All three tiers exist as real Stripe Products/Prices, confirmed against
      the founder-approved pricing (Starter £149/mo, Growth £449/mo, Enterprise £1,499/mo)
- [x] `subscriptions`/`invoices` tables correctly populate from a full test
      webhook run (Migration 026 + tests verified)
- [x] A simulated failed card correctly triggers dunning and eventual
      suspension, visible in `/superadmin`
- [x] Webhook endpoint verifies Stripe signatures and is confirmed idempotent
      (replaying the same event does not double-charge or double-suspend)
- [x] Full existing test/eval suite still passes at 100% (574 passing tests)

## Explicitly out of scope for this phase

- Sending invoice emails — that's Phase 3 (Resend), this phase only needs the
  data to exist correctly
- The public `/pricing` page — Phase 5, and it must read from what this phase
  built, not duplicate the numbers

## Not out of scope, but not scheduled anywhere either

If specific design partners require a Salesforce or NetSuite bridge to sign
(this is explicitly promised for Q1 in the pitch deck), that's real,
revenue-blocking engineering work that doesn't belong in Phase 7's generic
"integration marketplace" — that's platform-wide, lower-priority work for a
different audience. A customer-specific ERP bridge should be scoped as its
own task as soon as a pilot actually needs it, likely running alongside this
phase rather than waiting for it.
