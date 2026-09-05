#!/usr/bin/env bash
# deploy/aws/deploy-lambda.sh
# Package and deploy the VoxFlow AWS Lambda bridge for Amazon Connect.
#
# Ships BOTH code and configuration. Use this rather than a bare
# `aws lambda update-function-configuration`, which would leave stale code
# running against a freshly-changed config.
#
# Usage:
#   VOXFLOW_SECRET="<same value as the API's CONNECT_LAMBDA_SECRET>" \
#   VOXFLOW_API_URL="https://your-domain" \
#     ./deploy/aws/deploy-lambda.sh
#
# After deploying it invokes the function once with a synthetic Connect event.
# That single call proves three things at the same time: the new code is live,
# the API URL is reachable from Lambda, and the HMAC secret matches the API's.
# Skip it with SKIP_SMOKE_TEST=1.

set -euo pipefail

FUNCTION_NAME="${VOXFLOW_LAMBDA_NAME:-VoxFlow-Connect-Bridge}"
# Lambda must live in the same region as the Amazon Connect instance.
REGION="${AWS_REGION:-us-west-2}"
# Default to the always-on VM: Connect allows this Lambda ~8s and a sleeping
# free-tier host blows that budget, dropping the call.
API_URL="${VOXFLOW_API_URL:-https://api.yourdomain.com}"
SECRET="${VOXFLOW_SECRET:-}"
# First market is UK English.
DEFAULT_LANG="${VOXFLOW_DEFAULT_LANG:-en}"

echo "=========================================="
echo " Packaging VoxFlow Lambda for AWS Connect "
echo " Function: $FUNCTION_NAME in $REGION"
echo " API URL : $API_URL"
echo " Language: $DEFAULT_LANG"
echo "=========================================="

if [ -z "$SECRET" ]; then
    echo "WARNING: VOXFLOW_SECRET is empty. The Lambda will send unsigned requests"
    echo "         and the API will reject every turn with 403 invalid_signature."
    echo "         Set it to the same value as the API's CONNECT_LAMBDA_SECRET."
fi

# The env vars are sent as JSON, not AWS CLI shorthand: shorthand
# (Variables={K=V,...}) splits on commas and equals signs, so a secret
# containing either would be silently mangled or rejected.
case "$SECRET" in
    *'"'*|*'\'*)
        echo "ERROR: VOXFLOW_SECRET contains a double quote or backslash, which"
        echo "       cannot be embedded safely here. Rotate it to an alphanumeric"
        echo "       secret (e.g. openssl rand -hex 32) and update the API too."
        exit 1
        ;;
esac

BUILD_DIR=$(mktemp -d /tmp/voxflow-lambda-build.XXXXXX)
trap 'rm -rf "$BUILD_DIR"' EXIT

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cp "$SCRIPT_DIR/lambda_handler.py" "$BUILD_DIR/lambda_handler.py"
cp "$SCRIPT_DIR/lambda_handler.py" "$BUILD_DIR/lambda_function.py"

cd "$BUILD_DIR"
zip -q -r function.zip lambda_handler.py lambda_function.py

cat > env.json <<JSON
{
  "Variables": {
    "VOXFLOW_API_URL": "$API_URL",
    "VOXFLOW_SECRET": "$SECRET",
    "VOXFLOW_DEFAULT_LANG": "$DEFAULT_LANG"
  }
}
JSON

echo "==> Deploying function code to AWS Lambda..."

if ! aws lambda get-function --function-name "$FUNCTION_NAME" --region "$REGION" >/dev/null 2>&1; then
    echo "==> Lambda function does not exist yet in $REGION."
    echo "    Create it once (substitute your account ID and execution role):"
    echo
    echo "    aws lambda create-function \\"
    echo "        --function-name $FUNCTION_NAME \\"
    echo "        --runtime python3.12 \\"
    echo "        --role arn:aws:iam::<YOUR_ACCOUNT_ID>:role/<ROLE_NAME> \\"
    echo "        --handler lambda_handler.lambda_handler \\"
    echo "        --timeout 10 \\"
    echo "        --zip-file fileb://$BUILD_DIR/function.zip \\"
    echo "        --environment file://$BUILD_DIR/env.json \\"
    echo "        --region $REGION"
    echo
    echo "    Then re-run this script. Note the build directory is deleted on exit,"
    echo "    so copy the command out and run it from a fresh invocation if needed."
    exit 1
fi

aws lambda update-function-code \
    --function-name "$FUNCTION_NAME" \
    --zip-file "fileb://function.zip" \
    --region "$REGION" >/dev/null

aws lambda wait function-updated --function-name "$FUNCTION_NAME" --region "$REGION"

aws lambda update-function-configuration \
    --function-name "$FUNCTION_NAME" \
    --timeout 10 \
    --environment "file://env.json" \
    --region "$REGION" >/dev/null

aws lambda wait function-updated --function-name "$FUNCTION_NAME" --region "$REGION"

echo "✅ Deployed code + config to $FUNCTION_NAME in $REGION"

if [ "${SKIP_SMOKE_TEST:-0}" = "1" ]; then
    echo "==> Smoke test skipped (SKIP_SMOKE_TEST=1)."
    exit 0
fi

echo "==> Smoke test: invoking the function with a synthetic Connect event..."

# Mirrors what the contact flow sends: user_text comes from the Lex transcript.
cat > smoke-event.json <<'JSON'
{
  "Details": {
    "ContactData": {
      "ContactId": "voxflow-deploy-smoke-test",
      "CustomerEndpoint": { "Address": "+447700900000" },
      "SystemEndpoint": { "Address": "+442046404552" }
    },
    "Parameters": {
      "user_text": "Hello, this is a deployment smoke test."
    }
  }
}
JSON

if aws lambda invoke \
    --function-name "$FUNCTION_NAME" \
    --payload "fileb://smoke-event.json" \
    --region "$REGION" \
    smoke-response.json >/dev/null 2>&1; then

    echo "--- Lambda response ---"
    cat smoke-response.json
    echo
    echo "-----------------------"

    if grep -q '"error"' smoke-response.json; then
        echo "❌ The Lambda ran but could not reach the API, or the API rejected it."
        echo "   Check, in order:"
        echo "     1. Is $API_URL up?   curl -sS $API_URL/api/health"
        echo "     2. Does VOXFLOW_SECRET equal the API's CONNECT_LAMBDA_SECRET?"
        echo "        (a mismatch returns HTTP 403 invalid_signature)"
        echo "     3. CloudWatch logs for $FUNCTION_NAME for the exact exception."
        exit 1
    fi

    if grep -q '"agent_reply"' smoke-response.json; then
        echo "✅ Smoke test passed: the Lambda reached the API and got an agent reply."
        echo "   Code is live, $API_URL is reachable, and the HMAC secret matches."
    else
        echo "⚠️  Unexpected response shape — inspect the JSON above."
        exit 1
    fi
else
    echo "⚠️  Could not invoke the function (missing lambda:InvokeFunction permission?)."
    echo "    The deploy itself succeeded; verify manually in the AWS console."
fi
