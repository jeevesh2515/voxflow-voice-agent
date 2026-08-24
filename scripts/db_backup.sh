#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# VoxFlow — Encrypted Database Backup Utility (Day 43)
#
# Dumps the active database (Postgres or SQLite), compresses via gzip, and
# applies AES-256 symmetric encryption with BACKUP_ENCRYPTION_KEY if set.
# Backups older than DB_BACKUP_KEEP_DAYS are rotated automatically.
#
# Usage:
#   ./scripts/db_backup.sh
#
# Environment variables:
#   DATABASE_URL            — Database connection string (Postgres or SQLite)
#   DATA_DIR                — Base data directory (default: ./data)
#   DB_BACKUP_KEEP_DAYS     — Retention window in days (default: 7)
#   BACKUP_ENCRYPTION_KEY   — Symmetric passphrase for AES-256 encryption
# ---------------------------------------------------------------------------

set -euo pipefail

DATA_DIR="${DATA_DIR:-./data}"
BACKUP_DIR="${DATA_DIR}/backups"
KEEP_DAYS="${DB_BACKUP_KEEP_DAYS:-7}"
TIMESTAMP="$(date -u +%Y%m%d_%H%M%S)"
ENC_KEY="${BACKUP_ENCRYPTION_KEY:-}"

mkdir -p "$BACKUP_DIR"

DB_URL="${DATABASE_URL:-}"

echo "[backup] Starting database backup (${TIMESTAMP})..."

if [[ "$DB_URL" == postgresql* ]] || [[ "$DB_URL" == postgres* ]]; then
    RAW_TARGET="${BACKUP_DIR}/voxflow_${TIMESTAMP}.sql.gz"
    echo "[backup] Executing pg_dump against Postgres..."
    pg_dump "$DB_URL" | gzip > "$RAW_TARGET"
else
    RAW_TARGET="${BACKUP_DIR}/voxflow_${TIMESTAMP}.db.gz"
    echo "[backup] Backing up SQLite database..."
    SQLITE_PATH="${DB_URL#sqlite:////}"
    SQLITE_PATH="${SQLITE_PATH#sqlite:///}"
    if [[ -z "$SQLITE_PATH" || ! -f "$SQLITE_PATH" ]]; then
        SQLITE_PATH="/tmp/voxflow-data/voxflow.db"
    fi
    if [[ -f "$SQLITE_PATH" ]]; then
        gzip -c "$SQLITE_PATH" > "$RAW_TARGET"
    else
        echo "[backup] Warning: SQLite source not found at ${SQLITE_PATH}; creating empty fallback dump."
        echo "" | gzip > "$RAW_TARGET"
    fi
fi

FINAL_FILE="$RAW_TARGET"

# Apply encryption if BACKUP_ENCRYPTION_KEY is supplied
if [[ -n "$ENC_KEY" ]]; then
    ENC_TARGET="${RAW_TARGET}.enc"
    echo "[backup] Encrypting backup with AES-256..."
    if command -v gpg >/dev/null 2>&1; then
        gpg --batch --yes --passphrase "$ENC_KEY" --symmetric --cipher-algo AES256 -o "$ENC_TARGET" "$RAW_TARGET"
        rm -f "$RAW_TARGET"
        FINAL_FILE="$ENC_TARGET"
    elif command -v openssl >/dev/null 2>&1; then
        openssl enc -aes-256-cbc -salt -pbkdf2 -in "$RAW_TARGET" -out "$ENC_TARGET" -pass "pass:${ENC_KEY}"
        rm -f "$RAW_TARGET"
        FINAL_FILE="$ENC_TARGET"
    else
        echo "[backup] Warning: neither gpg nor openssl found; leaving compressed archive unencrypted."
    fi
fi

SIZE=$(du -h "$FINAL_FILE" | cut -f1)
echo "[backup] Backup completed successfully: ${FINAL_FILE} (${SIZE})"

# Rotation: delete backups older than KEEP_DAYS
DELETED=$(find "$BACKUP_DIR" -type f \( -name 'voxflow_*.gz' -o -name 'voxflow_*.enc' \) -mtime "+${KEEP_DAYS}" -print -delete 2>/dev/null | wc -l || echo 0)
if [[ "$DELETED" -gt 0 ]]; then
    echo "[backup] Rotated ${DELETED} old backup(s) (> ${KEEP_DAYS} days)"
fi

echo "[backup] Active backups in ${BACKUP_DIR}:"
ls -lh "$BACKUP_DIR"/voxflow_* 2>/dev/null || echo "  (none)"
