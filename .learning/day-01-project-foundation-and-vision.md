# Day 1 — Project Foundation And Vision

## Status

Complete. Phases 0–2 are implemented and the repo is ready for the next stage.

## Main learning goal

Understand the product vision, architecture design decisions, and the foundational work already built across Phases 0–2 before adding voice capabilities.

## What I learned

### 1. The problem VoxFlow solves

Regional FMCG distributors in India (e.g. PepsiCo distributors like Varun Beverages) sit in a call-heavy workflow:
- Inbound calls from supplier/retail networks placing POs, checking stock, asking about shipment status
- Outbound demand from quick-commerce partners (Swiggy Instamart, Blinkit, Flipkart Minutes)
- Staff manually juggling phone calls, Excel sheets, and WhatsApp

The bottleneck: staff unavailable = missed calls, manual data entry errors, no structured record of what was promised.

### 2. Solution architecture

```
Caller's Phone → Twilio → FastAPI Backend → LLM (Groq) → Postgres
                                              → STT (faster-whisper)
                                              → TTS (edge-tts)
                                              → Next.js Dashboard
```

Key design decisions:
- **Multi-tenant from day one** — `tenant_id` on every business table, RLS at DB level
- **Pluggable LLM** — Groq (primary), Ollama (local), OpenRouter (fallback)
- **Local STT/TTS** — faster-whisper + edge-tts, no cloud dependency for voice pipeline
- **Browser simulator before Twilio** — voice pipeline proven in-browser, telephony added later

### 3. Multi-tenancy pattern

Every query is scoped by `tenant_id`. The frontend `TenantProvider` drives which company's data is visible. The backend tools all accept `session: CallSession` carrying `tenant_id`. RLS at the database layer is the last line of defense.

### 4. Conversational state machine

Not free-form chat — a structured state machine:
1. Greet & Identify (lookup by phone)
2. Intent Classification (stock check / PO / shipment / appointment)
3. Slot-Filling (extract SKU, quantity, dates conversationally)
4. Action Execution (read/write DB)
5. Confirmation (read back result)
6. Fallback/Escalation

### 5. What Phases 0–2 built

**Phase 0 — Setup:**
- GitHub repo, FastAPI skeleton, Supabase project, Groq API wired
- Next.js frontend with dark neon design system
- All API keys in `.env` (never committed)

**Phase 1 — Database Foundation:**
- Full schema in `schema.md`: tenants, suppliers, stock, orders, shipments, calls, appointments, worksheet_logs, communication_logs
- SQLAlchemy models in `db.py`
- RLS policy blueprint documented
- Seed data for 4 tenants (Varun Beverages, Amul, Haldirams, Britannia) with realistic messy data
- `verify_db.py` for multi-tenant data verification

**Phase 2 — Auth & Dashboard:**
- Sign-up flow: register company, land on dashboard
- Sign-in flow: company selector + credentials/Quick Demo
- Workspace switcher in Topbar
- Session persistence in localStorage
- Dashboard pages: calls, orders, shipments, stock, suppliers, appointments, communications, simulator

### 6. Known gaps (documented in MEMORY.md)

- DB calls are synchronous inside async handlers — blocks event loop
- No real telephony — calls only work through browser simulator
- Staff auth is localStorage-based, not real Supabase Auth
- Caller auth is city/GSTIN only — no PIN for write actions
- No dashboard realtime — call logs need manual refresh
- No real pilot conversation validated

## Key architectures and files

| File | Purpose |
| --- | --- |
| `PRD.md` | Product requirements, problem, scope |
| `ARCHITECTURE.md` | System architecture, latency-critical path |
| `RULES.md` | Library choices, boundaries for AI assistants |
| `PHASES.md` | Week-by-week, day-by-day build plan |
| `MEMORY.md` | Live status — what's done, what's in progress |
| `DESIGN.md` | Dark neon design system tokens |
| `schema.md` | DDL + RLS policy reference |
| `apps/api/voxflow_api/db.py` | SQLAlchemy models (sync — needs async migration) |
| `apps/api/voxflow_api/agent/runner.py` | Tool-calling conversation loop |
| `apps/api/voxflow_api/agent/tools.py` | 11 agent tools with DB access |
| `apps/api/voxflow_api/voice/pipeline.py` | Voice pipeline orchestration |
| `apps/web/` | Next.js 14 dashboard |

## Interview explanation

I joined a project that already has Phases 0–2 built: a FastAPI backend with a working agent loop using pluggable LLM providers, 11 agent tools, a full multi-tenant database schema with RLS, local STT/TTS, and a Next.js dashboard. The most critical architectural issue is that all database calls are synchronous inside async request handlers, which blocks the event loop and adds real felt latency on voice calls. The immediate next step is to fix this by migrating to async SQLAlchemy before adding real telephony.

## Non-technical explanation

VoxFlow is a voice assistant for Indian FMCG distributors. When a supplier calls to place an order, the AI answers, checks stock, creates the order, and logs everything — without a human needing to pick up. The core architecture is already built; we're about to fix performance bottlenecks and then connect it to real phone lines.

## Day 1 outcome

Deep understanding of the product vision, architecture, existing codebase, and the critical next steps.

## Next step after Day 1

Day 2 should focus on the theory behind async database access, event loop blocking, and caching patterns — the foundations needed before Week 1 implementation.
