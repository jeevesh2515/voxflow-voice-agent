#!/usr/bin/env bash
#
# VoxFlow — point Twilio at the VM and map the number to a tenant.
#
# Does the three things a real inbound call needs, in the order they depend on
# each other:
#   1. sets PUBLIC_BASE_URL=https://$DOMAIN in the VM's .env, then RECREATES api.
#      A restart is not enough: env_file is read when the container is CREATED,
#      so `docker compose restart api` keeps the old, blank value. A blank
#      PUBLIC_BASE_URL makes routes/twilio.py hand Twilio a <Stream url="wss:///
#      twilio/media"> with no host, and the call connects then goes silent.
#   2. maps your Twilio number to a tenant in tenant_phone_numbers. Without the
#      row the webhook cannot tell whose orders the caller is asking about.
#   3. sets the number's Voice webhook to https://$DOMAIN/twilio/voice (POST) via
#      the Twilio API, so you never touch the console UI.
#
# scripts/map_phone.py cannot do this on the VM: it imports from apps/api on the
# filesystem, and the api image is built from apps/api as its ROOT context, so
# scripts/ is not in the image at all. The same work runs here inside the
# container, where twilio==9.4.1 and the ORM already live. map_phone.py also
# picks numbers[0] when told "auto"; on an account with more than one number that
# silently wires the wrong one, so this script refuses to guess.
#
# Idempotent. Re-run after changing DOMAIN or buying a different number.
#
# Usage:
#   ./deploy/wire-twilio.sh                        # number from TWILIO_PHONE_NUMBER
#   ./deploy/wire-twilio.sh +447460041934 varun     # explicit
#
set -euo pipefail

VM_HOST="${VM_HOST:-193.123.187.97}"
VM_USER="${VM_USER:-ubuntu}"
VM_KEY="${VM_KEY:-$HOME/Downloads/ssh-key-2026-08-03.key}"

PHONE="${1:-auto}"
TENANT="${2:-varun}"

SSH=(ssh -i "$VM_KEY" -o StrictHostKeyChecking=accept-new -o ConnectTimeout=15 "${VM_USER}@${VM_HOST}")
[[ -f "$VM_KEY" ]] || { echo "FAILED: SSH key not found at $VM_KEY" >&2; exit 1; }

echo "==> wiring Twilio  (number: ${PHONE}, tenant: ${TENANT})"

# The two arguments are prepended to the remote script as literal, %q-quoted
# assignments rather than smuggled through a nested `bash -c "..."`, where the
# layered quoting is one backslash away from expanding $(mktemp) on this Mac.
{
  printf 'VF_PHONE=%q\nVF_TENANT=%q\n' "$PHONE" "$TENANT"
  cat <<'REMOTE'
set -uo pipefail
cd /home/ubuntu/voxflow-voice-agent

ENV_FILE=.env
DOMAIN="$(grep -E '^DOMAIN=' "$ENV_FILE" | head -1 | cut -d= -f2- | tr -d '"'"'"' ')"
[[ -n "$DOMAIN" ]] || { echo "FAILED: DOMAIN not set in .env"; exit 1; }

# --- 1. PUBLIC_BASE_URL ----------------------------------------------------
cp "$ENV_FILE" "${ENV_FILE}.bak.$(date +%Y%m%d-%H%M%S)"
WANT="https://${DOMAIN}"
CURRENT="$(grep -E '^PUBLIC_BASE_URL=' "$ENV_FILE" | head -1 | cut -d= -f2- || true)"
if [[ "$CURRENT" == "$WANT" ]]; then
  echo "--- PUBLIC_BASE_URL already ${WANT}"
  ENV_CHANGED=0
else
  if grep -qE '^PUBLIC_BASE_URL=' "$ENV_FILE"; then
    awk -v v="$WANT" -F= '$1 == "PUBLIC_BASE_URL" { print "PUBLIC_BASE_URL=" v; next } { print }' \
      "$ENV_FILE" > "${ENV_FILE}.tmp" && mv "${ENV_FILE}.tmp" "$ENV_FILE"
  else
    printf 'PUBLIC_BASE_URL=%s\n' "$WANT" >> "$ENV_FILE"
  fi
  echo "--- PUBLIC_BASE_URL set to ${WANT}"
  ENV_CHANGED=1
fi

cd deploy
if [[ "$ENV_CHANGED" == "1" ]]; then
  # RECREATE, not restart: env_file is read at container-create time.
  echo "--- recreating api so it reads the new PUBLIC_BASE_URL"
  docker compose --env-file ../.env -f docker-compose.prod.yml \
    up -d --no-deps --force-recreate api || { echo "FAILED: api recreate"; exit 1; }

  echo "--- waiting for api health (up to 3 min)"
  ok=0
  for i in $(seq 1 36); do
    h="$(docker inspect -f '{{.State.Health.Status}}' voxflow-api 2>/dev/null || echo none)"
    [[ "$h" == "healthy" ]]   && { echo "    healthy after ~$((i*5))s"; ok=1; break; }
    [[ "$h" == "unhealthy" ]] && break
    sleep 5
  done
  [[ "$ok" == "1" ]] || { echo "FAILED: api not healthy"; docker logs voxflow-api --tail 30; exit 1; }

  # The recreate gave api a new container IP; Caddy caches the old one.
  echo "--- restarting caddy so it re-resolves api:8000"
  docker compose --env-file ../.env -f docker-compose.prod.yml restart caddy
  sleep 4
fi

# --- 2 + 3. Map the number and set the webhook, inside the api container ----
echo
echo "=== Twilio number -> tenant + voice webhook ==="
docker compose --env-file ../.env -f docker-compose.prod.yml \
  exec -T -e VF_PHONE="${VF_PHONE}" -e VF_TENANT="${VF_TENANT}" -e VF_DOMAIN="${DOMAIN}" \
  api python - <<'PY' 2>&1
import os, sys

from voxflow_api.config import get_settings
from voxflow_api.db import Tenant, TenantPhoneNumber, session_scope

phone_arg = os.environ["VF_PHONE"]
tenant_id = os.environ["VF_TENANT"]
domain = os.environ["VF_DOMAIN"]
webhook = "https://%s/twilio/voice" % domain

s = get_settings()
if not s.twilio_account_sid or not s.twilio_auth_token:
    print("FAILED: TWILIO_ACCOUNT_SID / TWILIO_AUTH_TOKEN missing from .env")
    sys.exit(1)
print("  PUBLIC_BASE_URL in the container: %r" % (s.public_base_url or ""))
print("  TWILIO_PHONE_NUMBER in the container: %r" % (s.twilio_phone_number or ""))
if not s.public_base_url:
    print("FAILED: PUBLIC_BASE_URL still blank inside the container — the recreate "
          "did not take, so TwiML would emit a hostless wss:// Stream URL")
    sys.exit(1)

from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException

client = Client(s.twilio_account_sid, s.twilio_auth_token)


def digits(v):
    return "".join(c for c in (v or "") if c.isdigit())


# --- Which account are these credentials actually for? ---------------------
# An empty number list is NOT the same as bad credentials: a wrong token raises
# TwilioRestException 20003, so reaching this point means the credentials are
# valid and the account genuinely has no numbers ATTACHED TO IT. The number can
# still exist — in a subaccount, or released when a trial lapsed — so print the
# account's identity and status before concluding anything.
try:
    acct = client.api.v2010.accounts(s.twilio_account_sid).fetch()
    print("  account: %s...%s  name=%r  type=%s  status=%s"
          % (s.twilio_account_sid[:6], s.twilio_account_sid[-4:],
             acct.friendly_name, acct.type, acct.status))
    if acct.status != "active":
        print("  WARNING: account status is %r — a suspended or closed account "
              "keeps its credentials working while releasing its numbers."
              % acct.status)
except TwilioRestException as exc:
    print("FAILED: could not fetch the account (%s). Check TWILIO_ACCOUNT_SID / "
          "TWILIO_AUTH_TOKEN in .env — they must be the LIVE credentials, not "
          "test credentials." % exc.msg)
    sys.exit(1)

# --- Collect numbers from this account AND every subaccount ----------------
# Numbers bought before a subaccount split live under the subaccount, and
# client.incoming_phone_numbers only ever looks at the credentialed account.
# Parent credentials can read and update a subaccount's resources by addressing
# them explicitly, which is what the accounts(sid) prefix below does.
owned = []   # (account_sid, account_label, number_resource)
for n in client.incoming_phone_numbers.list():
    owned.append((s.twilio_account_sid, "this account", n))

subs = []
try:
    subs = [a for a in client.api.v2010.accounts.list(limit=50)
            if a.sid != s.twilio_account_sid]
except TwilioRestException:
    pass
for a in subs:
    try:
        for n in client.api.v2010.accounts(a.sid).incoming_phone_numbers.list():
            owned.append((a.sid, "subaccount %r" % a.friendly_name, n))
    except TwilioRestException:
        continue

print("  numbers found: %d  (subaccounts scanned: %d)" % (len(owned), len(subs)))
for sid, label, n in owned:
    print("        %-16s %s  voice_url=%s" % (n.phone_number, label, n.voice_url or "-"))

# --- Resolve which number to wire -----------------------------------------
# Order: explicit argument, then TWILIO_PHONE_NUMBER from settings, then — only
# if the account owns exactly one — that one. Never "just take the first": on an
# account with several numbers that silently wires the wrong one, and the failure
# shows up as a phone call that rings nowhere.
want = phone_arg if phone_arg != "auto" else (s.twilio_phone_number or "")
if not want and len(owned) == 1:
    want = owned[0][2].phone_number
    print("  no number specified; the account owns exactly one, using it")

if not want:
    print("FAILED: no number to wire. Pass one explicitly, e.g.")
    print("        ./deploy/wire-twilio.sh +447460041934 %s" % tenant_id)
    sys.exit(1)

print("  target number: %s" % want)

match = next((t for t in owned if digits(t[2].phone_number) == digits(want)), None)

# 2. tenant_phone_numbers row. routes/twilio.py looks the call's DESTINATION up
#    here to decide whose catalogue and orders to answer from. Do this even when
#    Twilio ownership cannot be confirmed: the row is what makes an inbound call
#    resolvable, and it is correct as soon as the number points at this server.
with session_scope() as db:
    if db.get(Tenant, tenant_id) is None:
        print("FAILED: tenant %r does not exist — run deploy/seed-db.sh first" % tenant_id)
        sys.exit(1)
    canonical = match[2].phone_number if match else (
        want if want.startswith("+") else "+" + digits(want))
    row = db.get(TenantPhoneNumber, canonical)
    if row is None:
        db.add(TenantPhoneNumber(phone_number=canonical, tenant_id=tenant_id,
                                 label="Twilio inbound (%s)" % tenant_id))
        print("  mapped %s -> tenant %s" % (canonical, tenant_id))
    elif row.tenant_id != tenant_id:
        row.tenant_id = tenant_id
        print("  remapped %s -> tenant %s" % (canonical, tenant_id))
    else:
        print("  %s already mapped to tenant %s" % (canonical, tenant_id))

    # Drop the seed's placeholders once a real number is mapped. +1 555 01xx is
    # the reserved fictional range — those rows can never receive a call, and
    # leaving them makes the mapping table ambiguous to read later.
    for fake in ("+15550100001", "+15550100002"):
        if fake != canonical:
            stale = db.get(TenantPhoneNumber, fake)
            if stale is not None:
                db.delete(stale)
                print("  removed placeholder %s" % fake)

if match is None:
    print()
    print("FAILED: %s is not attached to these credentials, so the voice webhook "
          "cannot be set from here." % want)
    print("        The tenant mapping above IS done, so once the number points at")
    print("        this server the call will resolve correctly.")
    print("        Three things cause this, in order of likelihood:")
    print("          1. the number lives in a Twilio account whose SID is not the")
    print("             one in .env — copy Account SID + Auth Token from the")
    print("             console page that SHOWS this number, then re-run")
    print("          2. a lapsed trial released the number — check")
    print("             console.twilio.com > Phone Numbers > Manage > Released")
    print("          3. it was bought under a subaccount this token cannot read")
    print("        Manual fallback: console.twilio.com > Phone Numbers > Manage >")
    print("        Active numbers > %s > Voice > 'A call comes in' =" % want)
    print("        Webhook  %s  HTTP POST" % webhook)
    sys.exit(1)

acct_sid, _label, target = match
phone = target.phone_number

# 3. Voice webhook. POST, because routes/twilio.py declares @router.post("/voice").
if target.voice_url == webhook and (target.voice_method or "").upper() == "POST":
    print("  voice webhook already %s (POST)" % webhook)
else:
    up = client.api.v2010.accounts(acct_sid).incoming_phone_numbers(target.sid).update(
        voice_url=webhook, voice_method="POST")
    print("  voice webhook set to %s (%s)" % (up.voice_url, up.voice_method))

print("  READY — ring %s" % phone)
PY
rc=${PIPESTATUS[0]}
if [[ $rc -ne 0 ]]; then
  echo "RESULT: wiring failed"
  exit 1
fi

echo
echo "RESULT: TWILIO WIRED"
REMOTE
} | "${SSH[@]}" 'f=$(mktemp /tmp/voxflow-remote.XXXXXX); cat > "$f"; bash "$f" </dev/null; rc=$?; rm -f "$f"; exit $rc'

printf '\n\033[1;32m==> Done — call the number and the agent answers\033[0m\n'
