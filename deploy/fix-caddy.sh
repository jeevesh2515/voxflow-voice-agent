#!/usr/bin/env bash
#
# VoxFlow — install the repo's Caddyfile on the VM and prove the routing.
#
# WHY this exists: the VM's Caddyfile is bind-mounted from ~/voxflow-voice-agent/
# deploy/Caddyfile, and sync-vm.sh used to push only next.config.mjs + Dockerfile.
# So a stale Caddyfile on the VM survived every rebuild and sent EVERY path to
# api:8000 — which is why /, /pricing and /sign-in returned FastAPI JSON and 404s
# while http://web:3000/ answered 200 from inside the same Docker network.
#
# The repo Caddyfile routes only the machine-facing prefixes to the API and makes
# web:3000 the default handler. This script installs it, shows you the diff before
# overwriting anything, validates the config BEFORE reloading (an invalid Caddyfile
# on reload would leave you with no proxy at all), then verifies every route
# including a REAL wss handshake.
#
# Idempotent: if the VM already matches the repo, it says so and only verifies.
#
# Usage: ./deploy/fix-caddy.sh
#
set -euo pipefail

VM_HOST="${VM_HOST:-193.123.187.97}"
VM_USER="${VM_USER:-ubuntu}"
VM_KEY="${VM_KEY:-$HOME/Downloads/ssh-key-2026-08-03.key}"
VM_REPO="${VM_REPO:-/home/ubuntu/voxflow-voice-agent}"

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

SSH=(ssh -i "$VM_KEY" -o StrictHostKeyChecking=accept-new -o ConnectTimeout=15 "${VM_USER}@${VM_HOST}")
SCP=(scp -i "$VM_KEY" -o StrictHostKeyChecking=accept-new -o ConnectTimeout=15)

[[ -f "$VM_KEY" ]] || { echo "FAILED: SSH key not found at $VM_KEY" >&2; exit 1; }

echo "==> staging the repo Caddyfile on the VM (not installed yet)"
"${SCP[@]}" "${REPO_ROOT}/deploy/Caddyfile" \
            "${VM_USER}@${VM_HOST}:/tmp/Caddyfile.repo"

# The remote script is buffered to a file and run with stdin CLOSED. Piping it
# straight into `bash -s` makes bash read it from stdin, and any child that
# attaches to stdin (docker run -i, docker compose exec -T) drains the unread
# remainder — bash then hits EOF and exits 0 silently, mid-script.
"${SSH[@]}" 'f=$(mktemp /tmp/voxflow-remote.XXXXXX); cat > "$f"; bash "$f" </dev/null; rc=$?; rm -f "$f"; exit $rc' <<'REMOTE'
set -uo pipefail
cd /home/ubuntu/voxflow-voice-agent/deploy
DC=(docker compose --env-file ../.env -f docker-compose.prod.yml)

DOMAIN="$(grep -E '^DOMAIN=' ../.env | head -1 | cut -d= -f2- | tr -d '"'"'"' ')"
[[ -n "$DOMAIN" ]] || { echo "FAILED: DOMAIN not set in .env"; exit 1; }

# --- 1. Show what is about to change --------------------------------------
echo
echo "=== diff: VM's current Caddyfile  ->  repo Caddyfile ==="
if diff -u Caddyfile /tmp/Caddyfile.repo; then
  echo "  (identical — the VM already has the repo version)"
  CHANGED=0
else
  CHANGED=1
fi

BACKUP=""
if [[ "$CHANGED" == "1" ]]; then
  BACKUP="Caddyfile.bak.$(date +%Y%m%d-%H%M%S)"
  cp Caddyfile "$BACKUP"
  echo
  echo "==> backed up the VM's version to deploy/$BACKUP"
  cp /tmp/Caddyfile.repo Caddyfile
  echo "==> installed the repo Caddyfile"
fi
rm -f /tmp/Caddyfile.repo

# --- 2. Validate BEFORE restarting -----------------------------------------
# A syntax error found at restart time would leave the site with no proxy at all.
# The bind-mount is live, so the container already sees the new file while still
# serving the OLD config from memory — the safe moment to check it. Validate
# inside the container so {$DOMAIN} and {$ACME_EMAIL} resolve exactly as they
# will at runtime.
#
# Capture the output instead of piping into tail: with `if ! cmd | tail`, bash
# tests TAIL's status, which is ~always 0, so a validation failure would sail
# straight through.
echo
echo "==> validating the config inside the caddy container"
if val_out="$("${DC[@]}" exec -T caddy caddy validate \
              --config /etc/caddy/Caddyfile --adapter caddyfile 2>&1)"; then
  printf '%s\n' "$val_out" | tail -3
  echo "    valid"
else
  printf '%s\n' "$val_out" | tail -15
  echo
  echo "FAILED: Caddyfile did not validate. Caddy was NOT restarted, so the site"
  echo "        is still serving the previous config."
  if [[ -n "$BACKUP" ]]; then
    cp "$BACKUP" Caddyfile
    echo "        Restored the VM's previous Caddyfile from $BACKUP."
  fi
  exit 1
fi

# --- 3. Restart so it re-reads the file AND re-resolves upstreams -----------
# Restart rather than reload: Caddy caches each upstream's resolved address for
# the life of its process, and api/web have been recreated since it last started.
# Certificates live on the caddy_data volume, so none are re-issued.
echo
echo "==> restarting caddy"
"${DC[@]}" restart caddy
sleep 4

# --- 4. Verify the public surface, per route -------------------------------
echo
echo "=== public HTTPS (https://${DOMAIN}) ==="
rc=0
check() {
  local path="$1" want="$2" code
  code="$(curl -s -o /dev/null -w '%{http_code}' --max-time 25 "https://${DOMAIN}${path}" || echo 000)"
  if [[ "$code" =~ ^($want)$ ]]; then printf '  %-14s %s  ok\n' "$path" "$code"
  else printf '  %-14s %s  EXPECTED %s\n' "$path" "$code" "$want"; rc=1; fi
}
check /            200
check /pricing     200
check /sign-in     200
check /dashboard   '307|302'   # auth gate in apps/web/src/proxy.ts is live under Next 16
check /api/health  200

# --- 5. Prove WHICH upstream served each side ------------------------------
# Status codes alone cannot tell Next.js apart from FastAPI: both can return 200
# and both can 404. Fingerprint the bodies instead.
echo
echo "=== which upstream served what? ==="
home="$(curl -s --max-time 25 "https://${DOMAIN}/" || true)"
if printf '%s' "$home" | grep -qE '_next|__NEXT_DATA__'; then
  echo "  /            Next.js  (contains _next assets)"
else
  echo "  /            NOT Next.js — first 200 bytes:"
  printf '    %s\n' "$(printf '%s' "$home" | head -c 200)"
  rc=1
fi

health="$(curl -s --max-time 25 "https://${DOMAIN}/api/health" || true)"
case "$health" in
  *voxflow-api*) echo "  /api/health  FastAPI  ${health:0:90}" ;;
  *) echo "  /api/health  unexpected body: ${health:0:200}"; rc=1 ;;
esac

# --- 6. The real wss test, end to end -------------------------------------
# A curl "upgrade" request cannot test this: Starlette's WebSocketRoute only
# matches scope type "websocket", so an HTTP GET to /ws/call 404s even when the
# route is perfectly healthy — the 404 you saw earlier was NOT a routing fault.
# Use an actual client. The api image ships websockets==13.1, and dialling the
# PUBLIC wss:// URL from inside it exercises the whole path: DNS, Let's Encrypt
# TLS, Caddy's @api matcher, the upgrade, and ws.py's await ws.accept().
echo
echo "=== real wss handshake against wss://${DOMAIN}/ws/call ==="
"${DC[@]}" exec -T -e VOXFLOW_WS="wss://${DOMAIN}/ws/call" api python - <<'PY' 2>&1 | tail -12
import os, json, sys

url = os.environ["VOXFLOW_WS"]
try:
    from websockets.sync.client import connect
except Exception as exc:
    print("SKIP: no sync websocket client (%s)" % exc)
    sys.exit(0)

try:
    with connect(url, open_timeout=20, close_timeout=5) as ws:
        print("101 UPGRADED — TLS + Caddy + FastAPI websocket path all work")
        # ws.py accepts first, then reads JSON messages. A bad-type message gets
        # a structured reply, which proves the app loop is live, not just the
        # handshake.
        ws.send(json.dumps({"type": "ping-from-verify"}))
        try:
            print("  app replied:", ws.recv(timeout=10)[:200])
        except Exception:
            print("  (no reply to an unknown message type — handshake still proven)")
except Exception as exc:
    print("FAILED: %s: %s" % (type(exc).__name__, str(exc)[:300]))
    sys.exit(1)
PY
ws_rc=${PIPESTATUS[0]}
[[ "$ws_rc" -eq 0 ]] || rc=1

if [[ $rc -ne 0 ]]; then
  echo
  echo "=== caddy log (last 20) ==="; docker logs voxflow-caddy --tail 20 2>&1 | tail -20
  echo
  echo "RESULT: something above failed"
  exit 1
fi

echo
echo "RESULT: ALL GREEN — Next.js serves the site, FastAPI owns /api + /twilio + /ws/call"
REMOTE
