#!/usr/bin/env bash
# VoxFlow pre-flight check.
#
#   bash scripts/preflight.sh
#
# Run this BEFORE `docker compose up`. It validates every prerequisite that
# would otherwise fail silently or three minutes into a build, and tells you
# exactly which one is wrong.
#
# Exit 0 = safe to deploy. Exit 1 = something needs fixing.
#
# Safe to run repeatedly. Never prints secret values — only whether they are
# present and well-formed.

set -uo pipefail

PASS=0; WARN=0; FAIL=0
ok()   { echo "  ✅ $1"; PASS=$((PASS+1)); }
warn() { echo "  ⚠️  $1"; WARN=$((WARN+1)); }
bad()  { echo "  ❌ $1"; FAIL=$((FAIL+1)); }

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo
echo "VoxFlow pre-flight  —  $(date -u '+%Y-%m-%d %H:%M UTC')"
echo "════════════════════════════════════════════════════════"

# ── 1. Host ──────────────────────────────────────────────────────────────
echo
echo "1. Host"

if command -v docker >/dev/null 2>&1; then
  ok "docker $(docker version --format '{{.Client.Version}}' 2>/dev/null || echo present)"
  docker compose version >/dev/null 2>&1 && ok "docker compose plugin" \
    || bad "docker compose plugin missing — install docker-compose-plugin"
  docker info >/dev/null 2>&1 || bad "cannot talk to docker daemon (try: newgrp docker)"
else
  bad "docker not installed"
fi

TOTAL_MB=$(free -m 2>/dev/null | awk '/^Mem:/{print $2}')
SWAP_MB=$(free -m 2>/dev/null | awk '/^Swap:/{print $2}')
if [ -n "${TOTAL_MB:-}" ]; then
  if [ "$TOTAL_MB" -lt 1400 ] && [ "${SWAP_MB:-0}" -lt 512 ]; then
    bad "${TOTAL_MB}MB RAM and only ${SWAP_MB:-0}MB swap — the image build will likely be OOM-killed.
       Fix: sudo fallocate -l 2G /swapfile && sudo chmod 600 /swapfile \\
            && sudo mkswap /swapfile && sudo swapon /swapfile \\
            && echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab"
  else
    ok "memory ${TOTAL_MB}MB + ${SWAP_MB:-0}MB swap"
  fi
fi

DISK_AVAIL=$(df -Pm . 2>/dev/null | awk 'NR==2{print $4}')
[ "${DISK_AVAIL:-9999}" -lt 3000 ] \
  && warn "only ${DISK_AVAIL}MB disk free — the build needs ~2GB of headroom" \
  || ok "disk ${DISK_AVAIL}MB free"

# ── 2. Repo contents ─────────────────────────────────────────────────────
echo
echo "2. Repository"
for f in deploy/docker-compose.prod.yml deploy/Caddyfile apps/api/Dockerfile \
         migrations/001_customer_support_flow.sql SETUP.md; do
  [ -f "$f" ] && ok "$f" || bad "$f missing — is PR #1 merged and did you git pull?"
done
grep -q "faster-whisper" apps/api/requirements.txt 2>/dev/null \
  && bad "requirements.txt still has faster-whisper — you are on stale code, git pull" \
  || ok "requirements.txt is the lean server-side build"

# ── 3. .env ──────────────────────────────────────────────────────────────
echo
echo "3. Configuration (.env)"

if [ ! -f .env ]; then
  bad ".env not found — run: cp .env.example .env"
  echo; echo "Cannot continue without .env."; exit 1
fi
ok ".env present"

# Read without executing it — a stray backtick in a secret shouldn't run.
getenv() { grep -E "^\s*$1\s*=" .env | tail -1 | cut -d= -f2- | sed "s/^['\"]//; s/['\"]$//"; }

require() { # name, human hint
  local v; v="$(getenv "$1")"
  if [ -z "$v" ]; then bad "$1 is empty — $2"; else ok "$1 set"; fi
}

require GROQ_API_KEY       "get one free at console.groq.com"
require DATABASE_URL       "Supabase → Settings → Database → URI (direct, port 5432)"
require PUBLIC_BASE_URL    "your https URL, e.g. https://voxflow.duckdns.org"
require DOMAIN             "hostname without https://, e.g. voxflow.duckdns.org"
require ACME_EMAIL         "Let's Encrypt expiry notices go here"

# Twilio can legitimately come later, but warn loudly.
for t in TWILIO_ACCOUNT_SID TWILIO_AUTH_TOKEN; do
  [ -z "$(getenv $t)" ] && warn "$t empty — fine for now, required before a real call" || ok "$t set"
done

# ── Targeted correctness checks on values that are easy to get wrong ─────
DB="$(getenv DATABASE_URL)"
case "$DB" in
  *sqlite*)
    bad "DATABASE_URL is SQLite — production must point at Supabase Postgres" ;;
  *:6543/*)
    bad "DATABASE_URL uses port 6543 — Supabase's TRANSACTION pooler. It does not
       support prepared statements and is built for serverless functions.
       Use the SESSION pooler on port 5432 instead (same host, different port)." ;;
  *db.*.supabase.co*)
    # The direct endpoint is IPv6-only. Docker containers have no IPv6 by
    # default even when the host does, so this fails with
    # OSError: [Errno 101] Network is unreachable — after the app has already
    # started, which makes it look like a database problem rather than a
    # networking one.
    bad "DATABASE_URL uses the DIRECT endpoint (db.<ref>.supabase.co), which is
       IPv6-ONLY. This host/container is almost certainly IPv4-only, so connects
       fail with 'Network is unreachable'.
       Use the SESSION POOLER instead — Supabase dashboard → Connect →
       'Session pooler'. Note the username becomes tenant-qualified:
         postgresql://postgres.<project-ref>:<password>@aws-<region>.pooler.supabase.com:5432/postgres" ;;
  *pooler.supabase.com:5432*)
    case "$DB" in
      *YOUR-PASSWORD*|*\[YOUR*) bad "DATABASE_URL still contains the placeholder password" ;;
      postgresql://postgres.*)   ok "DATABASE_URL is the IPv4 session pooler (correct)" ;;
      *) bad "Session pooler requires a tenant-qualified username:
       postgres.<project-ref>  (not plain 'postgres')" ;;
    esac ;;
  postgresql://*)
    case "$DB" in
      *YOUR-PASSWORD*|*\[YOUR*) bad "DATABASE_URL still contains the placeholder password" ;;
      *) warn "DATABASE_URL is Postgres but not a recognised Supabase endpoint" ;;
    esac ;;
  "") : ;;
  *) warn "DATABASE_URL does not look like a postgresql:// URI" ;;
esac

# Does this host even have IPv6? Explains the direct-endpoint failure outright.
if [ -n "$DB" ]; then
  if ip -6 route show default 2>/dev/null | grep -q .; then
    ok "host has an IPv6 default route"
  else
    warn "host has NO IPv6 route — Supabase's direct endpoint cannot work here.
       Only the session pooler (IPv4) will connect."
  fi
fi

# Actually try to reach the database. Everything above is string inspection;
# this is the only check that proves connectivity.
DB_HOST=$(printf '%s' "$DB" | sed -n 's#.*@\([^:/]*\).*#\1#p')
DB_PORT=$(printf '%s' "$DB" | sed -n 's#.*@[^:]*:\([0-9]*\).*#\1#p')
if [ -n "$DB_HOST" ] && [ -n "$DB_PORT" ]; then
  if command -v nc >/dev/null 2>&1; then
    if nc -z -w 6 "$DB_HOST" "$DB_PORT" 2>/dev/null; then
      ok "TCP reachable: $DB_HOST:$DB_PORT"
    else
      bad "CANNOT REACH $DB_HOST:$DB_PORT — the app will start and then fail
       every query. If this is db.<ref>.supabase.co, it is the IPv6 problem
       above; switch to the session pooler."
    fi
  else
    warn "nc not installed — skipping the live database reachability probe"
  fi
fi

PBU="$(getenv PUBLIC_BASE_URL)"
case "$PBU" in
  https://*)
    case "$PBU" in
      */) bad "PUBLIC_BASE_URL has a trailing slash — Twilio signature validation will fail" ;;
      *)  ok "PUBLIC_BASE_URL is https with no trailing slash" ;;
    esac ;;
  http://*) bad "PUBLIC_BASE_URL is http — Twilio requires https" ;;
  "") : ;;
  *) bad "PUBLIC_BASE_URL must start with https://" ;;
esac

# DOMAIN must match PUBLIC_BASE_URL or Caddy gets a cert for the wrong name.
DOM="$(getenv DOMAIN)"
if [ -n "$DOM" ] && [ -n "$PBU" ]; then
  [ "${PBU#https://}" = "$DOM" ] && ok "DOMAIN matches PUBLIC_BASE_URL" \
    || bad "DOMAIN ($DOM) != PUBLIC_BASE_URL host (${PBU#https://}) — cert will not match"
fi

# Sheets is optional; make that explicit rather than a silent half-config.
SHEETS="$(getenv SHEETS_ENABLED)"
if [ "$SHEETS" = "true" ]; then
  if [ -z "$(getenv GOOGLE_SHEET_ID)" ] || [ -z "$(getenv GOOGLE_SERVICE_ACCOUNT_JSON)" ]; then
    bad "SHEETS_ENABLED=true but GOOGLE_SHEET_ID / GOOGLE_SERVICE_ACCOUNT_JSON are empty.
       Either complete SETUP.md step 5, or set SHEETS_ENABLED=false to defer it —
       calls still work and outcomes still persist to Postgres."
  else
    if echo "$(getenv GOOGLE_SERVICE_ACCOUNT_JSON)" | grep -q '"private_key"'; then
      ok "Google service account JSON looks well-formed"
    else
      bad "GOOGLE_SERVICE_ACCOUNT_JSON does not contain private_key — is it the whole JSON on one line?"
    fi
  fi
else
  warn "SHEETS_ENABLED is not true — call outcomes go to Postgres only (supported; add Sheets later)"
fi

# ── 4. Network ───────────────────────────────────────────────────────────
echo
echo "4. Network"

if [ -n "$DOM" ]; then
  RESOLVED=$(getent hosts "$DOM" 2>/dev/null | awk '{print $1}' | head -1)
  MYIP=$(curl -s --max-time 6 https://api.ipify.org 2>/dev/null)
  if [ -z "$RESOLVED" ]; then
    bad "$DOM does not resolve — set it up at duckdns.org and point it at this server"
  elif [ -n "$MYIP" ] && [ "$RESOLVED" != "$MYIP" ]; then
    bad "$DOM resolves to $RESOLVED but this server is $MYIP — Let's Encrypt will fail"
  else
    ok "$DOM resolves to this server ($RESOLVED)"
  fi
fi

for p in 80 443; do
  if command -v ss >/dev/null 2>&1 && ss -ltn 2>/dev/null | grep -q ":$p "; then
    warn "port $p already in use — Caddy will not be able to bind it"
  else
    ok "port $p free"
  fi
done

sudo iptables -C INPUT -m state --state NEW -p tcp --dport 443 -j ACCEPT 2>/dev/null \
  && ok "iptables allows 443" \
  || warn "could not confirm iptables rule for 443 (Oracle blocks this separately from the cloud security list)"

curl -s --max-time 8 -o /dev/null -w '' https://api.groq.com 2>/dev/null \
  && ok "outbound HTTPS to Groq works" || warn "could not reach api.groq.com"

# ── Summary ──────────────────────────────────────────────────────────────
echo
echo "════════════════════════════════════════════════════════"
echo "  $PASS passed · $WARN warnings · $FAIL blockers"
echo
if [ "$FAIL" -gt 0 ]; then
  echo "  ❌ Fix the blockers above before deploying."
  echo
  exit 1
fi
echo "  ✅ Ready. Deploy with:"
echo "     docker compose -f deploy/docker-compose.prod.yml up -d --build"
echo
exit 0
