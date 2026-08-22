# Deploying VoxFlow on an Oracle Cloud Always-Free VM

This is the copy-paste runbook that takes the containerized stack in this
directory (`docker-compose.prod.yml` + `Caddyfile`) from nothing to a **live,
always-on, HTTPS + `wss`** deployment on an Oracle Cloud **Always-Free ARM VM**,
at **$0/month** (Twilio is the only paid piece, and only once a real caller is
wired up — see step 8).

Everything else in the stack is free-tier: Caddy issues the TLS certificate
automatically, the Next.js app and FastAPI backend run as containers, and the
database is Supabase Postgres. Unlike Render Free, this VM **never sleeps** —
there is no cold start.

> Read `SETUP.md` (repo root) first for where each `.env` value comes from.
> This runbook covers only the Oracle VM + deploy specifics that `SETUP.md`
> does not.

---

## 0. What you are building

```
        Internet (HTTPS 443 / HTTP 80)
                 │
        ┌────────▼─────────┐   Oracle Always-Free ARM VM (Ubuntu, aarch64)
        │      Caddy       │   auto Let's Encrypt cert, wss, reverse proxy
        └───┬──────────┬───┘
   /api/*   │          │  everything else
 /twilio/*  │          │
 /ws/call   │          │
     ┌──────▼───┐  ┌───▼──────┐
     │   api    │  │   web    │   (both containers built natively on ARM)
     │ FastAPI  │  │ Next.js  │
     └────┬─────┘  └──────────┘
          │
   Supabase Postgres (free)   +   Groq (free)   +   edge-tts (free)
```

Routing is defined in [`Caddyfile`](./Caddyfile): the API owns
`/api/*`, `/twilio/*`, `/ws/call`, and the bare test routes; the Next.js app
serves everything else (marketing, auth, `/dashboard/*`, `/_next/*`).

---

## 1. Create the Always-Free ARM VM

In the Oracle Cloud console (**Compute → Instances → Create instance**):

| Setting | Value |
|---|---|
| Image | **Canonical Ubuntu 24.04** (or 22.04), **aarch64/ARM** |
| Shape | **VM.Standard.A1.Flex** (Ampere ARM — this is the Always-Free one) |
| OCPU / RAM | 2 OCPU / 12 GB is plenty; up to **4 OCPU / 24 GB** is free |
| Boot volume | Default (up to 200 GB total is free) |
| SSH keys | Upload your public key, or let Oracle generate one and **save the private key** |

Under **Networking**, keep the auto-created VCN and subnet, and assign a
**public IPv4 address**. Note that public IP.

> **Reserve the public IP.** An *ephemeral* Oracle public IP changes if the VM
> is stopped/started, which breaks your DNS + TLS. Either reserve it
> (**Networking → IP Management → Reserved public IPs**) or use the DuckDNS
> updater (step 4) so DNS follows the IP.

---

## 2. Open ports 80 and 443 — **BOTH layers** (the Oracle gotcha)

Oracle blocks inbound traffic in **two** independent places. You must open
80 and 443 in **both**, or Caddy can never get a certificate and the site is
unreachable. This is the single most common reason an Oracle deploy "hangs".

### 2a. VCN Security List (cloud firewall)

**Networking → Virtual Cloud Networks → your VCN → Security Lists → Default
Security List → Add Ingress Rules:**

| Stateless | Source CIDR | IP Protocol | Dest. Port |
|---|---|---|---|
| No | `0.0.0.0/0` | TCP | `80` |
| No | `0.0.0.0/0` | TCP | `443` |

### 2b. Instance iptables (OS firewall — the part everyone misses)

The stock Oracle **Ubuntu** image ships an iptables ruleset that `REJECT`s
everything inbound except SSH. Opening the Security List alone is not enough.
SSH into the VM (step 3) and run:

```bash
sudo iptables -L INPUT --line-numbers        # find the line number of the final REJECT rule
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 80 -j ACCEPT
sudo iptables -I INPUT 6 -m state --state NEW -p tcp --dport 443 -j ACCEPT
sudo netfilter-persistent save
```

`-I INPUT 6` inserts **before** the catch-all `REJECT`. On the stock Oracle
Ubuntu image the `REJECT` is around line 6 — confirm with the first command and
insert above it. Re-run `sudo iptables -L INPUT --line-numbers` to verify the
two `ACCEPT` lines appear before the `REJECT`.

---

## 3. SSH in and install Docker (ARM)

```bash
ssh -i /path/to/private_key ubuntu@YOUR_VM_PUBLIC_IP

# Docker Engine + compose plugin (the get.docker.com script supports arm64)
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER
newgrp docker                      # apply the group without re-login
docker version && docker compose version
```

---

## 4. Point your domain at the VM

Caddy issues a Let's Encrypt certificate over the HTTP-01 challenge, so your
domain **must resolve to the VM's public IP before you deploy**, and port 80
must be reachable (step 2).

**DuckDNS (free):** create a subdomain at <https://www.duckdns.org>, then set
its IP to your VM:

```bash
# One-off: point the record at the VM (use YOUR token + subdomain + IP)
curl "https://www.duckdns.org/update?domains=YOURSUB&token=YOURTOKEN&ip=YOUR_VM_PUBLIC_IP"
```

Verify it resolves (may take a minute):

```bash
dig +short YOURSUB.duckdns.org      # must print your VM public IP
```

> Using an ephemeral IP? Add the same `curl` line to `cron` every 5 minutes so
> DNS follows the IP. With a reserved IP you set it once.

---

## 5. Get the code and configure `.env`

The planning/learning files are gitignored, so cloning is safe.

```bash
cd ~
git clone https://github.com/jeevesh2515/voxflow-voice-agent.git
cd voxflow-voice-agent

cp .env.example .env
nano .env
```

Fill `.env` per `SETUP.md`. The minimum to go live (no telephony yet):

| Key | Value |
|---|---|
| `DOMAIN` | `YOURSUB.duckdns.org` (no `https://`) |
| `ACME_EMAIL` | your email (Let's Encrypt expiry notices) |
| `GROQ_API_KEY` | from console.groq.com |
| `DATABASE_URL` | Supabase **Session pooler** URL (IPv4). **Not** the direct `db.<ref>` host — it is IPv6-only and unreachable from a container. See `.env.example` §4. |
| `SUPABASE_URL` | `https://<ref>.supabase.co` |
| `SUPABASE_PUBLISHABLE_KEY` | Supabase anon/publishable key (baked into the web build) |
| `SUPABASE_JWKS_URL` | `https://<ref>.supabase.co/auth/v1/.well-known/jwks.json` |
| `PUBLIC_BASE_URL` | `https://YOURSUB.duckdns.org` |
| `API_CORS_ORIGINS` | `https://YOURSUB.duckdns.org` |

Twilio (`TWILIO_*`), Google Sheets, and the pilot/worker flags stay as-is for
now — Sheets and workers are off by default, telephony is wired in Day 2.

Run the pre-flight check — it catches a bad `.env` before a 10-minute build:

```bash
bash scripts/preflight.sh          # exit 0 = safe to deploy
```

---

## 6. Deploy

The images build **natively on the ARM VM** (both base images —
`python:3.12-slim` and `node:20-alpine` — are multi-arch, so no cross-build or
QEMU is needed). First build is ~5–10 minutes.

```bash
cd deploy
docker compose --env-file ../.env -f docker-compose.prod.yml up -d --build
```

`--env-file ../.env` makes `${DOMAIN}`, `${ACME_EMAIL}`, `${SUPABASE_URL}`, and
`${SUPABASE_PUBLISHABLE_KEY}` resolve from the same root `.env` the `api`
container already loads. One file, no duplication.

Watch it come up:

```bash
docker compose -f docker-compose.prod.yml logs -f caddy    # look for a cert being obtained
docker compose -f docker-compose.prod.yml ps               # all three: running/healthy
```

---

## 7. Verify it is live and always-on

```bash
# TLS + backend health (should print JSON, HTTP 200)
curl -sS https://YOURSUB.duckdns.org/api/health

# Marketing page served by Next.js (not the API)
curl -sSI https://YOURSUB.duckdns.org/ | head -n1        # HTTP/2 200
```

In a browser:
- `https://YOURSUB.duckdns.org/` → marketing site, valid padlock.
- `https://YOURSUB.duckdns.org/dashboard` → the dashboard app.

**Always-on check:** leave it 20+ minutes, hit `/api/health` again — it responds
instantly, no cold start. `restart: unless-stopped` brings every container back
after a VM reboot.

---

## 8. Wire real telephony (Day 2 — needs Twilio)

Once the site is live, point a Twilio number's Voice webhook at
`https://YOURSUB.duckdns.org/twilio/voice` and set `TWILIO_ACCOUNT_SID`,
`TWILIO_AUTH_TOKEN`, `TWILIO_PHONE_NUMBER`, and `PUBLIC_BASE_URL` in `.env`,
then `docker compose ... up -d` to reload. The Caddyfile already routes
`/twilio/*` (webhook + Media Stream `wss`) to the API with long-lived timeouts.
Trial numbers work for inbound (with a trial banner); details in the roadmap.

---

## 9. Keep-alive + nightly backup (Day 4 — scaffold now)

Supabase Free pauses a project after ~1 week idle, and there are no automatic
backups. Add both as VM cron jobs (`crontab -e`):

```bash
# Nightly Postgres backup to the api container's persistent volume (/app/data/backups)
15 2 * * *  docker exec voxflow-api /app/scripts/db_backup.sh >> ~/voxflow-backup.log 2>&1

# Weekly Supabase keep-alive ping (prevents the free project from pausing)
30 3 * * 0  curl -sS https://YOURSUB.duckdns.org/api/health > /dev/null
```

Backups land in the `voxflow_data` volume; copy them off-box periodically
(Supabase Free has no recovery guarantee).

---

## 10. Update / redeploy

```bash
cd ~/voxflow-voice-agent
git pull
cd deploy
docker compose --env-file ../.env -f docker-compose.prod.yml up -d --build
```

Changing any `NEXT_PUBLIC_*` value requires a **web rebuild** (`--build`),
because Next.js bakes those into the browser bundle at build time.

If something is wrong, the repo ships an Oracle-aware diagnostic:

```bash
bash scripts/vm-recovery.sh
```

---

## Troubleshooting

| Symptom | Cause / fix |
|---|---|
| Caddy log: cert challenge fails / times out | Port 80 not reachable. Recheck **both** step 2a (Security List) and 2b (iptables). `dig +short YOURSUB.duckdns.org` must equal the VM IP. |
| Site unreachable but containers "running" | iptables `REJECT` still above your `ACCEPT` rules (step 2b). Re-check line order. |
| `curl /api/health` works locally on VM but not from outside | Cloud firewall (2a) or DNS not propagated. |
| API log: `OSError: [Errno 101] Network is unreachable` to Postgres | You used the Supabase **direct** `db.<ref>.supabase.co` host (IPv6-only). Switch to the **Session pooler** host. See `.env.example` §4. |
| Browser: `NEXT_PUBLIC_API_URL` undefined / calls to wrong host | `.env` values were missing at build. Rebuild web: `docker compose ... up -d --build`. |
| API OOM / killed | `mem_limit` is 640 MB; the Always-Free VM has 12–24 GB, so raise the limit in the compose file if needed. |
```
