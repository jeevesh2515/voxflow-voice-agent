# VoxFlow Voice Agent

> Voice operations, automated. A pluggable, multi-tenant voice agent for supplier call operations — Hindi + English.

VoxFlow answers inbound supplier calls, captures purchase orders, checks stock, shares shipment status, schedules appointments, logs outbound notifications, and records every interaction across multiple independent companies. Built to be self-hostable or deployed on cloud infrastructure with zero lock-in.

---

## Key Features

- **Multi-Tenant Dashboard:** Switch between distinct company scopes (Varun Beverages, Amul Dairy, Haldirams, Britannia Industries) with strict RLS data isolation.
- **Bilingual Voice Pipeline:** Natural conversation in Hindi & English (STT → LLM → TTS).
- **Service & Action Tools:**
  - `lookup_supplier`: Multi-field phone/name matching
  - `verify_caller`: Security verification challenge via city or GSTIN
  - `check_stock`: Warehouse-level stock availability
  - `get_shipment_status`: Carrier tracking timeline updates
  - `create_po` & `verify_po`: Purchase order transaction management
  - `schedule_appointment`: Supplier meeting booking
  - `send_email` & `send_whatsapp_message`: Outbound notification logs
  - `update_worksheet` & `type_notes`: Free-form dictation and spreadsheet sync audit
- **Vercel Ready:** Seamless Next.js frontend deployment from GitHub.

---

## Quick Start (Zero Cost)

### 1. Clone & Configure
```bash
git clone https://github.com/jeevesh2515/voxflow-voice-agent.git
cd voxflow-voice-agent
cp .env.example .env
```

### 2. Backend Setup (FastAPI + Python 3.12)
```bash
cd apps/api
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Seed multi-tenant data
python -m voxflow_api.seed --reset

# Verify database health
python -m voxflow_api.verify_db

# Run API server
uvicorn voxflow_api.main:app --reload --port 8000
```

### 3. Frontend Setup (Next.js 14)
```bash
cd apps/web
npm install
npm run dev
```

Open:
- **Dashboard:** <http://localhost:3000/dashboard>
- **Phone Simulator:** <http://localhost:3000/dashboard/simulator>
- **API Docs:** <http://localhost:8000/docs>

---

## Deploying Frontend on Vercel

1. Push your repository to GitHub:
   ```bash
   git add .
   git commit -m "Phase 0 & 1 Complete: Multi-Tenant Database & Next.js Frontend"
   git push origin main
   ```
2. Connect your repository on [Vercel](https://vercel.com).
3. Set the Root Directory to repository root (uses `vercel.json`).
4. Add Environment Variables on Vercel:
   - `NEXT_PUBLIC_API_URL`: Your hosted FastAPI endpoint (or Railway/Render deployment URL)
   - `NEXT_PUBLIC_WS_URL`: Your WebSocket endpoint (`wss://...`)
5. Click **Deploy**!

---

## Database Schema & Supabase Configuration

VoxFlow supports **SQLite** for local development (`./voxflow.db`) and **Supabase / PostgreSQL** for production.

To configure Supabase in `.env`:
```env
DATABASE_URL=postgresql://postgres:password@db.xxx.supabase.co:5432/postgres
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_ANON_KEY=...
SUPABASE_SERVICE_ROLE_KEY=...
```

See [schema.md](file:///Users/jeeveshsingale/VoxFlow/voxflow-voice-agent/schema.md) for the complete SQL DDL definitions and Row-Level Security (RLS) policies.

---

## Architecture Overview

```
                   Browser Phone Simulator / Web Dashboard
                                    │
                         WebSocket / HTTP API
                                    │
                                    ▼
          ┌──────────────────────────────────────────────────┐
          │                  FastAPI Gateway                 │
          │                                                  │
          │   STT: faster-whisper (local CPU) → text         │
          │          │                                       │
          │          ▼                                       │
          │   Agent State Engine & Multi-Tenant Tools        │
          │    ├── lookup_supplier / verify_caller           │
          │    ├── check_stock / get_shipment_status         │
          │    ├── create_po / verify_po                     │
          │    ├── schedule_appointment                      │
          │    ├── send_email / send_whatsapp_message        │
          │    └── type_notes / update_worksheet             │
          │          │                                       │
          │          ▼                                       │
          │   TTS: edge-tts (Hindi & English output)          │
          └──────────────────────────────────────────────────┘
                   │                                  │
                   ▼                                  ▼
        SQLite / Supabase Postgres               Next.js 14
        (Tenant RLS Data Store)             (Dashboard UI on Vercel)
```

---

## License

MIT
