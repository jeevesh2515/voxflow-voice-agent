#!/usr/bin/env bash
#
# VoxFlow — sync the VM to the repo and redeploy, unattended.
#
# Run this from your Mac (NOT on the VM). It:
#   1. pulls the VM's regenerated package-lock.json back into this repo
#   2. pushes the repo's next.config.mjs + Dockerfile + Caddyfile + seed.py to the VM
#   3. repairs the VM's .env (joined lines, Sheets flag, CORS origin)
#   4. rebuilds the api + web containers and waits for health
#   5. verifies /, /dashboard and /api/health over HTTPS
#
# Safe to re-run: every step is idempotent and .env is backed up first.
#
# Usage:
#   ./deploy/sync-vm.sh
#   VM_HOST=1.2.3.4 VM_KEY=~/.ssh/other.key ./deploy/sync-vm.sh
#
set -euo pipefail

VM_HOST="${VM_HOST:-193.123.187.97}"
VM_USER="${VM_USER:-ubuntu}"
VM_KEY="${VM_KEY:-$HOME/Downloads/ssh-key-2026-08-03.key}"
VM_REPO="${VM_REPO:-/home/ubuntu/voxflow-voice-agent}"

# Resolve the repo root from this script's location, so cwd doesn't matter.
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

SSH=(ssh -i "$VM_KEY" -o StrictHostKeyChecking=accept-new -o ConnectTimeout=15 "${VM_USER}@${VM_HOST}")
SCP=(scp -i "$VM_KEY" -o StrictHostKeyChecking=accept-new -o ConnectTimeout=15)

say() { printf '\n\033[1;36m==> %s\033[0m\n' "$1"; }
die() { printf '\n\033[1;31mFAILED: %s\033[0m\n' "$1" >&2; exit 1; }

[[ -f "$VM_KEY" ]] || die "SSH key not found at $VM_KEY (set VM_KEY=...)"

say "Checking SSH to ${VM_USER}@${VM_HOST}"
"${SSH[@]}" 'echo ok >/dev/null' || die "cannot SSH to the VM"

# ---------------------------------------------------------------------------
# 1. Pull the VM's regenerated lockfile into the repo.
#
# The committed lockfile was stale (generated against Next 14 while
# package.json moved to Next 16), which breaks `npm ci` in Docker AND silently
# breaks Vercel rebuilds. The VM has a freshly regenerated, in-sync copy.
# ---------------------------------------------------------------------------
say "Pulling regenerated package-lock.json from the VM"
"${SCP[@]}" "${VM_USER}@${VM_HOST}:${VM_REPO}/apps/web/package-lock.json" \
            "${REPO_ROOT}/apps/web/package-lock.json"

# ---------------------------------------------------------------------------
# 2. Push the repo's deploy-affecting config to the VM.
#
# Only these files — never a whole-tree rsync, because .planning/ and
# .learning/ are private and must never leave this machine.
#
# The Caddyfile belongs in this list. It is bind-mounted into the container
# (./Caddyfile:/etc/caddy/Caddyfile:ro), so a stale copy on the VM survives
# every image rebuild untouched. One did: it routed EVERY path to api:8000, so
# /, /pricing and /sign-in returned FastAPI JSON and 404s while http://web:3000/
# answered 200 from inside the same Docker network. Rebuilding could never have
# fixed that, because the fault was in a file the rebuild does not read.
# ---------------------------------------------------------------------------
say "Pushing next.config.mjs + Dockerfile to the VM"
"${SCP[@]}" "${REPO_ROOT}/apps/web/next.config.mjs" \
            "${REPO_ROOT}/apps/web/Dockerfile" \
            "${VM_USER}@${VM_HOST}:${VM_REPO}/apps/web/"

say "Pushing Caddyfile to the VM"
"${SCP[@]}" "${REPO_ROOT}/deploy/Caddyfile" \
            "${VM_USER}@${VM_HOST}:${VM_REPO}/deploy/Caddyfile"

# seed.py is baked into the api image (apps/api has no source bind-mount), and
# this script rebuilds api. Pushing it here keeps the rebuilt image from
# reverting to the VM's older copy — the one whose single-transaction insert
# tripped products_tenant_id_fkey on Postgres.
say "Pushing the seeder to the VM"
"${SCP[@]}" "${REPO_ROOT}/apps/api/voxflow_api/seed.py" \
            "${VM_USER}@${VM_HOST}:${VM_REPO}/apps/api/voxflow_api/seed.py"

# ---------------------------------------------------------------------------
# 3-5. Repair .env, rebuild, verify — all on the VM.
# ---------------------------------------------------------------------------
say "Repairing .env, rebuilding api + web, verifying (this takes ~15 min)"
"${SSH[@]}" 'f=$(mktemp /tmp/voxflow-remote.XXXXXX); cat > "$f"; bash "$f" </dev/null; rc=$?; rm -f "$f"; exit $rc' <<'REMOTE'
set -euo pipefail
cd /home/ubuntu/voxflow-voice-agent

ENV_FILE=.env
[[ -f $ENV_FILE ]] || { echo "FAILED: $ENV_FILE missing"; exit 1; }

BACKUP="${ENV_FILE}.bak.$(date +%Y%m%d-%H%M%S)"
cp "$ENV_FILE" "$BACKUP"
echo "--- .env backed up to $BACKUP"

# Set or append a key. Value is written literally (no shell/sed metachar surprises)
# by rebuilding the file with awk rather than an in-place substitution.
set_env() {
  local key="$1" val="$2"
  if grep -qE "^${key}=" "$ENV_FILE"; then
    awk -v k="$key" -v v="$val" -F= '
      $1 == k { print k "=" v; next }
      { print }
    ' "$ENV_FILE" > "${ENV_FILE}.tmp" && mv "${ENV_FILE}.tmp" "$ENV_FILE"
  else
    printf '%s=%s\n' "$key" "$val" >> "$ENV_FILE"
  fi
  echo "--- set ${key}"
}

# 3a. Two .env lines lost their newline, so dotenv parsed each pair as ONE
#     mangled value and pydantic rejected the settings. Split them back.
#     Targeted, not a blanket regex: a generic "split on space" would corrupt
#     GOOGLE_SERVICE_ACCOUNT_JSON, whose single-line JSON legitimately
#     contains spaces.
python3 - <<'PY'
import io, re

path = ".env"
# Each entry: the exact joined line -> the two lines it should be.
repairs = [
    ("LLM_TEMPERATURE=0.2 LLM_MAX_TOKENS=512",
     ["LLM_TEMPERATURE=0.2", "LLM_MAX_TOKENS=512"]),
    ("STT_PROVIDER=groq GROQ_STT_MODEL=whisper-large-v3-turbo",
     ["STT_PROVIDER=groq", "GROQ_STT_MODEL=whisper-large-v3-turbo"]),
]

with io.open(path, encoding="utf-8") as fh:
    lines = fh.read().splitlines()

out, fixed = [], 0
for line in lines:
    for joined, parts in repairs:
        if line.strip() == joined:
            out.extend(parts)
            fixed += 1
            break
    else:
        out.append(line)

if fixed:
    with io.open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(out) + "\n")
print("--- split %d joined line(s)" % fixed)

# Report anything else that looks joined, but do NOT auto-edit it.
suspect = [
    l for l in out
    if re.match(r'^[A-Z][A-Z0-9_]*=\S*\s+[A-Z][A-Z0-9_]*=', l)
    and not l.startswith("GOOGLE_SERVICE_ACCOUNT_JSON=")
]
if suspect:
    print("--- WARNING: these lines still look joined; check them by hand:")
    for l in suspect:
        print("      %s" % l[:80])
PY

# 3b. Google Sheets is deferred (Day 3) and the service-account JSON is still a
#     placeholder, so leaving this on fails settings validation at boot.
#     Calls persist to Postgres regardless.
set_env SHEETS_ENABLED false

# 3c. The browser calls the API from https://$DOMAIN, so that origin must be
#     allowed or every dashboard fetch fails CORS.
DOMAIN="$(grep -E '^DOMAIN=' "$ENV_FILE" | head -1 | cut -d= -f2- | tr -d '"'"'"' ')"
[[ -n "$DOMAIN" ]] || { echo "FAILED: DOMAIN not set in .env"; exit 1; }
ORIGIN="https://${DOMAIN}"
CURRENT="$(grep -E '^API_CORS_ORIGINS=' "$ENV_FILE" | head -1 | cut -d= -f2- || true)"
if [[ "$CURRENT" != *"$ORIGIN"* ]]; then
  if [[ -n "$CURRENT" ]]; then
    set_env API_CORS_ORIGINS "${CURRENT},${ORIGIN}"
  else
    set_env API_CORS_ORIGINS "$ORIGIN"
  fi
else
  echo "--- API_CORS_ORIGINS already allows ${ORIGIN}"
fi

# 4. Rebuild. --env-file is mandatory: without it ${DOMAIN}, ${ACME_EMAIL} and
#    the NEXT_PUBLIC_* build args resolve blank and get baked into the image.
#    --force-recreate makes api re-read the repaired .env (env_file is read at
#    container create time, not on restart).
cd deploy
echo "--- building (next build on 1GB RAM takes ~15 min)"
docker compose --env-file ../.env -f docker-compose.prod.yml \
  up -d --build --force-recreate api web

# 4b. Restart Caddy. It resolves each upstream host once and caches the address
#     for the life of the process, so a Caddy left running across the recreate
#     above keeps dialing the OLD container IPs and returns 502 on every route.
#     Certificates persist on the caddy_data volume; nothing is re-issued.
#
#     Validate the just-pushed Caddyfile FIRST. The bind-mount is live, so the
#     container already sees the new file while still serving the previous config
#     from memory — the only safe moment to catch a syntax error.
if val_out="$(docker compose --env-file ../.env -f docker-compose.prod.yml \
              exec -T caddy caddy validate --config /etc/caddy/Caddyfile \
              --adapter caddyfile 2>&1)"; then
  echo "--- Caddyfile valid"
else
  printf '%s\n' "$val_out" | tail -15
  echo "FAILED: pushed Caddyfile does not validate; caddy left on the old config"
  exit 1
fi
docker compose --env-file ../.env -f docker-compose.prod.yml restart caddy

# 5. Wait for real readiness. Container State flips to "running" within
#    milliseconds of start, long before uvicorn binds a port — polling State is
#    what made an earlier run report 502 on a stack that was merely still
#    booting. Poll the api's declared healthcheck instead, and poll web's port
#    directly since that service declares no healthcheck.
echo "--- waiting for api health (up to 3 min)"
for i in $(seq 1 36); do
  h="$(docker inspect -f '{{.State.Health.Status}}' voxflow-api 2>/dev/null || echo none)"
  [[ "$h" == "healthy" ]] && { echo "    api healthy after ~$((i*5))s"; break; }
  [[ "$h" == "unhealthy" ]] && { echo "    api UNHEALTHY"; break; }
  sleep 5
done

echo "--- waiting for web to accept connections (up to 2 min)"
for i in $(seq 1 24); do
  if docker compose --env-file ../.env -f docker-compose.prod.yml \
       exec -T caddy wget -q -T 3 -O /dev/null http://web:3000/ </dev/null 2>/dev/null; then
    echo "    web answering after ~$((i*5))s"; break
  fi
  sleep 5
done

echo
echo "=== container state ==="
docker compose --env-file ../.env -f docker-compose.prod.yml ps

echo
echo "=== HTTPS checks (https://${DOMAIN}) ==="
rc=0
# Per-route expectations. /dashboard MUST redirect: Next 16 reads
# apps/web/src/proxy.ts as middleware, so the auth gate is enforced and an
# unauthenticated request is supposed to land on /sign-in. Demanding 200 there
# would fail a correctly-working stack.
check_route() {
  local path="$1" want="$2" code
  code="$(curl -s -o /dev/null -w '%{http_code}' --max-time 25 "https://${DOMAIN}${path}" || echo 000)"
  if [[ "$code" =~ ^($want)$ ]]; then
    printf '  %-14s %s  ok\n' "$path" "$code"
  else
    printf '  %-14s %s  EXPECTED %s\n' "$path" "$code" "$want"
    rc=1
  fi
}
check_route /           200
check_route /sign-in    200
check_route /dashboard  '307|302'
check_route /api/health 200

echo
echo "=== is Next.js serving the site? ==="
# The stale stack routed everything to FastAPI. Next.js pages carry __NEXT_DATA__
# or a /_next/ asset; a FastAPI 404 body does not. Probe / rather than
# /dashboard — the latter redirects and so has an empty body to grep.
if curl -s --max-time 25 "https://${DOMAIN}/" | grep -qE '_next|__NEXT_DATA__'; then
  echo "  yes — / is served by Next.js"
else
  echo "  NO — / is not Next.js output; Caddy routing or web container still wrong"
  rc=1
fi

if [[ $rc -ne 0 ]]; then
  echo
  echo "=== last 30 web log lines ==="
  docker logs voxflow-web --tail 30 2>&1 || true
  echo
  echo "=== last 30 api log lines ==="
  docker logs voxflow-api --tail 30 2>&1 || true
  exit 1
fi

echo
echo "ALL GREEN"
REMOTE

say "Done — VM synced and verified"
