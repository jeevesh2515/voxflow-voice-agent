# VoxFlow Delivery Phases

**Last updated:** 2026-08-20
**Current position:** Day 33 complete, deployed, and browser-verified. Day 34 typed durable jobs is next.
**Planning rule:** a milestone is complete only when its implementation, automated verification, deployment result, and safety boundary are recorded.

## Programme status

| Programme | Days | Status | Verified outcome |
|---|---:|---|---|
| Foundation and inbound voice | 1–24 | Complete | Multi-tenant FastAPI/Next.js product, inbound voice path, dashboard modules, initial campaign domain. |
| Durable execution foundation | 25–28 | Complete | Job ledger, outbox, atomic claim/lease, retry runtime, job-health read model, safe staging. |
| Controlled campaign cutover | 29–30 | Complete | Feature-gated worker, provider-operation idempotency, reconciliation foundation, tenant policy and auditable cancellation. |
| Enterprise analytics and monitoring | 31 | Complete | Tenant KPI/trend aggregates, durable health signals, redacted CSV reporting, and dashboard operator view. |
| Provider lifecycle hardening | 32 | Complete | Signed/fresh callbacks, immutable event ledger, tenant-derived reconciliation, quarantine, and lifecycle analytics. |
| Integration reliability and canary readiness | 33–38 | Day 33 complete; 34–38 planned | Dial sandbox callback certification is deployed and verified; next are typed jobs, internal test-tenant canary, traces, alert routing, dead-letter controls, and resilience game days. |
| Security and tenant controls | 39–43 | Planned | RBAC, RLS audit, callback hardening, retention, security evidence. |
| Voice quality and integrations | 44–48 | Planned | Evaluation corpus, release thresholds, provider/integration contracts. |
| Pilot readiness | 49–54 | Planned | Promotion controls, load/recovery rehearsal, tenant onboarding, controlled pilot. |

## Historical foundation: Days 1–24

Days 1–24 established the backend, dashboard, tenant-aware data model, inbound voice functionality, security controls, operational modules, deployment path, and outbound campaign domain. The detailed original day-by-day worksheets are retained under `.planning/` and `.learning/` as historical learning material. The source of current engineering truth is this document together with `MEMORY.md`, `ARCHITECTURE.md`, and the latest `.learning` day guides.

## Completed durable execution, callback certification, and observability: Days 25–33

| Day | Implementation | Verification and exit result |
|---:|---|---|
| 25 | Introduced `JobRun`, `JobOutbox`, `JobAttempt`, and `ProviderOperation`; campaign-target enqueue and outbox write are transactional. | Unique tenant/idempotency and atomic-enqueue tests passed; migration `003_durable_job_ledger.sql` added. |
| 26 | Added atomic job claiming, worker leases, stale-worker conditional transitions, and expired-lease recovery. | Competing claim and stale completion behavior tested. |
| 27 | Added `WorkerRuntime`, typed retry/permanent failure handling, full-jitter exponential backoff, and graceful drain signals. | Worker synthetic/retry/drain tests passed. |
| 28 | Added transactional outbox relay, tenant-safe job-health and recent-job APIs, dashboard operator panel, and safe staging. | Outbox/job health tests and staged production read verification passed; migration `004_outbox_relay_state.sql` added. |
| 29 | Added standalone campaign worker process, tenant canary filtering, dry run, provider-operation reserve/update, reconciliation, and no-redial retry behavior. | Campaign dispatch/reconciliation and kill-switch tests passed; production worker stayed disabled. |
| 30 | Added tenant policy, recipient consent/opt-out/purpose checks, timezone calling windows, daily budget, active capacity, exact deferral, immutable policy decisions, and durable cancellation. | Paused, closed-window, consent, opt-out, quota, API scoping, and audit-redaction tests passed; migration `005_campaign_policy_controls.sql` added. |
| 31 | Added tenant-safe operational KPI/trend aggregation, pull-based durable monitoring signals, redacted CSV enterprise reports, and a live analytics dashboard. | Tenant isolation, policy trends, lease/dead-letter alerting, CSV sensitive-data exclusion, backend lint/**184 tests**, and frontend lint/build passed. |
| 32 | Added fail-closed signed callback ingress, immutable provider events, unknown-call quarantine, duplicate/terminal ordering guards, terminal job reconciliation, and provider lifecycle analytics. | Callback signature/replay, tenant spoofing, duplicate, terminal, stale, unconfigured-before-payload-validation, quarantine, and lifecycle analytics tests passed; migration `006_provider_callback_lifecycle.sql` added. |
| 33 | Added the Dial sandbox callback adapter, raw-body HMAC verification, bounded freshness, controlled current/previous-secret overlap, outbound lifecycle normalizer, redacted adapter audit ledger, tenant application gate, analytics aggregate, and dashboard panel. | Six adapter fixture tests cover disabled fail-close, signature tamper, stale delivery, secret overlap, replay/ordering/terminal reconciliation, tenant block, and signed ping. Analytics tests prove tenant-scoped redaction. Migration `007_dial_sandbox_callback_adapter.sql` added. |

**Day 32 release evidence:** backend lint clean; **188 backend tests passing**; frontend lint/build passing with 20 routes; GitHub Actions implementation CI [#101](https://github.com/jeevesh2515/voxflow-voice-agent/actions/runs/32380869101) and follow-up correction CI #102 passed. The deployed Render callback endpoint returns `503 provider_callback_not_configured` for `{}` before schema validation, and the Vercel analytics page renders the Provider Lifecycle panel with 0 events/0 anomalies. The production campaign worker remains disabled and the callback secret is intentionally unconfigured, so no real provider callback or outbound call can mutate campaign state.

## Day 33 — Dial sandbox adapter certification (local milestone)

**Delivered locally:** The Dial route `POST /api/provider-callbacks/dial/events` is disabled by default and fails closed before parsing. When deliberately enabled in sandbox mode with a configured fixture secret, it verifies the raw-body HMAC/fresh timestamp, checks header/body event identity, normalizes only outbound `call.status_changed`/`call.ended`, acknowledges signed pings without lifecycle mutation, and routes an eligible normalized observation to Day 32. It writes only redacted audit dispositions and derives the tenant from the stored provider operation before enforcing a second allow-list.

| Work item | Local acceptance result |
|---|---|
| Provider signature adapter | Dial signature/header/envelope checks are isolated in `integrations/dial_callbacks.py`; tampered and stale events reject before normalization. |
| Event normalization | The provider body never supplies a tenant, queue, campaign, job, or recipient identity. |
| Replay and reordering drills | Exact replay creates no second lifecycle/audit record; post-terminal delayed event cannot regress the job/queue or re-dial. |
| Operator rollout gate | Adapter enablement, sandbox mode, secret presence, and stored-operation tenant allow-list must all be satisfied before application. |
| Callback observability | `provider_callback_adapter_audits` stores hash/disposition only; analytics/dashboard expose tenant-safe aggregate state and alerts. |

**Release evidence:** runtime commit [`0a52152`](https://github.com/jeevesh2515/voxflow-voice-agent/commit/0a5215275ff51d0b31b3bbadee825322cb30f429) was pushed to `main`; GitHub Actions [run #105](https://github.com/jeevesh2515/voxflow-voice-agent/actions/runs/32387989478) passed `api-lint`, `api-test`, and `web-lint`. The deployed Render Dial route returned `503 dial_callback_adapter_disabled` for `{}`, and tenant analytics returned the disabled/sandbox/zero-audit aggregate. The authenticated Vercel analytics dashboard rendered **Provider Lifecycle** 0/0 plus **Dial Sandbox Adapter** with **STAGED**, **AUDITS 0**, **BLOCKED**, and **Verification failures 0**.

**Safety boundary:** production campaign worker remains disabled. Day 33 used signed local fixtures only; it did not register a provider callback URL, configure a production secret, fire a provider ping, or authorize a real provider call. The deployed adapter remains disabled with no secret and no tenant allow-list.

## Upcoming campaign-cutover work

| Day | Planned focus | Required proof |
|---:|---|---|
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
