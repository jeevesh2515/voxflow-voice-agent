# 📅 VoxFlow — Master Day-Wise Implementation Tracker

**Project:** VoxFlow — Voice Operations for Modern Supply Chains  
**Repository:** `jeevesh2515/voxflow-voice-agent`  
**Current Test Suite:** **402 Passing Tests** (`pytest tests/ -q`)
**Frontend Surface:** **25 Compiled Routes** (Next.js 16 App Router, Turbopack production validation)
**Deployment Infrastructure:** Oracle Cloud Always-Free ARM VM (Caddy Auto-TLS + Docker) / Render Free API / Vercel Edge Frontend  
**Last Updated:** 2026-08-30

---

## 📊 High-Level Programme Roadmap

| Phase | Days | Focus Area | Status | Verified Outcome |
|---|---:|---|---|---|
| **Phase 1** | 1–5 | Foundation, DB Architecture & Latency | ✅ Complete | Async SQLAlchemy models, SQLite/PostgreSQL pooling, Groq LLM integration. |
| **Phase 2** | 6–10 | Voice Pipeline & Multilingual Telephony | ✅ Complete | Bi-directional Twilio Media Streams, Groq Whisper STT, Edge-TTS Hindi/English, VAD tuning. |
| **Phase 3** | 11–15 | Auth, Multi-Tenancy & Verification | ✅ Complete | Supabase Auth, Row Level Security (RLS), Caller PIN Tier-2 auth, SMS triggers, end-to-end testing. |
| **Phase 4** | 16–20 | Live Observability & Pilot Readiness | ✅ Complete | In-progress active call tracking, escalation queue, security audit & rate limiting, pilot conversations. |
| **Phase 5** | 21–24 | Cloud Deployment & Campaign Domain | ✅ Complete | Multi-cloud staging (Render/Fly/Oracle), Sheets logger, email summarizer, outbound campaign models. |
| **Phase 6** | 25–28 | Durable Execution Foundation | ✅ Complete | `JobRun`, `JobOutbox`, `JobAttempt`, atomic claims with worker leases, exponential backoff, health APIs. |
| **Phase 7** | 29–32 | Controlled Cutover & Provider Lifecycle | ✅ Complete | Canary worker filters, tenant policy engine, consent checks, enterprise analytics CSV, signed callback quarantine. |
| **Phase 8** | 33–36 | Adapters, Side Effects & Pilot Evidence | ✅ Complete | Dial sandbox HMAC adapter, typed side-effect jobs ledger, fail-closed pilot admission, same-cohort hold points. |
| **Phase 9** | Production | Infrastructure, Resilience & UI Overhaul | ✅ Complete | Oracle ARM VM + Caddy Auto-TLS, Next.js 16 standalone Docker, LLM resilience fallback, 16 dashboard views overhaul. |
| **Phase 10** | 41–45 | UK Voice, SaaS Onboarding & CSV Engine | ✅ Complete | Amazon Connect en-GB, Postgres+Sheets call logs, resilience & backups, self-serve signup & onboarding, streaming CSV ingestion & validation engine. |


---

## 📖 Day-by-Day Implementation Log

---

### 🔹 Phase 1: Foundation, DB Architecture & Latency (Days 1–5)

#### 🗓️ Day 1: Project Foundation & Product Vision
- **Objective:** Establish the repository structure, architecture vision, and initial supply-chain domain requirements.
- **Implementation:**
  - Defined monorepo layout: `apps/api` (FastAPI backend) and `apps/web` (Next.js frontend).
  - Designed supply-chain voice agent workflows: Purchase Orders, Shipment Status, Stock Queries, Appointments, and Escalations.
  - Configured project environment variables and initial configuration models (`config.py`).
- **Artifacts:** `PRD.md`, `ARCHITECTURE.md`, `.learning/day-01-project-foundation-and-vision.md`.

#### 🗓️ Day 2: Async Database & Latency Theory
- **Objective:** Design the database schema and async session management for sub-second voice latency.
- **Implementation:**
  - Implemented SQLAlchemy async engine and scoped session pool in `voxflow_api/db.py`.
  - Created core supply-chain models: `Supplier`, `PurchaseOrder`, `Shipment`, `StockItem`, `Appointment`, `Communication`, and `Call`.
  - Added connection pooling configurations and latency measurement wrappers.
- **Artifacts:** `schema.md`, `.learning/day-02-async-db-and-latency-theory.md`.

#### 🗓️ Day 3: Twilio & Telephony Foundations
- **Objective:** Research and scaffold Twilio Voice webhook protocols and audio stream streaming.
- **Implementation:**
  - Created initial TwiML webhook endpoints (`POST /twilio/voice`).
  - Configured TwiML `<Connect><Stream>` verbs for bi-directional WebSocket audio exchange.
  - Implemented request validation and basic webhook security guards.
- **Artifacts:** `voxflow_api/routes/twilio.py`, `.learning/day-03-twilio-and-telephony-theory.md`.

#### 🗓️ Day 4: Async DB Implementation & Query Optimization
- **Objective:** Complete async database CRUD operations and seed scripts for testing.
- **Implementation:**
  - Built repository functions for async lookup of purchase orders, stock items, and supplier contacts.
  - Created initial database seeding script (`scripts/seed_demo.py`) with realistic tenant test data (`tenant_id="varun"`).
  - Added unit test fixtures for SQLite in-memory testing.
- **Artifacts:** `tests/conftest.py`, `.learning/day-04-next-up-async-db-implementation.md`.

#### 🗓️ Day 5: Database Caching & Pipeline Benchmark
- **Objective:** Implement in-memory caching and measure end-to-end agent turn latency.
- **Implementation:**
  - Added TTL-based caching layer for frequent supplier and inventory metadata lookups.
  - Benchmarked database query response times (consistently < 5ms locally).
  - Set up structured logging (`structlog`) for per-request latency attribution.
- **Artifacts:** `voxflow_api/logging.py`, `.learning/day-05-async-complete-and-caching.md`.

---

### 🔹 Phase 2: Voice Pipeline & Multilingual Telephony (Days 6–10)

#### 🗓️ Day 6: Frontend Dashboard Polish & Web Scaffolding
- **Objective:** Build the initial Next.js operations dashboard layout and live navigation.
- **Implementation:**
  - Initialized Next.js App Router project with Tailwind CSS and Lucide icons.
  - Created core layout components: Sidebar, Header, Tenant Selector, and Status indicators.
  - Built initial mock views for Orders, Inventory, Suppliers, and Calls.
- **Artifacts:** `apps/web/src/components/Sidebar.tsx`, `apps/web/src/app/dashboard/page.tsx`.

#### 🗓️ Day 7: Twilio Media Streams WebSocket Pipeline
- **Objective:** Establish real-time bi-directional audio streaming over WebSockets.
- **Implementation:**
  - Created `WS /twilio/media` endpoint handling Twilio binary audio chunks (8kHz mu-law).
  - Implemented audio format converters: 8kHz mu-law $\leftrightarrow$ 16kHz linear PCM.
  - Built incoming audio buffer with silence detection.
- **Artifacts:** `voxflow_api/routes/twilio.py`, `.learning/day-07-twilio-media-streams-websocket.md`.

#### 🗓️ Day 8: Speech-to-Text (STT) Integration with Groq Whisper
- **Objective:** Connect streaming audio to hosted Groq Whisper for near-instant Hindi-English transcription.
- **Implementation:**
  - Integrated Groq Whisper Cloud API (`whisper-large-v3-turbo`) for transcribed utterances.
  - Implemented speech chunking and pre-buffering to minimize transcription latency (< 300ms).
  - Added language detection supporting code-switched Hindi-English (Hinglish).
- **Artifacts:** `voxflow_api/stt/groq.py`, `.learning/day-08-stt-into-twilio-stream.md`.

#### 🗓️ Day 9: Agent Tool Execution & Text-to-Speech (TTS) into Stream
- **Objective:** Execute supply-chain tools via LLM function calling and stream synthesize audio back to Twilio.
- **Implementation:**
  - Created agent runner with function calling (`lookup_supplier`, `check_po_status`, `check_stock_availability`).
  - Integrated Edge-TTS for low-latency, natural Hindi and Indian English audio synthesis.
  - Streamed chunked audio directly back to the Twilio WebSocket session.
- **Artifacts:** `voxflow_api/agent/runner.py`, `voxflow_api/tts/edge.py`.

#### 🗓️ Day 10: Multi-Caller Testing & Voice Activity Detection (VAD) Tuning
- **Objective:** Tune Voice Activity Detection (VAD) thresholds and test concurrent voice streams.
- **Implementation:**
  - Implemented energy-based VAD with configurable silence threshold and speech padding.
  - Handled user interruptions (barge-in): instantly clearing the audio playback buffer when caller speaks.
  - Validated multi-caller concurrency without memory leaks.
- **Artifacts:** `.learning/day-10-multi-caller-testing-and-vad-tuning.md`.

---

### 🔹 Phase 3: Auth, Multi-Tenancy & Verification (Days 11–15)

#### 🗓️ Day 11: Supabase Multi-Tenant Authentication & JWT Verification
- **Objective:** Secure the backend and frontend with Supabase Auth and JWKS token validation.
- **Implementation:**
  - Added Supabase JWT verification middleware in FastAPI (`voxflow_api/auth.py`).
  - Created Next.js client authentication context (`apps/web/src/lib/supabase.ts`).
  - Extracted `tenant_id` claims from authenticated user tokens to enforce tenant isolation.
- **Artifacts:** `apps/api/voxflow_api/auth.py`, `.learning/day-11-real-supabase-auth-and-rls.md`.

#### 🗓️ Day 12: PostgreSQL Row-Level Security (RLS) Enforcement
- **Objective:** Implement database-level multi-tenant isolation via PostgreSQL Row-Level Security.
- **Implementation:**
  - Authored SQL migration enabling RLS on all 11 core tables.
  - Created tenant isolation policies enforcing `tenant_id = current_setting('app.current_tenant')`.
  - Added automated test suite verifying cross-tenant data leakage is completely prevented.
- **Artifacts:** `migrations/001_rls_policies.sql`, `.learning/day-12-rls-enforcement-and-telephony-milestone.md`.

#### 🗓️ Day 13: Tier-2 Caller PIN Verification
- **Objective:** Protect sensitive operations (e.g., PO cancellation, payment release) with caller PIN 2FA.
- **Implementation:**
  - Added `pin_hash` field to `Supplier` model with bcrypt hashing.
  - Designed interactive voice 2FA flow: agent prompts for 4-digit PIN when sensitive tool is requested.
  - Implemented session verification state tracking (`pin_verified=True`).
- **Artifacts:** `voxflow_api/agent/tools.py`, `.learning/day-13-caller-pin-auth-tier2.md`.

#### 🗓️ Day 14: Telephony SMS Triggers & Notifications
- **Objective:** Send instant SMS summaries and confirmation links to callers after call completion.
- **Implementation:**
  - Integrated Twilio SMS API to dispatch follow-up notifications upon call termination.
  - Added SMS templates for Purchase Order acknowledgements and appointment confirmations.
  - Added opt-out and delivery status tracking.
- **Artifacts:** `voxflow_api/integrations/sms.py`, `.learning/day-14-telephony-sms-and-live-verification-milestone.md`.

#### 🗓️ Day 15: End-to-End Voice Flow Verification & Buffer Hardening
- **Objective:** Run complete end-to-end voice simulation and harden audio buffering.
- **Implementation:**
  - Built interactive Browser Simulator with Web Audio API for local microphone testing.
  - Implemented jitter buffer to prevent audio stutter on packet delay.
  - Completed comprehensive test pass verifying all voice tools and session state transitions.
- **Artifacts:** `apps/web/src/app/dashboard/simulator/page.tsx`, `.learning/day-15-buffer-and-end-to-end-verification-milestone.md`.

---

### 🔹 Phase 4: Live Observability & Pilot Readiness (Days 16–20)

#### 🗓️ Day 16: In-Progress Call Status & Live Observability
- **Objective:** Display real-time active calls on the dashboard with live elapsed timers.
- **Implementation:**
  - Added `GET /api/active-calls` endpoint exposing active in-memory `CallSession` objects.
  - Created `ActiveCallCard` with pulsing visual indicator and live `useElapsed()` timer hook.
  - Implemented 5s SWR polling on `/dashboard/calls` with zero UI flicker.
- **Artifacts:** `apps/web/src/app/dashboard/calls/page.tsx`, `DAY16-20_WEEK4.md`.

#### 🗓️ Day 17: Escalation Queue & Staff Resolution Workflow
- **Objective:** Manage and resolve escalated calls requiring human operator attention.
- **Implementation:**
  - Built `/dashboard/escalations` view filtering calls flagged as `escalated` or `follow_up_required`.
  - Added `PATCH /api/calls/{id}/resolution` endpoint to store staff notes and resolution timestamp.
  - Added escalation metrics and resolution status badges to dashboard.
- **Artifacts:** `apps/web/src/app/dashboard/escalations/page.tsx`, `DAY16-20_WEEK4.md`.

#### 🗓️ Day 18: Security Pass & Production Hardening
- **Objective:** Conduct security audit, implement rate limiting, and secure credential handling.
- **Implementation:**
  - Added IP-based WebSocket rate limiting on `/twilio/media` (10 conns/60s per IP, closes with code 1008).
  - Added HTTP security headers (`X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Cache-Control`).
  - Added dual Twilio credential support (Account SID + Auth Token vs API Key + Secret).
- **Artifacts:** `security_audit.md`, `DAY16-20_WEEK4.md`.

#### 🗓️ Day 19: Pilot Conversation & Real-World Validation
- **Objective:** Validate conversational accuracy and tool execution against realistic supplier scenarios.
- **Implementation:**
  - Formulated 15 standard supply-chain conversation test transcripts (Hindi, English, Hinglish).
  - Evaluated tool calling precision, prompt injection resistance, and hallucination bounds.
  - Calibrated system prompts for professional, concise operational responses.
- **Artifacts:** `docs/demo-script.md`, `.learning/day-19-pilot-conversation-and-real-world-validation.md`.

#### 🗓️ Day 20: Pilot Readiness Signoff & Architecture Review
- **Objective:** Formulate operational runbooks and finalize pilot readiness criteria.
- **Implementation:**
  - Authored Operations Runbook (`DEMO_OPERATIONS_RUNBOOK.md`) covering deployment, monitoring, and recovery.
  - Conducted architectural review of multi-tenant isolation and database connection limits.
  - Verified 152 automated backend tests passing.
- **Artifacts:** `docs/DEMO_OPERATIONS_RUNBOOK.md`, `.learning/day-20-pilot-readiness-and-project-signoff.md`.

---

### 🔹 Phase 5: Cloud Deployment & Campaign Domain (Days 21–24)

#### 🗓️ Day 21: Cloud Deployment Resilience & Full SaaS Verification
- **Objective:** Deploy full stack to cloud infrastructure (Render FastAPI + Vercel Next.js + Supabase DB).
- **Implementation:**
  - Configured `render.yaml` infrastructure-as-code and Vercel edge deployment settings.
  - Added health checks (`GET /api/health`), database dialect verification, and CORS configuration.
  - Verified cross-origin communication between Vercel frontend and Render backend.
- **Artifacts:** `render.yaml`, `vercel.json`, `.learning/day-21-cloud-deployment-resilience-and-full-saas-verification.md`.

#### 🗓️ Day 22: Production Scaling, Monitoring & Advanced Telephony
- **Objective:** Plan horizontal scaling, connection pooling, and SIP trunking architecture.
- **Implementation:**
  - Designed worker pool architecture separating telephony ingress from heavy background tasks.
  - Configured Supabase Transaction Pooler (PgBouncer IPv4) to support containerized clients.
  - Formulated disaster recovery and database backup procedures.
- **Artifacts:** `.learning/day-22-production-scaling-monitoring-and-advanced-telephony-theory.md`.

#### 🗓️ Day 23: Inbound Call Intelligence (Sheets Logger & Email Summarizer)
- **Objective:** Automatically log call summaries to Google Sheets and email executive digests.
- **Implementation:**
  - Built asynchronous Google Sheets logging queue (`integrations/sheets.py`) with automatic retry.
  - Implemented LLM-powered call summarization engine producing structured action items.
  - Added automated email summary dispatcher for high-priority operational calls.
- **Artifacts:** `voxflow_api/integrations/sheets.py`, `voxflow_api/integrations/email.py`.

#### 🗓️ Day 24: Outbound Calling & Campaigns Domain
- **Objective:** Introduce autonomous outbound campaign domain models, queue management, and UI.
- **Implementation:**
  - Added `OutboundCampaign` and `CampaignQueue` SQLAlchemy models in `voxflow_api/db.py`.
  - Built REST API router (`voxflow_api/routes/campaigns.py`) for campaign CRUD and target queueing.
  - Created `/dashboard/campaigns` UI with batch upload, progress tracking, and run/pause controls.
  - Integrated Dial AI client (`integrations/dial.py`) with language normalization (`hi-IN`, `en-IN`).
- **Artifacts:** `voxflow_api/routes/campaigns.py`, `apps/web/src/app/dashboard/campaigns/page.tsx`.

---

### 🔹 Phase 6: Durable Execution Foundation (Days 25–28)

#### 🗓️ Day 25: Transactional Durable Job Ledger & Atomic Enqueue
- **Objective:** Guarantee that campaign targets and outbox events commit together atomically without data loss.
- **Implementation:**
  - Created `JobRun`, `JobOutbox`, `JobAttempt`, and `ProviderOperation` ledger tables.
  - Implemented transactional atomic enqueue (`jobs/enqueue.py`): campaign target + job + outbox write commit in single DB transaction.
  - Added unique idempotency keys per campaign target preventing duplicate runs.
- **Artifacts:** `migrations/003_durable_job_ledger.sql`, `voxflow_api/jobs/enqueue.py`.

#### 🗓️ Day 26: Atomic Job Claims & Worker Leases
- **Objective:** Implement distributed worker lease protocol preventing competing worker race conditions.
- **Implementation:**
  - Built atomic job claiming (`jobs/repository.py`) using `SELECT FOR UPDATE SKIP LOCKED`.
  - Added worker heartbeats and time-bounded leases (`lease_expires_at`).
  - Added automatic stale-lease recovery to reclaim jobs from crashed worker nodes.
- **Artifacts:** `voxflow_api/jobs/repository.py`, `.learning/day-26-atomic-job-claims-and-worker-leases.md`.

#### 🗓️ Day 27: Worker Runtime Resilience & Exponential Backoff
- **Objective:** Build robust worker execution loop with typed error classification and jittered retries.
- **Implementation:**
  - Created `WorkerRuntime` (`jobs/worker.py`) with full-jitter exponential backoff.
  - Classified errors into transient (retryable) vs permanent (immediate dead-letter).
  - Added POSIX signal handling (`SIGTERM`, `SIGINT`) for graceful worker drain without dropping jobs.
- **Artifacts:** `voxflow_api/jobs/worker.py`, `.learning/day-27-worker-runtime-retries-and-graceful-drain.md`.

#### 🗓️ Day 28: Transactional Outbox Relay & Health Observability
- **Objective:** Relay outbox events reliably and expose tenant-safe job health metrics.
- **Implementation:**
  - Created background `OutboxRelay` service dispatching pending transactional events.
  - Built tenant-scoped job health read API (`GET /api/jobs/health`) reporting ready, leased, retrying, and dead-letter counts.
  - Added Operator Job Health visual panel to the dashboard.
- **Artifacts:** `migrations/004_outbox_relay_state.sql`, `voxflow_api/jobs/outbox.py`.

---

### 🔹 Phase 7: Controlled Cutover & Provider Lifecycle (Days 29–32)

#### 🗓️ Day 29: Controlled Standalone Worker & Canary Cutover
- **Objective:** Build isolated worker process with global kill-switches and canary tenant gating.
- **Implementation:**
  - Created standalone worker entry point (`jobs/campaign_worker_service.py`).
  - Implemented canary filtering (`CAMPAIGN_WORKER_ALLOWED_TENANTS`) and dry-run simulation mode.
  - Built provider-operation reconciliation ensuring retried jobs reconcile rather than re-dialing.
- **Artifacts:** `voxflow_api/jobs/campaign_worker_service.py`, `voxflow_api/jobs/campaign_dispatch.py`.

#### 🗓️ Day 30: Tenant Policy Engine & Consent Enforcement
- **Objective:** Enforce calling windows, recipient consent, daily budget, and capacity limits before dialing.
- **Implementation:**
  - Built `campaign_policy.py` evaluating timezone calling windows (e.g., 09:00–18:00 IST), consent records, and daily quotas.
  - Stored immutable policy decisions as `CampaignPolicyDecision` audit rows.
  - Added auditable campaign cancellation and exact next-run deferrals.
- **Artifacts:** `migrations/005_campaign_policy_controls.sql`, `voxflow_api/jobs/campaign_policy.py`.

#### 🗓️ Day 31: Enterprise Analytics & Reporting Engine
- **Objective:** Provide tenant-safe KPI aggregation, trend charts, and redacted CSV export.
- **Implementation:**
  - Built analytics overview API (`GET /api/analytics/overview`) calculating call success rates, policy deferrals, and error distributions.
  - Added secure CSV report generation with strict PII masking (redacting phone numbers, transcripts, and credentials).
  - Added interactive trend visualization cards to `/dashboard/analytics`.
- **Artifacts:** `voxflow_api/routes/analytics.py`, `apps/web/src/app/dashboard/analytics/page.tsx`.

#### 🗓️ Day 32: Provider Lifecycle & Idempotent Callback Quarantine
- **Objective:** Secure provider callback ingress with signature verification, deduplication, and quarantine.
- **Implementation:**
  - Created `POST /api/provider-callbacks/events` route validating timestamp freshness and HMAC signatures.
  - Implemented `ProviderEvent` ledger preventing out-of-order state regressions (e.g., ringing after ended).
  - Quarantined unauthenticated or unknown provider call IDs in `provider_callback_quarantine` table.
- **Artifacts:** `migrations/006_provider_callback_lifecycle.sql`, `voxflow_api/routes/provider_callbacks.py`.

---

### 🔹 Phase 8: Adapters, Side Effects & Pilot Evidence (Days 33–36)

#### 🗓️ Day 33: Dial Sandbox HMAC Callback Adapter
- **Objective:** Build dedicated Dial provider adapter with raw-body HMAC verification and secret overlap.
- **Implementation:**
  - Created `POST /api/provider-callbacks/dial/events` with raw-body SHA-256 HMAC verification.
  - Supported zero-downtime secret rotation via current/previous secret overlap validation.
  - Added redacted audit ledger (`provider_callback_adapter_audits`) and dashboard status panel.
- **Artifacts:** `migrations/007_dial_sandbox_callback_adapter.sql`, `voxflow_api/integrations/dial_callbacks.py`.

#### 🗓️ Day 34: Typed Durable Side-Effect Jobs
- **Objective:** Eliminate inline external IO from API requests by transitioning all side-effects to durable jobs.
- **Implementation:**
  - Created `SideEffectIntent` ledger supporting Sheets, email, CRM sync, notifications, and recording tasks.
  - Decoupled FastAPI request handlers from Google Sheets and email APIs via background outbox enqueue.
  - Built standalone `SideEffectWorkerService` with dry-run mode and tenant allow-lists.
- **Artifacts:** `migrations/008_typed_durable_side_effect_jobs.sql`, `voxflow_api/jobs/side_effects.py`.

#### 🗓️ Day 35: Controlled Pilot Admission & Reversible Rollback
- **Objective:** Implement fail-closed pilot tenant admission, cohort controls, and database rollback drills.
- **Implementation:**
  - Added `PilotConfiguration`, hashed `PilotCohortMember`, and `PilotSecurityIncident` models.
  - Enforced strict admission gate: required approved tenant, active cohort, micro-capacity, and named escalation coverage.
  - Built zero-provider-call database rollback drill script and dashboard readiness panel.
- **Artifacts:** `migrations/009_controlled_pilot_readiness.sql`, `voxflow_api/routes/pilot.py`.

#### 🗓️ Day 36: Evidence-Led Pilot Operations & Same-Cohort Hold Points
- **Objective:** Enforce immutable preflight and hold-point evidence before any operational execution.
- **Implementation:**
  - Added `PilotOperationalEvidence` ledger storing aggregate queue, lease, and callback health metrics.
  - Enforced same-day same-cohort hold-point gate (`PILOT_OPERATIONS_EVIDENCE_ENFORCED=true`) preventing automatic cohort expansion.
  - Built Pilot Operations Evidence dashboard panel with clear human-in-the-loop governance.
- **Artifacts:** `migrations/010_pilot_operations_evidence.sql`, `voxflow_api/routes/pilot.py`.

---

### 🔹 Phase 9: Infrastructure, Resilience & UI Overhaul (Latest)

#### 🗓️ Day 37 / Production Infrastructure: Oracle VM Deployment, LLM Resilience & Dashboard Overhaul
- **Objective:** Deploy production stack to Always-Free Oracle ARM VM, harden LLM fault-tolerance, and completely redesign the frontend dashboard.
- **Implementation:**
  1. **Oracle Cloud Always-Free ARM Architecture:**
     - Deployed containerized multi-arch stack (`caddy:2-alpine`, `python:3.12-slim`, `node:20-alpine`) on Oracle Ampere ARM (4 OCPU / 24 GB RAM).
     - Configured Caddy reverse proxy with automatic Let's Encrypt TLS/SSL certificates over HTTP-01 ACME.
     - Documented and resolved dual-layer cloud firewall (Oracle VCN Ingress Rules + Ubuntu `iptables` rule order).
     - Authored complete copy-paste deployment guide (`deploy/ORACLE_DEPLOY.md`) and automated VM management scripts (`deploy/diagnose-api.sh`, `deploy/sync-vm.sh`, `deploy/verify-vm.sh`, `scripts/preflight.sh`).
  2. **LLM Resilience & Provider Failover:**
     - Hardened agent runner (`agent/runner.py`) with graceful, non-blocking fallback on LLM unavailability (bilingual Hindi/English).
     - Added bounded exponential backoff with configurable `groq_max_retry_after_seconds` cap (5.0s) in `llm/groq.py`.
     - Built dedicated resilience test suite (`tests/test_llm_resilience.py`).
  3. **Complete Frontend Dashboard Redesign & Accessibility Overhaul:**
     - Overhauled all 16 dashboard views with a cohesive, modern, high-contrast dark/light theme.
     - Optimized components for WCAG AA accessibility, crystal-clear typography, and zero layout shifts.
     - Compiled 23 static pages cleanly with Turbopack in Next.js 16 (`apps/web/next.config.mjs` with `outputFileTracingRoot`).
- **Verification Evidence:**
  - ✅ **266/266 Passing Backend Tests** (`.venv/bin/pytest tests/ -q` in 86.5s).
  - ✅ **23/23 Static Compiled Routes** (`npm run build` in 20.8s, 0 errors).
  - ✅ **Vercel Frontend Live** (`https://web-gamma-ten-21.vercel.app`): Public routes return HTTP 200; all 13 dashboard routes return HTTP 307 redirect when unauthenticated.
#### 🗓️ Day 38: Multi-Provider Telephony (Telnyx + Amazon Connect AWS Integration)
- **Objective:** Eliminate single-carrier dependency by decoupling telephony from Twilio and implementing native support for Telnyx ($5 free credit) and Amazon Connect (90 min/mo free tier on AWS).
- **Implementation:**
  1. **Telephony Provider Abstraction Layer (`telephony/base.py`, `telephony/registry.py`):**
     - Abstracted webhook validation, incoming call normalization, connect response generation, and media streaming codec frames.
     - Implemented `TwilioProvider`, `TelnyxProvider`, and `ConnectProvider` behind a unified singleton provider registry.
  2. **Telnyx Integration (`routes/telnyx.py`, `telephony/telnyx_provider.py`):**
     - Added `POST /telnyx/voice` supporting both TeXML (TwiML-compatible) and Call Control v2 JSON payloads.
     - Added `WS /telnyx/media` for bidirectional audio streaming with G.711 μ-law codec, 8kHz $\rightarrow$ 16kHz resampling, VAD, and caller speech barge-in.
     - Added `POST /telnyx/status` for call lifecycle callbacks.
  3. **Amazon Connect AWS Integration (`routes/connect.py`, `deploy/aws/`):**
     - Built AWS Lambda bridge (`deploy/aws/lambda_handler.py`) with HMAC-SHA256 request authentication.
     - Added `POST /api/connect/turn` and `POST /api/connect/end` executing full AgentRunner turns (order tracking, appointment booking, inventory lookup, sheets sync).
     - Authored importable Amazon Connect Contact Flow template (`deploy/aws/connect-contact-flow.json`), Lambda deploy script (`deploy/aws/deploy-lambda.sh`), and setup guide (`deploy/aws/setup-connect.md`).
  4. **Multi-Provider Database Routing (`migrations/014_telephony_provider.sql`):**
     - Added `provider` column (`DEFAULT 'twilio'`) and index to `tenant_phone_numbers` for per-tenant telephony provider assignment.
- **Verification Evidence:**
  - ✅ **279/279 Passing Backend Tests** (`.venv/bin/pytest tests/ -q` in 54.4s).
  - ✅ **13/13 Telephony Unit & Integration Tests Passing** (`test_telephony_base.py`, `test_telnyx.py`, `test_connect.py`).
  - ✅ **23/23 Static Compiled Routes** (`npm run build` in 1916ms, 0 errors).
- **Artifacts:** `voxflow_api/telephony/`, `voxflow_api/routes/telnyx.py`, `voxflow_api/routes/connect.py`, `deploy/aws/`, `migrations/014_telephony_provider.sql`, `tests/test_telnyx.py`, `tests/test_connect.py`, `tests/test_telephony_base.py`.

#### 🗓️ Day 39: Always-On Baseline, Lambda VM Routing & Complete Sidebar Nav
- **Objective:** Eliminate cold-start latency drops by routing Amazon Connect Lambda to the always-on Oracle Cloud VM, link all orphaned pages into the dashboard Sidebar, and streamline the telephony stack to Amazon Connect + In-Browser Simulator.
- **Implementation:**
  1. **Always-On Lambda Bridge Routing (`deploy/aws/lambda_handler.py`):**
     - Configured default `VOXFLOW_API_URL` to `https://voxflow-jeevesh.duckdns.org` (Oracle Cloud VM with automated Caddy TLS), avoiding serverless cold-start timeouts.
  2. **Complete Dashboard Sidebar Nav (`apps/web/src/components/Sidebar.tsx`):**
     - Linked orphaned real pages: **Analytics** (`/dashboard/analytics`) under Main, and **Settings** (`/dashboard/settings`) under Account group.
  3. **Streamlined Telephony Engine:**
     - Standardized core telephony on Amazon Connect AWS Contact Center + In-Browser WebAudio Simulator.
     - Extracted audio codecs to `voxflow_api/voice/codecs.py` and eliminated ~3,000 lines of dead legacy telephony code.
  4. **Next.js 16 Route-Gate Protection (`apps/web/src/proxy.ts`):**
     - Verified active live route-gate proxy on Next.js 16 with Supabase auth guard.
- **Verification Evidence:**
  - ✅ **251/251 Passing Backend Tests** (`pytest tests/ -q` in 89.4s).
  - ✅ **23/23 Static Compiled Next.js Routes** (`npm run build` in 1416ms).
  - ✅ **Zero Lint / Type Errors** (`ruff check .` clean, ESLint clean, `tsc --noEmit` clean).
  - ✅ **Live Database Verified** (Supabase Postgres connection active, 5 tenant partitions verified).
- **Artifacts:** `deploy/aws/lambda_handler.py`, `apps/web/src/components/Sidebar.tsx`, `apps/api/voxflow_api/voice/codecs.py`, `.learning/day-39-ship-blockers-and-always-on-baseline.md`.

#### 🗓️ Day 40: Amazon Lex en-GB Speech Recognition & UK-English Defaults
- **Objective:** Fix spoken-voice speech recognition in Amazon Connect telephony by wiring an Amazon Lex V2 bot (`en-GB`) as the speech-to-text front door and aligning all system defaults to the UK-English enterprise market.
- **Implementation:**
  1. **Amazon Lex V2 Front Door & Contact Flow (`deploy/aws/connect-contact-flow.json`):**
     - Updated contact flow to use Amazon Polly `Amy` (`en-GB`) voice.
     - Added `GetCustomerSpeech` backed by Amazon Lex V2 (`AliasArn`) to capture caller spoken utterances into `$.Lex.InputTranscript` rather than DTMF keypad digits.
     - Routed blank/unmatched speech to Lambda for contextual English re-prompts.
  2. **AWS Lambda Bridge Hardening (`deploy/aws/lambda_handler.py`, `deploy/aws/deploy-lambda.sh`):**
     - Implemented English fallbacks, env-overridable language, and blank transcript re-prompting.
     - Upgraded `deploy-lambda.sh` to package JSON environment configurations, validate HMAC secret, and execute automated post-deploy smoke tests against the API.
     - Authored complete console runbook and rollback plan in `deploy/aws/LEX_SETUP.md`.
  3. **UK-English Platform Defaults:**
     - Configured default TTS voice to `en-GB-SoniaNeural` (`en`).
     - Aligned default language across `Tenant.default_language`, `Call.language`, prompts, schemas, and tenant provisioning to `en`.
  4. **Order-Independent Test Harness (`tests/test_connect_lambda_bridge.py`, `tests/conftest.py`):**
     - Created 14 unit and integration tests covering the Lambda bridge (transcript forwarding, blank re-prompting, HMAC header validation, timeout envelopes).
     - Added autouse session snapshot cleanup fixture in `conftest.py` ensuring complete test order independence.
- **Verification Evidence:**
  - ✅ **265/265 Passing Backend Tests** (`pytest tests/ -q`).
  - ✅ **23/23 Static Compiled Next.js Routes** (`npm run build`).
  - ✅ **Zero Lint / Static Analysis Errors** (`ruff check .` clean, ESLint clean).
- **Artifacts:** `deploy/aws/connect-contact-flow.json`, `deploy/aws/lambda_handler.py`, `deploy/aws/deploy-lambda.sh`, `deploy/aws/LEX_SETUP.md`, `apps/api/tests/test_connect_lambda_bridge.py`, `.learning/day-40-amazon-lex-en-gb-speech-capture.md`.

#### 🗓️ Day 41: Live Turn Latency & TTFT Benchmarking Harness
- **Objective:** Design, implement, and verify a modular, reproducible latency & TTFT benchmarking harness measuring mathematical percentile distributions (P50, P90, P95, P99) across every pipeline stage (STT, LLM reasoning/TTFT, TTS synthesis, and glass-to-glass conversational turns).
- **Implementation:**
  1. **Core Statistical Engine (`apps/api/voxflow_api/benchmarks/engine.py`):**
     - Computes exact distributions: Min, Mean, Max, StdDev, P50 (Median), P90, P95, P99.
     - Generates publication-ready ASCII distribution tables, ANSI horizontal bar charts, and structured Markdown/JSON reports.
  2. **Stage Timing Modules (`voxflow_api/benchmarks/`):**
     - `stt_bench.py`: Measures speech transcription turnaround and Real-Time Factor (RTF) across audio buffers.
     - `llm_bench.py`: Directly hooks into SSE chunk streams to capture Time to First Token (TTFT), Inter-Token Latency (ITL), and generation throughput (Tokens/sec).
     - `tts_bench.py`: Measures Time to First Byte (TTFB) and total audio synthesis turnaround.
     - `e2e_bench.py`: Measures cumulative glass-to-glass turn execution with live tool execution.
  3. **CLI Benchmark Runner (`scripts/benchmark_latency.py`):**
     - Single unified CLI executable supporting `--iterations`, `--stages`, `--mode <auto|live|mock>`, `--export-markdown`, and `--export-json`.
  4. **Dedicated Test Suite (`apps/api/tests/test_latency_benchmark.py`):**
     - Added 8 unit tests covering mathematical percentiles, formatters, and stage runners.
- **Verification Evidence:**
  - ✅ **273/273 Passing Backend Tests** (`pytest tests/ -q` in 93.1s).
  - ✅ **23/23 Static Compiled Next.js Routes** (`npm run build`).
  - ✅ **Zero Lint / Static Analysis Errors** (`ruff check .` clean, ESLint clean).
  - ✅ **Verified Baseline Telemetry Artifacts:** `BENCHMARK_REPORT.md` and `data/latency_benchmark.json`.
- **Artifacts:** `apps/api/voxflow_api/benchmarks/`, `scripts/benchmark_latency.py`, `apps/api/tests/test_latency_benchmark.py`, `BENCHMARK_REPORT.md`.

#### 🗓️ Day 42: Durable Call Logging (Postgres + Google Sheets Mirroring)
- **Objective:** Durably record every completed inbound voice call in the Postgres `calls` table (source of truth) and mirror it to a per-tenant Google Sheet off the request path with zero caller delay and idempotent retries.
- **Implementation:**
  1. **Postgres Schema & Latency Tracking (`db.py`, `migrations/015_call_latency.sql`):**
     - Added `avg_turn_latency_ms` column to `calls` table and created migration `015_call_latency.sql`.
     - Updated `migrations/000_base_schema.sql` base snapshot.
     - Calculated mean per-turn processing latency across recorded `turn_latencies` upon call persistence.
  2. **Google Sheets Call Log Mirroring (`integrations/gsheets.py`, `voice/pipeline.py`):**
     - Appended Day 42 headers `Tenant`, `Question`, `Answer`, and `Turn Latency (ms)` to `CALL_LOG_HEADERS` without reordering existing columns.
     - Built canonical mirror row payload mapping with fallback to first caller turn / last agent turn if outcome tool was skipped.
     - Implemented `sheet_mirror_enabled(tenant_id)` gate requiring explicit tenant admission in `SHEETS_CALL_LOG_TENANTS`.
     - Implemented detached, non-blocking mirror scheduling (`_schedule_sheet_mirror`, `_mirror_sheet`, `drain_background_tasks`).
     - Added dual-layer idempotency (in-process `_sheet_inflight` set + DB `sheet_synced` check) preventing duplicate writes on Lambda retries.
     - Ensured fail-soft behavior: Sheets API exceptions log war  4. **Comprehensive Test Suite (`tests/test_day42_sheet_logging.py`):**
      - Authored 7 tests covering column mapping, row builder, tenant allow-list gating, non-blocking end_session, idempotency, failure resilience, and crash-restart safety.
- **Verification Evidence:**
  - ✅ **282/282 Passing Backend Tests** (`pytest tests/ -q`).
  - ✅ **23/23 Static Compiled Next.js Routes** (`npm run build`).
  - ✅ **Zero Lint / Static Analysis Errors** (`ruff check .` clean, ESLint clean).
- **Artifacts:** `apps/api/voxflow_api/voice/pipeline.py`, `apps/api/voxflow_api/integrations/gsheets.py`, `apps/api/voxflow_api/db.py`, `apps/api/voxflow_api/config.py`, `migrations/015_call_latency.sql`, `apps/api/tests/test_day42_sheet_logging.py`, `.learning/day-42-real-call-logging-postgres-and-sheets.md`.

#### 🗓️ Day 43: Latency Tuning, Groq 429 Resilience, VAD Silence Re-Prompts & Backups
- **Objective:** Optimize per-turn speech latency (<2s glass-to-glass), harden Groq provider against rate limits with connection pooling and model fallbacks, implement progressive VAD silence re-prompting, and ensure data durability via Supabase keepalive and encrypted backups.
- **Implementation:**
  1. **Groq HTTP Client Connection Pooling & Jittered 429 Resilience (`llm/groq.py`, `config.py`):**
     - Upgraded `GroqProvider` to reuse a persistent `httpx.AsyncClient` with connection pooling (`Limits(max_keepalive_connections=10, max_connections=20)`), saving ~80–150ms per turn.
     - Implemented full-jitter exponential backoff on HTTP 429/503 responses (`min(base_wait * jitter, max_retry_after)`).
     - Added secondary fallback model (`llama-3.1-8b-instant`) when primary model experiences rate limit exhaustion.
  2. **Progressive VAD Silence & Timeout Handling (`voice/pipeline.py`, `routes/connect.py`, `deploy/aws/lambda_handler.py`):**
     - Added `silence_count: int = 0` to `CallSession`.
     - In `routes/connect.py`, handled empty input turns with progressive responses:
       - Silence turn 1: Contextual prompt ("Are you still there? What would you like to know?").
       - Silence turn 2: Re-assurance ("I'm still here. How can I help with your stock or order inquiry...?").
       - Silence turn 3: Polite call termination (`end_call=True`, `resolution_status="abandoned"`).
     - Reset `silence_count = 0` whenever caller speaks.
  3. **Data Durability & Automated Encrypted Backups (`scripts/`):**
     - Created `scripts/supabase_keepalive.py` with standalone `--once` and `--interval-hours 6` daemon modes to prevent Supabase Free Tier project pausing.
     - Upgraded `scripts/db_backup.sh` with AES-256 symmetric encryption (via `gpg` or `openssl`), multi-dialect support (Postgres `pg_dump` and SQLite), and automated 7-day retention rotation.
     - Created `scripts/db_restore_test.sh` for non-destructive automated decryption, decompression, and SQLite/Postgres schema integrity verification drills.
  4. **Dedicated Resilience Test Suite (`tests/test_day43_resilience.py`):**
     - Authored 7 comprehensive tests covering connection pooling, 429 jitter backoff, model fallback, progressive silence turns, silence resets, Supabase keep-alive, and encrypted backup/restore cycles.
- **Verification Evidence:**
  - ✅ **289/289 Passing Backend Tests** (`pytest tests/ -q` in 60.3s).
  - ✅ **23/23 Static Compiled Next.js Routes** (`npm run build`).
  - ✅ **Zero Lint / Static Analysis Errors** (`ruff check .` clean, ESLint clean).
  - ✅ **Verified Backup & Restore Drill:** Passed PRAGMA integrity check and 36 table validation.
  - ✅ **Verified Supabase Keepalive:** Successfully pinged live Supabase Postgres database.
- **Artifacts:** `apps/api/voxflow_api/llm/groq.py`, `apps/api/voxflow_api/voice/pipeline.py`, `apps/api/voxflow_api/routes/connect.py`, `deploy/aws/lambda_handler.py`, `scripts/supabase_keepalive.py`, `scripts/db_backup.sh`, `scripts/db_restore_test.sh`, `apps/api/tests/test_day43_resilience.py`, `.learning/day-43-latency-groq429-and-backups.md`.

#### 🗓️ Day 44: Self-Serve SaaS Signup & Centralized Tenant Provisioning
- **Objective:** Transform VoxFlow into an automated self-serve B2B SaaS platform where any business can register, instantly provision an isolated multi-tenant workspace with owner permissions and starter supply-chain data, and complete a 4-step interactive onboarding wizard without manual intervention.
- **Implementation:**
  1. **Centralized Provisioning Engine (`voxflow_api/services/provisioning.py`):**
     - Built `provision_tenant()` to handle transactional creation of `Tenant`, `TenantMember` (`role="owner"`, `status="active"`), optional phone mapping (`TenantPhoneNumber`), and pre-seeded starter catalog (`Product`, `Stock`, `Supplier`, `Order`, `Shipment`).
     - Implemented `generate_unique_tenant_slug()` for automatic URL-safe slug collision resolution (`acme-logistics`, `acme-logistics-2`, etc.).
     - Refactored CLI tool (`scripts/onboard_tenant.py`) to share this single source of truth.
  2. **Public Self-Serve Signup Endpoint (`routes/public_auth.py`):**
     - Created `POST /api/auth/signup` accepting company name, admin email, owner full name, language selection (`en` / `hi`), and optional Turnstile challenge verification.
  3. **Frontend Self-Serve Signup & 4-Step Onboarding Wizard (`apps/web`):**
     - Upgraded `/sign-up` with language selection (`en`/`hi`), Turnstile bot validation, active workspace caching, and automatic transition to onboarding.
     - Built `/onboarding` 4-step wizard:
       - **Step 1: Voice Persona & Language**: Agent name ("Vaani"), language preference, opening greeting.
       - **Step 2: Starter Catalog**: Overview of 3 pre-seeded SKUs, stock levels, supplier depot, and PO-1001.
       - **Step 3: Live Simulator Test**: Guided test prompts and 1-click test button.
       - **Step 4: Launch**: Direct transition into `/dashboard`.
  4. **Automated Test Suite & Browser Verification (`tests/test_day44_self_serve_provisioning.py`, `scratch/verify_day44.py`):**
     - Authored 6 tests covering provisioning, slug collision auto-disambiguation, Turnstile validation, multi-tenant isolation, and CLI script compatibility.
     - Verified end-to-end flow with Playwright capturing screenshots of all 4 onboarding steps.
- **Verification Evidence:**
  - ✅ **295/295 Passing Backend Tests** (`pytest tests/ -q` in 113.4s).
  - ✅ **24/24 Static Compiled Next.js Routes** (`npm run build` including `/onboarding`).
  - ✅ **Zero Lint / Static Analysis Errors** (`ruff check .` clean, ESLint clean).
  - ✅ **Browser Screenshots Captured:** `day44_shot_signup.png`, `day44_shot_onboarding_step1.png`, `day44_shot_onboarding_step2.png`, `day44_shot_onboarding_step3.png`, `day44_shot_onboarding_step4.png`, `day44_shot_dashboard_provisioned.png`.
- **Artifacts:** `apps/api/voxflow_api/services/provisioning.py`, `apps/api/voxflow_api/routes/public_auth.py`, `apps/web/src/app/onboarding/page.tsx`, `apps/web/src/app/sign-up/page.tsx`, `scripts/onboard_tenant.py`, `apps/api/tests/test_day44_self_serve_provisioning.py`, `.learning/day-44-self-serve-signup-and-tenant-provisioning.md`.

#### 🗓️ Day 45: Company Data Ingestion (Streaming CSV Validation & Multi-Tenant Upsert Engine)
- **Objective:** Enable multi-tenant SaaS clients to bulk-ingest their own operational supply chain data (Products, Stock, Suppliers, Purchase Orders, and Shipments) via streaming RFC-4180 CSV uploads with pre-flight dry-run schema validation, transactional upsert guarantees, and instant real-time accessibility to the AI voice agent.
- **Implementation:**
  1. **Data Ingestion Engine (`voxflow_api/services/data_ingestion.py`):**
     - Built streaming `csv.DictReader` parser supporting memory-efficient byte and text processing.
     - Defined comprehensive entity schemas, required headers, and type coercion validators for 5 models (`products`, `stock`, `suppliers`, `orders`, `shipments`).
     - Added downloadable RFC-4180 CSV template generator with production-grade sample data (`get_csv_template`).
     - Engineered transactional `ingest_csv_data` with all-or-nothing rollback semantics, multi-tenant isolation, and conflict resolution modes (`upsert` vs `strict`).
  2. **Database Multi-Tenant Composite Key (`voxflow_api/db.py` & `routes/data.py`):**
     - Updated `Product` model to use composite primary key `(sku, tenant_id)` to eliminate cross-tenant SKU collisions.
     - Updated `list_stock` SQL joins to bind on both `sku` and `tenant_id`.
  3. **REST Ingestion Endpoints (`routes/data.py` & `schemas.py`):**
     - `GET /api/data/entities`: Catalogs all 5 supported entities, required/optional fields, and descriptions.
     - `GET /api/data/templates/{entity}`: Streams downloadable CSV template with attachment headers.
     - `POST /api/data/{entity}/validate`: Pre-flight dry-run CSV validation returning row-level error reports, total/valid row counts, and live previews.
     - `POST /api/data/{entity}/import`: Authenticated bulk import endpoint with tenant isolation and read-only demo guardrails (`HTTP 403 demo_access_read_only`).
  4. **Interactive Dashboard UI (`apps/web`):**
     - Built `CsvImportModal.tsx`: Entity tab switching, downloadable template buttons, drag-and-drop file upload zone, raw CSV text editor, live validation preview table with error badges, and conflict resolution toggle.
     - Built `Company Data Hub` (`/dashboard/data`): Dedicated management center with live tenant metrics, entity schema requirements, direct template downloads, and enterprise data safeguards.
     - Added "Import CSV" triggers across `/dashboard/stock`, `/dashboard/orders`, `/dashboard/suppliers`, and `/dashboard/shipments`.
     - Integrated custom CSV data upload trigger in Step 2 of `/onboarding`.
  5. **Automated Test Suite & Browser Verification (`tests/test_day45_data_ingestion.py`, `scratch/verify_day45_browser.py`):**
     - Authored 10 tests verifying entity schemas, template generation, pre-flight error reporting, all-or-nothing rollback, idempotent upserting, tenant isolation, and real-time queryability by voice agent tools (`test_agent_queries_imported_csv_data`).
     - Verified end-to-end browser experience with Playwright capturing full modal import workflows and updated inventory tables.
- **Verification Evidence:**
  - ✅ **305/305 Passing Backend Tests** (`pytest apps/api/tests/ -q` in 106.29s).
  - ✅ **25/25 Static Compiled Next.js Routes** (`npm --prefix apps/web run build` including `/dashboard/data`).
  - ✅ **Zero Lint / Static Analysis Errors** (`ruff check apps/api` clean, ESLint clean).
  - ✅ **Browser Screenshots Captured:** `day45_data_hub.png`, `day45_modal_open.png`, `day45_modal_validated.png`, `day45_modal_success.png`, `day45_stock_page.png`, `day45_orders_page.png`, `day45_suppliers_page.png`, `day45_shipments_page.png`.
- **Artifacts:** `apps/api/voxflow_api/services/data_ingestion.py`, `apps/api/voxflow_api/routes/data.py`, `apps/api/voxflow_api/schemas.py`, `apps/api/voxflow_api/db.py`, `apps/web/src/components/dashboard/CsvImportModal.tsx`, `apps/web/src/app/dashboard/data/page.tsx`, `apps/api/tests/test_day45_data_ingestion.py`, `.learning/day-45-company-data-ingestion-csv.md`.

#### 🗓️ Day 46: Exact DID Routing & Secure Caller Verification
- **Objective:** Give each tenant explicit inbound-number ownership, automated route policy, and configurable caller PIN controls without exposing credentials or permitting fallback across tenants.
- **Implementation:**
  1. Added exact E.164 DID routing for Amazon Connect — the only provider with a live inbound resolution route — with provider matching, active-state enforcement, language policy, and fail-closed handling for unknown or inactive numbers. The schema stores `twilio`/`telnyx` as forward-compatible provider values, but the owner-facing API only accepts `connect` today so a tenant cannot create a mapping that will never receive a call.
  2. Added owner-only canonical tenant APIs for telephony posture, line creation/update/deactivation, and caller PIN set/reset; operators, viewers, demo users, and cross-tenant identities remain read-only or denied.
  3. Replaced new plaintext PIN storage with uniquely salted PBKDF2-HMAC-SHA256 hashes, constant-time verification, migration-on-success for legacy rows, 4–8 digit validation, confirmation checks, timestamps, and PIN redaction in CSV previews, tool traces, actions, logs, and transcripts.
  4. Added the `/dashboard/settings` telephony control plane with exact-DID posture, route/provider/language controls, immutable DID identity on edit, masked verification contacts, rotation warnings, and secret-free PIN reset UX.
  5. Added migrations `016_telephony_routing_and_caller_pins.sql` and `017_product_tenant_composite_key.sql`, current base-schema coverage, ephemeral deterministic test databases, and end-to-end routing/security regressions.
  6. **Independent security re-review hardening** (post-implementation): closed anonymous tenant-takeover in self-serve signup, removed the spoofable `X-VoxFlow-User-Id`/`usr-*` bearer identity bypass in production, bound the Amazon Connect Lambda HMAC to the exact raw request body, removed default-tenant fallback for a missing/unknown Connect DID, bound caller authorization (`verify_caller`/`verify_pin`) to the exact identified contact so verifying contact A can never authorize access to contact B, made PIN redaction proactive across replies/traces/transcripts/logs regardless of tool-call order, removed predictable seeded PINs, added a persistent cross-session caller-PIN lockout (`Supplier.pin_failed_attempts`/`pin_locked_until`, 10 failures → 15-minute lock, cleared on success or owner reset) with row-level locking on Postgres, restricted the owner-facing phone-number API to the one provider with a live inbound route, fixed a legacy SQLite `auth_pin NOT NULL` upgrade path (including its dropped foreign key), excluded structured `caller_phone` data from free-text PIN redaction, protected LLM tool-call identifiers from redaction so the tool-calling protocol never breaks, gated self-serve signup on a confirmed authenticated session so a caller can never be silently left owning an unclaimable placeholder-owned tenant, and added `017_product_tenant_composite_key.sql` + `_ensure_product_composite_key_sqlite` to reconcile multi-tenant product composite keys across existing deployed databases.
- **Verification Evidence:**
  - ✅ **351/351 Passing Backend Tests** (`.venv/bin/python -m pytest -q`).
  - ✅ **79/79 Adjacent Telephony/Auth/Tenancy/Ingestion/Schema Tests**, **6/6 focused routing tests**, and **6 new focused test files** covering persistent PIN lockout, PIN redaction, verification-authorization binding, the SQLite legacy auth_pin upgrade path, and SQLite legacy product composite-key upgrade path.
  - ✅ **Zero Ruff or ESLint Errors**; TypeScript `tsc --noEmit` passed.
  - ✅ **25/25 Compiled Next.js Routes** (`next build`).
  - ✅ Two independent full-diff security reviews found no remaining Critical/High findings before push.
- **Artifacts:** `migrations/016_telephony_routing_and_caller_pins.sql`, `migrations/017_product_tenant_composite_key.sql`, `voxflow_api/services/pin_security.py`, `voxflow_api/services/telephony_routing.py`, `voxflow_api/routes/admin.py`, `voxflow_api/routes/connect.py`, `voxflow_api/telephony/connect_provider.py`, `deploy/aws/lambda_handler.py`, `voxflow_api/auth.py`, `voxflow_api/routes/public_auth.py`, `voxflow_api/services/provisioning.py`, `apps/web/src/lib/auth-context.tsx`, `apps/web/src/app/sign-up/page.tsx`, `apps/web/src/components/settings/TelephonySettings.tsx`, `apps/api/tests/test_day46_telephony_routing.py`, `apps/api/tests/test_pin_persistent_lockout.py`, `apps/api/tests/test_pin_redaction.py`, `apps/api/tests/test_verification_authorization_binding.py`, `apps/api/tests/test_sqlite_legacy_auth_pin_upgrade.py`, `apps/api/tests/test_sqlite_legacy_product_upgrade.py`.

#### 🗓️ Day 47: Per-Tenant Agent Settings & Voice Persona Configuration
- **Objective:** Allow workspace owners to configure custom voice personas, prompt guidelines, business operating hours with timezone awareness, and fallback escalation rules per tenant without weakening exact-DID routing or caller-verification gates.
- **Implementation:**
  1. **Data Model & Schema Extensions (`Tenant`):** Extended `tenants` table with `voice_persona` (professional | friendly | concise | assertive), `business_hours_enabled`, `business_hours_start`, `business_hours_end`, `business_hours_timezone`, `business_days`, `out_of_hours_message`, `fallback_escalation_mode` (human_callback | transfer | voicemail), `fallback_phone`, `fallback_email`, and `max_verification_failures`.
  2. **Database Migrations:** Authored migration `018_tenant_agent_settings.sql`, updated `000_base_schema.sql`, and added automatic SQLite upgrade shims in `db.py` for local and staging environments.
  3. **Dynamic Prompt & Persona Engine (`prompts.py`, `runner.py`):** Added persona demeanor guidelines (Professional, Friendly, Concise, Assertive), operating hours schedule injection, out-of-hours response handling, fallback escalation routing rules, and instant in-memory prompt cache invalidation (`clear_tenant_prompt_cache`) upon configuration updates.
  4. **Server-Authoritative REST Endpoints (`admin.py`):** Added `GET /api/tenants/{tenant_id}/agent-settings` (accessible by all authorized workspace members) and `PATCH /api/tenants/{tenant_id}/agent-settings` (strictly restricted to `ROLE_OWNER` with E.164, time format, persona, and email validation).
  5. **Interactive Dashboard UI (`apps/web`):** Built `AgentSettings.tsx` and integrated it into `/dashboard/settings` with live persona cards, language selection, guidelines editor, weekday schedule chips, timezone dropdown, escalation mode picker, and real-time persona preview.
- **Verification Evidence:**
  - ✅ **370/370 Passing Backend Tests** (`python3 -m pytest tests/ -q` with 19 new focused Day 47 tests).
  - ✅ **25/25 Compiled Next.js Production Routes** (`next build`).
  - ✅ **Zero Lint / Static Analysis Errors** (`ruff check .` clean, ESLint clean, `tsc --noEmit` clean).
- **Artifacts:** `migrations/018_tenant_agent_settings.sql`, `migrations/000_base_schema.sql`, `apps/api/voxflow_api/db.py`, `apps/api/voxflow_api/agent/prompts.py`, `apps/api/voxflow_api/agent/runner.py`, `apps/api/voxflow_api/routes/admin.py`, `apps/web/src/lib/types.ts`, `apps/web/src/lib/api.ts`, `apps/web/src/components/settings/AgentSettings.tsx`, `apps/web/src/app/dashboard/settings/page.tsx`, `apps/api/tests/test_agent_settings.py`.

#### 🗓️ Day 48: Closed-Loop Escalation Ownership, SLAs & Operator Resolution
- **Objective:** Establish a closed-loop human escalation management system with priority calculations, configurable SLA breach deadlines, ticket assignment, and operator resolution actions.
- **Implementation:**
  1. **Data Model & Schema Extensions (`Call` & `Tenant`):** Extended `calls` with `escalation_priority` (critical | high | medium | low), `escalation_status` (none | pending | in_progress | resolved | dismissed), `assigned_to_user_id`, `assigned_at`, `sla_due_at`, `resolved_by_user_id`, and `resolution_category`. Extended `tenants` with `escalation_sla_minutes` (default 60).
  2. **Database Migrations:** Authored migration `019_escalation_lifecycle_and_sla.sql` with composite indexes (`idx_calls_tenant_escalation_sla`, `idx_calls_tenant_escalation_assigned`) and updated `000_base_schema.sql`.
  3. **Escalation Domain Service (`escalation_service.py`):** Added priority matrix (`derive_escalation_priority`), priority-weighted dynamic SLA due date calculator (`compute_sla_due_at`), SLA compliance metrics and queue aggregations (`get_escalation_kpis`), and atomic ticket claiming/resolution with audit tracking (`assign_escalation`, `resolve_escalation`).
  4. **Server-Authoritative REST Router (`routes/escalations.py`):** Mounted `/api/tenants/{tenant_id}/escalations` providing queue filtering (`status`, `priority`, `breached_only`), real-time KPI metrics (`/metrics`), single ticket detail (`/{call_id}`), claim/assign (`/{call_id}/assign`), and resolve/dismiss (`/{call_id}/resolve`), all protected by strict tenant RBAC (`ROLE_OWNER` & `ROLE_OPERATOR` write, `ROLE_VIEWER` read-only).
  5. **Interactive Dashboard UI (`apps/web`):** Built `ResolutionDrawer.tsx` slide-over modal for staff resolution notes, category tagging, and status transitions. Redesigned `/dashboard/escalations` with 5 KPI scorecards (Total, Open, SLA Breaches with pulse badge, Compliance %, Avg Resolution Time), status tabs, priority filters, search, quick claim actions, and ticket assignment.
  6. **Voice Pipeline Automatic SLA Initialization (`pipeline.py`):** Automatically initializes escalation state, priority, and target SLA timestamp during live call persistence whenever an escalation occurs.
- **Verification Evidence:**
  - ✅ **383/383 Passing Backend Tests** (`python3 -m pytest tests/ -q` with 13 new focused Day 48 tests).
  - ✅ **25/25 Compiled Next.js Production Routes** (`next build` including redesigned `/dashboard/escalations`).
  - ✅ **Zero Lint / Static Analysis Errors** (`ruff check .` clean, ESLint clean, `tsc --noEmit` clean).
- **Artifacts:** `migrations/019_escalation_lifecycle_and_sla.sql`, `migrations/000_base_schema.sql`, `apps/api/voxflow_api/services/escalation_service.py`, `apps/api/voxflow_api/routes/escalations.py`, `apps/api/voxflow_api/voice/pipeline.py`, `apps/web/src/components/dashboard/ResolutionDrawer.tsx`, `apps/web/src/app/dashboard/escalations/page.tsx`, `apps/web/src/lib/types.ts`, `apps/web/src/lib/api.ts`, `apps/api/tests/test_escalation_workflow.py`.

#### 🗓️ Day 49: Voice Eval Harness & Release Thresholds
- **Objective:** Build a repeatable, CI-integrated automated evaluation harness that scores the VoxFlow voice agent against 30 structured scenarios and enforces Release Gate #5 — "Never leak data before caller verification" — as a non-negotiable hard gate blocking any deployment.
- **Implementation:**
  1. **Scenario Dataset (`evals/scenarios.json`):** Authored 30 versioned, PII-free structured test cases across 7 categories: `security_adversarial` (7 hard-gate scenarios), `verification` (5), `order_inquiry` (5), `stock_inquiry` (4), `shipment_tracking` (3), `escalation_disputes` (4), and `out_of_scope` (2). Each scenario defines multi-turn dialogue, per-turn forbidden phrases, forbidden tool calls, must-call tools, and expected phrase assertions.
  2. **Eval Domain Engine (`services/eval_service.py`):** Implemented dataclasses `TurnResult`, `ScenarioResult`, `CategoryScore`, `ThresholdEval`, and `EvalReport` plus the full `run_voice_eval()` async orchestrator. Hard Gate assertions: `no_unverified_data_leak` (regex + phrase scanner), `no_cross_tenant_leak`, `no_system_prompt_leak`, `forbidden_tools_not_called`. Soft metrics: tool selection accuracy, expected phrase containment, spoken brevity (≤35 words/turn), P95 latency (≤3,500ms). Configurable `ReleaseThresholds` dataclass with 6 tunable thresholds. `release_ready = hard_gate_passed AND all_soft_thresholds_pass`.
  3. **REST API (`routes/evals.py`):** `GET /api/evals/scenarios` (metadata listing), `GET /api/evals/scorecard` (latest run, in-memory cache), `POST /api/evals/run` (on-demand harness execution with category/tenant/scenario-ID filters and custom threshold overrides), `GET /api/tenants/{tenant_id}/evals/scorecard` (tenant-scoped scorecard with RBAC).
  4. **CLI Tooling (`scripts/run_evals.py`):** Full-featured CLI with `--category`, `--strict` (exit code 1 on any threshold breach for CI/CD gating), `--output-json`, `--mock`, and colorized tabular scorecard output.
  5. **Frontend Dashboard (`VoiceEvalScorecard.tsx`, `readiness/page.tsx`):** 562-line premium dashboard component featuring a Release Gate #5 status banner (green/red), 5-metric scorecards (Hard Gates, Correctness, Security Compliance, Escalation, Avg Words/Turn), category performance table, and expandable scenario inspector with input text, expected vs actual tools, spoken replies, and assertion violations. Embedded into the `/dashboard/readiness` Pilot Gates view.
  6. **TypeScript Types & API Client (`types.ts`, `api.ts`):** Added `VoiceEvalScorecard`, `ScenarioResultOut`, `CategoryScoreOut`, `ReleaseGateStatus` interfaces; `getVoiceEvals()` and `runVoiceEvals()` API client methods.
  7. **Automated Test Suite (`tests/test_eval_harness.py`):** 8 pytest cases: scenario dataset schema integrity, hard gate trip on deliberate leak injection, hard gate hold when guardrails hold, tool selection and phrase assertions, category score aggregation, API scenario listing, API scorecard and run endpoint, and tenant-scoped scorecard endpoint.
- **Verification Evidence:**
  - ✅ **391/391 Passing Backend Tests** (`python3 -m pytest tests/ -q` in 148.7s with 8 new Day 49 eval harness tests).
  - ✅ **TypeScript Clean** (`npx tsc --noEmit` — 0 errors).
  - ✅ **Zero Lint / Static Analysis Errors** (`ruff check .` clean, ESLint clean).
  - ✅ **Hard Gate Trip Proven** — `test_hard_gate_blocks_release_on_data_leak` injects a pre-verification data leak and confirms gate trips with `release_ready=False` and non-zero CLI exit.
  - ✅ **Committed & Pushed** — `206589f feat(evals): Day 49 voice eval harness, release thresholds & scorecard dashboard`.
#### 🗓️ Day 50: RBAC Enforcement, Cross-Tenant Zero-Leak Isolation & Team Management
- **Objective:** Finalize enterprise-grade tenant isolation with 0-leak release gating (Release Gate #3) and enforce a strict 3-tier Role-Based Access Control matrix (`owner`, `operator`, `viewer`) with interactive team settings, role modification endpoints, and last-owner protection.
- **Implementation:**
  1. **Route-Level Scope & RBAC Hardening (`routes/data.py`, `routes/evals.py`):** Added explicit `tenant_id` query parameters and resolved tenant enforcement across single-resource lookups (`get_supplier`, `get_order`, `get_call`, `get_call_recording_link`, `download_call_recording`, and `validate_csv`). Scoped voice eval triggering to `{ROLE_OWNER, ROLE_OPERATOR}`.
  2. **Member Role Modification Endpoint (`routes/memberships.py`):** Implemented `PATCH /api/tenants/{tenant_id}/members/{user_id}/role` with `MemberRoleUpdateIn` schema. Restricted to `ROLE_OWNER` only. Enforced last-active-owner invariant returning `HTTP 409 Conflict` on attempted demotion or self-revocation when only one active owner remains.
  3. **Frontend Team Management UI (`TeamMembersSettings.tsx`):** Created 400+ line settings card in `/dashboard/settings` with active team roster table, role badges, joined timestamps, invitation modal with email/role selectors, live role change dropdowns for Owners, read-only badges for Operators/Viewers, and an interactive Role Permissions Matrix accordion.
  4. **Release Gate #3 Zero-Leak Test Suite (`tests/test_tenant_isolation_zero_leak.py`):** 5 exhaustive security test cases asserting that cross-tenant list queries return 403, ID enumeration across tenants returns 404 Not Found (zero information leakage), cross-tenant mutations return 403, intra-tenant queries return 0% foreign data rows, and composite SQL keys isolate rows at the database layer.
  5. **Comprehensive RBAC Matrix Test Suite (`tests/test_rbac_matrix.py`):** 6 exhaustive test cases validating full matrix permissions: `ROLE_VIEWER` can read all domain resources but is 403-blocked on all mutations; `ROLE_OPERATOR` can perform operational data CRUD & escalation resolutions but is 403-blocked from settings, phone numbers, caller PINs, and team management; `ROLE_OWNER` has full administrative power; and sole active owners cannot be demoted or revoked.
- **Verification Evidence:**
  - ✅ **402/402 Passing Backend Tests** (`python3 -m pytest tests/ -q` in 122.2s with 11 new Day 50 isolation and RBAC tests).
  - ✅ **25/25 Compiled Next.js Production Routes** (`next build` with Turbopack, 0 TypeScript errors).
  - ✅ **Release Gate #3 Zero-Leak Verification Passed** — 100% data boundary isolation verified across 11 entity types.
  - ✅ **Zero Lint / Static Analysis Errors** (`ruff check .` clean, ESLint clean, `tsc --noEmit` clean).
- **Artifacts:** `apps/api/voxflow_api/routes/data.py`, `apps/api/voxflow_api/routes/memberships.py`, `apps/api/voxflow_api/routes/evals.py`, `apps/web/src/lib/api.ts`, `apps/web/src/components/settings/TeamMembersSettings.tsx`, `apps/web/src/app/dashboard/settings/page.tsx`, `apps/api/tests/test_tenant_isolation_zero_leak.py`, `apps/api/tests/test_rbac_matrix.py`, `.learning/day-50-rbac-and-tenant-isolation.md`.

---

## 🎯 Verification & Test Summary Matrix

| Metric | Target | Current Value | Status |
|---|---|---|---|
| **Backend Unit & Integration Tests** | $\ge 200$ | **402 Passed** | ✅ Green |
| **Frontend Static Routes** | $\ge 15$ | **25 Compiled Pages** | ✅ Green |
| **Lint & Static Analysis** | 0 warnings | `ruff check .` clean, ESLint clean, `tsc --noEmit` clean | ✅ Clean |
| **Latency & TTFT Benchmarks** | Sub-second P50 | **P50 ~566ms glass-to-glass** | ✅ Verified |
| **Database Migrations** | Staged & Verified | 20 Migrations (`000`–`019`) | ✅ Current |
| **Telephony Providers Supported** | Enterprise Voice | Amazon Connect (AWS) + Amazon Lex STT + WebAudio Simulator | ✅ Verified |
| **Call Persistence & Mirroring** | Durable Logging | Postgres `calls` + Gated Google Sheets Mirror | ✅ Verified |
| **Multi-Tenant Isolation (Gate #3)** | Zero Data Leaks | **0% Foreign Rows, 404 on Foreign IDs, 403 on Cross-Tenant** | ✅ Verified |
| **RBAC Enforcement (3 Tiers)** | Owner / Operator / Viewer | Strict server-authoritative role gating & last-owner protection | ✅ Verified |
| **Team Management Surface** | Member Settings UI | Interactive Member Roster + Invites + Role Selector + Matrix | ✅ Verified |
| **Self-Serve Onboarding** | Instant Provisioning | `/sign-up` $\rightarrow$ `/onboarding` $\rightarrow$ `/dashboard` | ✅ Verified |
| **Bulk Data Ingestion** | Streaming CSV Engine | Pre-flight validation + Upsert semantics | ✅ Verified |
| **Authentication & Auth Gate** | Unauth Redirects | HTTP 307 $\rightarrow$ `/sign-in` | ✅ Verified |
| **Public Simulator Execution** | Hindi/English turns | Text turn + read-only tool | ✅ Verified |
| **Per-Tenant Agent Persona** | Custom Settings | 4 Personas + Business Hours + Escalation Policy | ✅ Verified |
| **Closed-Loop Escalations** | SLA & Resolution | 5 KPI Metrics + Queue + Resolution Drawer | ✅ Verified |
| **Voice Eval Harness (Gate #5)** | Release Gate #5 | 30 Scenarios × 7 Categories, Hard Gate 100% enforced | ✅ Verified |
| **CI/CD Eval Gate** | Exit 1 on leak | `--strict` mode trips on any pre-verification data leak | ✅ Verified |

---

## 🧭 Next Recommended Actions (Day 51+)

1. **Observability, Alerting & SLO Burn Rate (Day 51):** Real-time error monitors, webhook alerting for SLA breaches, structured alert policies, and latency distribution tracking.
2. **Security & Data Lifecycle (Day 52):** GDPR data-subject export & deletion pipelines, encryption at rest, secret rotation automation, and penetration test remediation.
3. **Billing, Landing & Go-Live Dry Run (Day 53):** Stripe subscription billing, public landing page, and full production go-live simulation.





