# 🤝 Claude Code Master Handoff Document: VoxFlow Voice Agent

> **Status**: Production-Ready MVP (Multi-Carrier Cloud Architecture)  
> **Last Verified**: August 23, 2026  
> **Tests**: **279/279 Passing** (Backend `pytest`) | **23/23 Static Routes** (Frontend `next build`)  
> **Repository**: [jeevesh2515/voxflow-voice-agent](https://github.com/jeevesh2515/voxflow-voice-agent) (branch: `main`)

---

## 🎯 1. System Overview & Architecture

VoxFlow is a multi-tenant, cloud-native conversational AI voice agent engineered for enterprise workflow automation. It handles inbound and outbound supplier/customer calls, order status inquiries, delivery scheduling, inventory audits, and escalation management with real-time Google Sheets synchronization.

```
                                ┌──────────────────────────────────────────────────────────┐
                                │                    TELEPHONY CARRIERS                    │
                                └──────┬────────────────────┬────────────────────┬─────────┘
                                       │                    │                    │
                          Twilio (UK DID)      Telnyx (US DID)      AWS Connect (UK DID)
                          +44 7460 041934      +1 802 589 8040      +44 20 4640 4552
                                       │                    │                    │
                                       ▼                    ▼                    ▼
                                ┌─────────────┐      ┌─────────────┐      ┌─────────────┐
                                │ POST /twilio│      │ POST /telnyx│      │ AWS Lambda  │
                                │   /voice    │      │   /voice    │      │   Bridge    │
                                └──────┬──────┘      └──────┬──────┘      └──────┬──────┘
                                       │                    │                    │
                                       ▼                    ▼                    │
                                ┌──────────────────────────────────┐             │
                                │   WSS Audio Stream (G.711 μ-law) │             │
                                │    /twilio/media & /telnyx/media │             │
                                └──────────────────┬───────────────┘             │
                                                   │                             │
                                                   ▼                             ▼
┌──────────────────────────────────────────────────────────────────────────────────────────┐
│                             VOXFLOW FASTAPI BACKEND (Python 3.12)                        │
│                                                                                          │
│  ┌───────────────────────┐   ┌───────────────────────┐   ┌────────────────────────────┐  │
│  │   Speech-to-Text      │   │     LLM Reasoning     │   │      Text-to-Speech        │  │
│  │   Groq Whisper Turbo  │──▶│   OpenAI GPT-4o-mini  │──▶│      Microsoft Edge-TTS    │  │
│  │   (8k -> 16k resample)│   │   Tool-Calling Agent  │   │      G.711 μ-law / Amazon  │  │
│  └───────────────────────┘   └───────────┬───────────┘   │      Polly Neural Voices   │  │
│                                          │               └────────────────────────────┘  │
│                                          ▼                                               │
│                              ┌───────────────────────┐                                   │
│                              │   Durable Tool Engine │                                   │
│                              │  - PO / Stock lookup  │                                   │
│                              │  - Appointment booking│                                   │
│                              │  - Google Sheets sync │                                   │
│                              └───────────┬───────────┘                                   │
└──────────────────────────────────────────┼───────────────────────────────────────────────┘
                                           │
                                           ▼
┌──────────────────────────────────────────────────────────────────────────────────────────┐
│                               DATABASE & PERSISTENCE LAYER                               │
│                                                                                          │
│  - Supabase PostgreSQL (Production) / SQLite (Local Tests)                               │
│  - Dual SQLAlchemy Engine: Sync (Psycopg2 REST) + Async (AsyncPG Tools)                  │
│  - Live Google Sheets Service Account: Append + Idempotent Queue Sync                    │
└──────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 📞 2. Telephony Matrix & Active Credentials

| Provider | Live Active Number | Protocol / Mechanism | Destination & Endpoint |
|---|---|---|---|
| **Amazon Connect (AWS)** | **`+44 20 4640 4552`** | Contact Flow $\rightarrow$ Lambda Bridge | `arn:aws:lambda:us-west-2:031247250483:function:VoxFlow-Connect-Bridge` $\rightarrow$ `POST /api/connect/turn` |
| **Twilio** | **`+44 7460 041934`** | TwiML Webhook + WebSocket Streaming | `POST /twilio/voice` + `WSS /twilio/media` |
| **Telnyx** | **`+1 802 589 8040`** | TeXML Webhook + WebSocket Streaming | `POST /telnyx/voice` + `WSS /telnyx/media` |
| **In-Browser Simulator** | *N/A (Microphone)* | Direct Browser Audio WebSocket | `WSS /ws/call` on `/dashboard/simulator` |

---

## 🗄️ 3. Deployment Environments & Infrastructure

### 🌐 Live Endpoints
- **Frontend App**: `https://voxflow-voice-agent.vercel.app` (or `https://voxflow-jeevesh.duckdns.org`)
- **Backend API**: `https://voxflow-jeevesh.duckdns.org` (Oracle Cloud VM, automated Caddy TLS)
- **Render Backup Backend**: `https://voxflow-voice-agent.onrender.com`
- **Database**: Supabase PostgreSQL (`aws-0-eu-central-1.pooler.supabase.com:5432`)

### 🔑 Environment Variables (`.env`)
```ini
# Core Backend
PORT=8000
DATABASE_URL=postgresql://postgres.epfdrwdfpqqyqfxffxol:VoxFlowPostgres2026@aws-0-eu-central-1.pooler.supabase.com:5432/postgres
DEFAULT_TENANT_ID=varun
PUBLIC_BASE_URL=https://voxflow-jeevesh.duckdns.org

# AI Models
OPENAI_API_KEY=sk-proj-...
GROQ_API_KEY=gsk_...
LANGSMITH_API_KEY=lsv2_pt_...

# Telephony
TELEPHONY_PROVIDER=connect
TWILIO_ACCOUNT_SID=AC_YOUR_TWILIO_SID_HERE
TWILIO_AUTH_TOKEN=YOUR_TWILIO_AUTH_TOKEN_HERE
TWILIO_PHONE_NUMBER=+447460041934
TWILIO_VALIDATE_SIGNATURE=true

# Amazon Connect (AWS Free Tier - 90 min/mo)
CONNECT_LAMBDA_SECRET=voxflow_connect_shared_secret_2026
CONNECT_INSTANCE_ID=voxflow-agent
CONNECT_LAMBDA_ARN=arn:aws:lambda:us-west-2:031247250483:function:VoxFlow-Connect-Bridge
CONNECT_PHONE_NUMBER=+442046404552
CONNECT_REGION=us-west-2

# Telnyx (Free $5 Signup Credit)
TELNYX_PHONE_NUMBER=+18025898040
TELNYX_VALIDATE_SIGNATURE=false

# Google Sheets
SHEETS_ENABLED=true
GOOGLE_SERVICE_ACCOUNT_JSON='{"type": "service_account", ...}'
```

---

## 🧪 4. Testing & Verification Guide

### Backend Tests
```bash
cd apps/api
source .venv/bin/activate
pytest tests/ -q
# Expected result: 279 passed in ~55s
```

### Frontend Build Verification
```bash
cd apps/web
npm run build
# Expected result: 23 static pages generated, 0 TypeScript errors
```

### AWS Lambda Deployment
```bash
# Update Lambda code in AWS automatically
VOXFLOW_LAMBDA_NAME=VoxFlow-Connect-Bridge AWS_REGION=us-west-2 VOXFLOW_API_URL=https://voxflow-jeevesh.duckdns.org ./deploy/aws/deploy-lambda.sh
```

### Oracle VM Deployment Sync
```bash
# Sync latest code and reload Docker containers on the VM
./deploy/sync-vm.sh
```

---

## 🚀 5. Roadmap & Next Tasks for Claude Code

When starting your next session with Claude Code, here are the recommended next priorities:

1. **Amazon Connect Contact Flow Customization**:
   - In AWS Amazon Connect console (`voxflow-agent.my.connect.aws`), link the custom contact flow prompt to handle DTMF fallback and multi-lingual voice prompts (`Aditi` vs `Kajal` vs `Joanna`).
2. **Outbound Voice Campaign Dispatching**:
   - Connect the `/dashboard/campaigns` UI directly to `POST /api/campaigns/{id}/dispatch` for automated batch outbound supplier notifications.
3. **Advanced Webhook Signature Verification**:
   - Add automated Ed25519 signature checks for Telnyx V2 webhooks in production mode.
4. **Frontend Realtime WebSocket Feed**:
   - Enhance the live calls dashboard (`/dashboard/calls`) with real-time waveform visualization during active calls.
