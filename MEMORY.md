# VoxFlow Memory / Live Status

**Purpose:** The project’s current source of truth. Update this file at the end of a material implementation, deployment, or verification session. Historical plans and early-session notes live in `.planning/` and `.learning/`; they are not current operational truth.

## Current position

**Last updated:** 2026-08-20
**Current milestone:** **Day 32 complete, deployed, and browser-verified — Provider Lifecycle and Idempotent Callback Reconciliation.**
**Next implementation:** **Day 33 — Provider Adapter Sandbox Certification and Callback Rollout.**
**Main branch:** `8f1b167` — Day 32 signed provider callback lifecycle (`b02c76f`) plus fail-closed-before-payload-validation correction (`8f1b167`).

The durable campaign and observability programme for Days 25–32 is implemented, committed, deployed, and verified. No real outbound provider call has been performed during any milestone or production verification.

## Verified delivery state

| Area | Verified state |
|---|---|
| Backend quality | `ruff check .` clean; **188 tests passing**, including the four Day 32 callback lifecycle tests. |
| Frontend quality | ESLint clean; Next.js 16.3.1 production build completed with **20 routes**. |
| CI | Day 32 implementation CI [#101](https://github.com/jeevesh2515/voxflow-voice-agent/actions/runs/32380869101) passed. Regression-correction CI **#102** for `8f1b167` also passed in 1 minute 3 seconds. |
| GitHub | `main` is synchronized at `8f1b167d906d43d3908815c551c5de7c3b13f7c2`; Day 32 is fully pushed. |
| Vercel | <https://voxflow-voice-agent.vercel.app/dashboard/analytics> loaded successfully in the authenticated browser and rendered the Day 32 Provider Lifecycle panel. |
| Render | `POST /api/provider-callbacks/events` with `{}` returned **503** and `provider_callback_not_configured`; `GET /api/analytics/overview?tenant_id=varun&days=7` returned **200** with the Day 32 `provider_lifecycle` aggregate. |
| Dashboard | Browser verification showed the tenant-local Provider Lifecycle panel with **0 events**, **0 anomalies**, and `Applied: 0 · Terminal ignored: 0`. |
| Session-free boundary | `/dashboard/campaigns` redirects to `/sign-in` without a session. |

## Durable campaign and monitoring system: completed Days 25–32

| Day | Completed scope |
|---:|---|
| 25 | Durable `JobRun`, `JobOutbox`, `JobAttempt`, and `ProviderOperation` ledger; atomic target enqueue/outbox persistence. |
| 26 | Atomic job claim with leases, stale-owner rejection, and expired-lease recovery. |
| 27 | `WorkerRuntime`, full-jitter exponential backoff, retry taxonomy, and graceful drain handling. |
| 28 | Transactional outbox relay, tenant-safe job-health/read APIs, dashboard operator panel, and staging gate. |
| 29 | Controlled standalone campaign worker, tenant canary filtering, dry run, provider-operation reconciliation, and no-redial behavior. |
| 30 | Explicit tenant policy, consent/opt-out, purpose check, timezone window, daily budget, capacity reservation, audit decisions, and terminal cancellation. |
| 31 | Tenant-safe analytics overview, KPI/trend/distribution aggregation, pull-based durable monitoring, alert classification, redacted CSV report, and dashboard reporting view. |
| 32 | Fail-closed signed callback ingress, immutable provider-event ledger, tenant-derived lookup, unknown-call quarantine, duplicate/terminal guard, job reconciliation, lifecycle aggregate, and callback anomaly alert. |

## Current production safety posture

The campaign system is intentionally operationally **implemented but non-executing** in production.

```text
DURABLE_CAMPAIGN_WORKER_ENABLED=false
PROVIDER_CALLBACK_VALIDATE_SIGNATURE=true
PROVIDER_CALLBACK_SHARED_SECRET=(intentionally unset)
activation_mode=staged
canary_allowed=false
dry_run=true
```

The deployed `GET /api/jobs/health?tenant_id=varun` response reported zero ready/running/retry/cancelled jobs and the staged rollout state. The deployed `GET /api/campaign-policies/varun` response reported `configured: false`, which is an expected fail-closed state. A missing policy is not permission to call.

## Day 30–32 invariants

1. FastAPI request handlers persist campaign intent; they do not issue a provider call inline.
2. A campaign worker requires the global kill switch and any future tenant canary gate to be explicitly enabled.
3. Policy evaluation runs before provider-operation reservation.
4. Missing/disabled policy, inactive campaign, absent/withdrawn consent, opt-out, and purpose mismatch cancel the durable target.
5. Closed window, budget exhaustion, and tenant capacity pressure defer to a durable next eligible time.
6. Each policy evaluation is stored as an immutable `CampaignPolicyDecision`.
7. One `ProviderOperation` idempotency key owns one external request; retries reconcile ambiguous/accepted operations rather than re-dial.
8. A callback resolves its tenant only from an existing stored provider operation; it never trusts callback tenant, campaign, queue, or job input.
9. Invalid, stale, unconfigured, duplicate, unknown, and late callbacks cannot create a provider request or reopen terminal campaign state. An unset callback secret returns `503` before malformed or incomplete payloads are schema-validated.
10. Analytics aggregates only persisted tenant facts and do not expose transcripts, phone numbers, raw job payloads, policy evidence, or raw callback payloads.
11. No real outbound call is allowed during local or browser verification.

## Open work and known boundaries

| Area | Current status | Next action |
|---|---|---|
| Provider-specific callback adapter | Generic normalized signed lifecycle is implemented, but no provider-specific callback registration/signature contract is certified. | Day 33 sandbox fixtures, normalizer, replay drill, and controlled adapter gate. |
| Campaign activation | Deliberately disabled. | Do not enable before internal-canary controls and Day 33 provider sandbox evidence. |
| Tenant policy data | API exists; deployed Varun policy is intentionally unconfigured. | Configure only as part of approved pilot checklist. |
| RBAC and full tenant access review | Not the Day 30 deliverable. | Future security/tenant-control phase. |
| Metrics, alerting, game days | Day 32 adds provider callback anomaly visibility; alert delivery, runbooks, and game days are not complete. | Add provider callback alert routing after Day 33 sandbox certification. |
| Live provider sandbox canary | Not authorized or executed. | Day 33 provider-specific sandbox certification only; no campaign worker activation. |

## Immediate next session

1. Capture one provider’s current sandbox callback contract and signature canonicalization from authoritative documentation.
2. Implement the provider-specific adapter that verifies and normalizes sandbox events into the Day 32 neutral callback shape.
3. Replay sandbox fixtures in original, duplicate, delayed, reordered, unknown-call, and signature-tampered sequences.
4. Add an explicit adapter rollout gate, callback verification/anomaly observability, and a tested rollback procedure.
5. Keep `DURABLE_CAMPAIGN_WORKER_ENABLED=false` and `PROVIDER_CALLBACK_SHARED_SECRET` unset in production until sandbox certification is complete.

## References

- [Architecture](ARCHITECTURE.md)
- [Product requirements](PRD.md)
- [Current roadmap](PHASES.md)
- [.learning Day 32 guide](.learning/day-32-provider-lifecycle-and-idempotent-callback-reconciliation.md)
- [.learning Day 33 guide](.learning/day-33-provider-adapter-sandbox-certification-and-callback-rollout.md)
