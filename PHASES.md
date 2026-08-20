# VoxFlow Delivery Phases

**Last updated:** 2026-08-20
**Current position:** Day 30 complete; Day 31 is the next implementation phase.
**Planning rule:** a milestone is complete only when its implementation, automated verification, deployment result, and safety boundary are recorded.

## Programme status

| Programme | Days | Status | Verified outcome |
|---|---:|---|---|
| Foundation and inbound voice | 1–24 | Complete | Multi-tenant FastAPI/Next.js product, inbound voice path, dashboard modules, initial campaign domain. |
| Durable execution foundation | 25–28 | Complete | Job ledger, outbox, atomic claim/lease, retry runtime, job-health read model, safe staging. |
| Controlled campaign cutover | 29–30 | Complete | Feature-gated worker, provider-operation idempotency, reconciliation foundation, tenant policy and auditable cancellation. |
| Provider lifecycle hardening | 31–33 | Next | Signed/deduplicated callbacks, integration jobs, internal test-tenant canary. |
| Reliability and observability | 34–38 | Planned | Queue metrics, traces, dead-letter controls, alerts, resilience game days. |
| Security and tenant controls | 39–43 | Planned | RBAC, RLS audit, callback hardening, retention, security evidence. |
| Voice quality and integrations | 44–48 | Planned | Evaluation corpus, release thresholds, provider/integration contracts. |
| Pilot readiness | 49–54 | Planned | Promotion controls, load/recovery rehearsal, tenant onboarding, controlled pilot. |

## Historical foundation: Days 1–24

Days 1–24 established the backend, dashboard, tenant-aware data model, inbound voice functionality, security controls, operational modules, deployment path, and outbound campaign domain. The detailed original day-by-day worksheets are retained under `.planning/` and `.learning/` as historical learning material. The source of current engineering truth is this document together with `MEMORY.md`, `ARCHITECTURE.md`, and the latest `.learning` day guides.

## Completed durable execution: Days 25–30

| Day | Implementation | Verification and exit result |
|---:|---|---|
| 25 | Introduced `JobRun`, `JobOutbox`, `JobAttempt`, and `ProviderOperation`; campaign-target enqueue and outbox write are transactional. | Unique tenant/idempotency and atomic-enqueue tests passed; migration `003_durable_job_ledger.sql` added. |
| 26 | Added atomic job claiming, worker leases, stale-worker conditional transitions, and expired-lease recovery. | Competing claim and stale completion behavior tested. |
| 27 | Added `WorkerRuntime`, typed retry/permanent failure handling, full-jitter exponential backoff, and graceful drain signals. | Worker synthetic/retry/drain tests passed. |
| 28 | Added transactional outbox relay, tenant-safe job-health and recent-job APIs, dashboard operator panel, and safe staging. | Outbox/job health tests and staged production read verification passed; migration `004_outbox_relay_state.sql` added. |
| 29 | Added standalone campaign worker process, tenant canary filtering, dry run, provider-operation reserve/update, reconciliation, and no-redial retry behavior. | Campaign dispatch/reconciliation and kill-switch tests passed; production worker stayed disabled. |
| 30 | Added tenant policy, recipient consent/opt-out/purpose checks, timezone calling windows, daily budget, active capacity, exact deferral, immutable policy decisions, and durable cancellation. | Paused, closed-window, consent, opt-out, quota, API scoping, and audit-redaction tests passed; migration `005_campaign_policy_controls.sql` added. |

**Day 30 release evidence:** backend lint clean; **182 backend tests passing**; frontend lint/build passing with 20 routes; GitHub CI passed; Vercel deployment passed; browser dashboard rendered staged health. No real outbound call was made.

## Day 31 — Provider lifecycle and idempotent callback reconciliation

**Objective:** Make callbacks an authenticated observation of an existing provider operation, not a command to create, reassign, or retry outbound work.

| Work item | Acceptance criterion |
|---|---|
| Signed callback validation | Invalid signature/replayed timestamp creates no provider event or state mutation. |
| Provider event ledger | Stable provider event ID or conservative event fingerprint is deduplicated immutably. |
| Lifecycle transition matrix | Accepted, connected, ended, recording-ready, successful outcome, and terminal failure transitions are explicit and tested. |
| Tenant derivation | Callback tenant comes only from the stored provider operation—not a request field. |
| Duplicate/out-of-order events | Counters, queue state, and terminal jobs remain idempotent; no re-dial path exists. |
| Capacity settlement | Terminal provider result settles Day 30 active capacity exactly once. |

**Safety boundary:** production campaign worker remains disabled. Day 31 does not authorize a real provider call.

## Upcoming campaign-cutover work

| Day | Planned focus | Required proof |
|---:|---|---|
| 32 | Move Sheets retry, email summarization, recording retrieval, CRM sync, and outbound notifications into typed durable jobs. | Disable legacy in-process loops in staging without losing work. |
| 33 | Internal test-tenant worker canary or provider sandbox only. | Crash/restart and callback-delay recovery with a unique provider-operation record. |
| 34 | Job metrics: backlog, age, claims, latency, lease expiry, retries, and cancellation/dead letters. | Tenant/job-type filtered dashboard or metrics view. |
| 35 | Correlated tracing through command, outbox, job, provider operation, callback, and communication record. | One target traceable end to end without a database shell. |
| 36 | Dead-letter operator controls: inspect, annotate, cancel, replay, and audit. | Explicit replay creates a new auditable attempt only. |

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
