# VoxFlow Memory / Live Status

**Purpose:** The project’s current source of truth. Update this file at the end of a material implementation, deployment, or verification session. Historical plans and early-session notes live in `.planning/` and `.learning/`; they are not current operational truth.

## Current position

**Last updated:** 2026-08-20
**Current milestone:** **Day 30 complete — Tenant Policy Controls and Auditable Cancellation.**
**Next implementation:** **Day 31 — Provider Lifecycle and Idempotent Callback Reconciliation.**
**Main branch:** `5dfe02e` — `feat: enforce tenant campaign dispatch policies`.

The durable campaign program for Days 25–30 is implemented, tested, committed, pushed to `main`, and deployed. No real outbound provider call has been performed during these milestones.

## Verified delivery state

| Area | Verified state |
|---|---|
| Backend quality | `ruff check voxflow_api tests` clean; **182 tests passing**. |
| Frontend quality | ESLint clean; Next.js 16.3.1 production build completed with **20 routes**. |
| CI | GitHub Actions run `32329027046` passed API lint, API tests, and web lint/build. |
| GitHub | `main` is synchronized at `5dfe02e`. |
| Vercel | Current production deployment succeeded at <https://voxflow-voice-agent.vercel.app>. |
| Render | API responds at <https://voxflow-voice-agent.onrender.com>. |
| Dashboard | Authenticated campaign page rendered durable health in the browser. |
| Session-free boundary | `/dashboard/campaigns` redirects to `/sign-in` without a session. |

## Durable campaign system: completed Days 25–30

| Day | Completed scope |
|---:|---|
| 25 | Durable `JobRun`, `JobOutbox`, `JobAttempt`, and `ProviderOperation` ledger; atomic target enqueue/outbox persistence. |
| 26 | Atomic job claim with leases, stale-owner rejection, and expired-lease recovery. |
| 27 | `WorkerRuntime`, full-jitter exponential backoff, retry taxonomy, and graceful drain handling. |
| 28 | Transactional outbox relay, tenant-safe job-health/read APIs, dashboard operator panel, and staging gate. |
| 29 | Controlled standalone campaign worker, tenant canary filtering, dry run, provider-operation reconciliation, and no-redial behavior. |
| 30 | Explicit tenant policy, consent/opt-out, purpose check, timezone window, daily budget, capacity reservation, audit decisions, and terminal cancellation. |

## Current production safety posture

The campaign system is intentionally operationally **implemented but non-executing** in production.

```text
DURABLE_CAMPAIGN_WORKER_ENABLED=false
activation_mode=staged
canary_allowed=false
dry_run=true
```

The deployed `GET /api/jobs/health?tenant_id=varun` response reported zero ready/running/retry/cancelled jobs and the staged rollout state. The deployed `GET /api/campaign-policies/varun` response reported `configured: false`, which is an expected fail-closed state. A missing policy is not permission to call.

## Day 30 invariants

1. FastAPI request handlers persist campaign intent; they do not issue a provider call inline.
2. A campaign worker requires the global kill switch and any future tenant canary gate to be explicitly enabled.
3. Policy evaluation runs before provider-operation reservation.
4. Missing/disabled policy, inactive campaign, absent/withdrawn consent, opt-out, and purpose mismatch cancel the durable target.
5. Closed window, budget exhaustion, and tenant capacity pressure defer to a durable next eligible time.
6. Each policy evaluation is stored as an immutable `CampaignPolicyDecision`.
7. One `ProviderOperation` idempotency key owns one external request; retries reconcile ambiguous/accepted operations rather than re-dial.
8. No real outbound call is allowed during local or browser verification.

## Open work and known boundaries

| Area | Current status | Next action |
|---|---|---|
| Provider callback lifecycle | Day 29 reconciliation foundation exists, but signed event-level accepted/connected/ended/outcome contract is not complete. | Day 31. |
| Campaign activation | Deliberately disabled. | Do not enable before internal-canary controls and Day 31 evidence. |
| Tenant policy data | API exists; deployed Varun policy is intentionally unconfigured. | Configure only as part of approved pilot checklist. |
| RBAC and full tenant access review | Not the Day 30 deliverable. | Future security/tenant-control phase. |
| Metrics, alerting, game days | Not complete. | Reliability phase after campaign cutover. |
| Live provider sandbox canary | Not authorized or executed. | Future approved internal Day 33-style checkpoint. |

## Immediate next session

1. Implement signed provider callback/event ingestion with a durable event deduplication record.
2. Define and test legal provider lifecycle transitions: request accepted, connected, ended, recording ready, business outcome, terminal failure.
3. Prove duplicate and out-of-order callback behavior does not reopen jobs, double-increment counters, or create a new provider request.
4. Preserve Day 30 policy and capacity evidence; callbacks may update an existing provider operation but must not bypass policy or cause re-dial.
5. Keep `DURABLE_CAMPAIGN_WORKER_ENABLED=false` in production until the separate canary approval gate is complete.

## References

- [Architecture](ARCHITECTURE.md)
- [Product requirements](PRD.md)
- [Current roadmap](PHASES.md)
- Day 30 delivery evidence is summarized in this file and the Day 30 learning guide.
- [.learning Day 30 guide](.learning/day-30-tenant-policy-controls-and-auditable-cancellation.md)
