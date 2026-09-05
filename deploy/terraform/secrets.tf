###############################################################################
# AWS Secrets Manager — all Phase 0 .env secrets migrated here
# ECS tasks get these via IAM role; no .env file in any deployed container
###############################################################################

# KMS key for encrypting secrets at rest
resource "aws_kms_key" "secrets" {
  description             = "VoxFlow secrets encryption key"
  deletion_window_in_days = 10
  enable_key_rotation     = true

  tags = { Name = "${local.name_prefix}-kms-secrets" }
}

resource "aws_kms_alias" "secrets" {
  name          = "alias/${local.name_prefix}-secrets"
  target_key_id = aws_kms_key.secrets.key_id
}

# --------------------------------------------------------------------------
# Application secrets (populated via: terraform apply -var-file=secrets.tfvars)
# --------------------------------------------------------------------------
resource "aws_secretsmanager_secret" "app_secrets" {
  name                    = "${local.name_prefix}/app/secrets"
  description             = "VoxFlow application secrets (API keys, tokens)"
  kms_key_id              = aws_kms_key.secrets.arn
  recovery_window_in_days = 7

  tags = { Name = "${local.name_prefix}-app-secrets" }
}

# This secret version is intentionally left with a placeholder.
# After `terraform apply`, run the helper script to populate real values
# from your local .env:  scripts/migrate-secrets-to-aws.sh
resource "aws_secretsmanager_secret_version" "app_secrets" {
  secret_id = aws_secretsmanager_secret.app_secrets.id
  secret_string = jsonencode({
    # Supabase (kept during migration; removed once RDS cutover is complete)
    SUPABASE_URL              = "REPLACE_ME"
    SUPABASE_SERVICE_ROLE_KEY = "REPLACE_ME"
    SUPABASE_PUBLISHABLE_KEY  = "REPLACE_ME"

    # Auth
    JWT_SECRET = "REPLACE_ME"

    # Resend email
    RESEND_API_KEY = "REPLACE_ME"

    # Crisp
    NEXT_PUBLIC_CRISP_WEBSITE_ID = "a7c229bd-a95a-446b-a810-7633d970d474"

    # Backup encryption
    BACKUP_ENCRYPTION_KEY = "REPLACE_ME"

    # AWS Connect
    AWS_ACCESS_KEY_ID_CONNECT     = "REPLACE_ME"
    AWS_SECRET_ACCESS_KEY_CONNECT = "REPLACE_ME"
  })

  # Ignore subsequent changes — the migration script will update this
  lifecycle {
    ignore_changes = [secret_string]
  }
}
