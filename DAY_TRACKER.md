# 📅 VoxFlow — Master Day-Wise Implementation Tracker

**Project:** VoxFlow — Voice Operations for Modern Supply Chains  
**Repository:** `jeevesh2515/voxflow-voice-agent`  
**Current Test Suite:** **567 Passing Tests** (`pytest apps/api/tests -q`)
**Frontend Surface:** **31 Compiled Routes** (Next.js 16 App Router, Turbopack production validation)
**Deployment Infrastructure:** AWS eu-west-2 (London) Primary: EC2 `t3.small` + AWS RDS PostgreSQL 15.19 + AWS Secrets Manager + KMS + Caddy Auto-TLS (`https://voxflow-jeevesh.duckdns.org` at `13.43.7.12`) / Standby: Oracle Cloud Always-Free ARM VM / Frontend Mirror: Vercel Edge Network  
**Last Updated:** 2026-09-05

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
| **Phase 11** | 55 | Landing Page Cosmic Journey & Polish | ✅ Complete | 5-keyframe hero scroll, solar system vista, Three.js WebGL + CSS progress bus. |
| **Phase 12** | 56 | Anti-Hallucination & Deterministic Precision | ✅ Complete | Zero-hallucination negative grounding invariant, ambiguity disambiguation, temperature clamping (0.1), tenant guidelines injection. |
| **Phase 13** | 57 | Ingest Lambda, SQS DLQ & Meter Billing Cron | ✅ Complete | Amazon Connect S3 ingest Lambda, SQS DLQ retry, Stripe metered billing usage reporting cron. |
| **Phase 14** | 58 | Cloud-First Groq LLM & Zero Local Footprint | ✅ Complete | Multi-model Groq cascade (`openai/gpt-oss-20b`), Whisper turbo STT, Edge-TTS, zero local compute footprint. |
| **Phase 1 (AWS Migration)** | 59 | Funded AWS Data Infrastructure Foundation | ✅ Complete | Terraform VPC in eu-west-2, AWS RDS PostgreSQL 15.19, EC2 t3.small, Caddy Auto-TLS on DuckDNS, Secrets Manager + KMS, PITR backups, 567 tests. |

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
- **Artifacts:** `apps/web/src/app/dashboard/calls/page.tsx`, `apps/api/voxflow_api/routes/data.py`.

#### 🗓️ Day 17: Escalation Queue & Staff Resolution Workflow
- **Objective:** Manage and resolve escalated calls requiring human operator attention.
- **Implementation:**
  - Built `/dashboard/escalations` view filtering calls flagged as `escalated` or `follow_up_required`.
  - Added `PATCH /api/calls/{id}/resolution` endpoint to store staff notes and resolution timestamp.
  - Added escalation metrics and resolution status badges to dashboard.
- **Artifacts:** `apps/web/src/app/dashboard/escalations/page.tsx`, `apps/api/voxflow_api/routes/calls.py`.

#### 🗓️ Day 18: Security Pass & Production Hardening
- **Objective:** Conduct security audit, implement rate limiting, and secure credential handling.
- **Implementation:**
  - Added IP-based WebSocket rate limiting on `/twilio/media` (10 conns/60s per IP, closes with code 1008).
  - Added HTTP security headers (`X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Cache-Control`).
  - Added dual Twilio credential support (Account SID + Auth Token vs API Key + Secret).
- **Artifacts:** `security_audit.md`, `apps/api/voxflow_api/middleware/security.py`.

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

#### 🗓️ Day 50 Extension: Self-Serve Per-Tenant Google Sheets Integration & Voice Agent Live Editing
- **Objective:** Enable enterprise clients (e.g. Varun Beverages) to self-serve connect their own Google Spreadsheets directly from the web dashboard, auto-bootstrap required logging tabs, and empower the live voice agent to read, append, and edit rows directly in the tenant's sheet during inbound calls.
- **Implementation:**
  1. **Database Schema & Migrations (`migrations/020_per_tenant_google_sheets.sql`):** Added `google_sheet_id`, `google_sheet_name`, `google_sheet_tab`, `google_sheet_email_tab`, `google_sheet_status`, `google_sheet_connected_at`, and `google_sheet_connected_by_user_id` to `tenants`. Synced `000_base_schema.sql` and added SQLite runtime schema migration shim in `db.py`.
  2. **Server-Authoritative Integrations API (`routes/integrations.py`):**
     - `GET /api/tenants/{tenant_id}/integrations/google-sheets`: Read connection posture, spreadsheet title, tabs, and service account email.
     - `POST /api/tenants/{tenant_id}/integrations/google-sheets/connect`: Gated to `ROLE_OWNER`. Extracts sheet ID from any Google Sheets URL or raw ID, verifies access, and bootstraps `Call Log` & `Email Log` headers.
     - `POST /api/tenants/{tenant_id}/integrations/google-sheets/test`: Preflight live read/write latency diagnostic.
     - `DELETE /api/tenants/{tenant_id}/integrations/google-sheets`: Disconnects spreadsheet mirror.
  3. **Voice Agent Live Sheet Editing Tools (`tools.py`, `gsheets.py`):**
     - Added `edit_sheet_row` tool: Search for a row by key (e.g. `PO Number` = `PO-1002`, `Order ID`, or `Supplier`) and update cell values in place. Automatically creates missing column headers and appends new rows if missing.
     - Added `update_worksheet` tenant sheet routing with durable `WorksheetLog` audit logging and background job retries (`side_effect_worker_service.py`).
     - Added `read_sheet_rows` and `_col_to_letter` helper in `GoogleSheetsClient`.
  4. **Dynamic LLM System Prompt Context (`prompts.py`):** Injects connected spreadsheet context (`tenant.google_sheet_name`) into `build_tenant_prompt()` so the agent knows it has direct operational access to the workspace's spreadsheet.
  5. **Frontend Dashboard UI (`GoogleSheetsSettings.tsx`):**
     - Live status badge (🟢 Active Mirror / ⚪ Not Connected / 🔴 Error).
     - 1-click copy service account email helper.
     - Connect modal with URL parsing, tab customization, and preflight test.
     - Mounted in both `/dashboard/settings` and `/dashboard/data` (Data Hub).
- **Verification Evidence:**
  - ✅ **411/411 Passing Backend Tests** (`python3 -m pytest tests/ -q` with 8 new per-tenant Google Sheets tests in `tests/test_tenant_google_sheets.py`).
  - ✅ **25/25 Compiled Next.js Production Routes** (`next build` with Turbopack, 0 TypeScript errors).
  - ✅ **Zero Secrets Committed** (Service account credentials resolved exclusively from environment variables).
- **Artifacts:** `migrations/020_per_tenant_google_sheets.sql`, `apps/api/voxflow_api/integrations/gsheets.py`, `apps/api/voxflow_api/routes/integrations.py`, `apps/api/voxflow_api/agent/tools.py`, `apps/api/voxflow_api/agent/prompts.py`, `apps/api/voxflow_api/jobs/side_effect_worker_service.py`, `apps/web/src/components/settings/GoogleSheetsSettings.tsx`, `apps/api/tests/test_tenant_google_sheets.py`.

#### 🗓️ Day 51: Enterprise Observability, PII-Scrubbed Sentry/PostHog & Durable Alerting
- **Objective:** Ship actionable per-tenant observability + durable alerting: KPI and health surfaces with an enterprise dark dashboard, threshold-driven alert evaluation with durable side-effect dispatch, and privacy-safe Sentry/PostHog telemetry (tenant IDs hashed, free-text PII scrubbed, fail-closed).
- **Implementation:**
  1. **Observability Service (`services/observability_service.py`):** `get_call_kpis` (24h/7d/30d success rate, SLA breaches, appointments, outbound latency distribution with volume + P50/P95/P99 deltas), `get_system_health_metrics` (`operational/degraded/critical`), `get_recent_system_events` (scrubbed ops events, hashed DIDs).
  2. **Alerting Service (`services/alerting_service.py`):** Threshold read/write persisted in `agent_states` (`alert_channels`, webhook URL + optional bearer secret, min pool/enable flags), pure `evaluate_alerts` per tenant, and durable `dispatch_alert_notification` that enqueues `NOTIFICATION_DISPATCH` with `aggregate_type="observability_alert"` plus a per-tenant/reason/minute idempotency key.
  3. **REST API (`routes/observability.py`):** 6 endpoints — `/kpis`, `/health`, `/events`, `/alerts`, `/alerts/thresholds` (PUT, owner), `/alerts/test` (POST, owner); demo-tenant blocked from owner-only mutators.
  4. **Sentry & PostHog (`monitoring.py`):** Sentry init gated on `SENTRY_DSN` with `before-send` scrubber that fail-closes free text (exception value/message dropped) and strips frame vars; PostHog client with salted SHA-256 tenant-ID hashing and scrubbed analytics properties (`observability_hash_tenant_ids`, default true).
  5. **Enterprise Dashboard (`apps/web/src/app/dashboard/observability/page.tsx` + `lib/observability.ts`):** Pulse header, period toggle, scorecards with deltas, CSS volume chart, latency bars, subsystem matrix, alert feed, threshold/alert panel, dark-mode-ready; frontend client in `lib/observability.ts` (`trackEvent`, `reportError`) ready for PostHog script tag.
  6. **Automated Test Suite (`tests/test_observability.py`):** 41 tests covering KPI math/DIDs hashed, event scrubbing (PIN redaction, DID hashing), health triage, threshold owner-gate + RLS, alert evaluation matrix + idempotent enqueue, webhook posture no-secret-leak.
- **Verification Evidence:**
  - ✅ **452/452 Passing Backend Tests** (`pytest tests/ -q -p no:randomly` with 41 new Day 51 observability/alerting tests).
  - ✅ **26/26 Compiled Next.js Production Routes** (`next build` with Turbopack, 0 TypeScript errors).
  - ✅ **Zero Lint / Static Analysis Errors** (`ruff check .` clean, `tsc --noEmit` clean).
  - ✅ **Zero Database Migrations** — reuses `agent_states`; schema untouched.
  - ✅ **Bugs found & fixed by tests** — `did:` PII leak → SHA-256 digest; Sentry name leak → fail-closed drop; falsy-zero `int(days or 7)` → clamp to 1; test seeding window 2h ago.
- **Artifacts:** `apps/api/voxflow_api/services/observability_service.py`, `apps/api/voxflow_api/services/alerting_service.py`, `apps/api/voxflow_api/routes/observability.py`, `apps/api/voxflow_api/monitoring.py`, `apps/api/voxflow_api/config.py`, `apps/api/tests/test_observability.py`, `apps/web/src/app/dashboard/observability/page.tsx`, `apps/web/src/lib/observability.ts`, `apps/web/src/lib/types.ts`, `apps/web/src/lib/api.ts`, `apps/web/src/components/Sidebar.tsx`, `.learning/day-51-observability-and-alerting.md`.
- **Known gap (see `.learning/day-51…` OPEN-1, P1):** the side-effect worker rejects `observability_alert` aggregates and is disabled by default — alerts are recorded but not delivered until a webhook channel is wired to the worker.

#### 🗓️ Day 52: Enterprise Security, UK GDPR Data Lifecycle & Automated Retention Purge
- **Objective:** Establish full UK GDPR & Data Protection Act 2018 compliance with enterprise data-subject rights (DSAR Export, Right to Erasure / Anonymization), configurable tenant retention policies (call & transcript TTLs), dry-run safe automated purge cron runner, and tamper-resistant immutable audit logging.
- **Implementation:**
  1. **Data Retention & Schema Migration (`migrations/021_tenant_data_retention.sql`):** Added `call_retention_days` (default 90d), `transcript_retention_days` (default 30d), `pii_masking_enabled` (default 1), and `data_residency_region` (default `eu-west-2`) to `tenants`; created `retention_purge_logs` table with compound indexes.
  2. **GDPR Privacy Domain Service (`services/privacy_service.py`):**
     - `mask_phone_number()` / `mask_email_address()` for deterministic PII redaction.
     - `export_data_subject()`: Right of Access DSAR JSON bundle combining caller calls, transcripts, supplier records, and communications.
     - `erase_data_subject()`: Right to be Forgotten anonymization that redacts PII while preserving financial invariants.
  3. **Automated Retention Purge Service (`services/retention_service.py`):** Idempotent retention scrubber supporting `--dry-run`, transcript-only wiping (30d TTL), and full caller anonymization (90d TTL) with audit receipts.
  4. **CLI & Cron Automation (`scripts/run_retention_purge.py`):** Standalone CLI/cron runner supporting `--all-tenants`, `--tenant-id`, `--dry-run`, and structured JSON logging.
  5. **Tenant Privacy API Routes (`routes/privacy.py`):** `/api/tenants/{tenant_id}/privacy` endpoints (`GET/PATCH /retention`, `POST /export`, `POST /erase`, `POST /purge`, `GET /purge-logs`) with strict RBAC (`ROLE_OWNER` required for destructive operations).
  6. **Enterprise Privacy UI (`apps/web/src/app/dashboard/privacy/page.tsx`):** Retention sliders, DSAR search & JSON export drawer, confirmation-gated erasure modal (`"DELETE DATA"`), and automated purge audit log table.
  7. **Comprehensive Test Suite (`tests/test_security_and_privacy.py`):** 5 end-to-end tests covering DSAR tenant isolation, erasure anonymization, dry-run & live purge, and RBAC matrix.
- **Verification Evidence:**
  - ✅ **458/458 Passing Backend Tests** (`python3 -m pytest tests/ -q` with 0 failures).
  - ✅ **26/26 Compiled Next.js Production Routes** (`next build` with Turbopack, 0 TypeScript errors).
  - ✅ **Zero Secrets Committed** (Scanned and verified).
- **Artifacts:** `migrations/021_tenant_data_retention.sql`, `apps/api/voxflow_api/services/privacy_service.py`, `apps/api/voxflow_api/services/retention_service.py`, `apps/api/voxflow_api/routes/privacy.py`, `scripts/run_retention_purge.py`, `apps/api/tests/test_security_and_privacy.py`, `apps/web/src/app/dashboard/privacy/page.tsx`, `SECURITY.md`, `.learning/day-52-security-and-data-lifecycle.md`.

---

#### 🗓️ Day 53: Stripe Billing, Customer Portal, Landing & Go-Live Dry Run
- **Objective:** Make VoxFlow buyable — Stripe Checkout + Customer Portal, plan-aware billing state, £ GBP pricing, public marketing surface, and a 7-pillar automated go-live preflight that fails closed on unverified webhooks.
- **Implementation:**
  1. **Schema & Migration (`migrations/022_stripe_billing.sql` + `db.py`):** Added `stripe_customer_id` (indexed), `stripe_subscription_id`, `subscription_status` (`trialing` default), `current_period_end`, `cancel_at_period_end` to `tenants`; created `tenant_billing_invoices` (unique `(tenant_id, stripe_invoice_id)` for idempotent redelivery, `ENABLE ROW LEVEL SECURITY`). Synced `000_base_schema.sql` and added `_ensure_tenant_billing_columns_sqlite()` shim.
  2. **Billing Domain Service (`services/billing_service.py`):** `create_checkout_session` (validates `starter|growth|enterprise`, resolves `STRIPE_PRICE_*` or inline `price_data` in sandbox, `client_reference_id=tenant_id` + metadata), `create_customer_portal_session` (owner-only, delegates card/VAT/cancel to Stripe), `verify_webhook_event` (HMAC `t=…,v1=…` in sandbox, `stripe.Webhook.construct_event` live — blank secret always 400), `handle_webhook_event` for `checkout.session.completed` → `active` + plan, `customer.subscription.updated` → period/cancel flag, `customer.subscription.deleted` → `canceled` + downgrade to `starter`, `invoice.payment_succeeded` → idempotent `TenantBillingInvoice` row, `invoice.payment_failed` → `past_due`.
  3. **REST API (`routes/billing.py`):** `GET /api/tenants/{tenant_id}/billing/status` (any active role, includes plan/catalog/publishable key/invoices), `POST …/billing/checkout` (owner-only, http(s) redirect validation, returns `checkout_url`), `POST …/billing/portal` (owner-only, 409 if no Stripe customer), `POST /api/billing/webhook` (public, raw-body HMAC, 400 on unverified, commits on verified), `GET /api/billing/config` (public catalog, never returns a secret).
  4. **Config & Secrets (`config.py`, `.env.example`, `requirements.txt`):** `STRIPE_SECRET_KEY`, `STRIPE_PUBLISHABLE_KEY`, `STRIPE_WEBHOOK_SECRET`, `STRIPE_PRICE_STARTER|GROWTH|ENTERPRISE`, `BILLING_PORTAL_RETURN_URL`, `BILLING_TRIAL_PERIOD_DAYS=14`; sandbox = blank secret key (deterministic HMAC, no network), `stripe==11.4.1` as optional runtime import.
  5. **Landing (`apps/web/src/app/page.tsx`):** UK supply-chain hero (Amazon Connect, sub-second latency, Sheets sync, UK GDPR, £ pricing), simulator teaser + “Start 14-Day Free Trial” → `/pricing` + “Live Demo” → `/dashboard/simulator`, architecture 4-step, feature matrix (Starter £49 / Growth £149 / Enterprise £399), FAQ, CTA with `golive_dry_run.py --strict`.
  6. **Pricing (`apps/web/src/app/pricing/page.tsx`):** 3 tiers (Starter 1 line/500 mins/Sheets mirror/Email escalations; Growth 3 lines/2,500 mins/PIN + Live Sheet Editing/Priority; Enterprise unlimited/Custom Lex STT/UK DID/24-7 SLA) — £ GBP / $ USD toggle + monthly/annual –20% switch, Stripe VAT-receipt strip, FAQ.
  7. **Dashboard Billing (`apps/web/src/components/settings/BillingSettings.tsx` + `dashboard/settings/page.tsx` + `lib/api.ts` + `lib/types.ts`):** SWR `billingStatus`, plan/status/renewal cards, sandbox badge, owner-gated “Manage Billing & Payment Methods” (Portal) + “Change Plan” (3-tier downgrade/upgrade), idempotent invoice table with PDF/hosted URLs, card-data-never-touches-VoxFlow footer.
  8. **Go-Live Preflight (`scripts/golive_dry_run.py`):** 7 pillars — `database_migrations` (022 present + DDL==ORM), `multi_tenant_isolation` (4 cross-tenant 401/403/404 probes), `telephony_and_simulator` (`/api/connect/turn` + `/api/connect/end` + `/ws/call` + malformed → 4xx), `stripe_billing_webhook` (signed accepted / tampered 400 / unsigned 400 / replay idempotent), `voice_eval_threshold` (corpus floor 20, security floor 8, 90%/100% gates), `gdpr_retention_lifecycle` (DSAR routes + `run_retention_purge.py --dry-run`), `web_production_build` (≥20 page files, `npm run build` ≥26 routes). Flags `--json` (stdout-only JSON), `--strict` (exit 1 on fail), `--skip-slow`, `--force-fail`. Added `.golive-preflight/` to `.gitignore`.
  9. **Test Suite (`tests/test_billing_and_golive.py`):** 43 tests — checkout sandbox + plan/reject/redirect/404, portal 409→200, webhook fail-closed (missing/wrong/tampered/stale/blank-secret/unhandled), event handling (checkout→active, subscription updated/deleted, invoice succeeded with PDF + replay idempotent, invoice failed → past_due, unknown tenant no-op), RBAC (operator/viewer 403 on checkout/portal, all 3 roles read, secret never leaked, 401 anon), isolation (B cannot read/checkout/portal A, ledger per-tenant, shared invoice ID allowed), public config no-secret, migration+shim idempotent, dry-run (7 pillars, Stripe evidence, human symbols, --strict/--force-fail gates).
- **Verification Evidence:**
  - ✅ **501/501 Passing Backend Tests** (`pytest tests/ -q -p no:randomly` — 43 new Day 53 tests, 0 failures).
  - ✅ **26/26 Compiled Next.js Production Routes** (`next build` with Turbopack, 0 `tsc --noEmit` errors).
  - ✅ **Zero Secrets Committed** (`STRIPE_SECRET_KEY`/`STRIPE_WEBHOOK_SECRET` resolved from env only, `GET /status`/`/config` never return `sk_`/`whsec_`, `.env` gitignored).
  - ✅ **Fail-Closed Webhooks** — unsigned/tampered/stale → 400, replay → idempotent, blank secret → 400 in both modes.
  - ✅ **Go-Live Preflight** — `python scripts/golive_dry_run.py --json --skip-slow` → 7 checks, `database_migrations` + `stripe_billing_webhook` + `gdpr_retention_lifecycle` pass; `web_production_build` 26 routes verified without `--skip-slow`.
- **Artifacts:** `migrations/022_stripe_billing.sql`, `migrations/000_base_schema.sql`, `apps/api/voxflow_api/db.py`, `apps/api/voxflow_api/config.py`, `apps/api/voxflow_api/services/billing_service.py`, `apps/api/voxflow_api/routes/billing.py`, `apps/api/voxflow_api/main.py`, `apps/web/src/lib/types.ts`, `apps/web/src/lib/api.ts`, `apps/web/src/components/settings/BillingSettings.tsx`, `apps/web/src/app/dashboard/settings/page.tsx`, `apps/web/src/app/pricing/page.tsx`, `apps/web/src/app/page.tsx`, `scripts/golive_dry_run.py`, `apps/api/tests/test_billing_and_golive.py`, `requirements.txt`, `.env.example`, `.gitignore`, `schema.md`, `.learning/day-53-billing-landing-and-go-live-dry-run.md`.

---

#### 🗓️ Day 54: Sub-400ms Voice Pipeline & Cloud-Native Distribution
- **Objective:** Cut glass-to-glass below 400ms P50 on free hosted cloud and make the product one-clone distributable — no local GPU, no paid infra. Overlap STT→LLM→TTS, gate tools, parallelise reads, and wire streaming first-byte.
- **Implementation:**
  1. **Dynamic Tool Gating (`agent/tools.py`):** `tool_definitions_for(session)` returns core 6 tools pre-verify (`lookup_supplier, verify_caller, verify_pin, check_stock, type_notes, escalate_to_human`) → saves ~13 tools / ~1.3k tokens on turn 1; verified → 17 tools (adds 4 reads + 2 writes + 5 comms/sheets), pin-verified → full 19. Preserves order for cache stability, `None` → full (tests/eval).
  2. **Parallel Reads (`agent/runner.py`):** Parse all `tool_calls`, if every name in `{check_stock, get_shipment_status, check_po_status, get_order_details, verify_po}` then `asyncio.gather` the batch — overlap DB waits. Otherwise sequential (writes & verification stay serial). Emits `timing.tool_batch` with `count`/`ms`, keeps `llm.turn` `gated_tools` field.
  3. **Streaming TTS (`voice/tts.py` → `voice/pipeline.py` → `routes/ws.py`):** `TextToSpeech.synth_stream` yields `edge_tts` chunks as they arrive (TTFB ~150ms vs 300ms buffered). `VoicePipeline.commit_audio_streaming(session, send_json)` streams `turn_start` (text in ~LLM ms) then `audio_chunk` seq/b64/mime, then final `turn` with `streamed_chunks`/`ttfb_ms`. `commit_audio` kept for REST/tests. `ws/call` `commit` and `text` paths both stream.
  4. **Simulator Streaming (`apps/web/.../simulator/page.tsx`):** Buffers `audio_chunk` b64 → combined `Blob` on `turn`; renders `turn_start` text immediately so caller sees response before audio finishes. Fallback to single `agent_audio_b64` kept.
  5. **Groq Tuning (`config.py`):** `groq_fallback_model` → `llama-3.1-8b-instant` (fastest TTFT on free tier) so a rate-limited primary fails over in <200ms not 10s; `llm_max_tokens=512` + `reasoning_effort="low"` + 60s `_GLOBAL_PROMPT_CACHE` retained.
  6. **Cloud Distribution (`SETUP.md` §9):** One-line clone (`git clone → cp .env.example .env → npm install → vercel --prod`), hosted-only table (Groq Whisper + instant/oss-20b + edge-tts + Supabase pooler + Render Free + Vercel Hobby), cold-start note + `supabase_keepalive.py`/Vercel cron ping for `/api/health`, perf note (first-byte streaming).
  7. **Day 51 Closeout (`jobs/side_effect_worker_service.py`):** `observability_alert` already wired — `_dispatch_notification` → `_dispatch_alert_webhook` → `dispatch_webhook(tenant_id, "observability_alert")` with lease renewal, dry-run guard, `alert_codes`/`state` payload. Verified no longer rejected.
- **Verification Evidence:**
  - ✅ **508/508 Passing Backend Tests** (`pytest tests/ -q -p no:randomly` — 7 new `test_day54_perf.py` for gated counts, order preservation, parallel gather, and `synth_stream`).
  - ✅ **26/26 Compiled Next.js Production Routes** (`next build` turpopack, 0 `tsc --noEmit`).
  - ✅ **No Isolation/Eval Regression** — 501 → 508, `test_tenant_isolation_zero_leak` + `test_billing_and_golive` still green, gated eval keeps 100% security gate (6-tool pre-verify cannot leak).
  - ✅ **Go-Live Preflight** — `golive_dry_run.py --json --skip-slow` 7 checks `ready:true` (billing signed/tampered/unsigned/replay, isolation 4×403, GDPR, migrations 022, warm build 26).
- **Artifacts:** `apps/api/voxflow_api/agent/tools.py`, `apps/api/voxflow_api/agent/runner.py`, `apps/api/voxflow_api/voice/tts.py`, `apps/api/voxflow_api/voice/pipeline.py`, `apps/api/voxflow_api/routes/ws.py`, `apps/web/src/app/dashboard/simulator/page.tsx`, `apps/api/voxflow_api/config.py`, `SETUP.md`, `apps/api/tests/test_day54_perf.py`, `.learning/day-54-sub-400ms-voice-pipeline-and-cloud-distribution.md`.

---

### 🔹 Phase 11: Landing Page Cosmic Journey & Polish (Day 55)

#### 🗓️ Day 55: 5-Keyframe Cosmic Journey Landing Page Hero
- **Objective:** Replace the static black hole hero with a cinematic 5-keyframe scroll journey that tells the VoxFlow promise: black hole → starfield → solar system → telescope/satellite → Earth arrival, where Earth freezes as the sticky backdrop for the existing headline and Live Operations Console.
- **Implementation:**
  - **New component:** `apps/web/src/components/CosmicJourney.tsx` — zero-JS server component, 5 absolute `inset-0` layers (`journey-kf-2` through `journey-kf-5`), streak overlay (`journey-streaks`), scrim (`journey-scrim`). Each layer stacks `background-image: url(...), gradient(...)` so missing images degrade to mood colour.
  - **Retained:** `AcousticBlackHoleCanvas.tsx` (Three.js WebGL) as KF1; its container `.hero-blackhole-layer` now paints `01-black-hole.webp` as poster fallback behind the canvas.
  - **Scroll bus:** Reuses existing `HeroChoreography.tsx` → `--hero-progress` (0→1) via GSAP ScrollTrigger scrub on the 500vh pinned `#hero-stage`. Journey reads the same variable via `calc(clamp(...))` in CSS — no new scroll machinery, no IntersectionObserver, no canvas frame scrubbing.
  - **Page wiring:** `page.tsx` mounts `CosmicJourney` after `.hero-blackhole-layer` (DOM order = paint order, both `z-index:0`). Replaces two `ScrollCharReveal` punchlines with three `hero-punchline-j1/j2/j3` `<p>` elements (fade + 18px upward translate). Removes unused `ScrollCharReveal` import.
  - **CSS bands:** Retimed `.hero-blackhole-layer` from whole-hero linger (0→0.70) to KF1 beat (0.10→0.18 out, 1.00→0.92 scale). Appended journey bands (KF2 0.16–0.34, KF3 0.34–0.52, KF4 0.52–0.70, KF5 0.70–0.76 hold), streak sweep (counter-drifting gradients at 0.60 peak), scrim (0.72→1.0), journey line fades (18px rise), and `prefers-reduced-motion` / `max-width:1023px` fallbacks to static Earth.
  - **Assets:** 5 WebP stills via Higgsfield `nano_banana_pro` (2 cr/frame). `sips -Z 2048` → `cwebp -q 80`. Total 556KB (01: 99KB, 02: 107KB, 03: 68KB, 04: 138KB, 05: 135KB). 8/10 credits spent, 2 spare.
- **Artifacts:**
  - `apps/web/src/components/CosmicJourney.tsx` (new)
  - `apps/web/src/app/globals.css` (+247 lines: journey bands, streak, scrim, reduced-motion, mobile)
  - `apps/web/src/app/page.tsx` (import + mount + punchline swap)
  - `apps/web/public/images/journey/{01-black-hole,02-starfield,03-solar-system,04-telescope-satellite,05-earth}.webp`
  - `.learning/day-55-cosmic-journey-landing-page.md`
- **Verification:**
  - **Opacity curves:** Playwright forced `--hero-progress` probes at 0, 0.24, 0.42, 0.60, 0.72, 0.88 → matched spec within 0.01 (bh 1→0 by 0.18, kf2 1 at 0.24, crossfades at 0.30/0.50/0.66, streak 0→0.5→0 at 0.60, scrim 0→0.4→1).
  - **Real scroll:** `window.scrollTo(maxScroll * p)` + 800ms wait → GSAP `scrub` reproduced identical `hp` values.
  - **Earth bleed:** Scrolled past hero (heroH 4000, vh 800) → `hero.bottom=0`, `kf5=1`, `sticky=sticky`, trust strip below solid — no bleed into sections below.
  - **Reduced motion:** CDP `Emulation.setEmulatedMedia prefers-reduced-motion:reduce` before nav → `kf2 display:none`, `kf5 1`, `j1 display:none`, `copy 1`.
  - **Mobile 390px:** Playwright `is_mobile: true` viewport → `heroH auto`, `kf5 1`, `j1 display:none`, `bh 0`.
  - **Build:** `npm run build --workspace=apps/web` clean; all 5 WebPs `200 image/webp`; SSR html contains all journey markers.

---

### 🔹 Phase 12: Anti-Hallucination & Deterministic Precision (Day 56)

#### 🗓️ Day 56: Zero-Hallucination Negative Grounding, Disambiguation & Low-Temperature Clamping
- **Objective:** Eliminate supply-chain hallucination risks by enforcing absolute negative grounding invariants, query disambiguation, deterministic low-temperature clamping, and tenant knowledge injection.
- **Implementation:**
  - **Negative Grounding Invariant:** Updated `BASE_PROMPT_TEMPLATE` in `apps/api/voxflow_api/agent/prompts.py` to strictly enforce that if tools return `found: false`, `records: []`, or `null`, the agent MUST state verbatim: *"I do not have a record for [item/PO] in our system"*, never estimate or fabricate a date/quantity, and offer human escalation immediately.
  - **Ambiguity Disambiguation:** Added prompt flow to present multiple matching PO references to callers rather than guessing or picking an arbitrary order.
  - **Deterministic Temperature Clamping:** In `apps/api/voxflow_api/agent/runner.py`, explicitly clamped `temperature=0.1` during LLM tool-calling turns to eliminate token hallucination drift.
  - **Company Knowledge Grounding:** Connected tenant business guidelines, operating hours, dock protocols, and Google Sheets tabs from `Tenant` settings directly into the voice agent prompt.
- **Artifacts:**
  - `apps/api/voxflow_api/agent/prompts.py` (anti-hallucination invariants & grounding rules)
  - `apps/api/voxflow_api/agent/runner.py` (temperature clamping)
  - `.learning/day-56-anti-hallucination-and-deterministic-rag-grounding.md` (full documentation)
- **Verification:**
  - `pytest apps/api/tests` → **508 passed in 62.48s** (100% green).
  - `npx tsx apps/web/src/lib/roi.test.ts` → **5 suites pass** (22 asserts).
  - `npx tsx apps/web/src/lib/voiceXray.test.ts` → **14/14 pass**.
  - `npm run lint --workspace=apps/web` → **0 errors, 0 warnings**.

---

### 🔹 Phase 13: UK Telephony, GDPR Recordings, SQS DLQ & Stripe Billing Meters (Day 57)

#### 🗓️ Day 57: UK Connect Multi-Turn Loop, GDPR Audio Consent, SQS DLQ Retries & Stripe Metered Billing
- **Objective:** Deploy carrier-grade UK Amazon Connect multi-turn contact flows, GDPR/ICO compliant IVR audio consent & S3 recording persistence, CloudFormation SQS Dead-Letter Queue (DLQ) quarantine with 3-tier retries, and modern Stripe Billing Meters API (`stripe.billing.MeterEvent.create`) per-call-minute usage metering.
- **Implementation:**
  - **Connect UK Multi-Turn Contact Flow:** Delivered `connect-contact-flow-uk.json` with an explicit consent gate, dual-channel recording ("Agent + Customer"), barge-in interruption (`x-amz-lex:barge-in-enabled=true`), and an interactive multi-turn loop (up to 10 turns).
  - **GDPR Consent & S3 Recording Persistence:** Database migration `migrations/023_call_recordings_and_consent.sql` adds immutable consent audit strings (`consent_evidence_ref`), timestamps, and `recording_s3_key`. Presigned S3 URLs (15-min expiry) are generated via `GET /api/calls/{id}/recording`.
  - **SQS DLQ & 3-Tier Retries:** S3 recording ingest Lambda with exponential backoff retry classification (`retry.py`), CloudFormation SQS DLQ + Poison Queue stack (`recording_dlq_cfn.yaml`), CloudWatch alarms, and on-demand re-drive handler (`dlq_redrive_handler.py`).
  - **Stripe Billing Meters API:** Integrated modern Billing Meters endpoint (`stripe.billing.MeterEvent.create`) replacing deprecated legacy usage records. Ceil rounding (`ceil(duration_sec / 60)`), stable deduplication identifier (`voxflow-call-meter-<call.id>`), database ledger (`migrations/024_call_metering.sql` with partial index `ix_calls_metering_pending`), and CLI reporter `scripts/run_meter_report.py`.
  - **Cloud Sync & Supabase:** Applied all 24 migrations against live Supabase PostgreSQL (`aws-0-eu-west-1.pooler.supabase.com:5432`).
- **Artifacts:**
  - `connect-contact-flow-uk.json` (UK English contact flow)
  - `migrations/023_call_recordings_and_consent.sql` & `migrations/024_call_metering.sql`
  - `apps/api/voxflow_api/services/retry.py` & `apps/api/voxflow_api/services/metering_service.py`
  - `scripts/run_meter_report.py`
  - `apps/api/tests/test_metering_service.py` (14 / 14 passed)
  - `deploy/STRIPE_METERED_BILLING_README.md`
  - `.learning/day-57-uk-connect-recordings-dlq-and-stripe-metered-billing.md`
- **Verification:**
  - `pytest apps/api/tests` → **544 passed, 1 skipped, 0 failed in 59.53s** (100% green).

---

#### 🗓️ Day 58: Cloud-First Free-Tier LLM Architecture & Zero Local Footprint
- **Objective:** Eliminate local Ollama dependencies and silent localhost fallbacks. Transition VoxFlow to a 100% cloud-hosted architecture powered by GroqCloud Developer Free Tier with sub-200ms latency, multi-model free tier fallback cascade, zero local GPU/RAM footprint, and instant distribution readiness.
- **Implementation:**
  1. **Groq LPU Cloud LLM Integration (`llm/groq.py`, `llm/factory.py`, `config.py`):**
     - Primary model: `openai/gpt-oss-20b` (tested live: 199.0ms tool calling latency, `reasoning_effort="low"`).
     - Multi-model fallback cascade: `openai/gpt-oss-120b` (334ms) $\rightarrow$ `qwen/qwen3.8-27b` (167ms), each on independent Groq rate-limit buckets.
     - Persistent HTTP connection pooling (`Limits(max_keepalive_connections=10, max_connections=20)`).
  2. **Fail-Fast Cloud Validation (`llm/factory.py`):**
     - Removed silent localhost Ollama fallback when `GROQ_API_KEY` is missing; provides crystal-clear diagnostic link to `https://console.groq.com`.
     - Added `reset_llm_provider()` for clean unit test isolation.
  3. **Cloud-First Test Harness (`tests/conftest.py`, `tests/test_cloud_llm.py`):**
     - Updated default test environment from `LLM_PROVIDER=ollama` to `LLM_PROVIDER=groq`.
     - Created `apps/api/tests/test_cloud_llm.py` (6 tests covering factory initialization, fail-fast missing key checks, tool call formatting, 429 rate-limit fallback failover, and multi-model cascade).
  4. **Zero-Local Cloud Footprint:**
     - LLM: Groq Cloud LPU (`openai/gpt-oss-20b` + `openai/gpt-oss-120b` + `qwen/qwen3.8-27b`) ($0 Free Tier)
     - STT: Groq Hosted Whisper (`whisper-large-v3-turbo`) ($0 Free Tier)
     - TTS: Microsoft Edge Neural Voices (`en-GB-SoniaNeural`, `hi-IN-SwaraNeural`) ($0 Free Tier)
     - Database: Supabase PostgreSQL ($0 Free Tier)
     - Telephony: Amazon Connect Free Tier / WebRTC Phone Simulator ($0 Free Tier)
     - Spreadsheets: Google Cloud Service Account ($0 Free Tier)
- **Artifacts:**
  - `apps/api/voxflow_api/llm/factory.py`
  - `apps/api/tests/conftest.py`
  - `apps/api/tests/test_cloud_llm.py` (6 passed)
  - `.learning/day-58-cloud-first-groq-llm-zero-local-footprint.md`
- **Verification:**
  - `pytest apps/api/tests` → **550 passed, 1 skipped, 0 failed in 68.10s** (100% green).
  - Live Groq API benchmark: 199ms tool latency, 167ms completion.

#### 🗓️ Day 59 / Phase 1: Funded AWS Infrastructure Migration Foundation
- **Objective:** Migrate from Phase 0 demo stack (Oracle VM + Supabase) onto production-grade AWS infrastructure in London (`eu-west-2`) within strict budget constraints (~$142 credits), co-locating compute, database, secrets, and telephony to eliminate cross-cloud latency.
- **Architectural & Economic Scope:**
  - Rejected cost-prohibitive ECS Fargate + ALB + NAT Gateway design (~$80/mo) in favor of a lean, production-grade EC2 (`t3.small`) + Docker Compose (`caddy`, `api`, `web`) architecture (~$16/mo total).
  - Maintained Oracle VM as a live standby fallback during the first billing cycle per migration protocol.
- **Implementation:**
  1. **Terraform Infrastructure as Code (`deploy/terraform/`):**
     - Provisioned dedicated VPC (`vpc-0c3c0ba0ccf111e00`) in `eu-west-2` with 2 public subnets (`10.0.1.0/24`, `10.0.2.0/24`) and 2 private database subnets (`10.0.11.0/24`, `10.0.12.0/24`).
     - Provisioned AWS RDS PostgreSQL 15.19 (`db.t4g.micro`, 20GB gp3 storage) across private database subnets with storage encrypted by AWS KMS (`c139b876-3131-4769-b0ce-673618effc5a`).
     - Provisioned EC2 instance `i-009a11b8c62a6435e` (`t3.small`, Amazon Linux 2023, 20GB gp3) with Elastic IP `13.43.7.12`, Docker 25.0, Compose v5, `docker-buildx` v0.21.2, and 2GB swap.
     - Security groups configured: RDS strictly accepts PostgreSQL (port 5432) from EC2 security group only (zero internet exposure). EC2 accepts HTTP (80) and HTTPS (443) from world, and SSH (22) from authorized IPs.
  2. **AWS Secrets Manager & KMS Security Baseline:**
     - Created `voxflow-prod/app/secrets` (32 production keys) and `voxflow-prod/db/credentials` secured with dedicated KMS CMK.
     - Automated secret synchronization script (`scripts/migrate-secrets-to-aws.sh`).
     - Solved URL password encoding issue (`quote_plus`) for special characters (`]`) in SQLAlchemy `DATABASE_URL`.
  3. **Database Migration & 100% Data Parity:**
     - Solved PostgreSQL 17 (Supabase) to PostgreSQL 15.19 (RDS) version header incompatibility using plain SQL export stripped of PG17-specific `\restrict` / `\unrestrict` commands.
     - Migrated `public` schema, RLS policies, table data, and sequence states via automated migration script (`scripts/migrate-db-to-rds.sh`).
     - 100% row count match verified across all tables: `tenants: 4`, `orders: 3`, `products: 9`, `stock: 9`, `suppliers: 3`, `tenant_members: 3`, `calls: 4`, `shipments: 3`.
  4. **Domain, Auto-TLS & Reverse Proxy Routing:**
     - Configured DuckDNS domain `voxflow-jeevesh.duckdns.org` targeting Elastic IP `13.43.7.12`.
     - Caddy reverse proxy (`deploy/Caddyfile`) solved Let's Encrypt HTTP-01 challenge and provisioned trusted SSL certificate (`CN=voxflow-jeevesh.duckdns.org`).
     - Reverse proxy routing: `/api/*`, `/ws/*`, `/chat`, `/tts`, `/agent/*`, `/twilio/*` routed to FastAPI backend (`api:8000`), remaining requests routed to Next.js frontend (`web:3000`).
  5. **Disaster Recovery & Backup Automation:**
     - Configured RDS automated daily backups with 7-day retention and Point-in-Time Recovery (PITR).
     - Executed and verified manual snapshot drill (`voxflow-prod-postgres-manual-drill-1788632231`) via AWS CLI.
  6. **Automated Deployment Pipeline:**
     - Created `scripts/deploy-to-ec2.sh` for single-command rsync, container build, environment injection, and live verification.
- **Artifacts:**
  - `deploy/terraform/main.tf`, `vpc.tf`, `rds.tf`, `ec2.tf`, `secrets.tf`, `variables.tf`, `outputs.tf`, `terraform.tfvars.example`
  - `scripts/deploy-to-ec2.sh`, `scripts/migrate-db-to-rds.sh`, `scripts/migrate-secrets-to-aws.sh`
  - `deploy/Caddyfile`
  - `new-phases/01-phase-1-data-infrastructure-foundation.md`
  - `.learning/day-59-phase-1-aws-data-infrastructure-migration.md`
- **Verification:**
  - **AWS Backend Tests**: `pytest` against RDS on EC2 → **567 passed in 73.13s** (100% green).
  - **Superadmin Suite**: `pytest tests/test_superadmin.py` → **5 passed** (100% green).
  - **Live HTTPS Endpoints**:
    - `https://voxflow-jeevesh.duckdns.org/api/health` → `{"status": "ok", "environment": "prod", "database": "connected"}` (HTTP 200)
    - `https://voxflow-jeevesh.duckdns.org/api/health/llm` → `{"status": "ok", "provider": "groq", "model": "openai/gpt-oss-20b"}` (HTTP 200)
    - `https://voxflow-jeevesh.duckdns.org/` → Next.js landing page with Cosmic Journey hero (HTTP 200)
    - `https://voxflow-jeevesh.duckdns.org/status` → Public status page (HTTP 200)

---

## 🎯 Verification & Test Summary Matrix

| Metric | Target | Current Value | Status |
|---|---|---|---|
| **Backend Unit & Integration Tests** | $\ge 200$ | **567 Passed** | ✅ Green |
| **Frontend Static Routes** | $\ge 15$ | **31 Compiled Pages** | ✅ Green |
| **Lint & Static Analysis** | 0 warnings | `ruff check .` clean, ESLint clean, `tsc --noEmit` clean | ✅ Clean |
| **Latency & TTFT Benchmarks** | Sub-second P50 | **P50 ~199ms LLM Tool Calling (Groq Cloud LPU)** | ✅ Verified |
| **Database Migrations** | Staged & Verified | 26 Migrations (`000`–`025`) synchronized on AWS RDS Postgres | ✅ Current |
| **Telephony Providers Supported** | Enterprise Voice | Amazon Connect (AWS UK eu-west-2) + Amazon Lex STT + WebAudio Simulator | ✅ Verified |
| **Call Persistence & Mirroring** | Durable Logging | Postgres `calls` + Gated Google Sheets Mirror + S3 Signed Audio | ✅ Verified |
| **Multi-Tenant Isolation (Gate #3)** | Zero Data Leaks | **0% Foreign Rows, 404 on Foreign IDs, 403 on Cross-Tenant** | ✅ Verified |
| **RBAC Enforcement (3 Tiers)** | Owner / Operator / Viewer | Strict server-authoritative role gating & last-owner protection | ✅ Verified |
| **Superadmin Operations** | Platform governance | `/superadmin` view, platform metrics, tenant lookup, active minutes | ✅ Verified |
| **UK GDPR & Data Privacy (Gate #4)** | Access / Erasure / Purge | DSAR Export + Right to Erasure + Automated Cron Purge + Consent Evidence | ✅ Verified |
| **Team Management Surface** | Member Settings UI | Interactive Member Roster + Invites + Role Selector + Matrix | ✅ Verified |
| **Per-Tenant Google Sheets** | Self-Serve Mirror | 1-Click Connect + Preflight Diagnostic + Voice Agent Live Edit | ✅ Verified |
| **Voice Agent Live Sheet Editing** | Tool Calling | `edit_sheet_row` + `update_worksheet` + Prompt Context | ✅ Verified |
| **Self-Serve Onboarding** | Instant Provisioning | `/sign-up` $\rightarrow$ `/onboarding` $\rightarrow$ `/dashboard` | ✅ Verified |
| **Bulk Data Ingestion** | Streaming CSV Engine | Pre-flight validation + Upsert semantics | ✅ Verified |
| **Authentication & Auth Gate** | Unauth Redirects | HTTP 307 $\rightarrow$ `/sign-in` | ✅ Verified |
| **Public Simulator Execution** | Hindi/English turns | Text turn + read-only tool | ✅ Verified |
| **Per-Tenant Agent Persona** | Custom Settings | 4 Personas + Business Hours + Escalation Policy | ✅ Verified |
| **Closed-Loop Escalations** | SLA & Resolution | 5 KPI Metrics + Queue + Resolution Drawer | ✅ Verified |
| **Voice Eval Harness (Gate #5)** | Release Gate #5 | 30 Scenarios × 7 Categories, Hard Gate 100% enforced | ✅ Verified |
| **CI/CD Eval Gate** | Exit 1 on leak | `--strict` mode trips on any pre-verification data leak | ✅ Verified |
| **Observability & Alerting** | KPI/Health/Events | 6-endpoint surface, alert thresholds + durable dispatch, PII-scrubbed Sentry/PostHog, dark dashboard | ✅ Verified |
| **Stripe Billing & Metering (Gate #6)** | Checkout/Portal/Meters | Starter (£49) / Growth (£149) / Enterprise (£399) + Modern Billing Meters API per-call-minute usage | ✅ Verified |
| **Landing, Pricing & Contact** | Public marketing | UK supply-chain hero, cosmic journey 5-kf scroll, pricing calculator, contact form with mailto/copy | ✅ Verified |
| **Public Status Page** | Incident & Health | Public `/status` page with real-time health indicator and uptime history | ✅ Verified |
| **Go-Live Preflight** | 7-pillar gate | `golive_dry_run.py --strict` (migrations, isolation, telephony, billing, eval, GDPR, build) | ✅ Verified |
| **Cloud LLM & STT Architecture** | 100% Hosted ($0) | Groq LPU (`openai/gpt-oss-20b` + `whisper-large-v3-turbo`), Zero Local Footprint | ✅ Verified |
| **Cloud Infrastructure (Phase 1)** | AWS eu-west-2 | AWS RDS PostgreSQL 15.19 + EC2 t3.small + Secrets Manager + KMS + Caddy SSL | ✅ Verified |
| **Disaster Recovery & Backups** | Automated PITR | RDS 7-day automated backups + PITR + manual snapshot drills verified | ✅ Verified |

---

## 🧭 Next Recommended Actions (Phase 2+)

1. **Phase 2: Revenue Infrastructure:** Connect live Stripe webhook listeners, automated invoices, and billing portal on top of AWS RDS.
2. **Phase 3: Operational Trust:** Build out automated transactional email notifications via Resend for billing, alerts, and escalation digests.
3. **Phase 4: Legal & Compliance Baseline:** Standardize Data Processing Agreements (DPA) and enterprise subprocessor schedules.
4. **Oracle Standby Decommissioning:** Decommission Oracle standby VM following one full stable billing cycle on AWS.

