#!/bin/bash
set -e

# Start Grafana in the background
echo "🚀 Starting Grafana..."
/run.sh &
GRAFANA_PID=$!

GF_SECURITY_ADMIN_USER=$(cat /run/secrets/grafana_user | tr -d '\n')
GF_SECURITY_ADMIN_PASSWORD=$(cat /run/secrets/grafana_password | tr -d '\n')

# Wait for Grafana to become healthy
echo "⏳ Waiting for Grafana to be ready..."
until curl -s -u "$GF_SECURITY_ADMIN_USER:$GF_SECURITY_ADMIN_PASSWORD" http://localhost:${GF_SERVER_HTTP_PORT}/api/health | jq -e '.database == "ok"' > /dev/null; do
  sleep 2
done

echo "✅ Grafana is ready. Generating token..."

# Create Service Account
echo "📝 Creating service account..."
SA_JSON=$(curl -s -X POST http://${GF_SECURITY_ADMIN_USER}:${GF_SECURITY_ADMIN_PASSWORD}@localhost:${GF_SERVER_HTTP_PORT}/api/serviceaccounts \
  -H "Content-Type: application/json" \
  -d '{"name": "dev", "role": "Admin"}')

echo "Service Account Response: $SA_JSON"

SA_ID=$(echo "$SA_JSON" | jq -r '.id')
echo "Service Account ID: $SA_ID"

# Create Token
echo "🔑 Creating token..."
TOKEN_JSON=$(curl -s -X POST http://${GF_SECURITY_ADMIN_USER}:${GF_SECURITY_ADMIN_PASSWORD}@localhost:${GF_SERVER_HTTP_PORT}/api/serviceaccounts/$SA_ID/tokens \
  -H "Content-Type: application/json" \
  -d '{"name": "dev-token", "secondsToLive": 0}')

echo "Token Response: $TOKEN_JSON"

TOKEN=$(echo "$TOKEN_JSON" | jq -r '.key')
echo "Extracted Token: $TOKEN"

# Save token to a shared volume location
echo -n "$TOKEN" > /run/shared/grafana_token
echo "✅ Token written to /run/shared/grafana_token"

echo "🎉 Grafana initialization complete!"

# Wait for the Grafana process (keep container running)
wait $GRAFANA_PID