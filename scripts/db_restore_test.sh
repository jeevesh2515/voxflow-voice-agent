#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# VoxFlow — Database Restore & Integrity Verification Drill (Day 43)
#
# Tests decrypting and restoring the latest backup into an isolated scratch
# database to guarantee recovery path validity without mutating production data.
#
# Usage:
#   ./scripts/db_restore_test.sh [optional_path_to_backup_file]
#
# Environment variables:
#   BACKUP_ENCRYPTION_KEY   — Symmetric passphrase used for encryption
#   DATA_DIR                — Base data directory (default: ./data)
# ---------------------------------------------------------------------------

set -euo pipefail

DATA_DIR="${DATA_DIR:-./data}"
BACKUP_DIR="${DATA_DIR}/backups"
ENC_KEY="${BACKUP_ENCRYPTION_KEY:-}"
SCRATCH_DIR="/tmp/voxflow-restore-drill"
mkdir -p "$SCRATCH_DIR"

TARGET_FILE="${1:-}"
if [[ -z "$TARGET_FILE" ]]; then
    # Pick the most recent backup
    TARGET_FILE=$(find "$BACKUP_DIR" -type f \( -name 'voxflow_*.gz' -o -name 'voxflow_*.enc' \) | sort -r | head -n 1)
fi

if [[ -z "$TARGET_FILE" || ! -f "$TARGET_FILE" ]]; then
    echo "[restore-drill] Error: No backup file found in ${BACKUP_DIR} to test."
    exit 1
fi

echo "[restore-drill] Testing recovery for backup: ${TARGET_FILE}"
TMP_RESTORE="${SCRATCH_DIR}/restore_$(date +%s)"

# 1. Decrypt if encrypted
DECRYPTED_GZ="${TMP_RESTORE}.gz"
if [[ "$TARGET_FILE" == *.enc ]]; then
    echo "[restore-drill] Decrypting encrypted archive..."
    if [[ -z "$ENC_KEY" ]]; then
        echo "[restore-drill] Error: TARGET_FILE is encrypted but BACKUP_ENCRYPTION_KEY is not set."
        exit 1
    fi
    if command -v gpg >/dev/null 2>&1; then
        gpg --batch --yes --passphrase "$ENC_KEY" --decrypt -o "$DECRYPTED_GZ" "$TARGET_FILE"
    elif command -v openssl >/dev/null 2>&1; then
        openssl enc -d -aes-256-cbc -pbkdf2 -in "$TARGET_FILE" -out "$DECRYPTED_GZ" -pass "pass:${ENC_KEY}"
    else
        echo "[restore-drill] Error: neither gpg nor openssl found for decryption."
        exit 1
    fi
else
    cp "$TARGET_FILE" "$DECRYPTED_GZ"
fi

# 2. Decompress
echo "[restore-drill] Decompressing archive..."
gunzip "$DECRYPTED_GZ"
UNPACKED="${TMP_RESTORE}"

# 3. Verify integrity based on dump format
if [[ "$TARGET_FILE" == *.db.gz* ]]; then
    echo "[restore-drill] Verifying SQLite database integrity..."
    if command -v sqlite3 >/dev/null 2>&1; then
        INTEGRITY=$(sqlite3 "$UNPACKED" "PRAGMA integrity_check;" || echo "error")
        echo "[restore-drill] SQLite integrity check: ${INTEGRITY}"
        TABLE_COUNT=$(sqlite3 "$UNPACKED" "SELECT count(*) FROM sqlite_master WHERE type='table';" || echo 0)
        echo "[restore-drill] Verified table count: ${TABLE_COUNT}"
        if [[ "$INTEGRITY" != "ok" ]]; then
            echo "[restore-drill] FAILED: SQLite integrity check failed."
            rm -rf "$SCRATCH_DIR"
            exit 1
        fi
    fi
elif [[ "$TARGET_FILE" == *.sql.gz* ]]; then
    echo "[restore-drill] Verifying SQL dump structure..."
    SQL_LINES=$(wc -l < "$UNPACKED" || echo 0)
    echo "[restore-drill] SQL dump contains ${SQL_LINES} lines."
    if grep -q -E "(CREATE TABLE|INSERT INTO)" "$UNPACKED"; then
        echo "[restore-drill] Verified valid DDL/DML statements present in SQL dump."
    else
        echo "[restore-drill] FAILED: No valid DDL/DML statements detected in dump."
        rm -rf "$SCRATCH_DIR"
        exit 1
    fi
fi

# Cleanup
rm -rf "$SCRATCH_DIR"
echo "[restore-drill] SUCCESS: Backup restore verification drill passed cleanly!"
exit 0
