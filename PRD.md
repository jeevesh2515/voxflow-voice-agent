# VoxFlow Product Requirements Document

**Status:** Living product document; Day 34 local implementation complete and pending release verification. Day 35 is the final controlled-pilot readiness gate.
**Last updated:** 2026-08-20
**Repository:** <https://github.com/jeevesh2515/voxflow-voice-agent>

## 1. Product statement

VoxFlow is a bilingual Hindi-English voice operations platform for FMCG and supply-chain teams. It supports verified inbound voice workflows, operational dashboards, and controlled outbound campaign execution for operational—not sales—use cases such as delayed shipment follow-up, purchase-order confirmation, and dock reminders.

The product is designed around a simple safety principle: operational automation must be **tenant scoped, policy controlled, and auditable**. A campaign target may not reach a telephony provider merely because an operator created a campaign or an HTTP request succeeded.

## 2. User problems

| User | Problem | Required product outcome |
|---|---|---|
| Operations staff | Manual supplier/customer calls delay shipment, PO, and dock workflows. | Structured call handling, operational records, campaign queues, and escalation visibility. |
| Tenant administrator | Cannot safely delegate outbound operational reminders without proof of consent and capacity controls. | Tenant-local policy, recipient preference, quotas, cancellation evidence, and a hard stop. |
| Operator | Cannot diagnose a stuck dispatch without database access. | Tenant-safe job health, target queue, reason codes, and audit timeline. |
| Platform owner | Provider retries can create duplicate side effects. | Durable job ledger, leases, provider-operation idempotency, reconciliation, and staged rollout. |

## 3. Product capabilities

### Inbound operations

VoxFlow supports tenant-aware inbound voice flows with caller verification, stock/order/shipment support, appointment scheduling, escalation, transcript persistence, and Hindi-English voice interaction. The dashboard provides operational lists, call records, inventory, orders, shipments, suppliers, appointments, communications, and a voice simulator.

### Durable outbound operations

Campaign targets are queued as durable work. The delivery path includes transactional enqueue/outbox persistence, lease-based job claims, attempt history, typed retry behavior, provider-operation idempotency, and callback/reconciliation primitives.

Day 30 adds central dispatch permission controls.

| Requirement | Behavior |
|---|---|
| Explicit tenant policy | Required before dispatch. Policy holds timezone, calling window, daily call limit, capacity, and enabled switch. |
| Recipient consent | Target requires granted consent for outbound campaigns or the specific campaign type. |
| Opt-out | Any opt-out is terminal and blocks provider access. |
| Active campaign | Draft, paused, or completed campaigns cannot dispatch. |
| Local calling hours | Closed windows defer to the exact next tenant-local opening time. |
| Daily budget and capacity | Reserved atomically per tenant local day; concurrent workers cannot overbook. |
| Auditable result | Each evaluation records an immutable allowed, deferred, or cancelled decision. |
| No provider duplication | A provider operation idempotency key owns a single external request; retries reconcile it. |
| Callback trust | A signed callback derives tenant ownership from the stored operation, deduplicates an immutable event ID, and never trusts callback tenant/campaign/queue/job input. |
| Unknown/late callback safety | Unknown call IDs quarantine without tenant state changes; duplicates and late events cannot reopen terminal queue/job/capacity state. |
| Provider protocol isolation | The Day 33 Dial adapter verifies the provider’s raw-body HMAC/freshness/envelope at the edge and maps only safe outbound lifecycle facts to Day 32. |
| Callback application gate | An HMAC-valid Dial event can apply only after one stored outbound operation resolves an explicitly allow-listed tenant; provider payload cannot select business ownership. |
| Adapter observability | Redacted audit receipts and tenant-safe analytics show verification, normalization, and rollout dispositions without raw body/header/secret/phone disclosure. |
| Side-effect ownership | Sheets, email scans, CRM synchronization, notifications, worksheet appends, and recording follow-up persist typed `SideEffectIntent`/job/outbox ownership transactionally. |
| No inline integration IO | Voice/API/callback/dashboard paths may persist intent but cannot send a notification, CRM webhook, Sheets write, Gmail fetch, recording retrieval, or direct outbound call inline. |
| Separate side-effect gate | An independent worker requires its own global enablement, tenant allow-list, and dry-run control; it is disabled in production. |
| Side-effect observability | Tenant-safe analytics/CSV show aggregate intent state, pending/error totals, rollout posture, and alert signals without raw external payloads. |

## 4. Current availability and safety boundary

The Vercel dashboard and Render API are live. The durable campaign system is implemented but **not enabled for live outbound traffic**.

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

This is the planned current state. The campaign UI does not bypass the worker global gate or issue inline telephony requests. The deployed policy endpoint can report an unconfigured tenant; this is fail closed and prevents accidental dispatch if a worker were ever misconfigured.

## 5. Non-goals at the current milestone

The following are deliberately out of scope for the current Day 34 production posture:

- Outbound cold calling, sales prospecting, payment collection, or campaign dispatch without recorded permission.
- Activating a production worker for an unapproved tenant.
- Enabling a provider request from an HTTP campaign route.
- Treating missing consent or policy as permission.
- Reopening a terminal cancellation automatically.
- Registering a live Dial provider callback URL, configuring a Dial signing secret, or firing a provider ping during ordinary deployment verification.
- Enabling the Dial sandbox adapter, campaign worker, or Day 34 side-effect worker merely because fixture/local certification is implemented.
- Calling Twilio, Dial, Sheets, Gmail, a CRM endpoint, a notification service, or recording URL inline from an API request, voice turn, callback, dashboard, or FastAPI lifespan loop.
- A broad multi-tenant pilot before provider adapter release verification, RBAC, observability, and release-readiness gates are completed.

## 6. Pilot requirements

A live operational canary can be considered only after the following evidence exists.

| Gate | Evidence |
|---|---|
| Worker safety | Global enablement is separately approved; worker process, tenant allow-list, and rollback are documented. |
| Tenant permission | Explicit policy, valid IANA timezone/window, daily limit, capacity, and enabled setting exist. |
| Recipient permission | Approved E.164 target has recorded consent and no opt-out. |
| Provider safety | Dry run, no-redial, reconciliation, duplicate callback, unknown-call quarantine, terminal ordering, and crash/restart tests pass. |
| Operator safety | Job health, policy reason, cancellation, and escalation/read-only support paths are visible. |
| Security | Provider-specific callback signature adapter is sandbox-certified, callback ingestion remains fail closed without its secret, tenant-safe APIs, side-effect intent redaction, and least-privilege access are verified. |
| Side-effect safety | Side-effect worker is separately disabled/dry-run/allow-listed, every integration operation has typed durable evidence, and rollback cannot leave unaccounted queued work. |
| Human operating coverage | Named primary/backup escalation responders, explicit operating hours, alert owners, and a tested pause/rollback procedure are approved. |
| Pilot scope | One named tenant, a fixed consented supplier cohort, capacity cap, expiry, and frozen metric definitions are approved in writing. |

## 7. Success metrics

| Metric | Early target |
|---|---|
| Policy-blocked dispatches that reach a provider | 0 |
| Duplicate provider operations per durable job | 0 |
| Cross-tenant campaign/job/audit reads | 0 |
| Campaign target outcome traceability | 100% decision and job state evidence |
| Time to identify a deferred/cancelled target | Operator can locate reason without database shell access |
| Pilot call volume | Intentionally zero until all release gates are met |
| Successful call completion | Defined as reconciled completed terminal calls divided by eligible initiated calls; target/denominator are frozen in the tenant-approved Day 35 scorecard. |
| Escalation rate | Defined as escalated calls divided by eligible answered calls; reviewed with category and staffing context rather than treated as an automatic failure. |
| First-call resolution (FCR) | Defined as eligible resolved calls with no later human follow-up in the approved attribution window divided by eligible answered calls. |
| Confirmed security incidents | Operational objective is 0 during the pilot; this is measured from incident/access/callback records, not guaranteed before operation. |

## 8. Near-term roadmap

Day 32 completed a generic signed, tenant-derived callback lifecycle with immutable event evidence, duplicate/terminal guards, quarantine, and operator lifecycle aggregates. Day 33 implements Dial-specific sandbox verification, outbound-event normalization, secret-overlap support, redacted adapter auditing, tenant rollout gating, and operator visibility; its production route remains disabled. Day 34 completes the local migration of Sheets, email scans, recording follow-up, CRM synchronization, notifications, and worksheet side effects into typed durable jobs, with a separate disabled/dry-run worker and aggregate-only dashboard evidence. Day 35 is the final pilot-readiness day: it must produce a written one-tenant/fixed-cohort/explicit-hours/human-escalation/scorecard/rollback package, with readiness measured by proof rather than a promise of business outcomes or zero incidents in advance.

## References

- [Architecture](ARCHITECTURE.md)
- [Roadmap](PHASES.md)
- [Live status](MEMORY.md)
- [Day 32 learning guide](.learning/day-32-provider-lifecycle-and-idempotent-callback-reconciliation.md)
- [Day 33 learning guide](.learning/day-33-provider-adapter-sandbox-certification-and-callback-rollout.md)
- [Day 34 learning guide](.learning/day-34-provider-callback-operational-readiness-and-canary-governance.md)
- [Day 35 learning guide](.learning/day-35-controlled-pilot-readiness-and-operational-gates.md)
