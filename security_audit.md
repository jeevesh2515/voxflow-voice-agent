# VoxFlow Security and Safety Audit

**Last updated:** 2026-08-20
**Scope:** Current repository controls through Day 34.
**Status:** Inbound/dashboard deployment is operational; outbound campaign execution and operational side-effect execution are intentionally safe-staged and are **not approved for general live activation**.

## 1. Security posture summary

VoxFlow applies layered controls to tenant-aware voice and campaign operations. Traditional authentication, tenant scoping, signed inbound telephony handling, secret isolation, and rate controls protect the existing application surface. Days 25–30 add a distinct safety layer for outbound side effects: durable intent, leases, provider-operation idempotency, global worker gating, tenant policy, recipient permission, quota/capacity controls, and immutable policy evidence. Day 32 adds a fail-closed signed callback ingress, immutable provider-event evidence, terminal-state guards, and unknown-call quarantine. Day 34 extends the durable boundary to application-side Sheets, email, CRM, notification, worksheet, and recording work through typed intent rows and a separately gated worker.

> The absence of a global worker enablement, tenant policy, recipient consent, or approved canary is a deliberate prohibition on outbound provider action—not a degraded mode that can fall open.

## 2. Authentication and tenant isolation

| Control | Status | Notes |
|---|---|---|
| Dashboard authentication | Implemented | Protected dashboard routes redirect session-free requests to sign-in. |
| Tenant-aware API access | Implemented | Campaign, queue, job-health, job list, policy, preference, and audit reads use tenant scoping. |
| Application tenant filters | Required | Every business/job/policy query must be filtered by owning tenant. |
| Database RLS | Production requirement | Maintain PostgreSQL RLS as a second boundary where the deployment access model supports it. |
| Twilio webhook validation | Implemented for inbound voice | Incoming telephony webhook signature validation remains required. |
| Provider callback trust | Implemented normalized ingress | Fresh HMAC/timestamp validation, tenant-derived operation lookup, immutable event deduplication, terminal guards, and quarantine are implemented; provider-specific adapter certification remains pending. |

## 3. Campaign side-effect controls

| Control | Status | Security/safety effect |
|---|---|---|
| API request vs. provider separation | Implemented | Campaign routes persist intent; no inline provider call. |
| Transactional outbox | Implemented | Domain change and future durable work commit together. |
| Lease-protected worker transition | Implemented | A stale worker cannot complete/cancel/retry a job after losing lease ownership. |
| Provider operation idempotency | Implemented | One stable tenant/idempotency key owns one external provider request. |
| Reconciliation/no-redial | Implemented foundation | Ambiguous/accepted provider state is reconciled rather than blindly re-dialed. |
| Global campaign-worker gate | Enforced in production | `DURABLE_CAMPAIGN_WORKER_ENABLED=false`. |
| Tenant canary restriction | Implemented | No deployed tenant is currently admitted. |
| Dry-run path | Implemented | Provider-free worker execution path supports controlled evidence. |
| Explicit tenant policy | Implemented | Missing/disabled/invalid policy cancels the target. |
| Consent and opt-out | Implemented | Missing consent, withdrawn consent, purpose mismatch, or opt-out blocks provider access. |
| Time/budget/capacity | Implemented | Tenant-local calling window, daily limit, and active-capacity reservation are enforced. |
| Immutable policy audit | Implemented | Each allowed/deferred/cancelled evaluation is recorded. |
| Signed callback ingress | Implemented, fail closed | Missing callback secret returns `503`; invalid/stale signature is rejected before persistence. |
| Immutable provider events | Implemented | `(provider, provider_event_id)` is unique; exact replay creates no second mutation. |
| Tenant-derived callback ownership | Implemented | Callback body cannot select tenant, campaign, queue, or job; stored provider operation owns the lookup. |
| Unknown callback quarantine | Implemented | Trusted but unmatched callback is recorded without a tenant relationship or operational state mutation. |
| Terminal lifecycle guard | Implemented | Late events are marked but cannot reopen a terminal operation, job, queue, or capacity result. |
| Typed side-effect intent | Implemented | A business/audit row, `SideEffectIntent`, `JobRun`, and `JobOutbox` are persisted atomically; job payloads carry an opaque intent ID only. |
| API/lifespan external-IO separation | Implemented | FastAPI no longer starts a Sheets retry or email scan loop; voice/API tools do not invoke Twilio, Dial, Sheets, or CRM webhooks inline. |
| Separate side-effect worker gate | Enforced in production | `DURABLE_SIDE_EFFECTS_WORKER_ENABLED=false`; no API service process claims operational integration jobs. |
| Side-effect dry-run | Enforced in production | `DURABLE_SIDE_EFFECTS_DRY_RUN=true`; an admitted future worker records dry-run evidence instead of integration IO. |
| Side-effect tenant admission | Enforced in production | Empty `DURABLE_SIDE_EFFECTS_ALLOWED_TENANTS` prevents any tenant worker claim. |
| Side-effect result redaction | Implemented | Intent rows store trusted aggregate references, hashes, bounded status/result codes, and no raw messages, recordings, callback bodies, signatures, or credentials. |

## 4. Input and data controls

| Surface | Control | Notes |
|---|---|---|
| Campaign target phone | E.164-style `+` validation | Invalid recipient number is a permanent non-provider failure. |
| Tenant policy | Valid IANA timezone, 24-hour window syntax, positive daily/capacity limits | Invalid policy fails closed. |
| Recipient preference | Tenant + recipient unique record with consent, purpose, opt-out, and source | A missing preference is not consent. |
| Policy audit read | Redacted operator response | Raw evidence JSON is not returned by the campaign policy-decision endpoint. |
| Provider callbacks | Signature/timestamp, payload bounds, typed normalized fields, and event-ID deduplication | Raw callback payload is not persisted; secret and provider-specific verification remain configuration/adapter concerns. |
| Durable side-effect intent | Typed allow-list, trusted aggregate ID, tenant idempotency, payload hash, bounded outcome code | Raw email/message/body, phone number, recording bytes, CRM webhook payload, signature, and provider secret are excluded from the intent/job ledger and analytics export. |
| SQL | SQLAlchemy parameterized queries | Raw interpolated SQL is prohibited. |

## 5. Secrets and deployment configuration

| Requirement | Status |
|---|---|
| `.env` and local environment files excluded from Git | Required and verified by repository ignore rules. |
| Provider/LLM/database credentials stored in deployment secret managers | Required. |
| Frontend uses only public configuration values | Required; no service-role key in browser environment. |
| Render campaign global flag remains false | Required until approved canary. |
| Provider callback signature validation remains true | Required. An absent callback secret must keep ingress fail closed until sandbox certification. |
| Canary tenant list remains empty/unapproved | Required until approved canary. |
| Render side-effect worker flag remains false | Required until the Day 35 controlled-pilot approval. |
| Side-effect dry-run remains true and allow-list empty | Required until a tenant-specific operational authorization has passed every preflight gate. |
| Learning journals contain no credentials | Required; `.learning/` is local and gitignored. |

## 6. Network and browser boundary

| Control | Current expectation |
|---|---|
| API CORS | Restrict to local development and approved Vercel origins. |
| Public frontend | Landing/about/pricing are public. |
| Dashboard | Session-free request must redirect to sign-in. |
| Inbound voice transport | Use HTTPS/WSS and provider signature validation. |
| Outbound campaign verification | Never press launch or enable a worker during ordinary deployment checks. |
| Operational-side-effect verification | Never send a notification, CRM webhook, Sheets write, Gmail fetch, or recording download during ordinary deployment checks. |

## 7. Known gaps and required next controls

| Gap | Risk | Required next action |
|---|---|---|
| Provider-specific callback adapter certification | **Day 33 local implementation complete.** An uncontrolled live subscription would still risk an unintended callback rollout. | Keep `DIAL_CALLBACK_ADAPTER_ENABLED=false` in production. The Dial adapter now verifies raw-body HMAC/freshness, normalizes outbound events only, audits redacted dispositions, and requires a stored-operation tenant allow-list before application. |
| RBAC for policy/replay/config mutation | Broad access could alter policy or worker configuration. | Add platform/tenant admin/operator/read-only authorization matrix. |
| Callback and side-effect alert routing/runbooks | Day 34 adds tenant-safe side-effect error/staged aggregates, but external alert routing, named incident owners, and formal drills are not yet implemented. | Day 35 must define the pilot roster, scorecard, callback/side-effect alert owners, response windows, and rollback drill. |
| Controlled-pilot authorization | Live provider and integration behavior is intentionally not verified. | Day 35 must require one approved tenant, fixed consented cohort, explicit operating hours, human escalation coverage, metric definitions, and a written go/no-go decision before a micro-cohort can be authorized. |
| Full security-header coverage | API response headers are not yet uniformly hardened. | Add/test a FastAPI security-header policy in later hardening work. |

## 8. Verification commands

```bash
# Backend quality
cd apps/api
.venv/bin/ruff check voxflow_api tests
.venv/bin/pytest -q

# Frontend quality
cd ../..
npm run lint --workspace=apps/web
npm run build --workspace=apps/web

# Safe deployment checks
curl -fsS https://voxflow-voice-agent.onrender.com/api/health
curl -fsS 'https://voxflow-voice-agent.onrender.com/api/jobs/health?tenant_id=varun'
curl -fsS https://voxflow-voice-agent.onrender.com/api/campaign-policies/varun
curl -sS -o /dev/null -w '%{http_code}\n' -X POST https://voxflow-voice-agent.onrender.com/api/provider-callbacks/events -H 'Content-Type: application/json' -d '{}'
curl -sS -o /dev/null -w '%{http_code}\n' -X POST https://voxflow-voice-agent.onrender.com/api/provider-callbacks/dial/events -H 'Content-Type: application/json' -d '{}'
curl -fsS 'https://voxflow-voice-agent.onrender.com/api/analytics/overview?tenant_id=varun&days=7'
# Confirm the delivered aggregate includes durable_side_effects with staged mode;
# do not invoke an endpoint that creates a side-effect intent or external request.
curl -I https://voxflow-voice-agent.vercel.app/dashboard/analytics
```

Expected Day 34 live result is staged rollout with the campaign worker and side-effect worker disabled, normalized callback ingress returning `503` while its secret is intentionally absent, and Dial sandbox ingress returning `503 dial_callback_adapter_disabled` before body parsing. The analytics response should include `dial_sandbox_adapter` and `durable_side_effects`, with `activation_mode=staged`, dry-run true, no admitted tenant, and zero intent/error counts in an untouched deployment. Do not treat a passing dashboard load, job-health read, analytics response, or callback rejection as authorization to enable outbound dispatch, configure a Dial secret, fire a provider ping, register a live provider callback URL, send an integration request, or create a live side-effect intent.

## References

- [Architecture](ARCHITECTURE.md)
- [Schema reference](schema.md)
- [Delivery phases](PHASES.md)
- `apps/api/voxflow_api/jobs/`
- `migrations/005_campaign_policy_controls.sql`
- `migrations/006_provider_callback_lifecycle.sql`
- `migrations/007_dial_sandbox_callback_adapter.sql`
- `migrations/008_typed_durable_side_effect_jobs.sql`
- `apps/api/voxflow_api/jobs/side_effects.py`
- `apps/api/voxflow_api/jobs/side_effect_worker_service.py`
- `apps/api/voxflow_api/integrations/dial_callbacks.py`
- `apps/api/voxflow_api/routes/dial_callbacks.py`
