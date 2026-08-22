# VoxFlow Memory / Live Status

**Purpose:** The project’s current source of truth. Update this file at the end of a material implementation, deployment, or verification session. Historical plans and early-session notes live in `.planning/` and `.learning/`; they are not current operational truth. Detailed day-by-day implementation tracking is catalogued in [`DAY_TRACKER.md`](DAY_TRACKER.md).

## Current position

**Last updated:** 2026-08-22  
**Current milestone:** **Phase 9 Infrastructure, Resilience & UI Overhaul complete.** Complete Oracle Cloud Always-Free ARM VM deployment architecture with Caddy auto-TLS, Next.js 16 standalone multi-arch containerization, LLM resilience fallback (Hindi/English), 16 redesigned dashboard views, **266 passing backend tests**, and **23 compiled frontend routes**.  
**Next implementation:** **Day 38 — Reliability SLOs, deterministic fault-injection drills, alert routing, and recovery evidence.**  
**Master Day-Wise Tracker:** See [`DAY_TRACKER.md`](DAY_TRACKER.md) for full day-by-day logs from Day 1 to current.

The durable campaign, observability, callback-certification, typed side-effect, pilot-readiness, and evidence-led pilot-operations programme for Days 25–36 is implemented, CI-validated, and browser-verified. The codebase includes a complete production deployment configuration for an Always-Free Oracle ARM VM running Docker + Caddy (`deploy/ORACLE_DEPLOY.md`), Render API backend, and Vercel Next.js edge frontend. No real outbound provider call, notification, provider subscription, signing-secret configuration, provider ping, CRM webhook, Sheets write, Gmail fetch, or recording download has been performed during any milestone or verification.

## Verified delivery state

| Area | Verified state |
|---|---|
| Backend quality | `ruff check .` clean; **266 tests passing** (`pytest tests/ -q` in 86.5s). Comprehensive coverage across DB models, agents, tools, workers, callbacks, resilience fallbacks, and multi-tenant security. |
| Frontend quality | ESLint clean; Next.js 16.3.1 production build completed with **23 compiled routes** (Turbopack, 0 errors), including full dark/light theme redesign, WCAG AA accessibility, and zero layout shift. |
| Oracle VM Deployment | Documented and configured in `deploy/ORACLE_DEPLOY.md`, `deploy/Caddyfile`, `deploy/docker-compose.prod.yml`, with automated helper scripts (`deploy/diagnose-api.sh`, `deploy/sync-vm.sh`, `deploy/verify-vm.sh`, `scripts/preflight.sh`). |
| LLM Resilience | Agent runner includes non-blocking fallback on LLM unavailability (`apps/api/voxflow_api/agent/runner.py`) and bounded retry-after with configurable max wait cap (`apps/api/voxflow_api/llm/groq.py`). Covered by `tests/test_llm_resilience.py`. |
| Day 34 local scope | `SideEffectIntent`, transactional job/outbox enqueue, separate staged worker service, migration `008`, legacy Sheets/email loop removal, direct notification/CRM/worksheet/call-dispatch migration, analytics/CSV aggregation, and dashboard visibility are complete locally. |
| Day 35 local scope | `PilotConfiguration`, `PilotCohortMember`, and `PilotSecurityIncident` models; migration `009`; fail-closed campaign admission; frozen scorecard; read-only pilot and rollback-preview APIs; dashboard panel; database-only rollback drill; `railway.json` temporary-host manifest. |
| Day 36 local scope | `PilotOperationalEvidence` model and migration `010`; trusted-service idempotent evidence recording; same-day same-cohort hold-point gate; read-only preflight/hold-point APIs; aggregate queue/callback/side-effect observability; pause evidence; and a non-activating dashboard panel. |
| Vercel Production | All public routes (`/`, `/about`, `/pricing`, `/sign-in`, `/sign-up`) return HTTP 200; all 13 dashboard routes return HTTP 307 redirect when unauthenticated. |

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
| 35 | `PilotConfiguration`, hashed fixed cohort ledger, pilot expiry/capacity/primary-backup coverage contract, fail-closed environment and policy gate, frozen scorecard definitions, confirmed security-incident count, read-only readiness/rollback APIs, dashboard panel, and a zero-provider-call database rollback drill. |
| 36 | `PilotOperationalEvidence` ledger, migration `010`, default-on same-cohort evidence gate, aggregate-only preflight/hold-point scorecards, trusted-service pause evidence, queue/callback/side-effect reliability visibility, no-auto-expansion contract, read-only routes, and dashboard panel. |

## Current production safety posture

The campaign system is intentionally operationally **implemented but non-executing** in production.

```text
DURABLE_CAMPAIGN_WORKER_ENABLED=false
PILOT_READINESS_ENFORCED=true
PILOT_READINESS_APPROVED_TENANTS=(intentionally empty)
PILOT_OPERATIONS_EVIDENCE_ENFORCED=true
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

The active Render API returned analytics with `durable_side_effects.activation_mode=staged`, `dry_run=true`, `tenant_allowed=false`, and zero intent/error counts. Its Day 35 scorecard returned `state=blocked`, `pilot_configuration_missing`, and a non-executable rollback preview. Day 36 preflight and hold-point independently returned `state=blocked`, zero running/callback-anomaly signals, and `no_auto_expansion=true` / `expansion_permitted=false`; both callback paths remain fail-closed before payload actions. A missing policy, pilot configuration, or evidence package is not permission to call.

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
17. When pilot readiness is enforced, a target requires both a named approved tenant in the environment and an approved, unexpired configuration with reviewed cohort membership, named escalation coverage, micro-capacity, and a frozen metric version.
18. Pilot readiness and rollback HTTP APIs are read-only. The database-only rollback drill refuses to proceed while a campaign worker is enabled or any scoped claim is active.
19. When Day 36 evidence enforcement is enabled, Day 35 approval still cannot admit a target without fresh current-day `continue_same_cohort` evidence for the exact pilot version. Pause, stale, missing, or version-mismatched evidence fails closed; automatic cohort expansion is never permitted.
20. Day 36 preflight and hold-point APIs expose aggregate queue, callback, side-effect, and evidence state only. They have no write route and cannot start, pause, expand, roll back, or contact an external system.

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
| Pilot scorecard and human operations | Day 35 implementation complete; production remains intentionally blocked with no real named cohort or approver record. | Obtain written one-tenant authority, consent-evidence references, E.164 cohort through the protected data steward, named primary/backup responders, hours, expiry, and go/no-go owner before any future activation decision. |
| Evidence-led pilot operations | **Day 36 complete and production-verified.** The production tenant remains blocked with no configuration or evidence record. | Preserve no-auto-expansion and empty allow-lists. Day 37 adds only reliability SLOs, deterministic drills, and recovery evidence. |
| Temporary backend workaround | **Resolved.** Render Free is active and Vercel Production uses it for both REST and WebSocket traffic. Fly remains stopped as a rollback/reference artifact only. | Warm Render `GET /api/health`, then promptly use the Vercel Phone Simulator with a text-only prompt. Do not treat a free sleeping service as a continuous production availability guarantee; do not deploy Fly with paid or always-on capacity. |

## Immediate next session

1. Begin **Day 37**: add tenant-scoped reliability SLO scorecards, deterministic database-only fault drills, read-only drill-result APIs/dashboard evidence, and a recovery-plan preview; do not change activation posture.
2. Preserve the hard safety boundary: both workers disabled; campaign and side-effect dry run; empty pilot/worker/adapter allow-lists; no callback signing secret; no provider/integration action.
3. Preserve Render’s Free Web Service posture: use **Prepare Simulator** (or warm `/api/health`) before a browser-only session, keep both Vercel origins aligned to Render, and do not add billing or configure always-on capacity.
4. Keep Fly stopped unless a future owner-approved rollback is required; if a backend origin changes, safely re-verify health, analytics, callback 503 responses, pilot scorecard/rollback-preview, Day 36 evidence APIs, and live Vercel panels first.
5. Collect the human-owned operating package before any go/no-go: written tenant authorization, consent evidence, a fixed E.164 cohort processed into hashes, explicit hours/expiry, named primary/backup coverage, alert owners, frozen metric approval, and a rollback owner.
6. Do not promise business KPIs or zero incidents before the controlled pilot measures them. Days 35–37 make them observable, bounded, reviewable, and reversible.

## References

- [Architecture](ARCHITECTURE.md)
- [Product requirements](PRD.md)
- [Current roadmap](PHASES.md)
- [.learning Day 32 guide](.learning/day-32-provider-lifecycle-and-idempotent-callback-reconciliation.md)
- [.learning Day 33 guide](.learning/day-33-provider-adapter-sandbox-certification-and-callback-rollout.md)
- [.learning Day 34 guide](.learning/day-34-provider-callback-operational-readiness-and-canary-governance.md)
- [.learning Day 35 guide](.learning/day-35-controlled-pilot-readiness-and-operational-gates.md)
