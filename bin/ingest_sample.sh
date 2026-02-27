#!/usr/bin/env bash
set -e

echo "Ingesting sample docs into Milvus via the edge proxy..."

EDGE_API_KEY=$(grep -E '^EDGE_API_KEY=' .env | cut -d= -f2-)
if [ -z "$EDGE_API_KEY" ]; then
  echo "ERROR: EDGE_API_KEY not found in .env"
  exit 1
fi

COUNT=0
SUCCESS=0
FAIL=0

while IFS= read -r line; do
  COUNT=$((COUNT+1))
  RESPONSE=$(curl -s -w "\n%{http_code}" \
    -H "X-API-Key: $EDGE_API_KEY" \
    -H "Content-Type: application/json" \
    -d "$line" \
    http://localhost:8088/ingest)
  BODY=$(echo "$RESPONSE" | sed '$d')
  STATUS=$(echo "$RESPONSE" | tail -n1)
  if [ "$STATUS" -eq 200 ]; then
    SUCCESS=$((SUCCESS+1))
    echo "✔ Document $COUNT ingested"
  else
    FAIL=$((FAIL+1))
    echo "✘ Document $COUNT failed (HTTP $STATUS)"
    echo "$BODY"
  fi
done < data/sample_articles.jsonl

echo ""
echo "Ingest complete."
echo "Total: $COUNT  Success: $SUCCESS  Failed: $FAIL"
