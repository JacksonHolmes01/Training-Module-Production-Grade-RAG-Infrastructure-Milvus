#!/usr/bin/env bash
# End-to-end check: host -> NGINX -> API -> Milvus -> Ollama.
set -euo pipefail
cd "$(dirname "$0")/.."
KEY="$(grep -E '^EDGE_API_KEY=' .env | cut -d= -f2-)"
U=http://localhost:8088
pass() { echo "  ✔ $1"; }
fail() { echo "  ✘ $1"; exit 1; }

echo "[1/6] proxy health"
[[ "$(curl -s $U/proxy-health)" == "ok" ]] && pass "NGINX is up" || fail "NGINX not reachable"

echo "[2/6] request without a key is rejected"
[[ "$(curl -s -o /dev/null -w '%{http_code}' $U/health)" == "401" ]] && pass "401 without key" || fail "expected 401"

echo "[3/6] request with a wrong key is rejected"
[[ "$(curl -s -o /dev/null -w '%{http_code}' -H 'X-API-Key: wrong' $U/health)" == "403" ]] && pass "403 with wrong key" || fail "expected 403"

echo "[4/6] API and database health"
curl -s -H "X-API-Key: $KEY" $U/health | grep -q '"db_ok":true' && pass "db_ok" || fail "database not healthy"

echo "[5/6] retrieval"
curl -s -G -H "X-API-Key: $KEY" $U/debug/retrieve --data-urlencode "q=what is defense in depth" \
  | grep -q '"title"' && pass "retrieval returned sources" || fail "no sources (did you run bin/ingest_sample.sh?)"

echo "[6/6] full chat (can take a minute on first run)"
curl -s -X POST -H "X-API-Key: $KEY" -H "Content-Type: application/json" $U/chat \
  -d '{"message":"What is defense in depth? Answer in one sentence."}' | grep -q '"answer"' \
  && pass "chat answered" || fail "chat failed"
echo "All smoke tests passed."
