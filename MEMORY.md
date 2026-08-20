# VoxFlow Memory / Live Status

**Purpose:** The project’s current source of truth. Update this file at the end of a material implementation, deployment, or verification session. Historical plans and early-session notes live in `.planning/` and `.learning/`; they are not current operational truth.

## Current position

**Last updated:** 2026-08-20
**Current milestone:** **Day 33 implemented and locally verified — Dial Sandbox Callback Adapter Certification and Controlled Rollout Gate.**
**Release state:** Commit, GitHub CI, Render deployment, and live Vercel/browser evidence are still required before Day 33 is release-complete.
**Next implementation:** **Day 34 — Typed Durable Jobs for Sheets, email, recording, CRM, and notification side effects.**
**Verified Day 32 runtime revision:** `8f1b167` — signed provider callback lifecycle (`b02c76f`) plus fail-closed-before-payload-validation correction (`8f1b167`). The subsequent `main` commits record final deployment evidence only.

The durable campaign, observability, and callback-certification programme for Days 25–33 is implemented locally. No real outbound provider call, provider subscription, signing-secret configuration, or provider ping has been performed during any milestone or verification.

## Verified delivery state

| Area | Verified state |
|---|---|
| Backend quality | `ruff check .` clean; **195 tests passing**. Day 33 adds six signed Dial adapter fixture tests plus tenant-safe adapter analytics/redaction coverage. |
| Frontend quality | ESLint clean; Next.js 16.3.1 production build completed with **20 routes**, including the Dial Sandbox Adapter dashboard panel. |
| Day 32 CI/deployment | Day 32 implementation CI [#101](https://github.com/jeevesh2515/voxflow-voice-agent/actions/runs/32380869101) and correction CI #102 passed; Render/Vercel Day 32 browser evidence remains recorded below. |
| Day 33 GitHub/CI | **Pending:** commit Day 33, push to `main`, and record the triggered CI run. |
| Day 33 Render | **Pending:** confirm migration/startup and safe `503 dial_callback_adapter_disabled` result for `{}`. |
| Day 33 Vercel/dashboard | **Pending:** confirm deployment and authenticated browser rendering of the Dial Sandbox Adapter panel in **STAGED** / **BLOCKED** state. |
| Day 32 Vercel | <https://voxflow-voice-agent.vercel.app/dashboard/analytics> loaded successfully in the authenticated browser and rendered the Day 32 Provider Lifecycle panel. |
| Day 32 Render | `POST /api/provider-callbacks/events` with `{}` returned **503** and `provider_callback_not_configured`; `GET /api/analytics/overview?tenant_id=varun&days=7` returned **200** with the Day 32 `provider_lifecycle` aggregate. |
| Session-free boundary | `/dashboard/campaigns` redirects to `/sign-in` without a session. |

## Durable campaign, monitoring, and adapter-certification system: completed locally through Day 33

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
activation_mode=staged
canary_allowed=false
dry_run=true
```

The deployed `GET /api/jobs/health?tenant_id=varun` response reported zero ready/running/retry/cancelled jobs and the staged rollout state. The deployed `GET /api/campaign-policies/varun` response reported `configured: false`, which is an expected fail-closed state. A missing policy is not permission to call.

## Day 30–33 invariants

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
13. No real outbound call, provider subscription, provider ping, or secret configuration is allowed during local or browser verification.

## Open work and known boundaries

| Area | Current status | Next action |
|---|---|---|
| Provider-specific callback adapter | **Day 33 locally complete.** The Dial sandbox adapter is implemented and remains disabled in production pending release verification. | Push/CI/deploy, verify production 503, analytics aggregate, and Vercel panel; do not configure a secret or subscription. |
| Campaign activation | Deliberately disabled. | Do not enable before future internal-canary controls; Day 33 callback fixture evidence does not authorize activation. |
| Tenant policy data | API exists; deployed Varun policy is intentionally unconfigured. | Configure only as part of approved pilot checklist. |
| RBAC and full tenant access review | Not the Day 30 deliverable. | Future security/tenant-control phase. |
| Metrics, alerting, game days | Day 33 adds verification-failure and rollout-blocked aggregates; external alert delivery, incident runbooks, and game days are not complete. | Day 38 alert-routing and resilience work. |
| Live provider sandbox canary | Not authorized or executed. | Do not register a provider subscription or enable the worker; a later internal-canary phase must provide separate approval. |

## Immediate next session

1. Inspect the Day 33 diff and create the implementation commit on `main`.
2. Push the commit and record the GitHub Actions API lint, API test, and web lint/build results.
3. Confirm Render receives the migration/model and that `POST /api/provider-callbacks/dial/events` with `{}` returns `503 dial_callback_adapter_disabled`.
4. Confirm the analytics overview includes `dial_sandbox_adapter` with disabled/sandbox/empty audit state.
5. Verify the Vercel analytics dashboard in the authenticated browser shows Provider Lifecycle and Dial Sandbox Adapter panels in the safe default state.
6. Keep `DURABLE_CAMPAIGN_WORKER_ENABLED=false`, `DIAL_CALLBACK_ADAPTER_ENABLED=false`, and all provider callback secrets unset. Begin Day 34 only after release evidence is recorded.

## References

- [Architecture](ARCHITECTURE.md)
- [Product requirements](PRD.md)
- [Current roadmap](PHASES.md)
- [.learning Day 32 guide](.learning/day-32-provider-lifecycle-and-idempotent-callback-reconciliation.md)
- [.learning Day 33 guide](.learning/day-33-provider-adapter-sandbox-certification-and-callback-rollout.md)
- [.learning Day 34 guide](.learning/day-34-provider-callback-operational-readiness-and-canary-governance.md)
