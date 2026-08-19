<div align="center">

# 🎙️ VoxFlow

### *Autonomous Voice AI & Real-Time Operations SaaS Platform for FMCG & Supply Chain Enterprises*

[![Next.js 14](https://img.shields.io/badge/Next.js-14.2-black?style=for-the-badge&logo=next.js)](https://nextjs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=for-the-badge&logo=fastapi)](https://fastapi.tiangolo.com/)
[![Python 3.12](https://img.shields.io/badge/Python-3.12-3776AB?style=for-the-badge&logo=python)](https://python.org)
[![Supabase](https://img.shields.io/badge/Supabase-Postgres-3ECF8E?style=for-the-badge&logo=supabase)](https://supabase.com)
[![Render Backend](https://img.shields.io/badge/Render-Live-46E3B7?style=for-the-badge&logo=render)](https://voxflow-voice-agent.onrender.com/api/health)
[![Vercel Ready](https://img.shields.io/badge/Vercel-Deployed-000000?style=for-the-badge&logo=vercel)](https://vercel.com)
[![Pytest 144/144](https://img.shields.io/badge/Tests-144%20Passing-brightgreen?style=for-the-badge&logo=pytest)](apps/api/tests/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](LICENSE)

<br />

[![Deploy with Vercel](https://vercel.com/button)](https://vercel.com/new/clone?repository-url=https%3A%2F%2Fgithub.com%2Fjeevesh2515%2Fvoxflow-voice-agent)

<p align="center">
  <a href="#-overview">Overview</a> •
  <a href="#-cloud-deployments">Deployments</a> •
  <a href="#-12-core-operational-modules">12 Modules</a> •
  <a href="#-system-architecture">Architecture</a> •
  <a href="#-quickstart">Quickstart</a> •
  <a href="#-enterprise-security">Security</a> •
  <a href="#-test-suite">Tests</a>
</p>

</div>

---

## ⚡ Overview

**VoxFlow** is a multi-tenant, enterprise voice AI SaaS platform engineered to automate inbound supplier, distributor, customer, and partner phone calls for FMCG brands (e.g. Varun Beverages / PepsiCo, Amul, Britannia) and supply chain logistics operators.

Operating seamlessly in **Hindi (`hi-IN`) & English (`en-IN`)** with ultra-low latency, VoxFlow executes complex, multi-step transactional voice workflows:

- 🔒 **Tier 1 & Tier 2 Security Gating**: Multi-factor caller authentication via registered phone numbers, city match, or GSTIN challenges before data disclosure, plus Tier 2 4-digit PIN verification (`verify_pin`) for high-privilege order creation (`create_po`).
- 📦 **Inventory & Stock Management**: Real-time multi-warehouse inventory lookups and stock availability confirmation.
- ⚡ **Autonomous Purchase Orders**: Conversational natural language slot-filling to generate, validate, and record Purchase Orders directly into the core database.
- 🚚 **Logistics & Shipment Tracking**: Real-time dispatch status, ETA lookup, carrier milestones, and GPS tracking.
- 📅 **Dock & Meeting Scheduling**: Automated appointment booking for warehouse dock arrivals and supplier reviews.
- 💬 **Omnichannel Dispatch**: Instant multi-channel notifications via automated email confirmations, SMS alerts, and WhatsApp messages.
- 🖥️ **Live Operations Control Center**: Real-time operations dashboard with active call monitoring, full transcripts, sentiment metrics, and human escalation desks.

---

## 🌐 Cloud Deployments

| Component | Provider | Production URL / Endpoint | Health Check |
|---|---|---|---|
| **Voice API Backend** | Render | `https://voxflow-voice-agent.onrender.com` | [`/api/health`](https://voxflow-voice-agent.onrender.com/api/health) |
| **Web Dashboard** | Vercel | [`https://web-gamma-ten-21.vercel.app`](https://web-gamma-ten-21.vercel.app) | `/dashboard` |
| **Database & Auth** | Supabase | `https://gujjyytfpqpkzbrtsink.supabase.co` | Managed Postgres Pooler |
| **Telemetry & Evals** | LangSmith | `voxflow-production` | Live Tracing & Latency |

---

## 🧩 12 Core Operational Modules

VoxFlow features 12 modules accessible via the web console:

| Module | Route | Key Features |
|---|---|---|
| 🎙️ **Live Simulator** | `/dashboard/simulator` | Real-time audio waveform visualizer, mic capture, Twilio phone emulator, and streaming transcript feed. |
| 📊 **Overview Control Center** | `/dashboard` | High-density KPI cards (Total POs, Active SKUs, Shipments, Total Minutes), active call cards, and quick actions. |
| 📞 **Calls & Audio Transcripts** | `/dashboard/calls` | Audio player, caller identification badges, sentiment classification, transcript viewer, and PO linkage. |
| 🚨 **Escalation Desk** | `/dashboard/escalations` | Real-time human handoff queue, priority badges (HIGH/URGENT), dispute reason classification, and 1-click staff resolution. |
| 📋 **Purchase Orders Ledger** | `/dashboard/orders` | Live order ledger, Signed/Unsigned filter, search by reference, CSV data export, and manual PO creation modal. |
| 🚚 **Shipments & Logistics** | `/dashboard/shipments` | Multi-carrier progress tracker, milestone timelines (Dispatched → In Transit → Customs → Out for Delivery → Delivered). |
| 📦 **Stock & Inventory** | `/dashboard/stock` | Multi-warehouse switching (Gurugram, Bhiwandi, Bengaluru), low-stock warning thresholds, unit valuation, and SKU search. |
| 👥 **Suppliers Directory** | `/dashboard/suppliers` | Supplier directory, 2FA PIN authorization status badges, contact metadata, and direct simulator launcher. |
| 📅 **Dock Appointments** | `/dashboard/appointments` | Warehouse dock scheduling, vehicle number & driver tracking, time-slot selection modal, and status updates. |
| 💬 **Outbound Communications** | `/dashboard/communications` | Omnichannel communication feed (WhatsApp, SMS, Email), filter tabs, delivery receipt statuses, and dispatch composer. |
| 📈 **Analytics & Evaluations** | `/dashboard/analytics` | First Contact Resolution (FCR: 94.8%), Average Handle Time (AHT: 1m 42s), CSAT sentiment breakdown, and LangSmith deep trace links. |
| ⚙️ **Agent & Telephony Settings** | `/dashboard/settings` | System prompt editor, Hindi/English bilingual switch, Twilio phone number bindings, and ERP HMAC webhook management. |

---

## 🏗 System Architecture

```
                               ┌───────────────────────────┐
                               │  Inbound Telephony Stream │
                               │  (Twilio / Carrier SIP)   │
                               └─────────────┬─────────────┘
                                             │ G.711 μ-law WebSocket
                                             ▼
 ┌────────────────────────────────────────────────────────────────────────────────────────┐
 │                              FastAPI Agent Gateway                                     │
 │                                                                                        │
 │  ┌───────────────────────┐   ┌───────────────────────┐   ┌──────────────────────────┐ │
 │  │ Silero VAD (Chunking) │──▶│ Groq Whisper L-v3-T   │──▶│ Llama-3.3-70B (LLM)      │ │
 │  └───────────────────────┘   └───────────────────────┘   └────────────┬─────────────┘ │
 │                                                                       │ Tool Calls     │
 │  ┌───────────────────────┐   ┌───────────────────────┐                │                │
 │  │ Twilio Media Outbound │◀──│ Edge-TTS / Kokoro TTS │◀───────────────┘                │
 │  └───────────────────────┘   └───────────────────────┘                                 │
 └───────────────────────────────────────────┬────────────────────────────────────────────┘
                                             │
              ┌──────────────────────────────┼──────────────────────────┐
              ▼                              ▼                          ▼
┌───────────────────────────┐ ┌───────────────────────────┐ ┌───────────────────────────┐
│ Supabase Postgres Cluster │ │  Google Sheets Logger     │ │  LangSmith Live Telemetry │
│  (Row-Level Security RLS) │ │  (Post-Call + Email Log)  │ │  (Trace Logs & Evals)     │
└───────────────────────────┘ └───────────────────────────┘ └───────────────────────────┘
             ▲
             │  3× Daily (APScheduler)
┌───────────────────────────┐
│  Email Summarizer Agent   │
│  (Gmail API → LLM → DB)   │
└───────────────────────────┘
```

---

## 🚀 Quickstart & Local Setup

### 1. Prerequisites
- Node.js 18+ & `npm`
- Python 3.12+ & `pip`
- Docker (optional, for container testing)

### 2. Clone & Configure Environment
```bash
git clone https://github.com/jeevesh2515/voxflow-voice-agent.git
cd voxflow-voice-agent
cp .env.example .env
```

### 3. Start Backend API (FastAPI)
```bash
cd apps/api
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Run self-test and seed database
python -m voxflow_api.seed --reset

# Launch FastAPI server (Port 8000)
uvicorn voxflow_api.main:app --reload --port 8000
```

### 4. Start Web Dashboard (Next.js 14)
```bash
cd apps/web
npm install
npm run dev
```

Visit:
- **Web Dashboard:** `http://localhost:3000/dashboard`
- **Phone Simulator:** `http://localhost:3000/dashboard/simulator`
- **FastAPI OpenAPI Docs:** `http://localhost:8000/docs`

---

## ☁️ Production Deployment

### Render Deployment (Backend API)
1. In Render, create a new **Web Service** from this GitHub repository.
2. Select **Docker** as the environment.
3. Configure the following Environment Variables:
   - `DATABASE_URL`: `postgresql://postgres.<project-ref>:<password>@aws-0-<region>.pooler.supabase.com:5432/postgres`
   - `SUPABASE_URL`: `https://<project-ref>.supabase.co`
   - `SUPABASE_ANON_KEY`: `<your-supabase-anon-key>`
   - `GROQ_API_KEY`: `<your-groq-api-key>`
   - `LANGSMITH_API_KEY`: `<your-langsmith-api-key>`
   - `LANGSMITH_PROJECT`: `voxflow-production`
   - `LANGSMITH_TRACING`: `true`
4. Render will dynamically assign `$PORT` (10000) and mark the service **Live**.

### Vercel Deployment (Frontend Web App)
1. Import this repository in Vercel.
2. Set **Root Directory** to `apps/web`.
3. Set Framework Preset to **Next.js**.
4. Configure Environment Variables:
   - `NEXT_PUBLIC_API_URL`: `https://voxflow-voice-agent.onrender.com`
   - `NEXT_PUBLIC_WS_URL`: `wss://voxflow-voice-agent.onrender.com`
   - `NEXT_PUBLIC_SUPABASE_URL`: `https://<project-ref>.supabase.co`
   - `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY`: `<your-publishable-key>`
   - `NEXT_PUBLIC_SUPABASE_ANON_KEY`: `<your-anon-key>`
5. Click **Deploy**.

---

## 🧪 Test Suite

VoxFlow maintains a 100% passing test suite across all modules, audio codecs, and security gates:

```bash
cd apps/api
pytest tests/ -v
```

```
============================= 144 passed in 9.47s ==============================
```

- **Audio & Media Codecs**: G.711 $\mu$-law transcoding, 8kHz to 16kHz resampling, RMS energy detection, audio roundtrip stability.
- **Twilio Webhook Security**: HMAC signature validation, rate limiters, unmapped number tenant fallback.
- **Support Workflows**: 2FA caller PIN verification, PO status retrieval, multi-tenant isolation barriers, Google Sheets fallback retry queue.
- **Database & Schema Integrity**: Row-Level Security (RLS) enforcement across all tables, idempotent migrations.

---

## 📄 License

Distributed under the **MIT License**. See [`LICENSE`](LICENSE) for details.
