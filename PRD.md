# VoxFlow Product Requirements Document

**Status:** Living product document; Day 33 local implementation complete and pending release verification.
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
activation_mode=staged
canary_allowed=false
dry_run=true
```

This is the planned current state. The campaign UI does not bypass the worker global gate or issue inline telephony requests. The deployed policy endpoint can report an unconfigured tenant; this is fail closed and prevents accidental dispatch if a worker were ever misconfigured.

## 5. Non-goals at the current milestone

The following are deliberately out of scope for the current Day 33 production posture:

- Outbound cold calling, sales prospecting, payment collection, or campaign dispatch without recorded permission.
- Activating a production worker for an unapproved tenant.
- Enabling a provider request from an HTTP campaign route.
- Treating missing consent or policy as permission.
- Reopening a terminal cancellation automatically.
- Registering a live Dial provider callback URL, configuring a Dial signing secret, or firing a provider ping during ordinary deployment verification.
- Enabling the Dial sandbox adapter or campaign worker merely because Day 33 fixture certification is implemented.
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
| Security | Provider-specific callback signature adapter is sandbox-certified, callback ingestion remains fail closed without its secret, tenant-safe APIs, and least-privilege access are verified. |

## 7. Success metrics

| Metric | Early target |
|---|---|
| Policy-blocked dispatches that reach a provider | 0 |
| Duplicate provider operations per durable job | 0 |
| Cross-tenant campaign/job/audit reads | 0 |
| Campaign target outcome traceability | 100% decision and job state evidence |
| Time to identify a deferred/cancelled target | Operator can locate reason without database shell access |
| Pilot call volume | Intentionally zero until all release gates are met |

## 8. Near-term roadmap

Day 32 completed a generic signed, tenant-derived callback lifecycle with immutable event evidence, duplicate/terminal guards, quarantine, and operator lifecycle aggregates. Day 33 locally implements Dial-specific sandbox verification, outbound-event normalization, secret-overlap support, redacted adapter auditing, tenant rollout gating, and operator visibility; its production route remains disabled pending release evidence. Day 34 moves Sheets, email, recording, CRM, and notification side effects into typed durable jobs. Subsequent work covers internal test-tenant canary execution, metrics/tracing, role controls, security hardening, evaluation quality, and pilot rehearsal.

## References

- [Architecture](ARCHITECTURE.md)
- [Roadmap](PHASES.md)
- [Live status](MEMORY.md)
- [Day 32 learning guide](.learning/day-32-provider-lifecycle-and-idempotent-callback-reconciliation.md)
- [Day 33 learning guide](.learning/day-33-provider-adapter-sandbox-certification-and-callback-rollout.md)
- [Day 34 learning guide](.learning/day-34-provider-callback-operational-readiness-and-canary-governance.md)
