# VoxFlow Memory / Live Status

**Purpose:** The project’s current source of truth. Update this file at the end of a material implementation, deployment, or verification session. Historical plans and early-session notes live in `.planning/` and `.learning/`; they are not current operational truth.

## Current position

**Last updated:** 2026-08-20
**Current milestone:** **Day 34 locally complete — Typed Durable Jobs for Sheets, email scans, recording follow-up, CRM sync, notifications, and worksheet side effects. CI, deployment, and browser verification are pending.**
**Next implementation:** **Day 35 — Final controlled-pilot readiness gates for one approved tenant, a fixed cohort, explicit hours, human escalation coverage, scorecard definitions, and rollback governance.**
**Verified Day 33 runtime revision:** `0a52152` — Dial sandbox adapter, rollout audit ledger, analytics visibility, migration `007`, and signed fixture certification. The subsequent `main` commit records final delivery evidence only.

The durable campaign, observability, and callback-certification programme for Days 25–33 is implemented, committed, deployed, and verified. Day 34 durable operational side effects are implemented and locally verified pending release gates. No real outbound provider call, notification, provider subscription, signing-secret configuration, provider ping, CRM webhook, Sheets write, Gmail fetch, or recording download has been performed during any milestone or verification.

## Verified delivery state

| Area | Verified state |
|---|---|
| Backend quality | `ruff check .` clean; **204 tests passing**. Day 34 adds typed side-effect atomicity, idempotency, tenant-isolation, dry-run no-IO, retry, manual scan queueing, direct-call rejection, and aggregate-redaction coverage. |
| Frontend quality | ESLint clean; Next.js 16.3.1 production build completed with **20 routes**, including the Dial Sandbox Adapter and Durable Side Effects dashboard panels. |
| Day 34 local scope | `SideEffectIntent`, transactional job/outbox enqueue, separate staged worker service, migration `008`, legacy Sheets/email loop removal, direct notification/CRM/worksheet/call-dispatch migration, analytics/CSV aggregation, and dashboard visibility are complete locally. |
| Day 34 release gates | Pending: commit/push, GitHub CI, Render deployment, safe analytics verification, and authenticated Vercel panel verification. |
| Day 32 CI/deployment | Day 32 implementation CI [#101](https://github.com/jeevesh2515/voxflow-voice-agent/actions/runs/32380869101) and correction CI #102 passed; Render/Vercel Day 32 browser evidence remains recorded below. |
| Day 33 GitHub/CI | Commit [`0a52152`](https://github.com/jeevesh2515/voxflow-voice-agent/commit/0a5215275ff51d0b31b3bbadee825322cb30f429) is pushed to `main`. GitHub Actions [run #105](https://github.com/jeevesh2515/voxflow-voice-agent/actions/runs/32387989478) passed all `api-lint`, `api-test`, and `web-lint` jobs. |
| Day 33 Render | `POST /api/provider-callbacks/dial/events` with `{}` returned **503** and `dial_callback_adapter_disabled`. Analytics returned **200** and included `dial_sandbox_adapter` with `adapter_enabled=false`, `sandbox_mode=true`, `tenant_allowed=false`, `audit_count=0`, and empty status counts. |
| Day 33 Vercel/dashboard | Authenticated [analytics dashboard](https://voxflow-voice-agent.vercel.app/dashboard/analytics) rendered the **Dial Sandbox Adapter** panel with **STAGED**, **AUDITS 0**, **Tenant gate BLOCKED**, and **Verification failures 0**, alongside Provider Lifecycle 0 events/0 anomalies. |
| Day 32 Vercel | <https://voxflow-voice-agent.vercel.app/dashboard/analytics> loaded successfully in the authenticated browser and rendered the Day 32 Provider Lifecycle panel. |
| Day 32 Render | `POST /api/provider-callbacks/events` with `{}` returned **503** and `provider_callback_not_configured`; `GET /api/analytics/overview?tenant_id=varun&days=7` returned **200** with the Day 32 `provider_lifecycle` aggregate. |
| Session-free boundary | `/dashboard/campaigns` redirects to `/sign-in` without a session. |

## Durable campaign, monitoring, adapter-certification, and side-effect system: completed locally through Day 34

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
| 33 | Dial-specific sandbox HMAC adapter, secret-overlap support, outbound lifecycle normalization, redacted adapter-audit ledger, tenant rollout gate, tenant-safe analytics alerts, and dashboard panel. |
| 34 | Typed `SideEffectIntent` ledger and atomic intent/job/outbox writes for Sheets, email scans, CRM sync, notifications, worksheet appends, and recording retrieval; independent staged worker; legacy in-process/direct-dispatch removal; tenant-safe analytics and dashboard panel. |

## Current production safety posture

The campaign system is intentionally operationally **implemented but non-executing** in production.

```text
DURABLE_CAMPAIGN_WORKER_ENABLED=false
PROVIDER_CALLBACK_VALIDATE_SIGNATURE=true
PROVIDER_CALLBACK_SHARED_SECRET=(intentionally unset)
DIAL_CALLBACK_ADAPTER_ENABLED=false
DIAL_CALLBACK_SANDBOX_MODE=true
DIAL_CALLBACK_ALLOWED_TENANTS=(intentionally empty)
DIAL_CALLBACK_SIGNING_SECRETS=(intentionally unset)
DURABLE_SIDE_EFFECTS_WORKER_ENABLED=false
DURABLE_SIDE_EFFECTS_DRY_RUN=true
DURABLE_SIDE_EFFECTS_ALLOWED_TENANTS=(intentionally empty)
activation_mode=staged
canary_allowed=false
dry_run=true
```

The deployed `GET /api/jobs/health?tenant_id=varun` response reported zero ready/running/retry/cancelled jobs and the staged rollout state. The deployed `GET /api/campaign-policies/varun` response reported `configured: false`, which is an expected fail-closed state. A missing policy is not permission to call.

## Day 30–34 invariants

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
11. A Dial callback is authenticated at the provider edge but can apply only after a stored outbound operation resolves an explicit allow-listed tenant.
12. Disabled, non-sandbox, unconfigured, malformed, stale, or tampered Dial ingress cannot parse/persist business data or create a provider request.
13. An API request, voice tool, callback, dashboard, or FastAPI lifespan process may persist a typed side-effect intent but cannot execute Sheets, email, CRM, notification, or recording IO inline.
14. The side-effect worker is independently disabled, dry-run protected, and tenant-allow-listed; no default tenant is admitted.
15. Side-effect intent/job payloads and analytics contain only trusted references, hashes, and bounded result facts—not raw messages, phone numbers, recordings, callback data, integration payloads, or secrets.
16. No real outbound call, notification, provider subscription, provider ping, secret configuration, CRM webhook, Sheets write, Gmail fetch, or recording download is allowed during local or browser verification.

## Open work and known boundaries

| Area | Current status | Next action |
|---|---|---|
| Provider-specific callback adapter | **Day 33 verified complete.** The Dial sandbox adapter is deployed and remains disabled in production. | Keep it disabled with no signing secret/allow-list until a separately approved future sandbox subscription or canary decision. |
| Campaign activation | Deliberately disabled. | Do not enable before future internal-canary controls; Day 33 callback fixture evidence does not authorize activation. |
| Tenant policy data | API exists; deployed Varun policy is intentionally unconfigured. | Configure only as part of approved pilot checklist. |
| RBAC and full tenant access review | Not the Day 30 deliverable. | Future security/tenant-control phase. |
| Metrics, alerting, game days | Day 33 adds verification-failure and rollout-blocked aggregates; external alert delivery, incident runbooks, and game days are not complete. | Day 38 alert-routing and resilience work. |
| Live provider sandbox canary | Not authorized or executed. | Do not register a provider subscription or enable the campaign worker; Day 35 requires separate written pilot approval and runbook evidence. |
| Operational side-effect worker | Day 34 implementation complete locally; production worker remains disabled and dry-run protected. | Do not configure an allow-list or enable it until Day 35 has a written tenant approval, integration review, named operator, and rollback proof. |
| Pilot scorecard and human operations | Not yet implemented or approved. | Day 35 must freeze metric definitions/denominators, one tenant/cohort/hours, primary/backup escalation responders, callback/side-effect alert owners, and rollback command ownership. |

## Immediate next session

1. Complete Day 34 release gates: commit/push, GitHub CI, Render deployment, safe analytics checks, and authenticated Vercel Durable Side Effects panel verification.
2. Preserve both safety boundaries: `DURABLE_CAMPAIGN_WORKER_ENABLED=false`, `DURABLE_SIDE_EFFECTS_WORKER_ENABLED=false`, `DURABLE_SIDE_EFFECTS_DRY_RUN=true`, `DIAL_CALLBACK_ADAPTER_ENABLED=false`, empty worker/adapter allow-lists, no signing secret, and no provider/integration call.
3. Begin Day 35 only with a clear pilot-readiness scope: written tenant authorization, fixed consented cohort, explicit time window, named primary/backup escalation coverage, frozen completion/escalation/FCR/security scorecard, alert owners, and durable rollback drill.
4. Do not promise business KPIs or zero incidents before the controlled pilot measures them. The Day 35 deliverable must make them observable, bounded, and reversible.

## References

- [Architecture](ARCHITECTURE.md)
- [Product requirements](PRD.md)
- [Current roadmap](PHASES.md)
- [.learning Day 32 guide](.learning/day-32-provider-lifecycle-and-idempotent-callback-reconciliation.md)
- [.learning Day 33 guide](.learning/day-33-provider-adapter-sandbox-certification-and-callback-rollout.md)
- [.learning Day 34 guide](.learning/day-34-provider-callback-operational-readiness-and-canary-governance.md)
- [.learning Day 35 guide](.learning/day-35-controlled-pilot-readiness-and-operational-gates.md)
