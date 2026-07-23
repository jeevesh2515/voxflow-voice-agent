<div align="center">

# 🎙️ VoxFlow Voice Agent

### *Enterprise Autonomous Voice Operations Platform for Multi-Tenant Supply Chains*

[![Next.js 14](https://img.shields.io/badge/Next.js-14.2-black?style=for-the-badge&logo=next.js)](https://nextjs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=for-the-badge&logo=fastapi)](https://fastapi.tiangolo.com/)
[![Python 3.12](https://img.shields.io/badge/Python-3.12-3776AB?style=for-the-badge&logo=python)](https://python.org)
[![Tests Passing](https://img.shields.io/badge/Pytest-15%2F15%20Passing-brightgreen?style=for-the-badge&logo=pytest)](apps/api/tests/test_api.py)
[![Supabase](https://img.shields.io/badge/Supabase-Postgres-3ECF8E?style=for-the-badge&logo=supabase)](https://supabase.com)
[![Tailwind CSS](https://img.shields.io/badge/Tailwind-v3.4-38B2AC?style=for-the-badge&logo=tailwind-css)](https://tailwindcss.com)
[![Deployed on Vercel](https://img.shields.io/badge/Vercel-Deployed-000000?style=for-the-badge&logo=vercel)](https://voxflow.madethis.app)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](LICENSE)

<br />

[![Deploy with Vercel](https://vercel.com/button)](https://vercel.com/new/clone?repository-url=https%3A%2F%2Fgithub.com%2Fjeevesh2515%2Fvoxflow-voice-agent)

<p align="center">
  <a href="#-key-features">Key Features</a> •
  <a href="#-multi-tenant-architecture">Multi-Tenancy</a> •
  <a href="#-dashboard-preview--ui">Dashboard UI</a> •
  <a href="#-quickstart">Quickstart</a> •
  <a href="#-deploying-on-vercel">Vercel Deployment</a> •
  <a href="#-architecture">Architecture</a> •
  <a href="#-documentation">Documentation</a>
</p>

</div>

---

## ⚡ What is VoxFlow?

**VoxFlow** is an enterprise-grade, zero-latency autonomous voice agent platform designed to automate high-volume supplier calls for enterprise FMCG & logistics brands (e.g. Varun Beverages / PepsiCo, Amul Dairy, Haldirams, Britannia).

Built with a **pluggable, cost-effective tech stack** (Twilio / WebSockets + faster-whisper + Groq Llama 3.1 + Edge-TTS + Supabase / Postgres), VoxFlow handles end-to-end phone conversations in **Hindi & English**:
- 🔍 **Identify & Verify Callers**: Security gate matching caller phone numbers, cities, and GSTINs.
- 📦 **Manage Inventory & POs**: Instant real-time stock lookups across warehouses and automated Purchase Order creation.
- 🚚 **Track Shipments & Logistics**: Real-time carrier status updates and delivery timeline queries.
- 📅 **Schedule Appointments**: Seamless booking for supplier meetings and dock arrival slots.
- 💬 **Outbound Multi-Channel Dispatch**: Automated email notifications and direct WhatsApp messages.
- 📑 **Audit Logs & Worksheets**: Interactive call logs, full transcripts, tool execution history, and spreadsheet sync.

---

## ✨ Key Features

| Feature | Description | Stack / Tech |
|---|---|---|
| **🏢 Multi-Tenant Dashboard** | Switch between distinct company scopes with complete data isolation | React Context + Next.js SWR + Postgres RLS |
| **🎙️ Bilingual Voice AI** | Natural, human-like voice conversations in Hindi (`hi-IN`) and English (`en-IN`) | STT (Whisper) + Groq (Llama 3.1) + Edge-TTS |
| **🔒 Identity Security Gate** | Verifies caller authorization via city/GSTIN challenge before disclosing data | `verify_caller` tool logic |
| **📱 Interactive Phone Simulator** | Built-in web phone simulator for real-time voice & text testing over WebSockets | WebSocket Streaming (`ws/call`) |
| **⚡ Purchase Order Engine** | Natural language slot-filling to generate, validate, and query POs | LangGraph-inspired state machine |
| **🚀 One-Click Vercel Deploy** | Production-ready Next.js 14 dashboard frontend configuration | Vercel Serverless / Static Build |

---

## 🏢 Multi-Tenant Enterprise Architecture

VoxFlow is built from the ground up for multi-tenancy. A single platform deployment serves multiple independent companies with strict data segregation:

```
                  VoxFlow Control Center (Topbar Tenant Switcher)
                                        │
    ┌───────────────────┬───────────────┴───────────────┬───────────────────┐
    ▼                   ▼                               ▼                   ▼
Varun Beverages     Amul Dairy                   Haldirams Snacks    Britannia Foods
(PepsiCo FMCG)    (Dairy & Cold Supply)       (Confectionery & Spices)  (Bakery & Biscuits)
```

Each tenant has isolated access to:
- Suppliers & Contacts
- Product SKUs, Warehouses & Stock Levels
- Active Purchase Orders & Shipment History
- Scheduled Appointments & Communication Dispatch Logs

---

## 🎨 Dashboard Preview & UI Features

The VoxFlow Web Application (`apps/web`) features a high-density, dark-mode design system with responsive layouts and micro-interactions:

```
 ┌───────────────────────────────────────────────────────────────────────────────────┐
 │ 🎙️ VoxFlow    [ Company: Varun Beverages ▼ ]                [ 🟢 Live Voice Ready ] │
 ├────────────────┬──────────────────────────────────────────────────────────────────┤
 │ 📊 Overview    │  📈 TOTAL POs     📦 ACTIVE SKUs     🚚 SHIPMENTS     📞 CALLS LOGS  │
 │ 📦 Stock       │     128              45                18               342        │
 │ 📋 Orders      ├──────────────────────────────────────────────────────────────────┤
 │ 🚚 Shipments   │ 🎙️ REAL-TIME VOICE SIMULATOR                                     │
 │ 👥 Suppliers   │ ┌──────────────────────────────────────────────────────────────┐ │
 │ 📅 Appointments│ │ Vaani: "नमस्ते! Varun Beverages में आपका स्वागत है। मैं..."   │ │
 │ 💬 Outbound    │ │ Supplier: "मुझे PEPSI 500ml का स्टॉक चेक करना है।"            │ │
 │ ⚙️ Simulator   │ └──────────────────────────────────────────────────────────────┘ │
 └────────────────┴──────────────────────────────────────────────────────────────────┘
```

---

## 🚀 Quickstart

### Prerequisites
- Node.js 18+ & `npm`
- Python 3.12+ & `pip`

### 1. Clone & Setup Environment
```bash
git clone https://github.com/jeevesh2515/voxflow-voice-agent.git
cd voxflow-voice-agent
cp .env.example .env
```

### 2. Backend Setup (FastAPI)
```bash
cd apps/api
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Reset and seed multi-tenant demo data
python -m voxflow_api.seed --reset

# Verify multi-tenant database health
python -m voxflow_api.verify_db

# Run unit & integration test suite (15/15 passing)
pytest

# Start FastAPI server
uvicorn voxflow_api.main:app --reload --port 8000
```

### 3. Frontend Setup (Next.js 14)
```bash
cd ../web
npm install
npm run dev
```

Visit:
- **Web Dashboard:** [http://localhost:3000/dashboard](http://localhost:3000/dashboard)
- **Phone Simulator:** [http://localhost:3000/dashboard/simulator](http://localhost:3000/dashboard/simulator)
- **API Documentation:** [http://localhost:8000/docs](http://localhost:8000/docs)

---

## 🌐 Deploying on Vercel

The frontend is ready for instant deployment on **Vercel**:

1. **Fork or Push** this repository to your GitHub account.
2. Go to **[Vercel Dashboard](https://vercel.com/new)** and click **Import Project**.
3. Select the repository root directory (uses [`vercel.json`](vercel.json)).
4. Configure Environment Variables on Vercel:
   ```env
   NEXT_PUBLIC_API_URL=https://your-backend-api.up.railway.app
   NEXT_PUBLIC_WS_URL=wss://your-backend-api.up.railway.app
   ```
5. Click **Deploy**. Your dashboard will be live at `https://your-project.vercel.app`!

---

## 🏗 Architecture

```
                    Browser Phone Simulator / Next.js Dashboard
                                         │
                              WebSocket / HTTP API
                                         │
                                         ▼
               ┌──────────────────────────────────────────────────┐
               │              FastAPI Agent Gateway               │
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

## 🛡 Security & Verification

VoxFlow enforces identity verification to prevent data leaks:
1. **Lookup**: Matches inbound caller phone numbers to tenant suppliers.
2. **Verification Gate**: Prompts callers to state their city or GSTIN before sharing confidential order or stock data.
3. **Escalation Fallback**: Automatically transfers low-confidence queries or unverified callers to human operators.

---

## 📚 Documentation

Detailed specifications and architectural decisions:
- [`ARCHITECTURE.md`](ARCHITECTURE.md) — Latency budget, system topology, folder structure.
- [`PRD.md`](PRD.md) — Product requirements, target FMCG persona, core workflow.
- [`PHASES.md`](PHASES.md) — Week-by-week build roadmap and daily checklists.
- [`RULES.md`](RULES.md) — Development constraints and library guidelines.
- [`DESIGN.md`](DESIGN.md) — Dark neon Tokyo design system specifications.
- [`MEMORY.md`](MEMORY.md) — Live status and verified build items.

---

## 📄 License

Distributed under the **MIT License**. See [`LICENSE`](LICENSE) for more information.
