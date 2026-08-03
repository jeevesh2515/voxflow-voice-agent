# VoxFlow — Setup & Deployment Guide

Everything below runs on a hosted service. Nothing runs on your laptop, and
nothing needs to stay switched on at home.

**Total time:** about 90 minutes end to end, most of it waiting.
**Total cost:** **$0/month** for infrastructure, plus Twilio (~$1.15/month for
a number and ~$0.013/minute of call time). Your Twilio trial credit covers
testing.

---

## What you are deploying

```
   Caller's phone
        │
        ▼
   Twilio  ──────── the only paid piece
        │  webhook + Media Stream (audio)
        ▼
   Oracle Cloud VM  ── FREE forever
   ├── Caddy      → automatic HTTPS certificate
   └── VoxFlow API (FastAPI, Docker)
        │
        ├──→ Groq          LLM + speech-to-text   FREE
        ├──→ edge-tts      speech synthesis        FREE
        ├──→ Supabase      Postgres database       FREE
        └──→ Google Sheets call log                FREE
        │
        ▼
   Vercel ── dashboard (already deployed)  FREE
```

**Why the backend can't live on Vercel:** a phone call holds a WebSocket open
for its entire duration. Vercel's serverless functions can't do that, and they
have no persistent memory for call state. The dashboard stays on Vercel; the
API needs a real always-on server.

---

## Before you start

Create these accounts. All free, all take about two minutes each:

| Service | URL | Card needed? |
|---|---|---|
| Groq | console.groq.com | No |
| Supabase | supabase.com | No |
| Google Cloud | console.cloud.google.com | No (for Sheets API) |
| Oracle Cloud | cloud.oracle.com | Yes — identity check only, never charged |
| DuckDNS | duckdns.org | No |
| Twilio | twilio.com | Yes — this one does cost money |

> **On Oracle and the card:** Oracle asks for a card to verify you're a real
> person. The Always Free resources stay free forever and your account cannot
> silently start charging you — it stays in a restricted "Always Free" mode
> unless you deliberately upgrade.

---

## Step 1 — Groq (LLM + speech-to-text)

1. Go to **console.groq.com** → sign in → **API Keys** → **Create API Key**.
2. Copy it now; you cannot view it again.

Keep it for `GROQ_API_KEY`. One key powers both the conversation model and
speech recognition.

---

## Step 2 — Supabase (database)

1. **supabase.com** → **New project**. Pick a region near your callers
   (`Mumbai (ap-south-1)` for India). Set a strong database password and
   save it.
2. Wait ~2 minutes for provisioning.
3. Go to **SQL Editor** → **New query**. Paste the entire contents of
   `schema.md`'s DDL block (section 1) and click **Run**. That creates the
   base tables.
4. **New query** again. Paste all of `migrations/001_customer_support_flow.sql`
   and **Run**. That adds PO signing, call outcomes, and tenant phone mapping.
5. Go to **Project Settings → Database → Connection string → URI**.
   Copy it, and replace `[YOUR-PASSWORD]` with the password from step 1.

> Use the **direct** connection on port **5432** — not the transaction pooler
> on 6543. VoxFlow is a long-running server; the pooler is for serverless.

Keep this for `DATABASE_URL`.

**One caveat:** Supabase free projects pause after 7 days with no activity.
A live phone line keeps it awake. If you leave the project idle for a week,
unpause it from the dashboard.

---

## Step 3 — Google Sheets (the call log)

This is where your ops team reads why people called and whether they left happy.

1. Create a new Google Sheet. Name the first tab exactly **`Call Log`**.
2. From the URL, copy the ID:
   `docs.google.com/spreadsheets/d/`**`1a2b3c...xyz`**`/edit`
   → that's `GOOGLE_SHEET_ID`.
3. Go to **console.cloud.google.com** → create a project (any name).
4. **APIs & Services → Library** → search **Google Sheets API** → **Enable**.
5. **APIs & Services → Credentials → Create Credentials → Service account**.
   Name it `voxflow-sheets`, click through, and create it.
6. Open the new service account → **Keys** → **Add key → Create new key →
   JSON**. A `.json` file downloads.
7. Open that JSON and copy the `client_email` value — it looks like
   `voxflow-sheets@your-project.iam.gserviceaccount.com`.
8. **Back in your Google Sheet**, click **Share**, paste that email, give it
   **Editor**, and untick "Notify people". **Skip this and nothing will ever
   be written** — the service account is a separate identity from your own
   Google account.

### Flattening the JSON for the env file

The whole JSON has to go on one line. Run this wherever you downloaded it:

```bash
# macOS / Linux
python3 -c "import json,sys;print(json.dumps(json.load(open(sys.argv[1]))))" service-account.json
```

Copy the output and put it in `.env` **wrapped in single quotes**:

```
GOOGLE_SERVICE_ACCOUNT_JSON='{"type":"service_account","project_id":"..."}'
```

---

## Step 4 — Oracle Cloud VM (your free server)

### 4.1 Create the instance

1. **cloud.oracle.com** → sign in → **Compute → Instances → Create instance**.
2. **Name:** `voxflow-api`
3. **Image:** Canonical **Ubuntu 24.04**
4. **Shape:** click **Change shape** → **Ampere** → `VM.Standard.A1.Flex`
   → set **1 OCPU / 6 GB RAM**. This is inside the Always Free allowance.
5. **SSH keys:** choose **Generate a key pair** and **download the private
   key**. You cannot download it later.
6. Make sure **Assign a public IPv4 address** is enabled.
7. **Create**.

> **If Oracle says "Out of capacity"** — this is common for Ampere A1 and is
> not something you did wrong. Two options:
> - Retry every few hours, or try a different Availability Domain in the region.
> - Or switch the shape to **`VM.Standard.E2.1.Micro`** (AMD, 1 OCPU, 1 GB RAM),
>   which is also Always Free and almost always available. VoxFlow's container
>   idles around 250 MB, so 1 GB is genuinely enough — this is a perfectly
>   good fallback, not a downgrade you'll regret.

Note the **public IP address** once it boots.

### 4.2 Open the firewall — both layers

Oracle blocks ports in *two* places, and forgetting the second is the single
most common reason a deployment appears dead.

**Layer 1 — the virtual network:**
Instance page → **Virtual cloud network** → **Security Lists** → **Default
Security List** → **Add Ingress Rules**, twice:

| Source CIDR | IP Protocol | Destination Port |
|---|---|---|
| `0.0.0.0/0` | TCP | `80` |
| `0.0.0.0/0` | TCP | `443` |

**Layer 2 — the VM's own iptables.** SSH in:

```bash
chmod 400 ~/Downloads/ssh-key-*.key
ssh -i ~/Downloads/ssh-key-*.key ubuntu@YOUR_PUBLIC_IP
```

Then:

```bash
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 80 -j ACCEPT
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 443 -j ACCEPT
sudo netfilter-persistent save
```

### 4.3 Install Docker

```bash
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER
newgrp docker          # applies the group without logging out
docker --version       # confirm
```

---

## Step 5 — A free domain with DuckDNS

Twilio requires a valid HTTPS certificate, and certificates need a hostname.
DuckDNS gives you one free.

1. **duckdns.org** → sign in with Google/GitHub.
2. Create a subdomain, e.g. `voxflow-yourname` → you get
   `voxflow-yourname.duckdns.org`.
3. Set the **current ip** field to your Oracle VM's public IP → **update ip**.
4. Confirm it resolves (from your own machine):
   ```bash
   ping voxflow-yourname.duckdns.org
   ```
   It should show your VM's IP.

---

## Step 6 — Deploy

SSH into the VM again, then:

```bash
git clone https://github.com/jeevesh2515/voxflow-voice-agent.git
cd voxflow-voice-agent
cp .env.example .env
nano .env
```

Fill in every value you collected. The ones that must be right:

```ini
GROQ_API_KEY=gsk_...
DATABASE_URL=postgresql://postgres:PASSWORD@db.xxxx.supabase.co:5432/postgres
TWILIO_ACCOUNT_SID=AC...
TWILIO_AUTH_TOKEN=...
PUBLIC_BASE_URL=https://voxflow-yourname.duckdns.org
GOOGLE_SERVICE_ACCOUNT_JSON='{"type":"service_account",...}'
GOOGLE_SHEET_ID=1a2b3c...
DOMAIN=voxflow-yourname.duckdns.org
ACME_EMAIL=you@example.com
API_CORS_ORIGINS=https://voxflow-voice-agent.vercel.app
```

Save (`Ctrl+O`, `Enter`, `Ctrl+X`), then start it:

```bash
docker compose -f deploy/docker-compose.prod.yml up -d --build
```

First build takes 3–5 minutes. Then check:

```bash
docker compose -f deploy/docker-compose.prod.yml logs -f
```

Caddy will fetch a certificate automatically — watch for
`certificate obtained successfully`. Then verify from anywhere:

```bash
curl https://voxflow-yourname.duckdns.org/api/health
# {"status":"ok",...}
```

If you get valid JSON over HTTPS, the hard part is done.

---

## Step 7 — Twilio

1. **console.twilio.com** → **Phone Numbers → Buy a number**.
   Choose a **US** number (~$1.15/mo) with **Voice** capability. Indian numbers
   need KYC paperwork and cost considerably more — use US for now.
2. Open the number's settings. Under **Voice Configuration**:
   - **A call comes in:** `Webhook`
   - **URL:** `https://voxflow-yourname.duckdns.org/twilio/voice`
   - **HTTP:** `POST`
3. **Save**.

### Point the number at a tenant

Back in Supabase → **SQL Editor**, with your real number:

```sql
INSERT INTO tenant_phone_numbers (phone_number, tenant_id, label)
VALUES ('+14155551234', 'varun', 'Main support line')
ON CONFLICT (phone_number) DO UPDATE
    SET tenant_id = EXCLUDED.tenant_id, label = EXCLUDED.label;
```

Without this row the call still works, but everyone lands on
`DEFAULT_TENANT_ID` — fine for one company, wrong the moment you have two.

---

## Step 8 — Point the dashboard at your API

1. **vercel.com** → your project → **Settings → Environment Variables**:

   | Name | Value |
   |---|---|
   | `NEXT_PUBLIC_API_URL` | `https://voxflow-yourname.duckdns.org` |
   | `NEXT_PUBLIC_WS_URL` | `wss://voxflow-yourname.duckdns.org` |

2. **Deployments → ⋯ → Redeploy** (env vars only apply to new builds).

---

## Step 9 — Your first real call

Seed some demo data first, so there's something to ask about:

```bash
docker compose -f deploy/docker-compose.prod.yml exec api python -m voxflow_api.seed
```

Now **call your Twilio number** and try this:

> **Agent:** "नमस्ते, VoxFlow में आपका स्वागत है…"
> **You:** "Hi, I'm calling from Varun Beverages."
> **Agent:** "Which city are you based in?"
> **You:** "Gurgaon."
> **Agent:** "Thanks — how can I help?"
> **You:** "Have you signed our PO?"
> **Agent:** "Which PO number?"
> **You:** "VB slash PO slash 2026 slash 0912."
> **Agent:** "Yes, signed on the 19th of July — 500 cases, currently in transit."

Then check all three places:
- **Google Sheet** — a new row with reason, solution, resolution, satisfaction
- **Dashboard → Calls** — the call with its transcript and badges
- **Logs** — `docker compose -f deploy/docker-compose.prod.yml logs -f api`

---

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| Call connects then silence | Backend unreachable | `curl https://YOUR-DOMAIN/api/health` |
| Twilio error 11200 | Webhook URL wrong or not HTTPS | Re-check the URL in the number config |
| `403 invalid_signature` in logs | `PUBLIC_BASE_URL` doesn't match the real URL | Must match exactly, no trailing slash |
| Caddy won't get a certificate | Ports 80/443 closed | Do **both** firewall layers in step 4.2 |
| Nothing appears in the Sheet | Sheet not shared with the service account | Step 3.8 — share as **Editor** |
| `sheets_not_configured` in logs | `SHEETS_ENABLED=false` or bad JSON | Check the single quotes around the JSON |
| Agent responds slowly | Falling back to local Whisper | Confirm `STT_PROVIDER=groq` |
| DB connection refused | Using the pooler port | Use the direct URI on port 5432 |
| Supabase suddenly unreachable | Free project auto-paused | Unpause in the Supabase dashboard |

Useful commands:

```bash
# Follow logs
docker compose -f deploy/docker-compose.prod.yml logs -f api

# Restart after an .env change
docker compose -f deploy/docker-compose.prod.yml up -d

# Rebuild after pulling new code
git pull && docker compose -f deploy/docker-compose.prod.yml up -d --build

# Check memory headroom
free -h && docker stats --no-stream
```

---

## Running costs

| Item | Monthly |
|---|---|
| Oracle Cloud VM | $0 — Always Free |
| Supabase | $0 — free tier |
| Groq (LLM + STT) | $0 — free tier, rate-limited |
| edge-tts | $0 |
| Google Sheets | $0 |
| Vercel | $0 — Hobby |
| **Twilio number** | **~$1.15** |
| **Twilio call time** | **~$0.013/min** |

100 calls averaging 3 minutes ≈ **$5/month all in**.

---

## What is still outstanding

Being straight with you about what is *not* done:

1. **No real call has been made yet.** Every layer is implemented and tested,
   but until you complete step 9, nothing has been proven against a live phone
   network. Expect to tune the VAD threshold (`_SILENCE_RMS`, `_SILENCE_MS` in
   `apps/api/voxflow_api/routes/twilio.py`) once you hear real callers.
2. **Staff dashboard login is still `localStorage`-based**, not real Supabase
   Auth. Fine for you; not fine before a customer's staff use it.
3. **RLS policies are written but not verified** against a live second tenant.
   Application-level `tenant_id` scoping is enforced and tested; the database
   backstop is untested.
4. **No live dashboard updates** — call rows appear on refresh, not in
   real time.
5. **Groq free tier is rate-limited per minute.** Fine for a pilot, will need
   the paid tier for real volume.

`MEMORY.md` tracks all of this and should be updated as you close each item.
