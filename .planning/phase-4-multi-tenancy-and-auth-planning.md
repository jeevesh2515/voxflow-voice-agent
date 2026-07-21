# Phase 4 — Multi-Tenancy & Authentication (Day 13–16)

Do not start this phase until you've had the real conversation with your
friend about the actual workflow (PRD.md section 13). This phase turns
your single-tenant prototype into something sellable to a second company —
it's wasted effort if the underlying workflow assumptions are wrong.

## Day 13

### Theory

Caller authentication and staff (dashboard) authentication are two
different systems with different risk profiles. Staff auth protects the
dashboard/data access (standard Supabase Auth). Caller auth protects
sensitive phone actions (placing/modifying orders) and needs to work over
voice, which rules out anything requiring the caller to type or click.

### Checklist

- [ ] Implement Supabase Auth for the staff dashboard (email/password or
      magic link)
- [ ] Design caller auth tiers: Tier 0 (no auth — general info only, if
      any), Tier 1 (phone number match — stock checks, shipment status),
      Tier 2 (phone match + spoken PIN or last-PO reference — placing/
      modifying orders)
- [ ] Implement Tier 1 caller auth (phone number lookup against
      `suppliers`)

### Definition of Done

A staff member can log into a dashboard (even a blank one) via Supabase
Auth. A test call from a known number passes Tier 1 auth; an unknown
number is correctly rejected/redirected.

## Day 14

### Theory

Tier 2 auth over voice needs to be simple enough to say out loud but hard
enough to not be trivially guessable. A 4-digit PIN tied to the supplier
record, or "confirm your last PO number," are both reasonable v1 options —
pick one and move on rather than over-engineering this.

### Checklist

- [ ] Implement Tier 2 caller auth (PIN or last-order confirmation)
- [ ] Gate `place_order` and any order-modification intent behind Tier 2
- [ ] Test: a caller who fails Tier 2 auth cannot place an order, and the
      call is logged as an auth failure, not silently dropped

### Definition of Done

A test call attempting to place an order without correct Tier 2 auth is
blocked and logged; a call with correct auth succeeds.

## Day 15

### Theory

`tenant_id` needs to be threaded through every layer now: the Twilio
number that was called maps to a tenant, every DB query in the LangGraph
agent is scoped to that tenant, and RLS enforces it as a last line of
defense.

### Checklist

- [ ] Add tenant resolution: incoming call's Twilio number (or a
      configured mapping) resolves to a `tenant_id` at the very start of
      the call flow
- [ ] Thread `tenant_id` through every node in the LangGraph agent and
      every DB query
- [ ] Create a second fake tenant with its own seed data, and confirm a
      call routed to tenant A never sees tenant B's suppliers/stock/orders

### Definition of Done

Two fake tenants exist with separate seed data. Calls routed to each
tenant only ever see their own data — verified by deliberately trying to
cross-query and confirming it's blocked at the RLS level.

## Day 16

### Theory

Onboarding a new tenant should not require you to hand-write code every
time. Even a minimal admin flow (a script or basic form to create a
tenant, add suppliers, map a phone number) saves you from being a
bottleneck as soon as you have a second real customer.

### Checklist

- [ ] Build a minimal tenant-onboarding script or admin form: create
      tenant, add initial suppliers/stock/SKUs, assign a Twilio number
- [ ] Document the onboarding steps in `ONBOARDING.md` so you're not
      relying on memory when a real company signs up

### Definition of Done

You can onboard a brand-new fake tenant end-to-end (create tenant, add
data, assign number, make a test call) using only your script/form and
`ONBOARDING.md`, without writing new code in the process.
