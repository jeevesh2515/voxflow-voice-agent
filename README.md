# VoxFlow Voice Agent

> Voice operations, automated. A pluggable, zero-cost voice agent for supplier call operations — Hindi + English.

VoxFlow answers inbound supplier calls, captures purchase orders, checks stock, shares shipment status, and logs every interaction. Built to be self-hostable on a single machine and configurable per business.

## What's inside

- **`apps/api`** — Python 3.12 + FastAPI voice pipeline (STT → LLM → TTS)
  - Pluggable LLM: Ollama (local), Groq (free tier), OpenRouter (free tier)
  - `faster-whisper` STT (local, CPU-friendly)
  - `edge-tts` for natural Hindi + English voice output
  - SQLite (dev) → Postgres (prod) data store
  - WebSocket realtime audio endpoint
- **`apps/web`** — Next.js 14 dashboard with a browser phone simulator
- **`packages/core`** — shared types and tool schemas
- **`data/`** — seed JSON for the Varun Beverages demo scenario
- **`docker-compose.yml`** — one-command stack

## Quick start (zero cost)

```bash
# 1. Clone and configure
git clone https://github.com/jeevesh2515/voxflow-voice-agent.git
cd voxflow-voice-agent
cp .env.example .env

# 2. Install backend deps
cd apps/api
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 3. Install frontend deps
cd ../web
npm install

# 4. Seed demo data
cd ../api
python -m voxflow_api.seed

# 5. Run (two terminals)
# Terminal A:
uvicorn voxflow_api.main:app --reload --port 8000
# Terminal B:
cd ../web && npm run dev
```

Open:
- Dashboard: <http://localhost:3000>
- API docs: <http://localhost:8000/docs>
- Phone simulator: <http://localhost:3000/dashboard/simulator>

For local LLM (no API key needed):
```bash
ollama pull llama3.1:8b
# Set LLM_PROVIDER=ollama in .env
```

For Groq (fast, free tier):
```bash
# Sign up at https://console.groq.com, copy API key
# Set LLM_PROVIDER=groq and GROQ_API_KEY=... in .env
```

## Architecture

```
            Browser Phone Simulator
                       │
                  WebSocket (audio)
                       │
                       ▼
┌──────────────────────────────────────────┐
│              FastAPI server              │
│                                          │
│  STT (faster-whisper) → text             │
│         │                                │
│         ▼                                │
│  LLM (pluggable) + Tools                 │
│   ├── lookup_supplier                    │
│   ├── check_stock                        │
│   ├── get_shipment_status                │
│   ├── create_po / verify_po              │
│   ├── save_call_log                      │
│   └── escalate_to_human                  │
│         │                                │
│         ▼                                │
│  TTS (edge-tts) → audio stream            │
└──────────────────────────────────────────┘
         │                       │
         ▼                       ▼
   SQLite (calls, POs,    Next.js dashboard
   stock, shipments,      (live calls, POs,
   suppliers)             analytics)
```

## Why this stack

| Choice | Why |
|---|---|
| Python 3.12 | Best AI/ML ecosystem, mature WebSockets |
| FastAPI | Async, type-safe, great DX, auto OpenAPI |
| faster-whisper | Free, local, accurate, CPU-runnable |
| Ollama / Groq / OpenRouter | Three free tiers, swap via env |
| edge-tts | Microsoft's free TTS — natural Hindi voices, no key |
| SQLite | Zero config, fast enough for thousands of calls/day |
| Next.js | Matches the MadeThis storefront, file-based routing |
| WebSocket audio | Streaming latency <500ms perceived |

## The supplier-call scenario (Varun Beverages)

The agent speaks to suppliers calling about PepsiCo product distribution. It:

1. Greets in the caller's language (Hindi or English)
2. Identifies the supplier by name or phone number
3. Routes the intent: order/PO, stock check, shipment status, or other
4. Captures structured data into the database
5. Confirms the action with the supplier
6. Escalates ambiguous or sensitive cases to a human queue

See `data/` for the seed scenario.

## Cost at scale

| Volume | Per-month cost (USD) |
|---|---|
| 0–500 calls | **$0** (Ollama + local Whisper + Edge TTS) |
| 500–5,000 calls | **$0** (Groq free tier + Edge TTS) |
| 5,000+ calls | ~$30 (Groq + Deepgram + Twilio) |

## License

MIT
