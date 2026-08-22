#!/usr/bin/env bash
#
# VoxFlow — diagnose why voxflow-api is unhealthy. Read-only, ~20 seconds.
#
# Gathers, in one pass: the healthcheck's own recorded failure output, the
# container's exit/OOM state, uvicorn's logs, a direct probe of /api/health
# from inside the container with the real error text, and a DB connectivity
# check. Run from your Mac.
#
# Usage: ./deploy/diagnose-api.sh
#
set -euo pipefail

VM_HOST="${VM_HOST:-193.123.187.97}"
VM_USER="${VM_USER:-ubuntu}"
VM_KEY="${VM_KEY:-$HOME/Downloads/ssh-key-2026-08-03.key}"

ssh -i "$VM_KEY" -o StrictHostKeyChecking=accept-new -o ConnectTimeout=15 \
    "${VM_USER}@${VM_HOST}" 'f=$(mktemp /tmp/voxflow-remote.XXXXXX); cat > "$f"; bash "$f" </dev/null; rc=$?; rm -f "$f"; exit $rc' <<'REMOTE'
set -uo pipefail
cd /home/ubuntu/voxflow-voice-agent/deploy

echo "=== 1. healthcheck's own recorded output (the decisive evidence) ==="
# Docker keeps stdout+stderr of the last few healthcheck runs. This says
# exactly how urlopen failed: connection refused vs HTTP 500 vs timeout.
docker inspect -f '{{range .State.Health.Log}}--- exit={{.ExitCode}} at {{.Start}}
{{.Output}}
{{end}}' voxflow-api 2>/dev/null | tail -40
echo "FailingStreak: $(docker inspect -f '{{.State.Health.FailingStreak}}' voxflow-api 2>/dev/null)"

echo
echo "=== 2. container state (restart loop? OOM kill?) ==="
# mem_limit is 640m on a 954MB box. An OOM kill here looks identical to a crash
# from the outside, so check it explicitly.
docker inspect -f 'Status={{.State.Status}} Running={{.State.Running}} ExitCode={{.State.ExitCode}} OOMKilled={{.State.OOMKilled}} Restarts={{.RestartCount}} StartedAt={{.State.StartedAt}}' voxflow-api

echo
echo "=== 3. memory usage right now ==="
docker stats --no-stream --format '{{.Name}}  mem={{.MemUsage}}  {{.MemPerc}}  cpu={{.CPUPerc}}' 2>/dev/null || true
free -m | head -3

echo
echo "=== 4. api logs (last 80) ==="
docker logs voxflow-api --tail 80 2>&1 | tail -80

echo
echo "=== 5. probe /api/health from inside the container, with real error ==="
docker exec voxflow-api python - <<'PY' 2>&1 | tail -30
import socket, sys, traceback, urllib.request, urllib.error

# Is anything bound to 8000 at all? Distinguishes "app never started" from
# "app started but the route errors".
s = socket.socket()
s.settimeout(4)
try:
    s.connect(("127.0.0.1", 8000))
    print("port 8000: OPEN")
except Exception as exc:
    print("port 8000: CLOSED (%s)" % exc)
    print("-> uvicorn is not listening; the app failed before binding. See logs above.")
    sys.exit(0)
finally:
    s.close()

try:
    with urllib.request.urlopen("http://localhost:8000/api/health", timeout=8) as r:
        print("GET /api/health -> %s" % r.status)
        print(r.read()[:600].decode("utf-8", "replace"))
except urllib.error.HTTPError as exc:
    # This is the case the healthcheck cannot show you: the app IS up, but the
    # route returns 4xx/5xx, so urlopen raises and Docker marks it unhealthy.
    print("GET /api/health -> HTTP %s" % exc.code)
    print(exc.read()[:1500].decode("utf-8", "replace"))
except Exception:
    traceback.print_exc()
PY

echo
echo "=== 6. does the api reach Postgres? ==="
# A health route that checks the DB will 500 on an unreachable pooler, which is
# the most likely reason for an up-but-unhealthy api.
docker exec voxflow-api python - <<'PY' 2>&1 | tail -20
import os, re, sys
url = os.environ.get("DATABASE_URL", "")
if not url:
    print("DATABASE_URL: NOT SET")
    sys.exit(0)
# Never print credentials.
print("DATABASE_URL host:", re.sub(r"://[^@]*@", "://<redacted>@", url)[:120])
try:
    import psycopg2
    conn = psycopg2.connect(url, connect_timeout=8)
    cur = conn.cursor()
    cur.execute("select 1")
    print("Postgres: OK ->", cur.fetchone())
    cur.execute("select count(*) from information_schema.tables where table_schema='public'")
    print("public tables:", cur.fetchone()[0])
    conn.close()
except Exception as exc:
    print("Postgres: FAILED ->", type(exc).__name__, str(exc)[:400])
PY

echo
echo "=== 7. which routes exist (is /api/health even registered?) ==="
docker exec voxflow-api python - <<'PY' 2>&1 | tail -25
try:
    from voxflow.main import app
except Exception:
    try:
        from main import app
    except Exception as exc:
        print("could not import app:", type(exc).__name__, str(exc)[:300])
        raise SystemExit(0)
paths = sorted({getattr(r, "path", "?") for r in app.routes})
print("total routes: %d" % len(paths))
for p in paths:
    if "health" in p or p.count("/") <= 2:
        print("  ", p)
PY

echo
echo "=== done ==="
REMOTE
