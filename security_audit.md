# VoxFlow Security and Safety Audit

**Last updated:** 2026-08-20
**Scope:** Current repository controls through Day 32.
**Status:** Inbound/dashboard deployment is operational; outbound campaign execution is intentionally safe-staged and is **not approved for general live activation**.

## 1. Security posture summary

VoxFlow applies layered controls to tenant-aware voice and campaign operations. Traditional authentication, tenant scoping, signed inbound telephony handling, secret isolation, and rate controls protect the existing application surface. Days 25–30 add a distinct safety layer for outbound side effects: durable intent, leases, provider-operation idempotency, global worker gating, tenant policy, recipient permission, quota/capacity controls, and immutable policy evidence. Day 32 adds a fail-closed signed callback ingress, immutable provider-event evidence, terminal-state guards, and unknown-call quarantine.

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

## 4. Input and data controls

| Surface | Control | Notes |
|---|---|---|
| Campaign target phone | E.164-style `+` validation | Invalid recipient number is a permanent non-provider failure. |
| Tenant policy | Valid IANA timezone, 24-hour window syntax, positive daily/capacity limits | Invalid policy fails closed. |
| Recipient preference | Tenant + recipient unique record with consent, purpose, opt-out, and source | A missing preference is not consent. |
| Policy audit read | Redacted operator response | Raw evidence JSON is not returned by the campaign policy-decision endpoint. |
| Provider callbacks | Signature/timestamp, payload bounds, typed normalized fields, and event-ID deduplication | Raw callback payload is not persisted; secret and provider-specific verification remain configuration/adapter concerns. |
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
| Learning journals contain no credentials | Required; `.learning/` is local and gitignored. |

## 6. Network and browser boundary

| Control | Current expectation |
|---|---|
| API CORS | Restrict to local development and approved Vercel origins. |
| Public frontend | Landing/about/pricing are public. |
| Dashboard | Session-free request must redirect to sign-in. |
| Inbound voice transport | Use HTTPS/WSS and provider signature validation. |
| Outbound campaign verification | Never press launch or enable a worker during ordinary deployment checks. |

## 7. Known gaps and required next controls

| Gap | Risk | Required next action |
|---|---|---|
| Provider-specific callback adapter certification | An undocumented or incorrectly canonicalized live provider callback could be rejected or mis-normalized. | Day 33 sandbox contract capture, signature fixtures, normalizer, replay/reorder drills, and controlled adapter gate. |
| RBAC for policy/replay/config mutation | Broad access could alter policy or worker configuration. | Add platform/tenant admin/operator/read-only authorization matrix. |
| Callback alert routing/runbooks | Day 32 exposes lifecycle aggregates but does not route alerts or provide incident drills. | Add provider event age, verification-failure, quarantine, duplicate, and anomaly response paths after adapter certification. |
| Internal canary evidence | Live provider behavior is intentionally not verified. | Use provider sandbox or approved single-target internal canary only after prerequisite gates. |
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
curl -I https://voxflow-voice-agent.vercel.app/dashboard/campaigns
```

Expected Day 32 live result is staged rollout with the campaign worker disabled and callback ingress returning `503` while the callback secret is intentionally absent. Do not treat a passing dashboard load, job-health read, or callback rejection as authorization to enable outbound dispatch or register a live provider callback URL.

## References

- [Architecture](ARCHITECTURE.md)
- [Schema reference](schema.md)
- [Delivery phases](PHASES.md)
- `apps/api/voxflow_api/jobs/`
- `migrations/005_campaign_policy_controls.sql`
- `migrations/006_provider_callback_lifecycle.sql`
