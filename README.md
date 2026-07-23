<div align="center">

# 🎙️ VoxFlow Voice Agent

### *Bilingual Autonomous Voice AI & Live Operations Platform for FMCG Distributors*

[![Next.js 14](https://img.shields.io/badge/Next.js-14.2-black?style=for-the-badge&logo=next.js)](https://nextjs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=for-the-badge&logo=fastapi)](https://fastapi.tiangolo.com/)
[![Python 3.12](https://img.shields.io/badge/Python-3.12-3776AB?style=for-the-badge&logo=python)](https://python.org)
[![Tests Passing](https://img.shields.io/badge/Pytest-15%2F15%20Passing-brightgreen?style=for-the-badge&logo=pytest)](apps/api/tests/test_api.py)
[![Supabase](https://img.shields.io/badge/Supabase-Postgres-3ECF8E?style=for-the-badge&logo=supabase)](https://supabase.com)
[![Tailwind CSS](https://img.shields.io/badge/Tailwind-v3.4-38B2AC?style=for-the-badge&logo=tailwind-css)](https://tailwindcss.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](LICENSE)

<br />

<p align="center">
  <a href="#-what-is-voxflow">What is VoxFlow?</a> •
  <a href="#-implemented-features--status">Implemented Features</a> •
  <a href="#-11-specialized-agent-tools">Agent Tools</a> •
  <a href="#-multi-tenant-architecture">Multi-Tenancy</a> •
  <a href="#-quickstart">Quickstart</a> •
  <a href="#-architecture--documentation">Architecture & Docs</a>
</p>

</div>

---

## ⚡ What is VoxFlow?

**VoxFlow** is a bilingual (Hindi & English) voice AI agent platform built for regional FMCG distributors and carrying & forwarding (C&F) agents in India (e.g. Varun Beverages / PepsiCo, Amul Dairy, Haldirams, Britannia).

It automates high-volume inbound phone calls from retail networks and quick-commerce partners (Swiggy Instamart, Blinkit, Flipkart Minutes, Zepto):
- 🔍 **Identify & Verify Callers**: Phone lookup and Tier-1 city/GSTIN identity verification.
- 📦 **Stock Checks & PO Creation**: Instant stock availability queries across warehouses and conversational Purchase Order creation.
- 🚚 **Shipment Tracking**: Real-time delivery status and ETA queries.
- 📅 **Appointment Scheduling**: Dock arrival slots and supplier meeting bookings.
- 📊 **Live Operations Dashboard**: High-density dark neon ops console for live transcripts, orders, stock, and escalation management.

---

## ✅ Implemented Features & Status

| Module / Component | Implementation Details | Status |
|---|---|---|
| **FastAPI Backend (`apps/api`)** | Async FastAPI server with CORS, health routes, summary stats, REST endpoints | ✅ Complete |
| **Agent State Engine** | LangGraph-inspired tool-calling loop (`runner.py`) with max-iteration guard | ✅ Complete |
| **Pluggable LLM Providers** | Groq (Llama 3.1 8B), Ollama, and OpenRouter integration via uniform SDK | ✅ Complete |
| **11 Agent Tools** | Stock, PO creation, supplier lookup, caller verification, email, WhatsApp, etc. | ✅ Complete |
| **Bilingual Voice Pipeline** | Local STT (`faster-whisper`) + `edge-tts` (Hindi `hi-IN` & English `en-IN`) | ✅ Complete |
| **Browser Phone Simulator** | Real-time WebSocket streaming audio/text phone simulator in dashboard | ✅ Complete |
| **Multi-Tenant Architecture** | `tenant_id` on all DB models (`schema.md`), RLS blueprint, topbar company switcher | ✅ Complete |
| **Next.js 14 Dashboard (`apps/web`)** | Dark neon Tokyo design system with Overview, Stock, POs, Shipments, Suppliers | ✅ Complete |
| **Automated Testing Suite** | Comprehensive pytest suite passing 15/15 unit and integration tests | ✅ 15/15 Passing |

---

## 🛠 11 Specialized Agent Tools

The AI agent executes structured backend functions in real time during phone calls:

1. `lookup_supplier`: Finds supplier record by phone number or partial name.
2. `verify_caller`: Verifies caller identity via city or GSTIN challenge.
3. `check_stock`: Queries real-time stock levels for SKUs across warehouses.
4. `get_shipment_status`: Retrieves tracking and delivery status for POs.
5. `create_po`: Creates a new Purchase Order with items, quantities, and totals.
6. `verify_po`: Validates PO details before finalizing.
7. `schedule_appointment`: Schedules dock arrival or supplier meetings.
8. `send_email`: Dispatches order summaries or confirmations via email.
9. `send_whatsapp_message`: Sends instant WhatsApp updates to suppliers.
10. `update_worksheet`: Logs custom structured updates to tenant worksheets.
11. `escalate_to_human`: Flags call for human intervention when confidence is low.

---

## 🏢 Multi-Tenant Architecture

VoxFlow enforces strict multi-tenancy at every level — database schemas, tool queries, and frontend dashboards scope data strictly to the active workspace:

```
                  VoxFlow Control Center (Topbar Tenant Switcher)
                                        │
    ┌───────────────────┬───────────────┴───────────────┬───────────────────┐
    ▼                   ▼                               ▼                   ▼
Varun Beverages     Amul Dairy                   Haldirams Snacks    Britannia Foods
(PepsiCo FMCG)    (Dairy & Cold Supply)       (Confectionery & Spices)  (Bakery & Biscuits)
```

---

## 🚀 Quickstart

### Prerequisites
- Python 3.12+
- Node.js 18+ & `npm`

### 1. Backend Setup (FastAPI)

```bash
cd apps/api

# Create & activate virtual environment
python3.12 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Seed multi-tenant demo database
python -m voxflow_api.seed --reset

# Verify database health
python -m voxflow_api.verify_db

# Run unit & integration tests
pytest

# Start FastAPI dev server
uvicorn voxflow_api.main:app --reload --port 8000
```

### 2. Frontend Setup (Next.js 14)

```bash
cd apps/web

# Install dependencies
npm install

# Start Next.js dev server
npm run dev
```

Visit:
- **Web Dashboard:** [http://localhost:3000/dashboard](http://localhost:3000/dashboard)
- **Phone Simulator:** [http://localhost:3000/dashboard/simulator](http://localhost:3000/dashboard/simulator)
- **API Documentation:** [http://localhost:8000/docs](http://localhost:8000/docs)

---

## 🏗 Architecture & Documentation

Project design and execution guidelines are documented in master planning files:

- [`ARCHITECTURE.md`](ARCHITECTURE.md) — System topology, latency-critical path budget, folder structure.
- [`PRD.md`](PRD.md) — Problem statement, target FMCG persona, core workflow, success metrics.
- [`PHASES.md`](PHASES.md) — Week-by-week build roadmap and daily definition of done.
- [`RULES.md`](RULES.md) — Architectural constraints, approved libraries, AI developer boundaries.
- [`DESIGN.md`](DESIGN.md) — Dark neon Tokyo visual identity, color tokens, typography.
- [`MEMORY.md`](MEMORY.md) — Live build status and verified completed items.

---

## 🛡 Security & Verification

VoxFlow strictly enforces security controls per [`security_audit.md`](.planning/security_audit.md):
- **Parameterized SQL Queries**: All database queries use SQLAlchemy ORM (`select(...)`, `.where(...)`) to eliminate SQL injection risks.
- **Tenant Isolation**: All database queries require `session.tenant_id`.
- **Identity Gate**: Caller verification (city / GSTIN challenge) required before disclosing order or stock data.

---

## 📄 License

Distributed under the **MIT License**. See [`LICENSE`](LICENSE) for details.
