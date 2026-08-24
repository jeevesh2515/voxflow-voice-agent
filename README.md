<div align="center">

# 🎙️ VoxFlow

### **Enterprise Conversational AI Voice Agent for Modern Supply Chains**
*Automate inbound & outbound supplier operations, purchase-order confirmations, dock scheduling, and live CRM/ERP synchronization with sub-second multilingual voice intelligence.*

<br/>

<p align="center">
  <a href="https://voxflow-voice-agent.vercel.app"><img src="https://img.shields.io/badge/⚡%20LIVE%20SAAS%20DEMO-voxflow--voice--agent.vercel.app-0F766E?style=for-the-badge&labelColor=111827" alt="Live Demo" /></a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/CI%2FCD-100%25%20PASSING-success?style=for-the-badge&logo=githubactions&logoColor=white&labelColor=111827" alt="CI Status" />
  <img src="https://img.shields.io/badge/TESTS-273%20PASSED-10B981?style=for-the-badge&logo=pytest&logoColor=white&labelColor=111827" alt="273 Pytest Tests Passed" />
  <img src="https://img.shields.io/badge/FRONTEND-23%20ROUTES-6366F1?style=for-the-badge&logo=nextdotjs&logoColor=white&labelColor=111827" alt="23 Next.js Routes" />
  <img src="https://img.shields.io/badge/VOICE-ENGLISH%20%28UK%29%20%2B%20HINDI-F97316?style=for-the-badge&labelColor=111827" alt="English (UK) + Hindi Multilingual" />
</p>

<p align="center">
  <img src="https://img.shields.io/badge/CLOUD-AWS%20%2B%20ORACLE%20VM-FF9900?style=for-the-badge&logo=amazonaws&logoColor=white&labelColor=111827" alt="AWS & Oracle VM" />
  <img src="https://img.shields.io/badge/TELEPHONY-AMAZON%20CONNECT%20%2B%20LEX-0284C7?style=for-the-badge&labelColor=111827" alt="Telephony Providers" />
  <img src="https://img.shields.io/badge/DATABASE-SUPABASE%20POSTGRES-3ECF8E?style=for-the-badge&logo=supabase&logoColor=white&labelColor=111827" alt="Supabase Postgres" />
  <a href="LICENSE"><img src="https://img.shields.io/badge/LICENSE-MIT-gray?style=for-the-badge&labelColor=111827" alt="MIT License" /></a>
</p>

<br/>

[**Explore Live SaaS App**](https://voxflow-voice-agent.vercel.app) &nbsp;·&nbsp; [**Implementation Tracker**](DAY_TRACKER.md) &nbsp;·&nbsp; [**System Architecture**](ARCHITECTURE.md) &nbsp;·&nbsp; [**Cloud Setup Guide**](deploy/ORACLE_DEPLOY.md)

</div>

---

## 💼 Executive Summary & ROI for Stakeholders

Supply chain and logistics enterprises handle tens of thousands of repetitive, time-critical phone calls every month—coordinating transporters, verifying purchase-order delivery ETAs, checking warehouse stock levels, and booking loading dock slots.

**VoxFlow** is a B2B AI Voice Operations platform designed to eliminate operational friction and manual call queues:

```
                  ┌─────────────────────────────────────────────────────────┐
                  │                 THE BUSINESS IMPACT                     │
                  ├────────────────────────────┬────────────────────────────┤
                  │   70%+ Inbound Deflection  │   Sub-600ms Voice Latency  │
                  │   Zero Missed PO Check-ins │   Live Google Sheets / ERP │
                  │   24/7 Bilingual Coverage  │   Multi-Tenant Enterprise  │
                  └────────────────────────────┴────────────────────────────┘
```

| Problem in Operations Today | VoxFlow Solution |
|---|---|
| **High Call Center Overhead**: Operations teams spend 40% of their day answering status check calls. | **Autonomous Voice Agent**: Resolves PO inquiries, stock checks, and dock scheduling with zero human intervention. |
| **Language & Dialect Adaptability**: Multi-region drivers and suppliers communicate across regional UK & global dialects. | **Adaptive Speech & Neural Voice Intelligence**: Amazon Lex V2 STT, Groq Whisper Turbo, and Polly/Edge neural speech. |
| **Data Silos & Delayed Data Entry**: Call outcomes are lost in spreadsheets or updated hours after the call ends. | **Real-Time Data Write-Back**: Idempotent synchronization directly into Google Sheets, PostgreSQL, and ERP databases. |
| **Legacy IVR Friction**: Keypad DTMF menus frustrate drivers and delay operational updates. | **Conversational Voice AI**: Spoken natural language understanding powered by **Amazon Connect + Amazon Lex V2**. |

---

## ⚡ Turn Latency Telemetry & Pipeline Breakdown

VoxFlow is a **turn-based voice pipeline** built for low latency. Every Amazon Connect turn is timed server-side — `POST /api/connect/turn` returns and logs a `latency_ms` field — so real per-turn processing time is **measured on live calls, not estimated**. End-to-end glass-to-glass latency (Lex transcribe → agent reasoning → Polly playback) is captured on real UK calls.

```
[Amazon Connect PSTN] ──> [Lambda Bridge · HMAC-SHA256] ──> [Lex V2 en-GB STT] ──> [Groq gpt-oss-20b · AgentRunner] ──> [Amazon Polly Neural en-GB] ──> [Caller]
```

| Pipeline Stage | Technology / Component | Technique |
| :--- | :--- | :--- |
| **Audio Capture** | Amazon Connect (PSTN, G.711 μ-law 8kHz) · Web Audio `AudioWorkletNode` for the browser simulator | Chunked PCM streaming |
| **Speech Detection** | Server-side RMS energy gate | 450ms trailing-silence threshold with barge-in flush |
| **Speech-to-Text** | Amazon Lex V2 (en-GB) on calls · Groq Whisper for the browser simulator | Permissive fallback intent preserves the raw transcript |
| **Agent Reasoning** | Groq `openai/gpt-oss-20b` (tool-calling `AgentRunner`) | Native function-calling — no external agent framework |
| **Audio Synthesis** | Amazon Polly Neural en-GB (Sonia / Amy) on calls · edge-tts for the browser simulator | Neural UK-English playback |
| **Turn Telemetry** | `latency_ms` on every `/api/connect/turn` | Live server-side per-turn timing |

### 🔬 Reproducible Latency & TTFT Benchmark Suite

To measure high-precision P50/P90/P99 latency distributions, TTFT, and generation throughput locally or in CI:

```bash
# Run full benchmark harness across all stages (STT, LLM TTFT, TTS, E2E)
python3 scripts/benchmark_latency.py --iterations 5 --export-markdown BENCHMARK_REPORT.md

# Benchmark live LLM streaming TTFT & tokens/sec throughput on Groq
python3 scripts/benchmark_latency.py --stages llm --mode live --iterations 10
```

Detailed metrics and percentile charts are exported to [`BENCHMARK_REPORT.md`](BENCHMARK_REPORT.md) and [`data/latency_benchmark.json`](data/latency_benchmark.json).

---

## 🏗️ End-to-End System Architecture

```mermaid
flowchart TB
    subgraph Carriers["🌐 Voice Ingestion & Telephony Layer"]
        AWS["📞 Amazon Connect (AWS)<br/>Enterprise Contact Center & DIDs"]
        WEB["💻 In-Browser Simulator<br/>Interactive Mic & WebAudio"]
    end

    subgraph Streaming["⚡ Cloud Gateway & Auth Layer"]
        LMB["AWS Lambda Bridge<br/>HMAC-SHA256 Signed Turns"]
        WSS["WSS Audio Pipeline<br/>G.711 μ-law · VAD · Barge-in"]
        CAD["Caddy Reverse Proxy<br/>Automated Let's Encrypt TLS"]
    end

    subgraph Intelligence["🧠 Core AI Reasoning & Voice Engine"]
        STT["🎙️ Amazon Lex V2 & Groq Whisper<br/>Sub-150ms Speech Recognition"]
        LLM["🤖 Groq & LLM Tool-Calling<br/>Autonomous AgentRunner Engine"]
        TTS["🔊 Amazon Polly & Edge-TTS<br/>Neural en-GB Amy / Sonia Speech"]
    end

    subgraph Tools["⚙️ Durable Operational Tool Layer"]
        T1["📦 PO Status & Tracking"]
        T2["📊 Stock Inventory Check"]
        T3["📅 Dock Appointment Scheduler"]
        T4["🚨 Supervisor Escalation Engine"]
    end

    subgraph Storage["🗄️ Persistence & Enterprise Workspaces"]
        PG["🐘 Supabase PostgreSQL<br/>Dual Engine (Sync + Async)"]
        GS["📑 Live Google Sheets Sync<br/>Idempotent Queue Relay"]
        DASH["🖥️ Next.js 16 SaaS Dashboard<br/>23 Interactive Routes"]
    end

    AWS --> LMB --> CAD
    WEB --> WSS --> CAD

    CAD --> STT --> LLM --> TTS
    LMB --> LLM
    LLM --> Tools

    Tools --> PG
    Tools --> GS
    PG --> DASH

    style Carriers fill:#1E293B,stroke:#38BDF8,color:#F8FAFC
    style Streaming fill:#0F172A,stroke:#818CF8,color:#F8FAFC
    style Intelligence fill:#134E4A,stroke:#2DD4BF,color:#F8FAFC
    style Tools fill:#312E81,stroke:#A78BFA,color:#F8FAFC
    style Storage fill:#1C1917,stroke:#F59E0B,color:#F8FAFC
```

---

## ⚡ Core Platform Capabilities

### 1. 🎙️ Natural Multilingual Voice Intelligence
- **English (UK) & Multilingual Fluency**: Conversational AI tailored for global supply chains, drivers, dispatchers, and warehouse managers.
- **Amazon Lex V2 & Neural Polly Voice**: Real-time speech front door capturing spoken words with sub-second neural speech playback.
- **Instant Speech Barge-In**: When a human speaks while the agent is speaking, the outbound playback queue is flushed immediately within 50ms.
- **Voice Activity Detection (VAD)**: RMS energy filtering with 450ms trailing silence threshold eliminates awkward conversational lag.

### 2. 📦 Autonomous Supply Chain Workflows
- **Purchase Order Inquiries**: Look up order numbers, item quantities, delivery statuses, and supplier milestones.
- **Real-Time Stock Checks**: Query SKU quantities across multiple warehouse storage bins and availability status.
- **Dock Appointment Booking**: Schedule loading and unloading appointments with automated conflict validation.
- **Smart Escalations**: Detects caller frustration or complex disputes and transfers call to a human supervisor with complete conversation summaries.

### 3. 📑 Live Enterprise Data Synchronization
- **Live Google Sheets Mirror**: Appends every call turn, order update, and appointment directly into Google Sheets with background idempotency retry queues.
- **Transactional Outbox Pattern**: Guarantees zero lost turns even during network dropouts or backend restarts.

### 4. 🏢 Multi-Tenant SaaS Workspace
- **Organization & Role-Based Isolation**: Distinct workspaces for individual companies (e.g., Varun Beverages, Amul) with dedicated phone numbers and isolated data partitions.
- **Full Operational Dashboard**: 23 compiled Next.js routes covering Calls, Escalations, Appointments, Inventory, Shipments, Campaigns, and Web-based Call Simulators.

---

## 📞 Telephony & Voice Channels

VoxFlow provides flexible voice interfaces for enterprise operations and rapid testing:

| Provider / Channel | Inbound Routing | Capabilities | Integration Mechanism |
|---|---|---|---|
| **Amazon Connect (AWS)** | Dedicated Enterprise DID *(Assigned per tenant)* | 90 Free Min/Mo, Global Contact Center, AWS Polly Neural Voices | AWS Lambda Bridge (`VoxFlow-Connect-Bridge`) + Amazon Lex V2 STT + REST Turns |
| **In-Browser Simulator** | Interactive Web Microphone | 100% Free, Zero Telecom Setup, Direct Streaming | WebAudio WebSocket at `/dashboard/simulator` |

---

## 🚀 Quickstart & Local Development

### Prerequisites
- Python 3.12+
- Node.js 20+ (Node 22 recommended)
- PostgreSQL (or local SQLite)

### 1. Clone the Repository
```bash
git clone https://github.com/jeevesh2515/voxflow-voice-agent.git
cd voxflow-voice-agent
```

### 2. Configure Environment Variables
```bash
cp .env.example .env
# Edit .env with your LLM keys, database credentials, and Connect settings
```

### 3. Start the Backend API
```bash
cd apps/api
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Run initial seed migrations
python -m voxflow_api.seed --reset

# Run backend server
uvicorn voxflow_api.main:app --host 0.0.0.0 --port 8000 --reload
```

### 4. Start the Frontend Dashboard
```bash
# In another terminal window from the repo root
npm install
npm run dev
# Dashboard opens at http://localhost:3000
```

---

## 🧪 Comprehensive Verification Suite

Run all automated test suites locally:

```bash
# 1. Run full backend test suite (265 unit, integration & resilience tests)
cd apps/api
pytest tests/ -v

# 2. Run backend linter
ruff check .

# 3. Run mock audio stream feeder (simulates real-time 16kHz PCM streaming & latency telemetry)
python3 ../../scripts/test_audio_stream.py

# 4. Run frontend typecheck and static build
cd ../web
npm run build
```

---

## 📊 Deployment & Infrastructure

- **Cloud Backend**: Docker Compose running on an **Oracle Cloud Always-Free ARM VM** (4 OCPU, 24GB RAM) with **Caddy** automated TLS reverse proxy.
- **Cloud Frontend**: **Vercel** Edge Network with sub-100ms global static asset delivery.
- **Serverless Voice Bridge**: **AWS Lambda** (`us-west-2`) integrated with **Amazon Connect Contact Flows**.
- **Live VM Sync Command**: `./deploy/sync-vm.sh` (automated code push, database migration, container reload, and zero-downtime health verification).

---

## 🏢 Enterprise Inquiries, Custom Pilots & Product Demos

VoxFlow is available as an enterprise B2B SaaS platform with private cloud deployment options (AWS, Oracle Cloud, Azure) or fully managed multi-tenant instances.

If you are a business stakeholder, supply chain leader, or enterprise partner interested in:
- **Scheduling a Live Interactive Voice Agent Demonstration**
- **Launching a Customized Pilot with Dedicated Phone Lines (US / UK / India)**
- **Connecting VoxFlow to your ERP (SAP, Oracle, NetSuite), WMS, or Custom Database**
- **Commercial Licensing, SLA Support, and Tenant Onboarding**

👉 **Get in touch with the founder**: [Open a GitHub Inquiry](https://github.com/jeevesh2515/voxflow-voice-agent/issues) or reach out directly to discuss your supply chain workflow requirements.

---

## 📄 License

Distributed under the [MIT License](LICENSE). Built for enterprise scalability and modern supply chains.
