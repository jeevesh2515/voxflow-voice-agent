#!/usr/bin/env bash
# deploy/aws/deploy-lambda.sh
# Package and deploy VoxFlow AWS Lambda Bridge for Amazon Connect

set -euo pipefail

FUNCTION_NAME="${VOXFLOW_LAMBDA_NAME:-VoxFlow-Connect-Bridge}"
REGION="${AWS_REGION:-us-east-1}"
API_URL="${VOXFLOW_API_URL:-https://voxflow-voice-agent.onrender.com}"
SECRET="${VOXFLOW_SECRET:-}"

echo "=========================================="
echo " Packaging VoxFlow Lambda for AWS Connect "
echo " Function: $FUNCTION_NAME in $REGION"
echo "=========================================="

BUILD_DIR=$(mktemp -d /tmp/voxflow-lambda-build.XXXXXX)
trap 'rm -rf "$BUILD_DIR"' EXIT

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cp "$SCRIPT_DIR/lambda_handler.py" "$BUILD_DIR/"

cd "$BUILD_DIR"
zip -q -r function.zip lambda_handler.py

echo "==> Deploying function code to AWS Lambda..."

if aws lambda get-function --function-name "$FUNCTION_NAME" --region "$REGION" >/dev/null 2>&1; then
    aws lambda update-function-code \
        --function-name "$FUNCTION_NAME" \
        --zip-file "fileb://function.zip" \
        --region "$REGION" >/dev/null
    
    aws lambda update-function-configuration \
        --function-name "$FUNCTION_NAME" \
        --environment "Variables={VOXFLOW_API_URL=$API_URL,VOXFLOW_SECRET=$SECRET}" \
        --region "$REGION" >/dev/null
    echo "✅ Successfully updated existing Lambda function: $FUNCTION_NAME"
else
    echo "==> Lambda function does not exist yet. Please create it in AWS Console or provide an execution role ARN:"
    echo "    aws lambda create-function \\"
    echo "        --function-name $FUNCTION_NAME \\"
    echo "        --runtime python3.12 \\"
    echo "        --role arn:aws:iam::<YOUR_ACCOUNT_ID>:role/<ROLE_NAME> \\"
    echo "        --handler lambda_handler.lambda_handler \\"
    echo "        --zip-file fileb://function.zip \\"
    echo "        --environment Variables={VOXFLOW_API_URL=$API_URL,VOXFLOW_SECRET=$SECRET} \\"
    echo "        --region $REGION"
fi
