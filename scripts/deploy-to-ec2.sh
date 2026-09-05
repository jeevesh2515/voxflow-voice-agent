#!/usr/bin/env bash
# deploy-to-ec2.sh
# Syncs the repo to the EC2 instance and runs docker compose
# Usage: ./scripts/deploy-to-ec2.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
REGION="eu-west-2"

# Get EC2 IP from Terraform output
EC2_IP=$(terraform -chdir="$ROOT/deploy/terraform" output -raw ec2_public_ip 2>/dev/null)
if [[ -z "$EC2_IP" ]]; then
  echo "ERROR: Could not get EC2 IP. Run 'terraform apply' first." >&2
  exit 1
fi

SSH_KEY="$HOME/.ssh/id_ed25519"
if [[ ! -f "$SSH_KEY" ]]; then
  SSH_KEY="$HOME/.ssh/id_rsa"
fi

SSH="ssh -i $SSH_KEY -o StrictHostKeyChecking=no ec2-user@$EC2_IP"
REMOTE_DIR="/home/ec2-user/voxflow"

echo "🚀 Deploying to EC2 at $EC2_IP..."

# Sync repo (exclude .git, node_modules, .env — secrets come from Secrets Manager)
rsync -avz --progress \
  --exclude '.git' \
  --exclude 'node_modules' \
  --exclude '.env' \
  --exclude '*.pyc' \
  --exclude '__pycache__' \
  --exclude '.pytest_cache' \
  --exclude '.ruff_cache' \
  --exclude 'voxflow_test.db' \
  -e "ssh -i $SSH_KEY -o StrictHostKeyChecking=no" \
  "$ROOT/" "ec2-user@$EC2_IP:$REMOTE_DIR/"

echo "📦 Building and starting containers..."
$SSH bash -s << 'REMOTE'
  set -euo pipefail
  cd /home/ec2-user/voxflow

  # Ensure .env is present
  if [[ ! -f .env ]]; then
    if [[ -f /home/ec2-user/.env ]]; then
      cp /home/ec2-user/.env .env
    elif [[ -f /etc/voxflow.env ]]; then
      cp /etc/voxflow.env .env
    else
      echo "ERROR: Neither /home/ec2-user/.env nor /etc/voxflow.env found."
      exit 1
    fi
  fi

  # Pull latest and rebuild
  docker compose -f docker-compose.prod.yml pull --ignore-pull-failures || true
  docker compose -f docker-compose.prod.yml up -d --build --remove-orphans

  echo "✅ Containers running:"
  docker compose -f docker-compose.prod.yml ps
REMOTE

echo ""
echo "✅ Deploy complete!"
echo "   Health check: https://voxflow-jeevesh.duckdns.org/api/health"
