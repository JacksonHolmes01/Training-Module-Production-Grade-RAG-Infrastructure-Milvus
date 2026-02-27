#!/usr/bin/env bash
set -euo pipefail

echo "=== Container status ==="
docker compose ps

echo ""
echo "=== API health ==="
EDGE_API_KEY=$(grep -E '^EDGE_API_KEY=' .env | cut -d= -f2- | tr -d '\r' 2>/dev/null || echo "")
if [ -n "$EDGE_API_KEY" ]; then
  curl -s http://localhost:8088/health -H "X-API-Key: $EDGE_API_KEY" | python3 -m json.tool 2>/dev/null || echo "(API not yet ready)"
else
  echo "(set EDGE_API_KEY in .env to check API health)"
fi

echo ""
echo "=== Ollama models ==="
docker exec ollama ollama list 2>/dev/null || echo "(Ollama not ready)"
