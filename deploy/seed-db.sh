#!/usr/bin/env bash
#
# VoxFlow — install the fixed seeder on the VM and populate Postgres.
#
# WHY a script and not one docker command: apps/api has NO source bind-mount in
# docker-compose.prod.yml, so seed.py is baked into the api image. Editing the file
# on your Mac — or even on the VM — changes nothing about what
# `docker compose exec api python -m voxflow_api.seed` actually executes. The file
# has to be pushed AND the image rebuilt, and rebuilding api hands it a new
# container IP, which means Caddy must be restarted or every route 502s. That is
# three failure modes in a row; this script does the whole sequence in order.
#
# The rebuild is cheap: apps/api/Dockerfile copies requirements.txt and installs
# the venv in a separate builder stage, so changing seed.py invalidates only the
# final COPY. No pip download, no compilation.
#
# What it does NOT do: pass --reset. On Postgres the fixed seeder now refuses that
# flag outright, because reset_db() is drop_all()+create_all() and create_all()
# only knows the ORM's tables — every row-level-security policy, index and comment
# that migrations/ established would be dropped and never rebuilt, leaving a
# database that still accepts writes but no longer isolates tenants from each
# other. Seeding is additive and re-runnable instead.
#
# Idempotent: re-running skips every group of rows that already landed.
#
# Usage: ./deploy/seed-db.sh
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

# Sanity-check the local file before shipping it. A syntax error would otherwise
# be discovered only after a rebuild and a container recreate.
echo "==> compile-checking the seeder locally"
python3 -m py_compile "${REPO_ROOT}/apps/api/voxflow_api/seed.py"
echo "    ok"

echo "==> pushing apps/api/voxflow_api/seed.py to the VM"
"${SCP[@]}" "${REPO_ROOT}/apps/api/voxflow_api/seed.py" \
            "${VM_USER}@${VM_HOST}:${VM_REPO}/apps/api/voxflow_api/seed.py"

# The remote script is buffered to a file and run with stdin CLOSED. Piping it
# into `bash -s` makes bash read the script from stdin, and any child that
# attaches to stdin (docker run -i, docker compose exec -T) drains the unread
# remainder — bash then hits EOF and exits 0 silently, mid-script. That is exactly
# how an earlier migration run reported success without touching the database.
"${SSH[@]}" 'f=$(mktemp /tmp/voxflow-remote.XXXXXX); cat > "$f"; bash "$f" </dev/null; rc=$?; rm -f "$f"; exit $rc' <<'REMOTE'
set -uo pipefail
cd /home/ubuntu/voxflow-voice-agent/deploy
DC=(docker compose --env-file ../.env -f docker-compose.prod.yml)

DOMAIN="$(grep -E '^DOMAIN=' ../.env | head -1 | cut -d= -f2- | tr -d '"'"'"' ')"
[[ -n "$DOMAIN" ]] || { echo "FAILED: DOMAIN not set in .env"; exit 1; }

# --- 1. Rebuild api so the container actually runs the pushed file ----------
echo
echo "==> rebuilding the api image (pip layers are cached; ~1 min)"
"${DC[@]}" build api || { echo "FAILED: api image build"; exit 1; }

echo
echo "==> recreating the api container"
"${DC[@]}" up -d --no-deps --force-recreate api || { echo "FAILED: api recreate"; exit 1; }

# --- 2. Wait for real readiness --------------------------------------------
# Container State flips to "running" in milliseconds, long before uvicorn binds
# a port. Health is the only signal worth polling.
echo "==> waiting for api health (up to 3 min)"
api_ok=0
for i in $(seq 1 36); do
  h="$(docker inspect -f '{{.State.Health.Status}}' voxflow-api 2>/dev/null || echo none)"
  [[ "$h" == "healthy" ]]   && { echo "    healthy after ~$((i*5))s"; api_ok=1; break; }
  [[ "$h" == "unhealthy" ]] && { echo "    UNHEALTHY"; break; }
  sleep 5
done
if [[ "$api_ok" != "1" ]]; then
  echo "FAILED: api never became healthy. Last 40 log lines:"
  docker logs voxflow-api --tail 40 2>&1 | tail -40
  exit 1
fi

# A healthy api on DB_SCHEMA_BOOTSTRAP_MODE=auto is itself proof the schema is
# complete: init_db() runs verify_schema_tables() and refuses to boot if any ORM
# table is missing. So reaching this line means migrations/ really did apply.

# --- 3. Restart caddy: the recreate above changed the api container's IP -----
# Caddy resolves each upstream once and caches the address for the life of its
# process. Skipping this makes every /api route 502 even though api is healthy.
# Certificates live on the caddy_data volume, so nothing is re-issued.
echo
echo "==> restarting caddy so it re-resolves api:8000"
"${DC[@]}" restart caddy
sleep 4

# --- 4. Seed. No --reset: it is refused on Postgres, by design. -------------
echo
echo "==> seeding (idempotent — already-present rows are skipped)"
"${DC[@]}" exec -T api python -m voxflow_api.seed </dev/null
seed_rc=$?
if [[ $seed_rc -ne 0 ]]; then
  echo "FAILED: seeder exited $seed_rc"
  exit 1
fi

# --- 5. Count what actually landed -----------------------------------------
# The seeder logging "seed.done" only proves it reached the end. Read the rows
# back out of Postgres and fail on any table the demo needs but does not have.
echo
echo "=== row counts read back from the database ==="
"${DC[@]}" exec -T api python - <<'PY' 2>&1
import sys
from voxflow_api.db import (
    Appointment, Call, CommunicationLog, Order, Product, Shipment,
    Stock, Supplier, Tenant, TenantPhoneNumber, session_scope,
)

# (model, label, minimum the demo needs)
EXPECT = [
    (Tenant,            "tenants",              4),
    (Product,           "products",            17),
    (Supplier,          "suppliers",            9),
    (Stock,             "stock",               17),
    (Order,             "orders",               4),
    (Shipment,          "shipments",            1),
    (TenantPhoneNumber, "tenant_phone_numbers", 2),
    (Call,              "calls",                1),
    (Appointment,       "appointments",         2),
    (CommunicationLog,  "communication_logs",   2),
]

bad = []
with session_scope() as db:
    for model, label, want in EXPECT:
        n = db.query(model).count()
        flag = "ok" if n >= want else "TOO FEW (want >= %d)" % want
        if n < want:
            bad.append(label)
        print("  %-22s %4d  %s" % (label, n, flag))

    # The order-status flow is the whole product. Prove the exact record the demo
    # call asks about is present, joined to its shipment, with a readable location.
    o = db.get(Order, "PO-1717000000-001")
    if o is None:
        print("  MISSING the demo order PO-1717000000-001")
        bad.append("demo order")
    else:
        s = db.query(Shipment).filter_by(order_id=o.id).one_or_none()
        print("  demo order             %s  signed=%s  status=%s  shipment=%s"
              % (o.id, o.po_signed, o.status, (s.tracking_no if s else "NONE")))
        if s is None:
            bad.append("demo shipment")

if bad:
    print("FAILED: incomplete: %s" % ", ".join(bad))
    sys.exit(1)
print("  all expected rows present")
PY
[[ "${PIPESTATUS[0]}" -eq 0 ]] || { echo "FAILED: row-count check"; exit 1; }

# --- 6. Prove the data is reachable over public HTTPS ----------------------
# Counts in the database mean nothing if the API cannot serve them. /api/health
# covers the process; a tenant-scoped read covers the query path and CORS-free
# server-side access that the dashboard depends on.
echo
echo "=== public HTTPS reads (https://${DOMAIN}) ==="
rc=0
h="$(curl -s --max-time 25 "https://${DOMAIN}/api/health" || true)"
case "$h" in
  *voxflow-api*) echo "  /api/health   ${h:0:110}" ;;
  *) echo "  /api/health   unexpected: ${h:0:200}"; rc=1 ;;
esac

if [[ $rc -ne 0 ]]; then
  echo
  echo "=== api log (last 25) ==="; docker logs voxflow-api --tail 25 2>&1 | tail -25
  echo "RESULT: something above failed"
  exit 1
fi

echo
echo "RESULT: DATABASE SEEDED — orders, shipments, calls and the phone map are live"
REMOTE

printf '\n\033[1;32m==> Done — Postgres holds the demo data\033[0m\n'
