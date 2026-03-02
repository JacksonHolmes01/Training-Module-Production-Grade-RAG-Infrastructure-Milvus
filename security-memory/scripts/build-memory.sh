#!/usr/bin/env bash
# build-memory.sh — Drop (optional) and rebuild the ExpandedVSCodeMemory collection
#
# Usage:
#   ./security-memory/scripts/build-memory.sh          # add new chunks (no drop)
#   ./security-memory/scripts/build-memory.sh --fresh  # drop collection and reingest from scratch
#
# Requirements:
#   - docker compose stack is running and healthy
#   - EDGE_API_KEY is set in .env

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# ── Check stack is up ──────────────────────────────────────────────────────────
if ! docker ps --filter "name=ingestion-api" --filter "status=running" | grep -q ingestion-api; then
  echo "ERROR: ingestion-api container is not running."
  echo "Run: docker compose up -d && docker compose ps"
  exit 1
fi

if ! docker ps --filter "name=milvus" --filter "status=running" | grep -q "^.*milvus"; then
  echo "ERROR: milvus container is not running."
  echo "Run: docker compose up -d && docker compose ps"
  exit 1
fi

# ── Optional: drop collection before reingest ──────────────────────────────────
if [[ "${1:-}" == "--fresh" ]]; then
  echo ">>> Dropping ExpandedVSCodeMemory collection..."
  docker exec -i ingestion-api python - <<'PY'
from pymilvus import connections, utility, Collection
import os
connections.connect(
    host=os.getenv("MILVUS_HOST", "milvus"),
    port=int(os.getenv("MILVUS_PORT", "19530")),
    timeout=30,
)
collection_name = os.getenv("SECURITY_COLLECTION", "ExpandedVSCodeMemory")
if utility.has_collection(collection_name):
    Collection(collection_name).drop()
    print(f"Dropped: {collection_name}")
else:
    print(f"Collection '{collection_name}' does not exist — nothing to drop.")
PY
  echo ">>> Collection dropped."
fi

# ── Run ingestion ──────────────────────────────────────────────────────────────
echo ">>> Starting security memory ingestion..."
echo "    This embeds chunks via Ollama one at a time."
echo "    Expected time: 1–20 minutes depending on corpus size."
echo ""

docker exec -i ingestion-api python -m app.security_memory.ingest

# ── Verify ────────────────────────────────────────────────────────────────────
echo ""
echo ">>> Verifying collection..."
docker exec -i ingestion-api python - <<'PY'
from pymilvus import connections, Collection, utility
import os
connections.connect(
    host=os.getenv("MILVUS_HOST", "milvus"),
    port=int(os.getenv("MILVUS_PORT", "19530")),
    timeout=10,
)
collection_name = os.getenv("SECURITY_COLLECTION", "ExpandedVSCodeMemory")
if not utility.has_collection(collection_name):
    print(f"ERROR: collection '{collection_name}' does not exist after ingestion.")
    exit(1)
col = Collection(collection_name)
col.load()
count = col.num_entities
if count == 0:
    print(f"WARNING: collection '{collection_name}' exists but has 0 entities.")
else:
    print(f"OK: collection '{collection_name}' has {count} entities.")
PY

# ── Health check via API ───────────────────────────────────────────────────────
if [ -f "$REPO_ROOT/.env" ]; then
  EDGE_API_KEY=$(grep -E '^EDGE_API_KEY=' "$REPO_ROOT/.env" | cut -d= -f2- | tr -d '[:space:]')
  if [ -n "$EDGE_API_KEY" ] && [ "$EDGE_API_KEY" != "replace-with-long-random-value" ]; then
    echo ""
    echo ">>> API health check..."
    curl -s http://localhost:8088/memory/health \
      -H "X-API-Key: $EDGE_API_KEY" | python -m json.tool || true
  fi
fi

echo ""
echo ">>> Done. Security memory is ready."
