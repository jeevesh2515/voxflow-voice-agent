#!/usr/bin/env bash
#
# VoxFlow — find out what this Twilio account really has, and optionally buy the
# inbound number the product needs.
#
# WHY: wire-twilio.sh proved the credentials are valid (the account fetch
# succeeded — bad credentials raise TwilioRestException 20003) and that the
# account owns ZERO phone numbers across zero subaccounts. So the +44 number is
# not a released Twilio number hiding somewhere; the account has never had one
# attached. The remaining explanation is that +44... is a VERIFIED CALLER ID, not
# a purchased number — a trial makes you verify your own mobile so you can call
# and text it, and a verified caller ID is outbound-only: it has no voice webhook
# and cannot receive an inbound call. This script checks that directly.
#
# Two modes:
#   (default)      read-only diagnosis. Buys nothing, changes nothing.
#   --buy COUNTRY  purchases ONE voice-capable local number in COUNTRY, sets its
#                  voice webhook, maps it to the tenant, writes it to the VM's
#                  .env and recreates api so it takes effect.
#
# --buy spends real money (trial credit, then ~$1.15/mo). It is deliberately
# behind an explicit flag, prints exactly what it is about to do, and waits so
# Ctrl-C still works.
#
# Usage:
#   ./deploy/twilio-number.sh                 # diagnose only
#   ./deploy/twilio-number.sh --buy US        # buy a US local number, tenant=varun
#   ./deploy/twilio-number.sh --buy GB varun  # buy a GB local number
#
set -euo pipefail

VM_HOST="${VM_HOST:-193.123.187.97}"
VM_USER="${VM_USER:-ubuntu}"
VM_KEY="${VM_KEY:-$HOME/Downloads/ssh-key-2026-08-03.key}"

ACTION="diagnose"
COUNTRY="US"
TENANT="varun"

if [[ "${1:-}" == "--buy" ]]; then
  ACTION="buy"
  COUNTRY="${2:?--buy needs a 2-letter country code, e.g. --buy US}"
  TENANT="${3:-varun}"
elif [[ -n "${1:-}" ]]; then
  # Plain "$1", not ${1@Q}: macOS ships bash 3.2, where @Q is a syntax error and
  # would kill the script before it printed this message.
  echo "FAILED: unknown argument '$1'. Use no arguments to diagnose, or --buy COUNTRY [TENANT]." >&2
  exit 1
fi

SSH=(ssh -i "$VM_KEY" -o StrictHostKeyChecking=accept-new -o ConnectTimeout=15 "${VM_USER}@${VM_HOST}")
[[ -f "$VM_KEY" ]] || { echo "FAILED: SSH key not found at $VM_KEY" >&2; exit 1; }

if [[ "$ACTION" == "buy" ]]; then
  printf '\033[1;33m'
  cat <<WARN
About to PURCHASE a phone number on your Twilio account.
  country : ${COUNTRY}
  tenant  : ${TENANT}
  cost    : charged to trial credit first, then about \$1.15/month + per-minute
  effect  : a real DID is provisioned, its voice webhook is pointed at this
            server, and the VM's .env TWILIO_PHONE_NUMBER is rewritten.
Releasing it later is one click in the console, but the month is not refunded.
Ctrl-C within 8 seconds to abort.
WARN
  printf '\033[0m'
  sleep 8
fi

echo "==> querying Twilio  (mode: ${ACTION}, country: ${COUNTRY}, tenant: ${TENANT})"

# Arguments are prepended as literal %q-quoted assignments rather than smuggled
# through a nested bash -c "...", where the layered quoting is one backslash away
# from expanding $(mktemp) on this Mac instead of on the VM.
{
  printf 'VF_ACTION=%q\nVF_COUNTRY=%q\nVF_TENANT=%q\n' "$ACTION" "$COUNTRY" "$TENANT"
  cat <<'REMOTE'
set -uo pipefail
cd /home/ubuntu/voxflow-voice-agent

ENV_FILE=.env
DOMAIN="$(grep -E '^DOMAIN=' "$ENV_FILE" | head -1 | cut -d= -f2- | tr -d '"'"'"' ')"
[[ -n "$DOMAIN" ]] || { echo "FAILED: DOMAIN not set in .env"; exit 1; }

cd deploy
OUT="$(mktemp /tmp/voxflow-twilio.XXXXXX)"

docker compose --env-file ../.env -f docker-compose.prod.yml \
  exec -T -e VF_ACTION="${VF_ACTION}" -e VF_COUNTRY="${VF_COUNTRY}" \
           -e VF_TENANT="${VF_TENANT}" -e VF_DOMAIN="${DOMAIN}" \
  api python - <<'PY' 2>&1 | tee "$OUT"
import os, sys

from voxflow_api.config import get_settings
from voxflow_api.db import Tenant, TenantPhoneNumber, session_scope

action = os.environ["VF_ACTION"]
country = os.environ["VF_COUNTRY"].upper()
tenant_id = os.environ["VF_TENANT"]
domain = os.environ["VF_DOMAIN"]
webhook = "https://%s/twilio/voice" % domain

s = get_settings()
if not s.twilio_account_sid or not s.twilio_auth_token:
    print("FAILED: TWILIO_ACCOUNT_SID / TWILIO_AUTH_TOKEN missing from .env")
    sys.exit(1)

from twilio.rest import Client
# TwilioException is the BASE class; TwilioRestException subclasses it. Catching
# only the subclass is a trap: twilio/base/page.py raises the bare base class for
# a failed page fetch, so `except TwilioRestException` lets a 401 escape and kill
# the script. Every call below catches the base, and reads .code via getattr
# because only the subclass has one.
from twilio.base.exceptions import TwilioException

client = Client(s.twilio_account_sid, s.twilio_auth_token)


def digits(v):
    return "".join(c for c in (v or "") if c.isdigit())


def err(exc):
    """Readable one-liner for either exception class.

    Only TwilioRestException carries .msg/.code; the base class carries neither,
    so printing type(exc).__name__ tells you nothing useful about what Twilio
    actually refused.
    """
    code = getattr(exc, "code", None)
    msg = getattr(exc, "msg", None) or str(exc)
    return msg if code is None else "%s (code %s)" % (msg, code)


# --- 1. Account and remaining credit --------------------------------------
print("=== account ===")
print("  sid    %s...%s" % (s.twilio_account_sid[:6], s.twilio_account_sid[-4:]))
try:
    acct = client.api.v2010.accounts(s.twilio_account_sid).fetch()
except TwilioException as exc:
    print("FAILED: cannot read the account: %s" % err(exc))
    print("        These must be the LIVE Account SID and Auth Token, not the")
    print("        test credentials.")
    sys.exit(1)
print("  name   %r" % acct.friendly_name)
print("  type   %s" % acct.type)
print("  status %s" % acct.status)
try:
    bal = client.balance.fetch()
    print("  credit %s %s" % (bal.balance, bal.currency))
except TwilioException as exc:
    # Trial accounts are refused the Balance API outright, with HTTP 401 and
    # code 20003 — the SAME code a wrong auth token returns. The account fetch
    # above already succeeded, which is what actually proves the credentials
    # are good; do not read 20003 here as an auth failure.
    print("  credit unavailable: %s" % err(exc))
    print("         (trials are blocked from this API — check the console header)")

# --- 2. What the account actually holds ----------------------------------
# The distinction that matters: an INCOMING phone number is a DID you own and can
# attach a voice webhook to. An OUTGOING CALLER ID is just your own phone,
# verified so a trial may dial it. Only the first can receive a call.
print()
print("=== incoming phone numbers (can receive calls) ===")
incoming = []
try:
    incoming = client.incoming_phone_numbers.list(limit=50)
except TwilioException as exc:
    print("  could not list: %s" % err(exc))
if incoming:
    for n in incoming:
        print("  %-18s voice_url=%s" % (n.phone_number, n.voice_url or "-"))
else:
    print("  none — nothing on this account can receive an inbound call")

print()
print("=== verified caller IDs (outbound only, CANNOT receive calls) ===")
callerids = []
callerids_readable = True
try:
    callerids = client.outgoing_caller_ids.list(limit=50)
except TwilioException as exc:
    # Trials cannot read this list over the API. Not knowing is fine — it only
    # affects how the verdict below is WORDED, never whether a number exists.
    callerids_readable = False
    print("  cannot list on a Trial account: %s" % err(exc))
    print("  read it by eye at console.twilio.com > Phone Numbers > Manage >")
    print("  Verified Caller IDs")
if callerids:
    for c in callerids:
        print("  %-18s %r" % (c.phone_number, c.friendly_name))
elif callerids_readable:
    print("  none")

configured = s.twilio_phone_number or ""
if configured:
    in_incoming = any(digits(n.phone_number) == digits(configured) for n in incoming)
    in_callerids = any(digits(c.phone_number) == digits(configured) for c in callerids)
    print()
    print("=== verdict for TWILIO_PHONE_NUMBER=%s ===" % configured)
    if in_incoming:
        print("  it IS a number you own — wire-twilio.sh can set its webhook")
    elif in_callerids:
        print("  it is a VERIFIED CALLER ID, not a Twilio number. That is why the")
        print("  webhook could not be set: there is no webhook to set. Twilio will")
        print("  never send an inbound call for it, because the call never reaches")
        print("  Twilio at all — dialling it rings your own handset directly.")
        print("  You need to BUY a number.")
    else:
        # The owned-numbers list is the only one that decides this, and it read
        # cleanly. Whether the caller-ID list was readable changes nothing about
        # the conclusion — only about which of the two harmless explanations
        # applies to a number that cannot receive a call either way.
        print("  it is NOT a number this account owns — the owned list above is")
        print("  empty, and that list is authoritative. So no inbound call can")
        print("  ever arrive on it and there is no webhook field to point here.")
        if callerids_readable:
            print("  It is not a verified caller ID either, so it is either on a")
            print("  different Twilio login or simply your personal mobile, which")
            print("  is how it ended up as the default in config.py.")
        else:
            print("  Whether it is also a verified caller ID could not be read on a")
            print("  Trial, but that would not help: caller IDs are outbound-only.")
        print("  Either way the fix is the same — BUY a number.")

# --- 3. What is purchasable ----------------------------------------------
print()
print("=== voice-capable numbers available in %s ===" % country)
avail, kind = [], "local"
for attempt in ("local", "toll_free"):
    try:
        avail = getattr(client.available_phone_numbers(country), attempt).list(
            voice_enabled=True, limit=5)
    except TwilioException as exc:
        print("  %s search failed: %s" % (attempt, err(exc)))
        continue
    if avail:
        kind = attempt
        break
    print("  no %s numbers offered" % attempt)

if avail:
    print("  (%s numbers)" % kind)
    for a in avail:
        print("  %-18s %s" % (a.phone_number, a.locality or a.region or ""))
    if kind == "toll_free":
        print("  Toll-free costs more per month than local — about $2 vs $1.15.")
else:
    print("  nothing purchasable in %s. Some countries (GB included) require a" % country)
    print("  regulatory bundle — proof of a local address — before Twilio will")
    print("  sell you a number. US local numbers need no bundle.")
    if country != "US":
        print("  Re-run with US, or complete the bundle at")
        print("  console.twilio.com > Phone Numbers > Regulatory Compliance.")

if action != "buy":
    print()
    print("=== nothing was purchased or changed (diagnosis mode) ===")
    sys.exit(0)

# --- 4. Purchase, webhook and tenant mapping in one shot -----------------
if not avail:
    print()
    print("FAILED: nothing available to buy in %s" % country)
    sys.exit(1)

with session_scope() as db:
    if db.get(Tenant, tenant_id) is None:
        print("FAILED: tenant %r does not exist — run deploy/seed-db.sh first" % tenant_id)
        sys.exit(1)

pick = avail[0].phone_number
print()
print("=== buying %s ===" % pick)
try:
    # voice_url is set AT CREATION so there is no window in which Twilio owns a
    # number pointed at its own demo TwiML instead of at this server.
    bought = client.incoming_phone_numbers.create(
        phone_number=pick,
        voice_url=webhook,
        voice_method="POST",
        friendly_name="VoxFlow inbound (%s)" % tenant_id,
    )
except TwilioException as exc:
    code = getattr(exc, "code", None)
    print("FAILED: purchase rejected: %s" % err(exc))
    if code in (21649, 21650, 21651):
        print("        That code means a regulatory bundle is required for %s." % country)
        print("        US local numbers need none — try --buy US.")
    elif code == 20003:
        print("        On a Trial, 20003 usually means the trial credit is spent.")
        print("        Upgrade the account or add funds, then re-run.")
    sys.exit(1)

print("  bought      %s" % bought.phone_number)
print("  voice_url   %s (%s)" % (bought.voice_url, bought.voice_method))

with session_scope() as db:
    row = db.get(TenantPhoneNumber, bought.phone_number)
    if row is None:
        db.add(TenantPhoneNumber(phone_number=bought.phone_number, tenant_id=tenant_id,
                                 label="Twilio inbound (%s)" % tenant_id))
        print("  mapped      %s -> tenant %s" % (bought.phone_number, tenant_id))
    else:
        row.tenant_id = tenant_id
        print("  remapped    %s -> tenant %s" % (bought.phone_number, tenant_id))

    # The +44 row wire-twilio.sh wrote points at a number Twilio does not route.
    # Leaving it in the mapping table is a trap for whoever reads it next.
    if configured and digits(configured) != digits(bought.phone_number):
        stale = db.get(TenantPhoneNumber, configured)
        if stale is not None:
            db.delete(stale)
            print("  removed     stale mapping for %s (not a Twilio number)" % configured)

# Marker line the shell greps to update .env on the host.
print("PURCHASED=%s" % bought.phone_number)
PY
py_rc=${PIPESTATUS[0]}

if [[ $py_rc -ne 0 ]]; then
  rm -f "$OUT"
  echo
  echo "RESULT: failed"
  exit 1
fi

NEWNUM="$(grep -m1 '^PURCHASED=' "$OUT" | cut -d= -f2- || true)"
rm -f "$OUT"

if [[ -z "$NEWNUM" ]]; then
  echo
  echo "RESULT: diagnosis complete — nothing changed"
  exit 0
fi

# --- 5. Persist the number in .env and recreate api ------------------------
# The container reads TWILIO_PHONE_NUMBER at settings-load time and env_file is
# read when the container is CREATED, so a restart would keep the old value.
cd ..
cp "$ENV_FILE" "${ENV_FILE}.bak.$(date +%Y%m%d-%H%M%S)"
if grep -qE '^TWILIO_PHONE_NUMBER=' "$ENV_FILE"; then
  awk -v v="$NEWNUM" -F= '$1 == "TWILIO_PHONE_NUMBER" { print "TWILIO_PHONE_NUMBER=" v; next } { print }' \
    "$ENV_FILE" > "${ENV_FILE}.tmp" && mv "${ENV_FILE}.tmp" "$ENV_FILE"
else
  printf 'TWILIO_PHONE_NUMBER=%s\n' "$NEWNUM" >> "$ENV_FILE"
fi
echo
echo "--- .env TWILIO_PHONE_NUMBER=${NEWNUM}"

cd deploy
echo "--- recreating api so it reads the new number"
docker compose --env-file ../.env -f docker-compose.prod.yml \
  up -d --no-deps --force-recreate api || { echo "FAILED: api recreate"; exit 1; }

ok=0
for i in $(seq 1 36); do
  h="$(docker inspect -f '{{.State.Health.Status}}' voxflow-api 2>/dev/null || echo none)"
  [[ "$h" == "healthy" ]]   && { echo "    api healthy after ~$((i*5))s"; ok=1; break; }
  [[ "$h" == "unhealthy" ]] && break
  sleep 5
done
[[ "$ok" == "1" ]] || { echo "FAILED: api not healthy"; docker logs voxflow-api --tail 30; exit 1; }

# The recreate gave api a new container IP and Caddy caches the old one.
echo "--- restarting caddy so it re-resolves api:8000"
docker compose --env-file ../.env -f docker-compose.prod.yml restart caddy
sleep 4

echo
echo "RESULT: NUMBER LIVE — ring ${NEWNUM}"
echo "        Trial accounts play a short Twilio notice before your TwiML runs."
REMOTE
} | "${SSH[@]}" 'f=$(mktemp /tmp/voxflow-remote.XXXXXX); cat > "$f"; bash "$f" </dev/null; rc=$?; rm -f "$f"; exit $rc'
