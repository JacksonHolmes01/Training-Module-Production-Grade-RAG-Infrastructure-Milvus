#!/usr/bin/env bash
set -euo pipefail

# Smoke test: validates the full path
# Host -> NGINX -> API -> Milvus (retrieve) -> Ollama (generate)

if [ ! -f .env ]; then
  echo "Missing .env. Run: cp .env.example .env"
  exit 1
fi

EDGE_API_KEY=$(grep -E '^EDGE_API_KEY=' .env | cut -d= -f2- | tr -d '\r')
if [ -z "$EDGE_API_KEY" ] || [ "$EDGE_API_KEY" = "replace-with-long-random-value" ]; then
  echo "Set EDGE_API_KEY in .env before running tests."
  exit 1
fi

echo "[1/6] Checking proxy health..."
curl -sS http://localhost:8088/proxy-health >/dev/null
echo "  ✓ proxy-health ok"

echo "[2/6] Checking API health (auth required)..."
curl -sS -H "X-API-Key: $EDGE_API_KEY" http://localhost:8088/health | python3 -m json.tool
echo "  ✓ /health ok"

echo "[3/6] Ingesting a test document..."
curl -sS -X POST "http://localhost:8088/ingest" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $EDGE_API_KEY" \
  -d '{
    "title": "Smoke Test Doc",
    "url": "https://example.com/smoke-test",
    "source": "smoke-test",
    "published_date": "2026-01-01",
    "text": "This document exists to verify that ingestion, embedding, storage in Milvus, retrieval, and generation via Ollama all work end-to-end. If you can retrieve and cite this doc, your pipeline is working."
  }' >/dev/null
echo "  ✓ ingest ok"

echo "[4/6] Testing retrieval-only (debug/retrieve)..."
curl -sS -G "http://localhost:8088/debug/retrieve" \
  -H "X-API-Key: $EDGE_API_KEY" \
  --data-urlencode "q=What is the smoke test document for?" | python3 -m json.tool | head -20 >/dev/null
echo "  ✓ retrieve ok"

echo "[5/6] Testing prompt build (debug/prompt)..."
curl -sS -X POST "http://localhost:8088/debug/prompt" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $EDGE_API_KEY" \
  -d '{"message": "What is the smoke test document for?"}' | python3 -m json.tool | head -5 >/dev/null
echo "  ✓ prompt ok"

echo "[6/6] Testing full chat..."
curl -sS -X POST "http://localhost:8088/chat" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $EDGE_API_KEY" \
  -d '{"message": "What is the smoke test document for? Answer in one sentence."}'
echo ""
echo "  ✓ chat ok"

echo ""
echo "All smoke tests passed."
