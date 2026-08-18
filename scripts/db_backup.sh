#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# VoxFlow — Postgres backup to local volume
#
# Runs pg_dump against the production Supabase Postgres and saves a
# compressed dump to /app/data/backups/.  Old backups beyond the retention
# window are deleted automatically.
#
# Usage (inside the API container):
#   /app/scripts/db_backup.sh
#
# Or via docker exec:
#   docker exec voxflow-api /app/scripts/db_backup.sh
#
# Environment variables (read from .env):
#   DATABASE_URL           — Postgres connection string (required)
#   DB_BACKUP_KEEP_DAYS    — how many days to keep (default: 7)
# ---------------------------------------------------------------------------

set -euo pipefail

BACKUP_DIR="${DATA_DIR:-/app/data}/backups"
KEEP_DAYS="${DB_BACKUP_KEEP_DAYS:-7}"
TIMESTAMP="$(date -u +%Y%m%d_%H%M%S)"
FILENAME="voxflow_${TIMESTAMP}.sql.gz"

mkdir -p "$BACKUP_DIR"

echo "[backup] Starting pg_dump → ${BACKUP_DIR}/${FILENAME}"

# DATABASE_URL is already in the environment (from .env / docker compose).
# pg_dump reads it natively via the conninfo string.
pg_dump "$DATABASE_URL" | gzip > "${BACKUP_DIR}/${FILENAME}"

SIZE=$(du -h "${BACKUP_DIR}/${FILENAME}" | cut -f1)
echo "[backup] Done — ${FILENAME} (${SIZE})"

# Rotate: delete dumps older than KEEP_DAYS.
DELETED=$(find "$BACKUP_DIR" -name 'voxflow_*.sql.gz' -type f -mtime "+${KEEP_DAYS}" -print -delete | wc -l)
if [ "$DELETED" -gt 0 ]; then
    echo "[backup] Rotated ${DELETED} old backup(s) (> ${KEEP_DAYS} days)"
fi

echo "[backup] Current backups in ${BACKUP_DIR}:"
ls -lh "$BACKUP_DIR"/voxflow_*.sql.gz 2>/dev/null || echo "  (none)"
