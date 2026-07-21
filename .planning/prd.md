# VoxFlow Voice Agent — Product Requirements Document

**Status:** Draft v0.1 — pre-validation stage
**Owner:** Jesse (Jeevesh Singale)
**Last updated:** 2026-07-21

---

## 0. Reality Check (read this before anything else)

This PRD describes a product that does not have a validated customer yet. The
target scenario (a distributor handling PepsiCo-partner supplier calls) is
based on a secondhand description from a friend, not a direct conversation
with the person doing the work. Before Phase 4 (multi-tenancy) begins, this
document requires an update based on an actual conversation with that friend
— specifically: real call types, real fields tracked, real pain ranked by
frequency. Treat everything under "Assumed Workflow" below as a hypothesis,
not a spec.

---

## 1. Problem Statement

Small and mid-size distributors/partners in supply chains (e.g. a regional
distributor for a large FMCG brand) receive a high volume of phone calls from
suppliers and retailers for:

- Placing purchase orders (POs)
- Checking stock availability
- Checking shipment/dispatch status
- General order verification

Today, this is handled manually by one or a small number of staff who
simultaneously juggle spreadsheets (often Excel), phone calls, and manual
data entry. This creates:

- Bottlenecks when the person is on another call or unavailable
- Data entry errors and delayed updates
- No structured record of what was discussed or promised on a call
- No way to scale without hiring more staff per call volume increment

## 2. Solution

VoxFlow is a voice AI agent that answers inbound calls on behalf of a
business, holds a natural conversation to identify caller intent, reads from
and writes to the business's own database in real time, gives verbal
confirmations, and logs a structured summary of every call automatically.

It is NOT a generic chatbot wrapper. It is scoped narrowly to
transactional, structured-data phone workflows (order placement, stock
lookup, shipment status) where the value is verifiable and measurable
(calls handled without a human, data entered without manual re-typing,
full audit trail of every call).

## 3. Target Customer (initial)

- **Primary (validation target):** Small-to-mid distributors/C&F agents
  supplying for large FMCG brands in India, who currently handle
  supplier/retailer calls manually via phone + Excel.
- **Not yet targeted:** Enterprise call centers, multi-language national
  hotlines, anything requiring outbound sales calls. Keep scope narrow
  until v1 is proven on one real customer.

## 4. Core User Stories

1. As a supplier, I call the company's number, the agent identifies me
   (by phone number or verbally), and I can place a PO, check stock, or ask
   about a shipment — without waiting for a human.
2. As a business owner/ops manager, I can see a real-time dashboard of
   calls in progress, what's being asked, and what the agent is doing.
3. As a business owner, after any call, I get a structured log: caller,
   intent, entities captured (SKU, qty, PO number), outcome, and whether
   a human follow-up is needed.
4. As a business owner, sensitive actions (placing a large order, changing
   an existing PO) require the caller to be authenticated first
   (e.g. registered phone number + verbal PIN, or an existing supplier ID).
5. As a business owner, if the agent isn't confident it understood
   correctly, it says so and flags the call for human follow-up instead
   of guessing.
6. As the SaaS operator (Jesse), each company using VoxFlow is a separate
   tenant with its own database records, call logs, and configuration —
   no cross-tenant data leakage.

## 5. Out of Scope for v1

- Outbound calling / cold-calling
- Multi-language support beyond English + Hindi (Hinglish) code-switching
- Payment processing over the phone
- Full CRM replacement — VoxFlow reads/writes structured data, it does
  not replace existing business systems entirely
- Any claim of "zero errors" — the real goal is graceful fallback to a
  human when confidence is low, not perfection

## 6. Assumed Workflow (to be validated, not built blindly)

Call comes in →

1. Identify caller (phone number lookup against `suppliers` table, or
   ask for supplier ID/name)
2. Authenticate if the intent requires it (e.g. placing/modifying a PO)
3. Classify intent: place PO / check stock / check shipment status / other
4. Slot-fill required details via conversation (SKU, quantity, PO number)
5. Query or write to the tenant's database
6. Confirm back verbally what was found/done
7. Log the full interaction (transcript + structured summary) to
   `call_logs`
8. If confidence is low at any step, escalate: "I'll have someone call
   you back," and flag for human review — never guess on a data write

## 7. Tech Stack

| Layer | Choice | Why |
|---|---|---|
| Telephony | Twilio Voice | Pay-per-minute, no upfront cost, India coverage |
| Speech-to-text | Deepgram or Whisper API | Cost-effective, good latency |
| LLM / reasoning | Groq (Llama 3.1) | Already used in ExpertIQ/ClinicalRAG; fast inference for real-time conversation |
| Text-to-speech | ElevenLabs or Azure TTS | Free/cheap tier available |
| Orchestration | LangGraph | Reused pattern from ExpertIQ (multi-agent workflow) |
| Database | Supabase (Postgres) | Free tier, built-in auth, realtime subscriptions — useful for the live dashboard |
| Backend | FastAPI | Consistent with existing stack (ExpertIQ, ClinicalRAG) |
| Frontend | Next.js (already built) | Existing frontend + brand kit to be integrated |
| Multi-tenancy | Row-level security in Supabase, tenant_id on all tables | Required before selling to a second company |

## 8. Data Model (draft — see schema.md for full DDL)

- `tenants` — one row per company using VoxFlow
- `suppliers` — per-tenant contact directory
- `stock` — per-tenant SKU/quantity records
- `orders` (POs) — per-tenant order records
- `shipments` — per-tenant dispatch/shipment status
- `call_logs` — every call: transcript, intent, entities extracted, outcome,
  escalation flag, timestamps
- `users` — tenant staff who can log into the dashboard (Supabase Auth)

## 9. Authentication & Security

- **Tenant staff login:** Supabase Auth (email/password or magic link),
  scoped per tenant via row-level security.
- **Caller authentication (for sensitive actions):** phone number match
  against registered supplier record, optionally + spoken PIN/last-order
  reference for higher-risk actions (large orders, PO changes). Read-only
  queries (stock check) can be lower-friction than writes (placing a PO).
- **Data isolation:** every table has a `tenant_id`; Supabase row-level
  security policies enforce that tenant A can never read/write tenant B's
  data, enforced at the database level, not just the application level.

## 10. Real-Time Dashboard

- Live view of active calls (via Supabase Realtime subscriptions)
- Per-call transcript stream as it happens
- Post-call summary feed: intent, entities, outcome, escalations needing
  human follow-up
- Manual override: a staff member can "join"/take over a flagged call

## 11. Success Metrics (for the first real pilot, not vanity metrics)

- % of calls fully handled without human intervention
- % of calls correctly escalated (not incorrectly auto-handled when it
  shouldn't have been)
- Data entry accuracy vs. manual process (spot-checked)
- Time saved per day for the person currently doing this manually
- Zero cross-tenant data leakage (non-negotiable, tested explicitly)

## 12. Commercial Model (draft, revisit after pilot)

- Per-tenant monthly subscription based on call volume tier, not per-seat
  (this is a call-handling tool, not a team tool)
- Pilot/design-partner phase: free or heavily discounted in exchange for
  real usage data, feedback, and a case study/testimonial
- Do not price this before you have one working pilot — pricing without
  proof is a guess dressed up as a decision

## 13. Immediate Next Step (before more building)

Have the actual conversation with your friend about the real workflow.
This PRD should be revised after that conversation, specifically sections
6 (Assumed Workflow) and 8 (Data Model). Everything else can proceed in
parallel.
