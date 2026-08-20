# VoxFlow Delivery Phases

**Last updated:** 2026-08-20
**Current position:** Day 32 complete; Day 33 provider-adapter sandbox certification is the next implementation phase.
**Planning rule:** a milestone is complete only when its implementation, automated verification, deployment result, and safety boundary are recorded.

## Programme status

| Programme | Days | Status | Verified outcome |
|---|---:|---|---|
| Foundation and inbound voice | 1–24 | Complete | Multi-tenant FastAPI/Next.js product, inbound voice path, dashboard modules, initial campaign domain. |
| Durable execution foundation | 25–28 | Complete | Job ledger, outbox, atomic claim/lease, retry runtime, job-health read model, safe staging. |
| Controlled campaign cutover | 29–30 | Complete | Feature-gated worker, provider-operation idempotency, reconciliation foundation, tenant policy and auditable cancellation. |
| Enterprise analytics and monitoring | 31 | Complete | Tenant KPI/trend aggregates, durable health signals, redacted CSV reporting, and dashboard operator view. |
| Provider lifecycle hardening | 32 | Complete | Signed/fresh callbacks, immutable event ledger, tenant-derived reconciliation, quarantine, and lifecycle analytics. |
| Integration reliability and canary readiness | 33–38 | Planned | Provider sandbox certification, typed jobs, internal test-tenant canary, traces, alert routing, dead-letter controls, resilience game days. |
| Security and tenant controls | 39–43 | Planned | RBAC, RLS audit, callback hardening, retention, security evidence. |
| Voice quality and integrations | 44–48 | Planned | Evaluation corpus, release thresholds, provider/integration contracts. |
| Pilot readiness | 49–54 | Planned | Promotion controls, load/recovery rehearsal, tenant onboarding, controlled pilot. |

## Historical foundation: Days 1–24

Days 1–24 established the backend, dashboard, tenant-aware data model, inbound voice functionality, security controls, operational modules, deployment path, and outbound campaign domain. The detailed original day-by-day worksheets are retained under `.planning/` and `.learning/` as historical learning material. The source of current engineering truth is this document together with `MEMORY.md`, `ARCHITECTURE.md`, and the latest `.learning` day guides.

## Completed durable execution and observability: Days 25–32

| Day | Implementation | Verification and exit result |
|---:|---|---|
| 25 | Introduced `JobRun`, `JobOutbox`, `JobAttempt`, and `ProviderOperation`; campaign-target enqueue and outbox write are transactional. | Unique tenant/idempotency and atomic-enqueue tests passed; migration `003_durable_job_ledger.sql` added. |
| 26 | Added atomic job claiming, worker leases, stale-worker conditional transitions, and expired-lease recovery. | Competing claim and stale completion behavior tested. |
| 27 | Added `WorkerRuntime`, typed retry/permanent failure handling, full-jitter exponential backoff, and graceful drain signals. | Worker synthetic/retry/drain tests passed. |
| 28 | Added transactional outbox relay, tenant-safe job-health and recent-job APIs, dashboard operator panel, and safe staging. | Outbox/job health tests and staged production read verification passed; migration `004_outbox_relay_state.sql` added. |
| 29 | Added standalone campaign worker process, tenant canary filtering, dry run, provider-operation reserve/update, reconciliation, and no-redial retry behavior. | Campaign dispatch/reconciliation and kill-switch tests passed; production worker stayed disabled. |
| 30 | Added tenant policy, recipient consent/opt-out/purpose checks, timezone calling windows, daily budget, active capacity, exact deferral, immutable policy decisions, and durable cancellation. | Paused, closed-window, consent, opt-out, quota, API scoping, and audit-redaction tests passed; migration `005_campaign_policy_controls.sql` added. |
| 31 | Added tenant-safe operational KPI/trend aggregation, pull-based durable monitoring signals, redacted CSV enterprise reports, and a live analytics dashboard. | Tenant isolation, policy trends, lease/dead-letter alerting, CSV sensitive-data exclusion, backend lint/**184 tests**, and frontend lint/build passed. |
| 32 | Added fail-closed signed callback ingress, immutable provider events, unknown-call quarantine, duplicate/terminal ordering guards, terminal job reconciliation, and provider lifecycle analytics. | Callback signature/replay, tenant spoofing, duplicate, terminal, stale, unconfigured, quarantine, and lifecycle analytics tests passed; migration `006_provider_callback_lifecycle.sql` added. |

**Day 32 local release evidence:** backend lint clean; **188 backend tests passing**; frontend lint/build passing with 20 routes. The production campaign worker remains disabled and the callback secret is intentionally unconfigured, so no real provider callback or outbound call can mutate campaign state.

## Day 33 — Provider adapter sandbox certification and callback rollout

**Objective:** Certify a provider-specific callback adapter against documented sandbox fixtures before registering any live callback URL or permitting callback application for a tenant.

| Work item | Acceptance criterion |
|---|---|
| Provider signature adapter | Documented canonicalization verifies authentic sandbox events and rejects tampering before database access. |
| Event normalization | Provider-specific payloads map only to the Day 32 normalized event shape; no callback tenant/queue/job input is trusted. |
| Replay and reordering drills | Original, duplicate, delayed, and reordered fixtures leave counters and lifecycle state correct. |
| Operator rollout gate | An explicit adapter feature flag and tenant allow-list can stop application immediately. |
| Callback observability | Verification failures, quarantines, duplicates, event age, and anomalies have tenant-safe operator visibility. |

**Safety boundary:** production campaign worker remains disabled. Day 33 may use sandbox fixtures only; it does not authorize a real provider call.

## Upcoming campaign-cutover work

| Day | Planned focus | Required proof |
|---:|---|---|
| 33 | Provider-specific sandbox callback certification, replay drills, and controlled adapter gate. | Documented signature contract and safe adapter fixture suite; live callback remains disabled. |
| 34 | Move Sheets retry, email summarization, recording retrieval, CRM sync, and outbound notifications into typed durable jobs. | Disable legacy in-process loops in staging without losing work. |
| 35 | Internal test-tenant worker canary or provider sandbox only. | Crash/restart and callback-delay recovery with a unique provider-operation record. |
| 36 | Correlated tracing through command, outbox, job, provider operation, callback, and communication record. | One target traceable end to end without a database shell. |
| 37 | Dead-letter operator controls: inspect, annotate, cancel, replay, and audit. | Explicit replay creates a new auditable attempt only. |
| 38 | Alert routing, runbooks, and resilience game-day preparation. | Every critical durable-work signal has a named response path. |

## Non-negotiable release gates

No production campaign expansion is permitted without all of the following:

1. No direct provider side effect from an API request transaction.
2. Provider-operation idempotency and callback event deduplication proven by tests.
3. Tenant-scoped rows, APIs, policies, and audit reads.
4. Explicit consent, opt-out, timezone, budget, and capacity controls.
5. Feature-flag rollback, worker drain, queue health, and operator ownership.
6. Queue-age/failure/callback-lag observability and actionable runbooks.
7. A scoped test tenant, approved test target, and no broader tenant cohort.

## Required end-of-day maintenance

1. Update `MEMORY.md` with current branch, test count, deployment state, safety posture, and next action.
2. Update the current and next `.learning/day-NN-*.md` guides.
3. Update this roadmap when a day changes status.
4. Update `README.md`, `ARCHITECTURE.md`, `schema.md`, `security_audit.md`, and app READMEs when the delivered architecture or operator procedure changes.
5. Never force-add `.learning/`; it remains intentionally local and gitignored.
