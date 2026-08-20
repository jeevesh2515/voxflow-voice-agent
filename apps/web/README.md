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

The Day 35 production build generates 20 routes without TypeScript/build errors.

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
| `/dashboard/analytics` | Tenant-safe KPIs, monitoring attention queue, redacted CSV reporting, aggregate provider lifecycle counts, Dial sandbox-adapter readiness, Day 34 durable side-effect health, and Day 35 controlled-pilot readiness evidence. |
| `/dashboard/settings` | Agent, telephony, and operations settings. |

## Analytics and callback lifecycle visibility

The analytics page passes the active tenant to read-only endpoints. It displays aggregate provider callback event count, application count, terminal-ignored count, and anomaly count without receiving raw callback payloads, secrets, phone numbers, job payloads, or transcripts. Day 33 adds the **Dial Sandbox Adapter** panel, which shows only tenant-safe adapter mode, audit-receipt count, tenant gate state, and verification-failure total. Day 34 adds the **Durable Side Effects** panel, which displays only activation mode, dry-run state, tenant gate, intent/pending/error totals, and type/status aggregates for Sheets, email, CRM, notifications, and recordings. Day 35 adds **Controlled Pilot Readiness**, displaying a non-activating readiness state, redacted cohort count, frozen metric values, and rollback-preview status. None of these panels contains a callback body, signature, secret, provider action, raw side-effect payload, or configuration control. Changing a reporting period, refreshing the page, or downloading the redacted CSV cannot issue a provider or integration request.

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
| `NEXT_PUBLIC_API_URL` | `https://voxflow-voice-agent.fly.dev` temporarily, while Render remains outage-blocked |
| `NEXT_PUBLIC_WS_URL` | Approved WebSocket base for the deployed backend if configured |
| Supabase public values | Public browser configuration only; never a service role secret |

After a Vercel deployment, verify public routes return `200`, a session-free dashboard route redirects to sign-in, and authenticated dashboard renders display staged durable health, the read-only Provider Lifecycle aggregate, the Dial Sandbox Adapter, Durable Side Effects, and Controlled Pilot Readiness panels. In the safe default deployment the adapter panel must show **STAGED**, tenant gate **BLOCKED**, and zero audit/verification-failure counts; the Day 34 panel must show **STAGED**, zero intents/errors, tenant gate **BLOCKED**, and dry-run protection; Day 35 must show **BLOCKED**, cohort `0/0`, zero rollback actions, and `Pilot Configuration Missing`. See the root [README](../../README.md) and [SETUP.md](../../SETUP.md) for the complete deployment and Render-restoration procedure.
