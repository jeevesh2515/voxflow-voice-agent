# VoxFlow Delivery Phases

**Last updated:** 2026-08-20
**Current position:** Day 35 controlled-pilot readiness is source-complete and locally verified. Day 34 Render deployment verification remains blocked by the documented provider outage; Day 35 deployed verification will use the staged temporary backend path. Day 36 is evidence-led pilot operations, not automatic pilot activation or expansion.
**Planning rule:** a milestone is complete only when its implementation, automated verification, deployment result, and safety boundary are recorded.

## Programme status

| Programme | Days | Status | Verified outcome |
|---|---:|---|---|
| Foundation and inbound voice | 1–24 | Complete | Multi-tenant FastAPI/Next.js product, inbound voice path, dashboard modules, initial campaign domain. |
| Durable execution foundation | 25–28 | Complete | Job ledger, outbox, atomic claim/lease, retry runtime, job-health read model, safe staging. |
| Controlled campaign cutover | 29–30 | Complete | Feature-gated worker, provider-operation idempotency, reconciliation foundation, tenant policy and auditable cancellation. |
| Enterprise analytics and monitoring | 31 | Complete | Tenant KPI/trend aggregates, durable health signals, redacted CSV reporting, and dashboard operator view. |
| Provider lifecycle hardening | 32 | Complete | Signed/fresh callbacks, immutable event ledger, tenant-derived reconciliation, quarantine, and lifecycle analytics. |
| Integration reliability and pilot readiness | 33–35 | Source-complete; deployed verification pending temporary backend | Dial callback certification, typed durable side-effect jobs, and Day 35 fail-closed pilot admission establish final pilot-readiness controls. No worker, callback secret, or provider integration is enabled. |
| Post-pilot observability and resilience | 36–38 | Planned | Correlated tracing, dead-letter operator controls, alert routing, and resilience game-day evidence follow only after the pilot-readiness decision. |
| Security and tenant controls | 39–43 | Planned | RBAC, RLS audit, callback hardening, retention, security evidence. |
| Voice quality and integrations | 44–48 | Planned | Evaluation corpus, release thresholds, provider/integration contracts. |
| Pilot readiness | 49–54 | Planned | Promotion controls, load/recovery rehearsal, tenant onboarding, controlled pilot. |

## Historical foundation: Days 1–24

Days 1–24 established the backend, dashboard, tenant-aware data model, inbound voice functionality, security controls, operational modules, deployment path, and outbound campaign domain. The detailed original day-by-day worksheets are retained under `.planning/` and `.learning/` as historical learning material. The source of current engineering truth is this document together with `MEMORY.md`, `ARCHITECTURE.md`, and the latest `.learning` day guides.

## Completed durable execution, callback certification, typed side effects, and controlled-pilot readiness: Days 25–35

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
| 34 | Added typed `SideEffectIntent` ownership for Sheets, email scans, CRM sync, notifications, worksheet appends, and recording follow-up; atomically coupled intent/job/outbox writes; independent gated worker; legacy process-loop/direct-dispatch removal; redacted analytics and dashboard panel. | Atomicity, idempotency, dry-run no-IO, tenant isolation, retry classification, manual email queueing, direct-call rejection, analytics/CSV redaction, and legacy-flow tests pass. Migration `008_typed_durable_side_effect_jobs.sql` added. |
| 35 | Added fail-closed pilot tenant admission, `PilotConfiguration`, hashed `PilotCohortMember` records, a confirmed-security-incident count, frozen scorecard formulas, read-only pilot and rollback-preview APIs, dashboard evidence panel, and database-only rollback drill. | 11 focused Day 35 tests plus full backend **215-test** suite passed; API lint and frontend lint/build passed. Migration `009_controlled_pilot_readiness.sql` and `railway.json` temporary-host manifest added. |

**Day 32 release evidence:** backend lint clean; **188 backend tests passing**; frontend lint/build passing with 20 routes; GitHub Actions implementation CI [#101](https://github.com/jeevesh2515/voxflow-voice-agent/actions/runs/32380869101) and follow-up correction CI #102 passed. The deployed Render callback endpoint returns `503 provider_callback_not_configured` for `{}` before schema validation, and the Vercel analytics page renders the Provider Lifecycle panel with 0 events/0 anomalies. The production campaign worker remains disabled and the callback secret is intentionally unconfigured, so no real provider callback or outbound call can mutate campaign state.

## Day 33 — Dial sandbox adapter certification (verified release)

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

## Day 34 — Typed durable operational side-effect jobs (local milestone)

**Delivered locally:** Day 34 replaces the remaining API-process Sheets retry/email-scheduling ownership and direct side-effect tool calls with an append-only `side_effect_intents` ledger and existing durable job/outbox infrastructure. Each type carries a trusted aggregate reference and tenant idempotency key; no raw external payload, phone number, message body, recording bytes, callback material, or secret is stored in the intent/job payload. The new side-effect worker is distinct from the campaign worker and cannot be built without `DURABLE_SIDE_EFFECTS_WORKER_ENABLED=true` plus an explicit tenant allow-list.

| Work item | Local acceptance result |
|---|---|
| Transactional typed intent | Trusted business/audit state, `SideEffectIntent`, `JobRun`, and `JobOutbox` commit together; repeat enqueue returns the same intent/job. |
| Legacy ownership removal | FastAPI no longer starts the Sheets retry or email scan loops; the manual email route queues a durable job. |
| Direct-dispatch removal | Voice/API notification and CRM paths persist durable intent; direct outbound-call tool rejects and legacy webhook dispatcher is a safety no-op. |
| Worker safety | Disabled worker cannot claim; dry-run worker records evidence without integration IO; retryable vs permanent outcomes remain bounded. |
| Operator evidence | Tenant-safe analytics/CSV/dashboard expose activation mode, gates, intent/pending/error totals, and aggregate distributions only. |

**Pending release evidence:** Day 34 commit `9e8c809` and CI #107 passed, and the Vercel frontend revision is live. Render free-service builds/deploys/spin-up remain blocked by the official Google Cloud upstream incident. Production configuration remains staged: campaign and side-effect workers disabled, side-effect dry-run true, empty tenant allow-lists, disabled Dial adapter, and no generic callback secret.

## Day 35 — Final controlled-pilot readiness gate (source-complete)

Day 35 implements the measurable, reversible readiness package without promising business outcomes or activating a tenant. The production-default policy gate requires an explicit environment tenant approval plus an approved, unexpired pilot record containing hashed reviewed cohort membership, named primary/backup escalation coverage, micro-capacity, and a frozen metric-contract version. The scorecard reports completion, escalation, FCR, and confirmed security incidents with fixed denominators/exclusions; rates are `null` until data exists. The read-only APIs have no activation route, and the rollback drill refuses to run if a worker is enabled or a scoped job has an active lease. A real pilot remains blocked pending human-owned authorization and temporary-backend deployment verification.

## Post-pilot observability and resilience work

| Day | Planned focus | Required proof |
|---:|---|---|
| 35 | Final controlled-pilot readiness: one approved tenant, fixed consented supplier cohort, explicit operating hours, human escalation coverage, pilot scorecard, callback/side-effect alert ownership, and rollback governance. | **Source-complete.** Fail-closed admission, frozen metrics, read-only scorecard, and zero-provider-call rollback drill pass. The signed human operating package and deployed verification remain required. |
| 36 | Evidence-led pilot operations: preflight, hold-point scorecard review, callback/queue observability, pause/rollback evidence, and no-auto-expansion discipline. | An operator can produce one redacted, tenant-scoped evidence packet for every approved window and account for every claim, callback, escalation, and rollback decision. |
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
