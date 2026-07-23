<div align="center">

# 🎙️ VoxFlow

### *Autonomous Voice AI & Real-Time Operations SaaS Platform for FMCG & Supply Chain Enterprises*

[![Next.js 14](https://img.shields.io/badge/Next.js-14.2-black?style=for-the-badge&logo=next.js)](https://nextjs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=for-the-badge&logo=fastapi)](https://fastapi.tiangolo.com/)
[![Python 3.12](https://img.shields.io/badge/Python-3.12-3776AB?style=for-the-badge&logo=python)](https://python.org)
[![Supabase](https://img.shields.io/badge/Supabase-Postgres-3ECF8E?style=for-the-badge&logo=supabase)](https://supabase.com)
[![Tailwind CSS](https://img.shields.io/badge/Tailwind-v3.4-38B2AC?style=for-the-badge&logo=tailwind-css)](https://tailwindcss.com)
[![Vercel Ready](https://img.shields.io/badge/Vercel-Deployed-000000?style=for-the-badge&logo=vercel)](https://vercel.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](LICENSE)

<br />

[![Deploy with Vercel](https://vercel.com/button)](https://vercel.com/new/clone?repository-url=https%3A%2F%2Fgithub.com%2Fjeevesh2515%2Fvoxflow-voice-agent)

<p align="center">
  <a href="#-overview">Overview</a> •
  <a href="#-key-capabilities">Capabilities</a> •
  <a href="#-multi-tenant-architecture">Multi-Tenancy</a> •
  <a href="#-ops-dashboard--simulator">Dashboard & Simulator</a> •
  <a href="#-quickstart">Quickstart</a> •
  <a href="#-system-architecture">Architecture</a> •
  <a href="#-enterprise-security">Security</a>
</p>

</div>

---

## ⚡ Overview

**VoxFlow** is a multi-tenant, enterprise voice AI SaaS platform engineered to automate inbound supplier, customer, and partner phone calls for FMCG brands, regional distributors, and logistics operators.

Operating seamlessly in **Hindi & English** with ultra-low latency, VoxFlow automates transactional call workflows end-to-end:

- 🔒 **Identity Verification**: Multi-factor caller authentication via registered phone numbers, city match, or GSTIN challenges before data disclosure.
- 📦 **Inventory & Stock Management**: Real-time multi-warehouse inventory lookups and stock availability confirmation.
- ⚡ **Autonomous Purchase Orders**: Conversational natural language slot-filling to generate, validate, and record Purchase Orders directly into the core database.
- 🚚 **Logistics & Shipment Tracking**: Real-time dispatch status, ETA lookup, and carrier tracking queries.
- 📅 **Dock & Meeting Scheduling**: Automated appointment booking for dock arrivals and supplier reviews.
- 💬 **Omnichannel Dispatch**: Instant multi-channel notifications via automated email confirmations and direct WhatsApp messages.
- 🖥️ **Live Operations Control Center**: Real-time dashboard with call monitoring, full transcripts, confidence scores, and seamless human escalation controls.

---

## ✨ Key Capabilities

| Capability | Description | Tech Stack |
|---|---|---|
| **🏢 Multi-Tenant Workspace Engine** | Dynamic enterprise tenant switching with complete database & state isolation | React Context + FastAPI Middleware + Supabase RLS |
| **🎙️ Bilingual Voice AI Engine** | Natural, human-like voice synthesis and transcription in Hindi (`hi-IN`) & English (`en-IN`) | Local Whisper STT + Groq LLM (Llama 3.1) + Edge-TTS |
| **🔒 Identity Security Gate** | Caller authorization challenge (City / GSTIN) before disclosing business data | Automated Tool Execution Guard |
| **📱 Real-Time Phone Simulator** | In-browser WebSocket phone simulator for live voice and text testing | WebSockets (`ws/call`) + Audio Streaming |
| **⚡ Automated Order Processing** | Natural language slot-filling and confirmation engine for PO creation | LLM Tool Calling Engine |
| **🚀 Cloud Deployment Ready** | Pre-configured for cloud backend deployment and Vercel serverless hosting | Next.js 14 + FastAPI + Docker / Vercel |

---

## 🏢 Multi-Tenant Enterprise Architecture

VoxFlow is built natively for multi-tenancy. A single platform deployment safely handles isolated organizational workspaces:

```
                  VoxFlow Enterprise Workspace Switcher
                                    │
    ┌───────────────────┬───────────┴───────────┬───────────────────┐
    ▼                   ▼                       ▼                   ▼
     Company A           Company B               Company C           Company D
(FMCG Beverages)    (Dairy Products)       (Snacks & Foods)     (Bakery & Goods)
```

Each tenant workspace maintains complete logical data isolation for:
- Suppliers & Client Contacts
- Product Catalogs, Warehouses & Live Stock
- Active Purchase Orders & Shipment Histories
- Scheduled Appointments & Communication Dispatch Logs

---

## 🎨 Ops Dashboard & Simulator

The VoxFlow Dashboard (`apps/web`) offers a high-density, dark neon operations console designed for live call monitoring:

```
 ┌───────────────────────────────────────────────────────────────────────────────────┐
 │ 🎙️ VoxFlow    [ Workspace: Company A ▼ ]                    [ 🟢 Live Voice Ready ] │
 ├────────────────┬──────────────────────────────────────────────────────────────────┤
 │ 📊 Overview    │  📈 TOTAL POs     📦 ACTIVE SKUs     🚚 SHIPMENTS     📞 CALL LOGS   │
 │ 📦 Stock       │     128              45                18               342        │
 │ 📋 Orders      ├──────────────────────────────────────────────────────────────────┤
 │ 🚚 Shipments   │ 🎙️ REAL-TIME VOICE PHONE SIMULATOR                               │
 │ 👥 Suppliers   │ ┌──────────────────────────────────────────────────────────────┐ │
 │ 📅 Appointments│ │ Agent: "Welcome to VoxFlow Voice Ops. How can I help?"        │ │
 │ 💬 Outbound    │ │ Caller: "I need to check stock for PEPSI 500ml."             │ │
 │ ⚙️ Simulator   │ └──────────────────────────────────────────────────────────────┘ │
 └────────────────┴──────────────────────────────────────────────────────────────────┘
```

---

## 🚀 Quickstart

### Prerequisites
- Node.js 18+ & `npm`
- Python 3.12+ & `pip`

### 1. Clone & Configure Environment
```bash
git clone https://github.com/jeevesh2515/voxflow-voice-agent.git
cd voxflow-voice-agent
cp .env.example .env
```

### 2. Start Backend API (FastAPI)
```bash
cd apps/api

# Create & activate Python environment
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Initialize database schema & seed demo workspace data
python -m voxflow_api.seed --reset

# Run backend test suite
pytest

# Launch FastAPI server
uvicorn voxflow_api.main:app --reload --port 8000
```

### 3. Start Frontend Dashboard (Next.js 14)
```bash
cd ../web
npm install
npm run dev
```

Access local services:
- **Web Dashboard:** [http://localhost:3000/dashboard](http://localhost:3000/dashboard)
- **Phone Simulator:** [http://localhost:3000/dashboard/simulator](http://localhost:3000/dashboard/simulator)
- **API Documentation:** [http://localhost:8000/docs](http://localhost:8000/docs)

---

## 🏗 System Architecture

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
                Supabase Postgres                     Next.js 14
             (Tenant Data Store)                 (Dashboard UI on Vercel)
```

---

## 🛡 Enterprise Security & Compliance

VoxFlow is built with security and compliance best practices:

1. **Parameterized Queries**: 100% ORM-driven SQL queries via SQLAlchemy to prevent SQL injection vulnerabilities.
2. **Tenant Scoping**: All API endpoints and background tool execution handlers strictly enforce tenant context matching.
3. **Verification Challenge**: Confidential inventory and financial order data are protected behind mandatory caller authentication challenges.
4. **Human Escalation Guard**: Low-confidence or unverified voice interactions are automatically routed to human operators.

---

## 📄 License

Distributed under the **MIT License**. See [`LICENSE`](LICENSE) for details.
