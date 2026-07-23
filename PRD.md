# VoxFlow — Product Requirements Document

**Status:** Living document — Phase 2 of build complete, Phase 3 (voice/Twilio) next
**Owner:** Jesse (Jeevesh Singale)
**Repo:** github.com/jeevesh2515/voxflow-voice-agent
**Last updated:** 2026-07-23

---

## 0. Reality Check

No paying customer or design partner has been confirmed yet. "Varun Beverages"
in this document is a hypothesis target, informed secondhand (a friend who
works there), not a validated spec. Do not let Phase 4+ (real Twilio numbers,
billing, pricing commitments) proceed without an actual conversation
confirming the workflow described in Section 5 is accurate.

---

## 1. Problem Statement

Regional distributors and C&F (carrying & forwarding) agents for large FMCG
brands in India — e.g. a PepsiCo distributor like Varun Beverages — sit in
the middle of a call-heavy, error-prone workflow:

- **Inbound calls** from their own supplier/retail network placing POs,
  checking stock, asking about shipment status
- **Outbound-facing demand** from modern trade and quick-commerce partners
  (Swiggy Instamart, Blinkit, Flipkart Minutes) who expect fast, accurate
  stock and order confirmation — often on tight SLAs
- One or a handful of ops staff manually juggling phone calls, Excel
  sheets, and WhatsApp to keep all of this straight

This creates bottlenecks (staff unavailable = calls missed or delayed),
data entry errors (manual re-typing from a phone call into Excel), and no
structured record of what was promised on any given call — which becomes a
real liability when a quick-commerce partner disputes a stock commitment.

## 2. Solution

VoxFlow is a bilingual (Hindi/English) voice AI agent that answers inbound
calls on behalf of a distributor, identifies and verifies the caller,
handles stock checks/PO creation/shipment status via natural conversation,
writes structured data to the company's database in real time, and gives
staff a live dashboard of every call — in progress and completed — with
full transcripts and an audit trail.

It is explicitly scoped to **structured, transactional phone workflows**
(stock check, PO creation, shipment status, appointment scheduling) — not
a general-purpose chatbot, not outbound sales, not payment processing.

## 3. Target Customer

- **Primary (validation target):** Regional FMCG distributors/C&F agents
  in India handling high call volume from their supplier network and
  answering to modern-trade/quick-commerce demand (Swiggy Instamart,
  Blinkit, Flipkart Minutes, Zepto, etc.)
- **Buyer persona:** Ops manager or owner who currently relies on 1-2
  people manually handling all supplier/customer calls plus Excel
  reconciliation
- **Not yet targeted:** National call centers, multi-brand/multi-category
  retail hotlines, anything requiring outbound cold-calling

## 4. Current Build Status (as of this document)

Already implemented in the repo:
- FastAPI backend (`apps/api`) with a working agent loop (`AgentRunner`)
  using pluggable LLM providers (Groq / Ollama / OpenRouter)
- 11 working agent tools: `lookup_supplier`, `verify_caller`, `check_stock`,
  `get_shipment_status`, `create_po`, `verify_po`, `schedule_appointment`,
  `send_email`, `send_whatsapp_message`, `update_worksheet`, `type_notes`,
  `escalate_to_human`
- Full multi-tenant schema (`schema.md`) with `tenant_id` on every
  business table, RLS policy blueprint for Supabase
- Local STT (`faster-whisper`) and TTS (`edge-tts`) wired into a
  WebSocket-based voice pipeline (`voice/pipeline.py`) — currently
  reachable via an in-browser phone simulator, not real phone calls
- Next.js 14 dashboard (`apps/web`) with pages for calls, orders,
  shipments, stock, suppliers, appointments, communications, a simulator,
  pricing, and sign-in/sign-up — with a working tenant-switcher for
  multiple demo companies (Varun Beverages, Amul, Haldirams, Britannia)
- A distinctive dark neon design system already implemented (see
  DESIGN.md)

**Not yet implemented:**
- Real telephony (Twilio) — calls currently only work through the browser
  simulator, not an actual phone number
- Async/non-blocking DB layer (current DB calls are synchronous inside
  async request handlers — see ARCHITECTURE.md)
- Caller-side PIN/stronger auth beyond city/GSTIN verification
- Real Supabase Auth for staff login (currently `localStorage`-based
  session, per `security_audit.md`)
- Any real pilot or design partner

## 5. Assumed Core Workflow (validate before Phase 4)

1. Call arrives → resolve `tenant_id` (which company was called)
2. Agent greets caller in Hindi or English (auto-detected)
3. `lookup_supplier` by phone number
4. For sensitive actions, `verify_caller` (city or GSTIN challenge)
5. Classify intent: stock check / place PO / shipment status / schedule
   appointment / other
6. Slot-fill required details conversationally
7. Execute: `check_stock`, `create_po`, `get_shipment_status`, or
   `schedule_appointment`
8. Read back result verbally, confirm before any write
9. Log full transcript + structured actions to `calls` table
10. If confidence is low at any point, `escalate_to_human` — never guess
    on a data write

## 6. Out of Scope for v1

- Outbound/cold calling
- Languages beyond Hindi + English (Hinglish code-switching should be
  handled within these two, not additional languages)
- Payment processing over the phone
- Full ERP/CRM replacement
- Multi-warehouse routing logic beyond what `stock.warehouse` already
  supports

## 7. Success Metrics for First Real Pilot

- % of calls fully resolved without human intervention
- % of calls correctly escalated (not wrongly auto-handled)
- Data entry accuracy vs. the manual Excel process it replaces
- Staff time saved per day
- Zero cross-tenant data leakage — tested explicitly, not assumed

## 8. Commercial Model (draft — do not finalize before a pilot)

- Per-tenant monthly subscription tiered by call volume, not per-seat
- Pilot phase: free or heavily discounted for a real design partner in
  exchange for usage data and a testimonial
- `apps/web/src/app/pricing/page.tsx` already exists as a scaffold —
  populate it with real tiers only after pilot data exists, not before

## 9. Immediate Next Step

Have the real conversation with the friend at Varun Beverages about the
actual workflow before Phase 4 (multi-tenancy hardening / real caller
auth) locks in assumptions that may not match reality.
