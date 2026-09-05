#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# VoxFlow — encrypted Postgres backup to an off-VM private GitHub repo
# (Phase 0, step 6).
#
# Supabase free tier has no point-in-time recovery, so this is the recovery
# path: nightly pg_dump, gzip, AES-256 via gpg, pushed to a private repo the
# VM reaches only through a write-limited deploy key.
#
# What it does, in order:
#   1. pg_dump the live Supabase Postgres (throwaway postgres:17-alpine
#      container — no client tools needed on the host)
#   2. gzip + gpg AES-256 symmetric encryption with BACKUP_ENCRYPTION_KEY
#   3. commit + push to the backups repo (deploy key, write-only scope there)
#   4. prune repo copies older than BACKUP_KEEP_DAYS_REPO (default 30)
#   5. append one JSON evidence line to ~/voxflow-ops/backup.jsonl
#
# The plaintext dump never touches disk unencrypted outside the pipe, and the
# encrypted local copy is removed after a successful push — the repo is the
# store, the VM keeps only the log. (If the push fails, the local encrypted
# file is KEPT and the failure is logged, so a network blip never silently
# eats a backup.)
#
# Usage:
#   ./deploy/backup_to_github.sh
#
# Environment (all read from ../.env unless already exported):
#   DATABASE_URL            Supabase pooler URL (trailing space tolerated)
#   BACKUP_ENCRYPTION_KEY   REQUIRED. Symmetric gpg passphrase. Anyone holding
#                           this key plus the repo can read every backup, so it
#                           lives only in the VM .env (chmod 600) and in your
#                           password manager — nowhere else.
#   BACKUP_REPO_SSH         git URL of the backups repo
#                           (default git@github.com:jeevesh2515/voxflow-backups.git)
#   BACKUP_DEPLOY_KEY       path to the deploy private key
#                           (default ~/.ssh/voxflow_backups_ed25519)
#   BACKUP_KEEP_DAYS_REPO   repo retention in days (default 30)
#   OPS_DIR                 ops state dir (default ~/voxflow-ops)
#
# Exit codes: 0 = pushed, 1 = failed (evidence still logged).
# ---------------------------------------------------------------------------

set -uo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OPS_DIR="${OPS_DIR:-$HOME/voxflow-ops}"
BACKUP_REPO_SSH="${BACKUP_REPO_SSH:-git@github.com:jeevesh2515/voxflow-backups.git}"
BACKUP_DEPLOY_KEY="${BACKUP_DEPLOY_KEY:-$HOME/.ssh/voxflow_backups_ed25519}"
KEEP_REPO="${BACKUP_KEEP_DAYS_REPO:-30}"
LOG_FILE="$OPS_DIR/backup.jsonl"
WORK="$OPS_DIR/backups-work"
CLONE="$OPS_DIR/backups-repo"

TS="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
STAMP="$(date -u +%Y%m%d_%H%M%S)"
mkdir -p "$OPS_DIR" "$WORK"

log_line() {
    # $1 status, $2 detail
    python3 - "$TS" "$1" "$2" <<'PY' >> "$LOG_FILE"
import json, sys
print(json.dumps({"ts": sys.argv[1], "status": sys.argv[2], "detail": sys.argv[3][:300]}))
PY
}

fail() {
    log_line "failed" "$1"
    echo "[backup] ${TS} status=failed detail=$1" >&2
    exit 1
}

if [[ -z "${DATABASE_URL:-}" && -f "${REPO_ROOT}/.env" ]]; then
    DATABASE_URL="$(grep '^DATABASE_URL=' "${REPO_ROOT}/.env" | head -1 | cut -d= -f2- | tr -d '\r' | xargs)"
fi
if [[ -z "${BACKUP_ENCRYPTION_KEY:-}" && -f "${REPO_ROOT}/.env" ]]; then
    BACKUP_ENCRYPTION_KEY="$(grep '^BACKUP_ENCRYPTION_KEY=' "${REPO_ROOT}/.env" | head -1 | cut -d= -f2- | tr -d '\r' | xargs)"
fi
[[ -n "${DATABASE_URL:-}" ]] || fail "DATABASE_URL not set"
[[ -n "${BACKUP_ENCRYPTION_KEY:-}" ]] || fail "BACKUP_ENCRYPTION_KEY not set"
[[ "${DATABASE_URL}" == postgres* ]] || fail "DATABASE_URL is not postgres"
[[ -f "$BACKUP_DEPLOY_KEY" ]] || fail "deploy key missing at $BACKUP_DEPLOY_KEY"
export GIT_SSH_COMMAND="ssh -i $BACKUP_DEPLOY_KEY -o StrictHostKeyChecking=accept-new -o ConnectTimeout=20"

ENC_FILE="$WORK/voxflow_${STAMP}.sql.gz.enc"

# 1+2. Dump | compress | encrypt. Plaintext exists only inside the pipe.
docker run --rm "${PSQL_IMAGE:-postgres:17-alpine}" pg_dump "$DATABASE_URL" 2>"$WORK/pg_dump.err" \
    | gzip \
    | gpg --batch --yes --passphrase "$BACKUP_ENCRYPTION_KEY" \
          --symmetric --cipher-algo AES256 -o "$ENC_FILE" \
    || fail "pg_dump/gpg failed: $(head -c 200 "$WORK/pg_dump.err")"

SIZE="$(du -h "$ENC_FILE" | cut -f1)"

# 3. Push to the private repo.
if [[ ! -d "$CLONE/.git" ]]; then
    rm -rf "$CLONE"
    git clone -q "$BACKUP_REPO_SSH" "$CLONE" 2>"$WORK/clone.err" \
        || fail "clone failed: $(head -c 200 "$WORK/clone.err")"
fi
cp "$ENC_FILE" "$CLONE/"
cd "$CLONE"
git pull -q --rebase 2>/dev/null || true
git add "voxflow_${STAMP}.sql.gz.enc"

# 4. Prune repo copies older than retention (encrypted blobs accumulate fast).
find . -maxdepth 1 -name 'voxflow_*.sql.gz.enc' -mtime "+$KEEP_REPO" -delete 2>/dev/null || true
git add -A
if git diff --cached --quiet; then
    fail "nothing to commit after dump (unexpected)"
fi
git -c user.name="voxflow-backup" -c user.email="backup@voxflow.local" \
    commit -qm "nightly backup ${STAMP} (${SIZE})" \
    || fail "commit failed"
git push -q origin HEAD 2>"$WORK/push.err" \
    || fail "push failed: $(head -c 200 "$WORK/push.err")"

# 5. Push succeeded: the repo is the store, drop the local encrypted copy.
rm -f "$ENC_FILE"
log_line "ok" "pushed voxflow_${STAMP}.sql.gz.enc (${SIZE})"
echo "[backup] ${TS} status=ok file=voxflow_${STAMP}.sql.gz.enc size=${SIZE} -> ${LOG_FILE}"
