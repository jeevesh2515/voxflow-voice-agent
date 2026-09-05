# VoxFlow Web Dashboard

Next.js **16.3.1** dashboard for VoxFlow voice operations. The application uses TypeScript, Tailwind CSS, and SWR, and is deployed at <https://voxflow-voice-agent.vercel.app>.

## Run locally

```bash
npm install
cp .env.example .env.local
npm run dev
```

The app runs at <http://localhost:3000>. Set `NEXT_PUBLIC_API_URL=http://localhost:8000` when using the local FastAPI backend.

## Quality checks

```bash
npm run lint
npm run build
```

The current production build generates **31 routes** without TypeScript/build errors.

## Main pages

| Route | Purpose |
|---|---|
| `/` | Public product landing page. |
| `/dashboard` | Operations overview. |
| `/dashboard/simulator` | Browser phone simulator. |
| `/dashboard/calls` | Tenant-scoped call history and transcripts. |
| `/dashboard/orders` | Purchase-order operations. |
| `/dashboard/shipments` | Shipment tracking. |
| `/dashboard/stock` | Stock and warehouse views. |
| `/dashboard/suppliers` | Supplier/customer directory. |
| `/dashboard/appointments` | Dock/meeting scheduling. |
| `/dashboard/communications` | Outbound communication history. |
| `/dashboard/escalations` | Escalation review and resolution workflow. |
| `/dashboard/campaigns` | Campaign staging, target queue, durable job health, and policy-stop visibility. |
| `/dashboard/analytics` | Tenant-safe KPIs, monitoring attention queue, redacted CSV reporting, aggregate provider lifecycle counts, Dial sandbox-adapter readiness, Day 34 durable side-effect health, Day 35 controlled-pilot readiness, and Day 36 pilot-operations evidence. |
| `/dashboard/settings` | Server-authoritative exact-DID routing, provider/language/verification policy, line deactivation, masked PIN posture, and owner-only caller PIN set/reset. |

## Telephony settings safety

The settings page reads `GET /api/tenants/{tenant_id}/telephony`. An active exact-DID status is treated as the only valid routing posture. Owners can add/update/deactivate line policy and set/reset a per-contact 4–8 digit PIN; operators, viewers, and demo sessions are read-only. DID identity is immutable during edit, phone contacts are masked, and neither plaintext PINs nor stored hashes are rendered or retained by the page.

## Analytics and callback lifecycle visibility

The analytics page passes the active tenant to read-only endpoints. It displays aggregate provider callback event count, application count, terminal-ignored count, and anomaly count without receiving raw callback payloads, secrets, phone numbers, job payloads, or transcripts. Day 33 adds the **Dial Sandbox Adapter** panel, which shows only tenant-safe adapter mode, audit-receipt count, tenant gate state, and verification-failure total. Day 34 adds the **Durable Side Effects** panel, which displays only activation mode, dry-run state, tenant gate, intent/pending/error totals, and type/status aggregates for Sheets, email, CRM, notifications, and recordings. Day 35 adds **Controlled Pilot Readiness**, displaying a non-activating readiness state, redacted cohort count, frozen metric values, and rollback-preview status. Day 36 adds **Pilot Operations Evidence**, which reports aggregate preflight blocking reasons, current same-cohort hold state, queue/lease counts, callback flags, and the explicit `NO AUTO-EXPANSION` rule. None of these panels contains a callback body, signature, secret, provider action, raw side-effect payload, cohort contact, evidence snapshot, or configuration control. Changing a reporting period, refreshing the page, or downloading the redacted CSV cannot issue a provider or integration request.

## Campaign dashboard safety behavior

The campaigns page is an operator read/control surface; it is not permission to place a real call. It passes the active tenant on campaign queue and stage/run requests, reads tenant-safe durable job health, and displays the rollout mode, outbox state, queue status, cancelled targets, and policy-stop total.

In the current production environment the expected panel state is:

```text
SAFE STAGING
NO INLINE DIALLING
```

The campaign worker and independent Day 34 side-effect worker are globally disabled in production. Do not use browser verification to press `Launch Campaign`, trigger an email scan, or invoke a provider/integration action. The dashboard cannot bypass backend worker gates or tenant policy/consent controls.

## Production environment

| Variable | Value |
|---|---|
| `NEXT_PUBLIC_API_URL` | Production FastAPI endpoint (or omitted for relative same-origin proxy) |
| `NEXT_PUBLIC_WS_URL` | Production WebSocket endpoint (or omitted for dynamic window.location resolution) |
| Supabase public values | Public browser configuration only; never a service role secret |

After a Vercel deployment, verify public routes return `200`, a session-free dashboard route redirects to sign-in, and authenticated dashboard renders display staged durable health, the read-only Provider Lifecycle aggregate, the Dial Sandbox Adapter, Durable Side Effects, Controlled Pilot Readiness, and Pilot Operations Evidence panels. In the safe default deployment the adapter panel must show **STAGED**, tenant gate **BLOCKED**, and zero audit/verification-failure counts; the Day 34 panel must show **STAGED**, zero intents/errors, tenant gate **BLOCKED**, and dry-run protection; Day 35 must show **BLOCKED**, cohort `0/0`, zero rollback actions, and `Pilot Configuration Missing`; Day 36 must show **BLOCKED**, `0` running jobs, `0` callback flags, and `NO AUTO-EXPANSION · HUMAN HOLD POINT REQUIRED`. See the root [README](../../README.md) and [SETUP.md](../../SETUP.md) for the complete free-tier deployment and safe warm-up procedure.
