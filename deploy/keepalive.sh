#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# VoxFlow — Supabase keep-alive ping (Phase 0, step 3)
#
# Supabase free-tier projects pause after ~7 days without activity. This runs a
# real SQL statement against the project and appends one JSON line of evidence
# to a persistent log, so the schedule can be AUDITED later instead of trusted.
#
# Why it pings the database directly instead of an HTTP health route
# ------------------------------------------------------------------
# `/api/health` only reads settings — it never opens a database connection, so
# curling it would report success while the project drifted toward a pause. And
# routing the ping through the API would couple "does the database stay awake"
# to "is the app container currently healthy", which are separate failures. psql
# runs in a throwaway container, so this keeps working across app deploys,
# rebuilds, and outages.
#
# Usage:
#   ./deploy/keepalive.sh                    # read DATABASE_URL from ../.env
#   DATABASE_URL=postgresql://... ./deploy/keepalive.sh
#
# Environment:
#   DATABASE_URL   Overrides the value read from the .env beside the repo root
#   KEEPALIVE_LOG  Append-only evidence log (default ~/voxflow-ops/keepalive.jsonl)
#   PSQL_IMAGE     Postgres client image (default postgres:16-alpine)
#
# Exit codes: 0 = query succeeded, 1 = ping failed (the line is still logged).
# ---------------------------------------------------------------------------

set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_FILE="${KEEPALIVE_LOG:-$HOME/voxflow-ops/keepalive.jsonl}"
PSQL_IMAGE="${PSQL_IMAGE:-postgres:16-alpine}"

# The committed .env carries a trailing space on DATABASE_URL. The application
# strips it in db.py::_clean_db_url, but psql does not — it tries to open a
# database literally named "postgres " and fails. `xargs` with no args trims.
if [[ -z "${DATABASE_URL:-}" && -f "${REPO_ROOT}/.env" ]]; then
    DATABASE_URL="$(grep '^DATABASE_URL=' "${REPO_ROOT}/.env" | head -1 | cut -d= -f2- | tr -d '\r' | xargs)"
fi
DATABASE_URL="${DATABASE_URL:-}"

TS="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
mkdir -p "$(dirname "$LOG_FILE")"

log_line() {
    # $1 status, $2 detail, $3 tenants ("" when unknown), $4 elapsed_ms
    python3 - "$TS" "$1" "$2" "$3" "$4" <<'PY' >> "$LOG_FILE"
import json, sys
ts, status, detail, tenants, elapsed = sys.argv[1:6]
row = {"ts": ts, "status": status, "elapsed_ms": int(elapsed or 0), "detail": detail[:300]}
if tenants:
    row["tenant_count"] = int(tenants)
print(json.dumps(row))
PY
}

if [[ -z "$DATABASE_URL" ]]; then
    log_line "failed" "DATABASE_URL not set and not found in .env" "" 0
    echo "[keepalive] ${TS} status=failed reason=no_database_url" >&2
    exit 1
fi

if [[ "$DATABASE_URL" != postgres* ]]; then
    log_line "skipped" "DATABASE_URL is not postgres; nothing can pause" "" 0
    echo "[keepalive] ${TS} status=skipped reason=not_postgres"
    exit 0
fi

START_MS=$(($(date +%s%N) / 1000000))

# Two facts in one round trip: the connection works, and the schema is readable.
# A bare `SELECT 1` proves only that the socket opened.
OUT="$(docker run --rm "$PSQL_IMAGE" psql "$DATABASE_URL" \
        -tAc 'select (select count(*) from tenants);' 2>&1)"
RC=$?

ELAPSED_MS=$(( $(($(date +%s%N) / 1000000)) - START_MS ))
OUT_TRIMMED="$(printf '%s' "$OUT" | tr -d '\n' | xargs 2>/dev/null || printf '%s' "$OUT")"

if [[ $RC -eq 0 && "$OUT_TRIMMED" =~ ^[0-9]+$ ]]; then
    log_line "ok" "tenants=${OUT_TRIMMED}" "$OUT_TRIMMED" "$ELAPSED_MS"
    echo "[keepalive] ${TS} status=ok tenants=${OUT_TRIMMED} elapsed=${ELAPSED_MS}ms -> ${LOG_FILE}"
    exit 0
fi

log_line "failed" "$OUT_TRIMMED" "" "$ELAPSED_MS"
echo "[keepalive] ${TS} status=failed rc=${RC} detail=${OUT_TRIMMED}" >&2
exit 1
