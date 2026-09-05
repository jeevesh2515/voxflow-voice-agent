#!/usr/bin/env bash
# push-images-to-ecr.sh
# Builds Docker images locally and pushes them to ECR
#
# Usage: ./scripts/push-images-to-ecr.sh [git-tag]
# Example: ./scripts/push-images-to-ecr.sh v1.0.0
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
REGION="eu-west-2"
TAG="${1:-latest}"
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
REGISTRY="${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com"

# ECR URLs from Terraform output
API_REPO=$(terraform -chdir="$ROOT/deploy/terraform" output -raw ecr_api_url)
WEB_REPO=$(terraform -chdir="$ROOT/deploy/terraform" output -raw ecr_web_url)

echo "🔐 Authenticating with ECR..."
aws ecr get-login-password --region "$REGION" | \
  docker login --username AWS --password-stdin "$REGISTRY"

echo "🏗️  Building API image..."
docker build -t "$API_REPO:$TAG" -t "$API_REPO:latest" \
  -f "$ROOT/apps/api/Dockerfile" "$ROOT/apps/api"

echo "🏗️  Building Web image..."
# Pull build args from .env
source <(grep -E '^(NEXT_PUBLIC_CRISP_WEBSITE_ID|SUPABASE_URL|SUPABASE_PUBLISHABLE_KEY)' "$ROOT/.env")
docker build \
  --build-arg NEXT_PUBLIC_CRISP_WEBSITE_ID="${NEXT_PUBLIC_CRISP_WEBSITE_ID:-}" \
  --build-arg NEXT_PUBLIC_SUPABASE_URL="${SUPABASE_URL:-}" \
  --build-arg NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY="${SUPABASE_PUBLISHABLE_KEY:-}" \
  -t "$WEB_REPO:$TAG" -t "$WEB_REPO:latest" \
  -f "$ROOT/apps/web/Dockerfile" "$ROOT/apps/web"

echo "📤 Pushing API image..."
docker push "$API_REPO:$TAG"
docker push "$API_REPO:latest"

echo "📤 Pushing Web image..."
docker push "$WEB_REPO:$TAG"
docker push "$WEB_REPO:latest"

echo "✅ Images pushed:"
echo "   API: $API_REPO:$TAG"
echo "   Web: $WEB_REPO:$TAG"
