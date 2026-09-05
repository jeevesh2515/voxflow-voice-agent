###############################################################################
# EC2 — t3.small running Docker Compose (API + Web + Caddy)
###############################################################################

# SSH key pair
resource "aws_key_pair" "voxflow" {
  key_name   = "${local.name_prefix}-key"
  public_key = var.ssh_public_key
  tags       = { Name = "${local.name_prefix}-key" }
}

# Latest Amazon Linux 2023 AMI (x86_64 — matches t3.small)
data "aws_ami" "al2023" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["al2023-ami-*-x86_64"]
  }

  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }

  filter {
    name   = "architecture"
    values = ["x86_64"]
  }
}

# Elastic IP — static address so DuckDNS A record stays stable across reboots
resource "aws_eip" "ec2" {
  domain = "vpc"
  tags   = { Name = "${local.name_prefix}-eip" }
}

resource "aws_eip_association" "ec2" {
  instance_id   = aws_instance.app.id
  allocation_id = aws_eip.ec2.id
}

# IAM role — lets EC2 read secrets from Secrets Manager without hardcoded keys
resource "aws_iam_role" "ec2" {
  name = "${local.name_prefix}-ec2-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "ec2.amazonaws.com" }
    }]
  })

  tags = { Name = "${local.name_prefix}-ec2-role" }
}

resource "aws_iam_role_policy" "ec2_secrets" {
  name = "${local.name_prefix}-ec2-secrets"
  role = aws_iam_role.ec2.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["secretsmanager:GetSecretValue", "secretsmanager:DescribeSecret"]
        Resource = [
          aws_secretsmanager_secret.db_credentials.arn,
          aws_secretsmanager_secret.app_secrets.arn
        ]
      },
      {
        Effect   = "Allow"
        Action   = ["kms:Decrypt"]
        Resource = [aws_kms_key.secrets.arn]
      }
    ]
  })
}

resource "aws_iam_instance_profile" "ec2" {
  name = "${local.name_prefix}-ec2-profile"
  role = aws_iam_role.ec2.name
  tags = { Name = "${local.name_prefix}-ec2-profile" }
}

# User data — bootstraps Docker, Docker Compose, and clones the repo on first boot
locals {
  user_data = <<-USERDATA
    #!/bin/bash
    set -euxo pipefail

    # System updates
    dnf update -y
    dnf install -y git jq awscli

    # Docker
    dnf install -y docker
    systemctl enable --now docker
    usermod -aG docker ec2-user

    # Docker Compose v2
    mkdir -p /usr/local/lib/docker/cli-plugins
    curl -fsSL "https://github.com/docker/compose/releases/latest/download/docker-compose-linux-aarch64" \
      -o /usr/local/lib/docker/cli-plugins/docker-compose
    chmod +x /usr/local/lib/docker/cli-plugins/docker-compose

    # Swap (2 GB) — Next.js build needs it on t3.small
    fallocate -l 2G /swapfile
    chmod 600 /swapfile
    mkswap /swapfile
    swapon /swapfile
    echo '/swapfile none swap sw 0 0' >> /etc/fstab

    # Pull app secrets from Secrets Manager into /etc/voxflow.env
    REGION="${var.aws_region}"
    SECRET_ARN="${aws_secretsmanager_secret.app_secrets.arn}"
    DB_SECRET_ARN="${aws_secretsmanager_secret.db_credentials.arn}"

    DB_JSON=$(aws secretsmanager get-secret-value \
      --region "$REGION" --secret-id "$DB_SECRET_ARN" \
      --query SecretString --output text)

    APP_JSON=$(aws secretsmanager get-secret-value \
      --region "$REGION" --secret-id "$SECRET_ARN" \
      --query SecretString --output text)

    cat > /etc/voxflow.env << EOF
    DATABASE_URL=$(echo "$DB_JSON" | jq -r '.url')
    SUPABASE_URL=$(echo "$APP_JSON" | jq -r '.SUPABASE_URL')
    SUPABASE_SERVICE_ROLE_KEY=$(echo "$APP_JSON" | jq -r '.SUPABASE_SERVICE_ROLE_KEY')
    SUPABASE_PUBLISHABLE_KEY=$(echo "$APP_JSON" | jq -r '.SUPABASE_PUBLISHABLE_KEY')
    JWT_SECRET=$(echo "$APP_JSON" | jq -r '.JWT_SECRET')
    RESEND_API_KEY=$(echo "$APP_JSON" | jq -r '.RESEND_API_KEY')
    BACKUP_ENCRYPTION_KEY=$(echo "$APP_JSON" | jq -r '.BACKUP_ENCRYPTION_KEY')
    NEXT_PUBLIC_CRISP_WEBSITE_ID=$(echo "$APP_JSON" | jq -r '.NEXT_PUBLIC_CRISP_WEBSITE_ID')
    DOMAIN=${var.domain}
    ACME_EMAIL=${var.acme_email}
    DATA_DIR=/app/data
    EOF

    chmod 600 /etc/voxflow.env

    # Signal success
    touch /var/lib/cloud/instance/boot-finished
    echo "VoxFlow bootstrap complete" | logger -t voxflow
  USERDATA
}

# EC2 instance
resource "aws_instance" "app" {
  ami                    = data.aws_ami.al2023.id
  instance_type          = var.ec2_instance_type
  key_name               = aws_key_pair.voxflow.key_name
  subnet_id              = aws_subnet.public.id
  vpc_security_group_ids = [aws_security_group.ec2.id]
  iam_instance_profile   = aws_iam_instance_profile.ec2.name

  user_data                   = base64encode(local.user_data)
  user_data_replace_on_change = false  # Don't recreate instance on user_data change

  root_block_device {
    volume_size           = 30   # GB — enough for Docker images + data
    volume_type           = "gp3"
    encrypted             = true
    delete_on_termination = true
    tags                  = { Name = "${local.name_prefix}-root-volume" }
  }

  metadata_options {
    http_endpoint               = "enabled"
    http_tokens                 = "required"   # IMDSv2 only (security best practice)
    http_put_response_hop_limit = 1
  }

  tags = { Name = "${local.name_prefix}-app" }

  lifecycle {
    # Prevent accidental termination
    prevent_destroy = true
  }
}
