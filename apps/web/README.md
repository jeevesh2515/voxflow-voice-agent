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

The Day 32 production build generates 20 routes without TypeScript/build errors.

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
| `/dashboard/analytics` | Tenant-safe KPIs, monitoring attention queue, redacted CSV reporting, and aggregate provider lifecycle counts. |
| `/dashboard/settings` | Agent, telephony, and operations settings. |

## Analytics and callback lifecycle visibility

The analytics page passes the active tenant to the read-only analytics endpoint. It displays aggregate provider callback event count, application count, terminal-ignored count, and anomaly count without receiving raw callback payloads, secrets, phone numbers, job payloads, or transcripts. Changing a reporting period, refreshing the page, or downloading the redacted CSV cannot issue a provider call.

## Campaign dashboard safety behavior

The campaigns page is an operator read/control surface; it is not permission to place a real call. It passes the active tenant on campaign queue and stage/run requests, reads tenant-safe durable job health, and displays the rollout mode, outbox state, queue status, cancelled targets, and policy-stop total.

In the current production environment the expected panel state is:

```text
SAFE STAGING
NO INLINE DIALLING
```

The API worker is globally disabled in production. Do not use browser verification to press `Launch Campaign` or trigger a provider action. The dashboard cannot bypass the backend worker gate or tenant policy/consent controls.

## Production environment

| Variable | Value |
|---|---|
| `NEXT_PUBLIC_API_URL` | `https://voxflow-voice-agent.onrender.com` |
| `NEXT_PUBLIC_WS_URL` | Approved WebSocket base for the deployed backend if configured |
| Supabase public values | Public browser configuration only; never a service role secret |

After a Vercel deployment, verify public routes return `200`, a session-free dashboard route redirects to sign-in, and authenticated dashboard renders display staged durable health plus the read-only provider lifecycle aggregate. See the root [README](../../README.md) and [SETUP.md](../../SETUP.md) for the complete deployment procedure.
