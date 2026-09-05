#!/usr/bin/env bash
# migrate-db-to-rds.sh
# Dumps Supabase PostgreSQL → restores to AWS RDS
# Verifies row counts before signalling cutover readiness
#
# Usage: ./scripts/migrate-db-to-rds.sh
# Prereqs: psql, pg_dump, pg_restore installed; terraform applied; VPN/bastion access to RDS
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
REGION="eu-west-2"
DUMP_FILE="/tmp/voxflow_supabase_$(date +%Y%m%d_%H%M%S).dump"

# --------------------------------------------------------------------------
# 1. Get source (Supabase) connection from .env
# --------------------------------------------------------------------------
if [[ -f "$ROOT/.env" ]]; then
  SUPABASE_DB_URL=$(grep '^SUPABASE_DB_URL\|^DATABASE_URL' "$ROOT/.env" | head -1 | cut -d= -f2-)
fi

if [[ -z "${SUPABASE_DB_URL:-}" ]]; then
  echo "ERROR: Set SUPABASE_DB_URL in your .env (the Supabase direct connection string)"
  exit 1
fi

# --------------------------------------------------------------------------
# 2. Get target (RDS) connection from Secrets Manager
# --------------------------------------------------------------------------
SECRET_ARN=$(terraform -chdir="$ROOT/deploy/terraform" output -raw db_secret_arn)
RDS_URL=$(aws secretsmanager get-secret-value \
  --region "$REGION" \
  --secret-id "$SECRET_ARN" \
  --query 'SecretString' --output text | jq -r '.url')

echo "📦 Dumping Supabase database..."
pg_dump "$SUPABASE_DB_URL" \
  --format=custom \
  --no-owner \
  --no-acl \
  --file="$DUMP_FILE"
echo "   Dump written: $DUMP_FILE ($(du -sh $DUMP_FILE | cut -f1))"

echo "📥 Restoring to RDS..."
pg_restore "$RDS_URL" \
  --format=custom \
  --no-owner \
  --no-acl \
  --verbose \
  "$DUMP_FILE"

echo ""
echo "🔍 Verifying row counts..."
# Get counts from Supabase
SRC_COUNTS=$(psql "$SUPABASE_DB_URL" -t -c \
  "SELECT tablename, n_live_tup FROM pg_stat_user_tables ORDER BY tablename;")

# Get counts from RDS
DST_COUNTS=$(psql "$RDS_URL" -t -c \
  "SELECT tablename, n_live_tup FROM pg_stat_user_tables ORDER BY tablename;")

echo "=== SOURCE (Supabase) ==="
echo "$SRC_COUNTS"
echo ""
echo "=== DESTINATION (RDS) ==="
echo "$DST_COUNTS"

echo ""
echo "✅ Migration complete. Manually verify the counts match above."
echo "   Only update DNS/ECS env vars after manual spot-check passes."
