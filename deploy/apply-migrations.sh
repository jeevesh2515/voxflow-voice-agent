#!/usr/bin/env bash
#
# VoxFlow — apply the reviewed SQL migrations to the production database, then
# bring the API up.
#
# WHY this and not DB_SCHEMA_BOOTSTRAP_MODE=always: `always` would run
# Base.metadata.create_all(), which emits tables from the ORM only. The
# checked-in migrations additionally establish row-level security (22 policies),
# 89 indexes and 8 column comments that create_all never produces. Booting off
# create_all would give a database that accepts writes but lacks the RLS that
# keeps one tenant's calls away from another's. So: apply the SQL, leave the
# mode on `auto`, and let the API's own verify_schema_tables() confirm the result.
#
# Every statement is idempotent (CREATE TABLE/INDEX IF NOT EXISTS, ADD COLUMN
# IF NOT EXISTS, DROP POLICY IF EXISTS before CREATE POLICY), so re-running this
# script is safe and is the correct response to a partial failure.
#
# Usage: ./deploy/apply-migrations.sh
#
set -euo pipefail

VM_HOST="${VM_HOST:-193.123.187.97}"
VM_USER="${VM_USER:-ubuntu}"
VM_KEY="${VM_KEY:-$HOME/Downloads/ssh-key-2026-08-03.key}"

ssh -i "$VM_KEY" -o StrictHostKeyChecking=accept-new -o ConnectTimeout=15 \
    "${VM_USER}@${VM_HOST}" 'f=$(mktemp /tmp/voxflow-remote.XXXXXX); cat > "$f"; bash "$f" </dev/null; rc=$?; rm -f "$f"; exit $rc' <<'REMOTE'
set -uo pipefail
cd /home/ubuntu/voxflow-voice-agent

MIG_DIR="$PWD/migrations"
[[ -d "$MIG_DIR" ]] || { echo "FAILED: $MIG_DIR not found (git pull on the VM first)"; exit 1; }

count="$(ls -1 "$MIG_DIR"/*.sql 2>/dev/null | wc -l | tr -d ' ')"
echo "==> found $count migration files"
[[ "$count" -gt 0 ]] || { echo "FAILED: no .sql files"; exit 1; }

# psql speaks libpq URLs, not SQLAlchemy ones. Strip any driver suffix
# (postgresql+psycopg2:// / postgresql+asyncpg:// -> postgresql://).
RAW_URL="$(grep -E '^DATABASE_URL=' .env | head -1 | cut -d= -f2- | tr -d '"'"'"' ')"
[[ -n "$RAW_URL" ]] || { echo "FAILED: DATABASE_URL not set in .env"; exit 1; }
PG_URL="$(printf '%s' "$RAW_URL" | sed -E 's|^postgresql\+[a-z0-9]+://|postgresql://|')"

# Never echo credentials.
echo "==> target: $(printf '%s' "$PG_URL" | sed -E 's|://[^@]*@|://<redacted>@|')"

# The api image does not contain migrations/ (its build context is apps/api),
# so use a throwaway postgres client with the directory mounted read-only.
PSQL_IMAGE=postgres:16-alpine
docker image inspect "$PSQL_IMAGE" >/dev/null 2>&1 || {
  echo "==> pulling $PSQL_IMAGE"
  docker pull -q "$PSQL_IMAGE"
}

run_psql() {
  docker run --rm \
    -v "$MIG_DIR":/migrations:ro \
    -e PGCONNECT_TIMEOUT=15 \
    "$PSQL_IMAGE" \
    psql "$PG_URL" -v ON_ERROR_STOP=1 --no-psqlrc --quiet "$@"
}

echo
echo "==> connectivity check"
run_psql -tAc 'select version()' || { echo "FAILED: cannot connect to Postgres"; exit 1; }

echo
echo "==> applying migrations in order"
# --single-transaction per file: a file either lands whole or not at all, so a
# failure never leaves half a migration behind.
for f in $(ls -1 "$MIG_DIR"/*.sql | sort); do
  name="$(basename "$f")"
  printf '  %-42s ' "$name"
  if out="$(run_psql --single-transaction -f "/migrations/$name" 2>&1)"; then
    echo "ok"
  else
    echo "FAILED"
    echo "$out" | tail -25
    echo
    echo "Stopped at $name. Nothing from this file was committed."
    exit 1
  fi
done

echo
echo "==> verifying schema"
tables="$(run_psql -tAc "select count(*) from information_schema.tables where table_schema='public'" | tr -d ' ')"
echo "  public tables: $tables"
rls="$(run_psql -tAc "select count(*) from pg_policies where schemaname='public'" | tr -d ' ')"
echo "  row-level security policies: $rls"
idx="$(run_psql -tAc "select count(*) from pg_indexes where schemaname='public'" | tr -d ' ')"
echo "  indexes: $idx"

# The API refuses to boot unless every ORM-mapped table exists. Check the exact
# set it complained about rather than trusting a count.
missing="$(run_psql -tAc "
  with expected(t) as (values
    ('agent_states'),('appointments'),('calls'),('campaign_dispatch_reservations'),
    ('campaign_policy_decisions'),('campaign_queue'),('communication_logs'),
    ('drill_results'),('job_attempts'),('job_outbox'),('job_runs'),('orders'),
    ('outbound_campaigns'),('pilot_cohort_members'),('pilot_configurations'),
    ('pilot_operational_evidence'),('pilot_security_incidents'),('privacy_requests'),
    ('products'),('provider_callback_adapter_audits'),('provider_callback_quarantines'),
    ('provider_events'),('provider_operations'),('recipient_campaign_preferences'),
    ('reliability_slos'),('shipments'),('side_effect_intents'),('stock'),('suppliers'),
    ('tenant_campaign_policies'),('tenant_daily_dispatch_usage'),('tenant_members'),
    ('tenant_phone_numbers'),('tenant_privacy_policies'),('tenants'),('worksheet_logs'))
  select coalesce(string_agg(t, ', '), 'none') from expected
  where t not in (select table_name from information_schema.tables where table_schema='public')
" | tr -d '\r')"
echo "  still missing: $missing"
[[ "$missing" == "none" ]] || { echo "FAILED: schema incomplete"; exit 1; }

# --- bring the API up ------------------------------------------------------
echo
echo "==> restarting api (531 restarts of the old crash loop end here)"
cd deploy
DC=(docker compose --env-file ../.env -f docker-compose.prod.yml)
"${DC[@]}" up -d --force-recreate api
# Caddy caches upstream IPs for the life of its process; a recreated api gets a
# new IP, so Caddy must be restarted or every /api/* request 502s.
"${DC[@]}" restart caddy

echo "==> waiting for api health (up to 3 min)"
health=none
for i in $(seq 1 36); do
  health="$(docker inspect -f '{{.State.Health.Status}}' voxflow-api 2>/dev/null || echo none)"
  [[ "$health" == "healthy" ]] && { echo "    healthy after ~$((i*5))s"; break; }
  sleep 5
done
[[ "$health" == "healthy" ]] || {
  echo "    still $health — last 40 api log lines:"
  docker logs voxflow-api --tail 40 2>&1 | tail -40
  exit 1
}

echo
echo "=== container state ==="
"${DC[@]}" ps

DOMAIN="$(grep -E '^DOMAIN=' ../.env | head -1 | cut -d= -f2- | tr -d '"'"'"' ')"
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
check /sign-in      200
check /dashboard   '307|302'   # auth gate in src/proxy.ts is live under Next 16
check /api/health   200
echo
echo "/api/health body: $(curl -s --max-time 25 "https://${DOMAIN}/api/health" | head -c 300)"

[[ $rc -eq 0 ]] || { echo; echo "RESULT: HTTPS checks failed"; exit 1; }
echo
echo "RESULT: ALL GREEN"
REMOTE
