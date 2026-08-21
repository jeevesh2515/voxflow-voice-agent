# VoxFlow Memory / Live Status

**Purpose:** The project’s current source of truth. Update this file at the end of a material implementation, deployment, or verification session. Historical plans and early-session notes live in `.planning/` and `.learning/`; they are not current operational truth.

## Current position

**Last updated:** 2026-08-21
**Current milestone:** **Day 36 complete and production-verified — immutable redacted pilot-operational evidence, read-only preflight/hold-point APIs, same-cohort evidence admission gate, queue/callback observability, pause evidence, and no-auto-expansion governance.**
**Next implementation:** **Day 37 — Reliability SLOs, deterministic fault-injection drills, and recovery evidence.**
**Verified Day 33 runtime revision:** `0a52152` — Dial sandbox adapter, rollout audit ledger, analytics visibility, migration `007`, and signed fixture certification. The subsequent `main` commit records final delivery evidence only.

The durable campaign, observability, callback-certification, typed side-effect, pilot-readiness, and evidence-led pilot-operations programme for Days 25–36 is implemented, CI-validated, and browser-verified. Render remains blocked by its documented free-service deployment outage, so the temporary API remains `https://voxflow-voice-agent.fly.dev` and Vercel Production uses that origin. The current `main` revision is `94c46d5`, which restores the Fly configuration to an automatic-stop, automatic-wake-up **free-tier demonstration posture**. No real outbound provider call, notification, provider subscription, signing-secret configuration, provider ping, CRM webhook, Sheets write, Gmail fetch, or recording download has been performed during any milestone or verification.

## Verified delivery state

| Area | Verified state |
|---|---|
| Backend quality | `ruff check .` clean; **223 tests passing**. Day 36 adds immutable operational evidence, same-day same-cohort hold-point enforcement, queue/callback preflight signals, pause evidence, and tenant-safe read-only API coverage. |
| Frontend quality | ESLint clean; Next.js 16.3.1 production build completed with **20 routes**, including Dial Sandbox Adapter, Durable Side Effects, Controlled Pilot Readiness, and Pilot Operations Evidence dashboard panels. |
| Day 34 local scope | `SideEffectIntent`, transactional job/outbox enqueue, separate staged worker service, migration `008`, legacy Sheets/email loop removal, direct notification/CRM/worksheet/call-dispatch migration, analytics/CSV aggregation, and dashboard visibility are complete locally. |
| Day 34 release gates | Commit `9e8c809` and GitHub CI #107 passed. Render remains outage-blocked, but Fly API safe analytics verification and the Vercel Durable Side Effects panel are now verified. |
| Day 35 local scope | `PilotConfiguration`, `PilotCohortMember`, and `PilotSecurityIncident` models; migration `009`; fail-closed campaign admission; frozen scorecard; read-only pilot and rollback-preview APIs; dashboard panel; database-only rollback drill; `railway.json` temporary-host manifest. |
| Day 35 GitHub/CI | Commit [`8f14f1b`](https://github.com/jeevesh2515/voxflow-voice-agent/commit/8f14f1b3aa8608441eb8f81ac2cd90b42ee940a5) is pushed to `main`. GitHub Actions [run #108](https://github.com/jeevesh2515/voxflow-voice-agent/actions/runs/32396910278) passed `api-lint`, `api-test`, and `web-lint`. |
| Fly temporary API | Fly deployment [`1920953`](https://fly.io/apps/voxflow-voice-agent/deployments/1920953/deploy) completed successfully on `0047c93`, which includes Day 36 commit `93c5a40`. Safe health, analytics, pilot-readiness, preflight, hold-point, and both callback 503 checks passed. |
| Day 35/Vercel release gates | Vercel Production uses the Fly API origin. The live authenticated analytics page rendered all Day 33–35 staged panels and remains session-protected. |
| Day 36 local scope | `PilotOperationalEvidence` model and migration `010`; trusted-service idempotent evidence recording; same-day same-cohort hold-point gate; read-only preflight/hold-point APIs; aggregate queue/callback/side-effect observability; pause evidence; and a non-activating dashboard panel. |
| Day 36 local verification | Focused Day 35/36 tests: **18 passed**; full API suite: **223 passed** (including the datetime-safe simulator-evidence regression); API lint, frontend lint, and production build with 20 routes passed. No worker, provider, callback, or integration was enabled. |
| Day 36 GitHub CI | Day 36 code commit [`93c5a40`](https://github.com/jeevesh2515/voxflow-voice-agent/commit/93c5a409ebba5dcb3e2da39991a6d89fecf58845) passed GitHub Actions [run #32438697291](https://github.com/jeevesh2515/voxflow-voice-agent/actions/runs/32438697291): `api-lint`, `api-test`, and `web-lint`. The complete repair sequence concludes with [`94c46d5`](https://github.com/jeevesh2515/voxflow-voice-agent/commit/94c46d507b2a46ca95e6ad208c89ff76589a86c1); CI [run #32448033216](https://github.com/jeevesh2515/voxflow-voice-agent/actions/runs/32448033216) passed the same three jobs. |
| Day 36 production/API | `GET /api/health` returned **200**. Analytics returned **200** with staged dry-run side effects and zero intent/error counts. Day 35 readiness returned **200** and **BLOCKED**. Day 36 preflight returned **200**, `configured=false`, `state=blocked`, `no_auto_expansion=true`, `requires_human_hold_point=true`, zero running jobs, and zero callback anomalies; hold-point returned **200**, `state=blocked`, and `expansion_permitted=false`. Both deliberately malformed callback requests returned **503** before any provider action. |
| Day 36 Vercel/dashboard | The authenticated [analytics dashboard](https://voxflow-voice-agent.vercel.app/dashboard/analytics) rendered **Pilot Operations Evidence** with **HOLD POINT BLOCKED**, **RUNNING 0**, **CALLBACK FLAGS 0**, `Queue: 0 ready/retrying · 0 dead letters`, and **NO AUTO-EXPANSION · HUMAN HOLD POINT REQUIRED**. A free-tier simulator demonstration must warm the API immediately before connecting because idle Fly machines can stop. |
| Post-Day 36 runtime repairs | `c52fe83` corrects the frontend API origin; `6017b0d` waits for WebSocket `OPEN`; `0047c93` adds reproducible Fly configuration; `2a0151c` selects Groq model `openai/gpt-oss-20b`; `4415ac2` adds Groq reasoning controls; `039c168` degrades safely when hosted TTS is unavailable; `d5cd0ed` serializes simulator-evidence datetimes safely; and `94c46d5` restores `auto_stop_machines='stop'` / `min_machines_running=0` for the owner-mandated free-tier posture. Controlled WebSocket probes returned complete Hindi agent turns with tool actions, and `/api/llm-health` returned healthy. |
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

The temporary deployed API returned analytics with `durable_side_effects.activation_mode=staged`, `dry_run=true`, `tenant_allowed=false`, and zero intent/error counts. Its Day 35 scorecard returned `state=blocked`, `pilot_configuration_missing`, and a non-executable rollback preview. Day 36 preflight and hold-point independently returned `state=blocked`, zero running/callback-anomaly signals, and `no_auto_expansion=true` / `expansion_permitted=false`; both callback paths returned 503 before payload actions. A missing policy, pilot configuration, or evidence package is not permission to call.

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
| Temporary backend workaround | Render and Railway were both deployment-blocked; Koyeb is unavailable; Fly temporary API is live and Vercel Production uses it. | Keep Fly in automatic-stop, automatic-wake-up **free-tier demonstration mode** only. Warm `/api/health`, then use the simulator immediately; it cannot provide a continuous production availability guarantee. When Render recovers, repeat safe API/browser checks before restoring the original API origin and retiring Fly. |

## Immediate next session

1. Begin **Day 37**: add tenant-scoped reliability SLO scorecards, deterministic database-only fault drills, read-only drill-result APIs/dashboard evidence, and a recovery-plan preview; do not change activation posture.
2. Preserve the hard safety boundary: both workers disabled; campaign and side-effect dry run; empty pilot/worker/adapter allow-lists; no callback signing secret; no provider/integration action.
3. Preserve the Fly temporary backend and Vercel Production API origin only while Render remains unavailable. Retain automatic stop / automatic wake-up for the owner-mandated free-tier demonstration stage; do not add billing or configure always-on capacity.
4. On Render recovery, safely re-verify health, analytics, callback 503 responses, pilot scorecard/rollback-preview, Day 36 evidence APIs, and live Vercel panels before restoring the Render origin and retiring Fly.
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
