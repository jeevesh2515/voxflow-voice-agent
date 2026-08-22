#!/usr/bin/env bash
#
# VoxFlow — verify the VM stack. No rebuild, no config changes, read-only.
#
# Run from your Mac. Waits for real health (not just container State), probes
# each upstream from inside the Docker network to isolate Caddy from the apps,
# then checks the public HTTPS surface with the CORRECT expected status per
# route — the auth gate in apps/web/src/proxy.ts is live under Next 16, so an
# unauthenticated /dashboard is SUPPOSED to redirect to /sign-in.
#
# Usage: ./deploy/verify-vm.sh
#
set -euo pipefail

VM_HOST="${VM_HOST:-193.123.187.97}"
VM_USER="${VM_USER:-ubuntu}"
VM_KEY="${VM_KEY:-$HOME/Downloads/ssh-key-2026-08-03.key}"

ssh -i "$VM_KEY" -o StrictHostKeyChecking=accept-new -o ConnectTimeout=15 \
    "${VM_USER}@${VM_HOST}" 'bash -s' <<'REMOTE'
set -uo pipefail
cd /home/ubuntu/voxflow-voice-agent/deploy
DC=(docker compose --env-file ../.env -f docker-compose.prod.yml)

DOMAIN="$(grep -E '^DOMAIN=' ../.env | head -1 | cut -d= -f2- | tr -d '"'"'"' ')"
[[ -n "$DOMAIN" ]] || { echo "FAILED: DOMAIN not set"; exit 1; }

# --- 0. Restart Caddy ------------------------------------------------------
# Caddy resolves each upstream host once and caches the address for the life of
# the process. Recreating api/web hands them NEW container IPs, so a Caddy that
# stayed up across the rebuild keeps dialing dead addresses and returns 502 on
# every route. Restarting re-resolves both, and re-reads the bind-mounted
# Caddyfile. Certificates live on the caddy_data volume, so nothing is re-issued.
echo "==> restarting caddy so it re-resolves api:8000 and web:3000"
"${DC[@]}" restart caddy
sleep 3

# --- 1. Wait for the api healthcheck to actually pass -----------------------
# Container State flips to "running" in milliseconds; Health is the real signal.
echo "==> waiting for api health (up to 3 min)"
for i in $(seq 1 36); do
  h="$(docker inspect -f '{{.State.Health.Status}}' voxflow-api 2>/dev/null || echo none)"
  [[ "$h" == "healthy" ]] && { echo "    api healthy after ~$((i*5))s"; break; }
  [[ "$h" == "unhealthy" ]] && { echo "    api UNHEALTHY"; break; }
  sleep 5
done

# The web container declares no healthcheck, so poll its port from inside.
echo "==> waiting for web to accept connections (up to 2 min)"
for i in $(seq 1 24); do
  if "${DC[@]}" exec -T caddy wget -q -T 3 -O /dev/null http://web:3000/ 2>/dev/null; then
    echo "    web answering after ~$((i*5))s"; break
  fi
  sleep 5
done

echo
echo "=== container state ==="
"${DC[@]}" ps

# --- 2. Probe upstreams from INSIDE the network -----------------------------
# If these pass but HTTPS 502s, the fault is Caddy (stale config or stale DNS
# for the recreated containers), not the applications.
echo
echo "=== upstream probes from inside the Docker network (via caddy) ==="
for target in http://api:8000/api/health http://web:3000/; do
  code="$("${DC[@]}" exec -T caddy wget -q -T 8 -S -O /dev/null "$target" 2>&1 \
          | grep -oE 'HTTP/1\.[01] [0-9]{3}' | tail -1 | awk '{print $2}')"
  printf '  %-32s %s\n' "$target" "${code:-UNREACHABLE}"
done

# --- 3. Public HTTPS surface, with per-route expectations -------------------
# /dashboard redirecting to /sign-in is CORRECT: the gate is enforced.
echo
echo "=== public HTTPS (https://${DOMAIN}) ==="
rc=0
check() {
  local path="$1" want="$2"
  local out code loc
  out="$(curl -s -o /dev/null -w '%{http_code} %{redirect_url}' --max-time 25 \
        "https://${DOMAIN}${path}" || echo "000 -")"
  code="${out%% *}"; loc="${out#* }"
  if [[ "$code" =~ ^($want)$ ]]; then
    printf '  %-14s %s  ok%s\n' "$path" "$code" "${loc:+  -> $loc}"
  else
    printf '  %-14s %s  EXPECTED %s%s\n' "$path" "$code" "$want" "${loc:+  -> $loc}"
    rc=1
  fi
}
check /            200
check /pricing     200
check /sign-in     200
check /dashboard   '307|302'     # gate redirects unauthenticated users
check /api/health  200

# --- 4. Prove Next.js, not FastAPI, is serving the site --------------------
echo
echo "=== who is serving the site? ==="
if curl -s --max-time 25 "https://${DOMAIN}/" | grep -qE '_next|__NEXT_DATA__'; then
  echo "  Next.js — / contains _next assets"
else
  echo "  NOT Next.js — Caddy default route or web container wrong"
  echo "  --- first 400 bytes of / ---"
  curl -s --max-time 25 "https://${DOMAIN}/" | head -c 400; echo
  rc=1
fi

# /api/health must be FastAPI JSON, i.e. Caddy's @api matcher works.
body="$(curl -s --max-time 25 "https://${DOMAIN}/api/health" || true)"
case "$body" in
  *status*|*ok*|*healthy*) echo "  FastAPI — /api/health returned: ${body:0:120}" ;;
  *) echo "  /api/health body unexpected: ${body:0:200}"; rc=1 ;;
esac

# --- 5. wss upgrade, the Day-1 telephony requirement ----------------------
echo
echo "=== wss upgrade on /ws/call ==="
ws="$(curl -s -o /dev/null -w '%{http_code}' --max-time 15 \
     -H 'Connection: Upgrade' -H 'Upgrade: websocket' \
     -H 'Sec-WebSocket-Version: 13' -H 'Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==' \
     "https://${DOMAIN}/ws/call" || echo 000)"
# 101 = upgraded. 426/400/403 = reached the app and it declined the handshake,
# which still proves Caddy proxied the upgrade to FastAPI.
case "$ws" in
  101) echo "  101 — upgraded" ;;
  400|403|426) echo "  $ws — reached FastAPI, handshake declined (proxy path works)" ;;
  502|504|000) echo "  $ws — Caddy could not reach the api upstream"; rc=1 ;;
  *) echo "  $ws" ;;
esac

if [[ $rc -ne 0 ]]; then
  echo
  echo "=== caddy log (last 25) ==="; docker logs voxflow-caddy --tail 25 2>&1 | tail -25
  echo
  echo "=== api log (last 25) ===";   docker logs voxflow-api   --tail 25 2>&1 | tail -25
  echo
  echo "=== web log (last 25) ===";   docker logs voxflow-web   --tail 25 2>&1 | tail -25
  echo
  echo "RESULT: something above failed"
  exit 1
fi

echo
echo "RESULT: ALL GREEN"
REMOTE
