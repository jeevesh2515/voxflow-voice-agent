#!/bin/bash
# VoxFlow backend recovery script for Oracle Cloud Always Free VM
# Run this on the VM via SSH after logging in.
set -euo pipefail

echo "=== VoxFlow Backend Recovery ==="
echo "Date: $(date -u)"
echo ""

# 1. Check if the VM is actually reachable
echo "[1] Host health"
if ! command -v docker &>/dev/null; then
  echo "FAIL: docker not installed"
  exit 1
fi
echo "docker: $(docker --version)"
echo ""

# 2. Check running containers
echo "[2] Docker containers"
docker ps -a --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" || true
echo ""

# 3. Check Caddy logs for TLS/reverse proxy errors
echo "[3] Caddy status"
if docker ps --filter "name=voxflow-caddy" --format "{{.Names}}" | grep -q voxflow-caddy; then
  echo "Caddy container: RUNNING"
  docker logs voxflow-caddy --tail 30 2>&1 || true
else
  echo "Caddy container: NOT RUNNING"
fi
echo ""

# 4. Check API container logs
echo "[4] API container logs"
if docker ps --filter "name=voxflow-api" --format "{{.Names}}" | grep -q voxflow-api; then
  echo "API container: RUNNING"
  docker logs voxflow-api --tail 50 2>&1 || true
else
  echo "API container: NOT RUNNING"
fi
echo ""

# 5. Check ports
echo "[5] Port listeners"
sudo ss -lntp | grep -E ':80 |:443 ' || echo "No listeners on 80/443"
echo ""

# 6. Check firewall
echo "[6] Firewall (iptables)"
sudo iptables -L INPUT -n | head -20 || echo "Cannot read iptables"
echo ""

# 7. Local health checks
echo "[7] Local health probes"
echo -n "  API health (localhost): "
if curl -sS -m 5 http://127.0.0.1:8000/api/health | head -c 200; then
  echo ""
else
  echo "FAIL (no response or error)"
fi

echo -n "  Public HTTPS: "
if curl -sS -m 5 https://voxflow-jeevesh.duckdns.org/ | head -c 200; then
  echo ""
else
  echo "FAIL (timeout or error)"
fi
echo ""

# 8. DuckDNS IP
echo "[8] DuckDNS resolution"
dig +short voxflow-jeevesh.duckdns.org || nslookup voxflow-jeevesh.duckdns.org 1.1.1.1 | tail -5
echo ""

# 9. Common fixes
echo "[9] Recommended actions:"
echo "  docker compose -f deploy/docker-compose.prod.yml up -d --build"
echo "  docker compose -f deploy/docker-compose.prod.yml logs -f"
echo "  sudo iptables -I INPUT -p tcp --dport 443 -j ACCEPT"
echo "  sudo iptables -I INPUT -p tcp --dport 80 -j ACCEPT"
