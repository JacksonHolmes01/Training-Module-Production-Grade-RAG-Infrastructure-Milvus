#!/usr/bin/env bash
# query-test.sh — Run a set of test queries against the security memory API
#
# Usage:
#   ./security-memory/scripts/query-test.sh
#
# Requirements:
#   - docker compose stack is running
#   - EDGE_API_KEY is set in .env

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# ── Load API key ───────────────────────────────────────────────────────────────
if [ ! -f "$REPO_ROOT/.env" ]; then
  echo "ERROR: .env file not found at $REPO_ROOT/.env"
  exit 1
fi

EDGE_API_KEY=$(grep -E '^EDGE_API_KEY=' "$REPO_ROOT/.env" | cut -d= -f2- | tr -d '[:space:]')
if [ -z "$EDGE_API_KEY" ] || [ "$EDGE_API_KEY" = "replace-with-long-random-value" ]; then
  echo "ERROR: EDGE_API_KEY is not set or is still the placeholder value."
  echo "Edit your .env file and set EDGE_API_KEY to a real random value."
  exit 1
fi

BASE_URL="http://localhost:8088"

echo "========================================"
echo "  Security Memory Query Tests (Milvus)"
echo "========================================"
echo ""

# ── Helper function ────────────────────────────────────────────────────────────
run_query() {
  local label="$1"
  local payload="$2"
  echo "----------------------------------------"
  echo "TEST: $label"
  echo "----------------------------------------"
  curl -s -X POST "$BASE_URL/memory/query" \
    -H "Content-Type: application/json" \
    -H "X-API-Key: $EDGE_API_KEY" \
    -d "$payload" | python -m json.tool
  echo ""
}

# ── Health check first ─────────────────────────────────────────────────────────
echo ">>> Health check..."
HEALTH=$(curl -s "$BASE_URL/memory/health" -H "X-API-Key: $EDGE_API_KEY")
echo "$HEALTH" | python -m json.tool

OK=$(echo "$HEALTH" | python -c "import sys,json; d=json.load(sys.stdin); print(d.get('ok','false'))" 2>/dev/null || echo "false")
COUNT=$(echo "$HEALTH" | python -c "import sys,json; d=json.load(sys.stdin); print(d.get('points_count',0))" 2>/dev/null || echo "0")

if [ "$OK" != "True" ]; then
  echo "ERROR: memory health check failed. Is the stack running?"
  exit 1
fi

if [ "$COUNT" = "0" ] || [ "$COUNT" = "None" ]; then
  echo "WARNING: collection is empty. Run build-memory.sh first."
  exit 1
fi

echo ">>> Health OK. Running queries..."
echo ""

# ── Test queries ───────────────────────────────────────────────────────────────

run_query "Docker root container detection (CIS + Docker)" \
  '{"query": "Docker containers running as root user", "tags": ["cis", "docker"], "top_k": 3}'

run_query "OWASP API injection risks" \
  '{"query": "API injection and input validation vulnerabilities", "tags": ["owasp"], "top_k": 3}'

run_query "NIST access control principles" \
  '{"query": "least privilege and access control enforcement", "tags": ["nist"], "top_k": 3}'

run_query "MITRE lateral movement techniques" \
  '{"query": "lateral movement and privilege escalation attacks", "tags": ["mitre"], "top_k": 3}'

run_query "Kubernetes network policy" \
  '{"query": "network segmentation and pod-to-pod communication controls", "tags": ["kubernetes", "cis"], "top_k": 3}'

run_query "Unfiltered broad query (no tag filter)" \
  '{"query": "secrets management and credential rotation", "top_k": 4}'

# ── Score summary ──────────────────────────────────────────────────────────────
echo "========================================"
echo "  All tests complete."
echo ""
echo "  Score reference (Milvus COSINE metric):"
echo "    >= 0.90  Excellent semantic match"
echo "    0.75-0.89  Good match"
echo "    0.60-0.74  Moderate match"
echo "    < 0.60   Weak match — consider adding more documents"
echo ""
echo "  NOTE: Milvus returns cosine similarity directly (not distance)."
echo "  Higher scores = better match (opposite of Weaviate distance)."
echo "========================================"
