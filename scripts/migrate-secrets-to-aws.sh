#!/usr/bin/env bash
# migrate-secrets-to-aws.sh
# Reads .env from the project root and pushes each secret to the
# AWS Secrets Manager secret created by Terraform.
#
# Usage: ./scripts/migrate-secrets-to-aws.sh
# Prereqs: aws CLI configured, terraform already applied
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ENV_FILE="$ROOT/.env"
REGION="eu-west-2"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "ERROR: .env not found at $ENV_FILE" >&2
  exit 1
fi

# Discover the secret ARN from Terraform output
SECRET_ARN=$(terraform -chdir="$ROOT/deploy/terraform" output -raw app_secret_arn 2>/dev/null)
if [[ -z "$SECRET_ARN" ]]; then
  echo "ERROR: Could not read app_secret_arn from Terraform output. Run 'terraform apply' first." >&2
  exit 1
fi

echo "Migrating secrets to: $SECRET_ARN"

# Load .env (skip comments and empty lines)
declare -A SECRETS
while IFS='=' read -r key value; do
  [[ "$key" =~ ^#.*$ || -z "$key" ]] && continue
  SECRETS["$key"]="$value"
done < <(grep -v '^\s*#' "$ENV_FILE" | grep -v '^\s*$' | sed 's/export //')

# Build JSON payload with the keys we care about
JSON=$(jq -n \
  --arg jwt        "${SECRETS[JWT_SECRET]:-MISSING}" \
  --arg resend     "${SECRETS[RESEND_API_KEY]:-MISSING}" \
  --arg supa_url   "${SECRETS[SUPABASE_URL]:-MISSING}" \
  --arg supa_key   "${SECRETS[SUPABASE_SERVICE_ROLE_KEY]:-MISSING}" \
  --arg supa_pub   "${SECRETS[SUPABASE_PUBLISHABLE_KEY]:-MISSING}" \
  --arg backup_key "${SECRETS[BACKUP_ENCRYPTION_KEY]:-MISSING}" \
  --arg crisp      "${SECRETS[NEXT_PUBLIC_CRISP_WEBSITE_ID]:-a7c229bd-a95a-446b-a810-7633d970d474}" \
  '{
    JWT_SECRET: $jwt,
    RESEND_API_KEY: $resend,
    SUPABASE_URL: $supa_url,
    SUPABASE_SERVICE_ROLE_KEY: $supa_key,
    SUPABASE_PUBLISHABLE_KEY: $supa_pub,
    BACKUP_ENCRYPTION_KEY: $backup_key,
    NEXT_PUBLIC_CRISP_WEBSITE_ID: $crisp
  }')

aws secretsmanager put-secret-value \
  --region "$REGION" \
  --secret-id "$SECRET_ARN" \
  --secret-string "$JSON"

echo "✅ Secrets migrated successfully."
echo "   Verify in console: https://eu-west-2.console.aws.amazon.com/secretsmanager"
