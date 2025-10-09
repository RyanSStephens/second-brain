#!/bin/bash
# deploy.sh — Deploy second-brain to a host behind Cloudflare Tunnel
#
# Prerequisites:
#   - Docker installed on the host
#   - cloudflared configured with a tunnel
#   - .env file with API keys
#
# Usage: ./scripts/deploy.sh [host]

set -euo pipefail

HOST="${1:-localhost}"

echo "==> Building Docker image..."
docker build -t second-brain:latest .

echo "==> Stopping existing containers..."
docker compose down 2>/dev/null || true

echo "==> Starting services..."
docker compose up -d

echo "==> Waiting for health check..."
for i in $(seq 1 30); do
    if curl -sf http://localhost:8000/health > /dev/null 2>&1; then
        echo "==> App is healthy!"
        break
    fi
    sleep 1
done

echo "==> Checking cloudflared tunnel..."
if systemctl is-active --quiet cloudflared 2>/dev/null; then
    echo "==> Cloudflare tunnel is running"
else
    echo "==> Starting cloudflare tunnel..."
    cloudflared tunnel --config /etc/cloudflared/config.yml run second-brain &
fi

echo ""
echo "Deploy complete. App available at:"
echo "  Local:  http://localhost:8000"
echo "  Public: https://brain.ryanstephens.work"
echo ""
echo "Health: curl http://localhost:8000/health"
echo "Metrics: curl http://localhost:8000/metrics"
