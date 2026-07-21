# VoxFlow — web dashboard

Next.js 14 dashboard + browser phone simulator.

## Run

```bash
npm install
cp .env.example .env.local
npm run dev
```

App on <http://localhost:3000>. Expects the API on <http://localhost:8000>.

## Pages

- `/` — landing
- `/dashboard` — overview
- `/dashboard/simulator` — phone simulator (mic + text input)
- `/dashboard/calls` — call log + transcripts
- `/dashboard/orders` — order list
- `/dashboard/shipments` — shipment timeline
- `/dashboard/stock` — stock by warehouse
- `/dashboard/suppliers` — supplier directory
