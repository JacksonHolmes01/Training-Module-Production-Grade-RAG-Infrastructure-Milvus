#!/usr/bin/env bash
# Sends every document in data/sample_articles.jsonl through NGINX to /ingest.
set -uo pipefail
cd "$(dirname "$0")/.."
KEY="$(grep -E '^EDGE_API_KEY=' .env | cut -d= -f2-)"
RESP="$(mktemp)"
trap 'rm -f "$RESP"' EXIT
ok=0; fail=0; n=0
while IFS= read -r line; do
  [[ -z "$line" ]] && continue
  n=$((n+1))
  # Pace requests and retry if NGINX's rate limit answers 429
  for attempt in 1 2 3 4 5; do
    code=$(curl -s -o "$RESP" -w '%{http_code}' -X POST http://localhost:8088/ingest \
      -H "X-API-Key: $KEY" -H "Content-Type: application/json" -d "$line")
    [[ "$code" != "429" ]] && break
    sleep 2
  done
  sleep 0.2
  if [[ "$code" == "200" ]]; then ok=$((ok+1)); echo "  ✔ document $n ingested"
  elif [[ "$code" == "000" ]]; then
    echo "  ✘ could not reach the API at localhost:8088. Is the stack running? (docker compose ps)"; exit 1
  else fail=$((fail+1)); echo "  ✘ document $n failed (HTTP $code): $(cat "$RESP")"; fi
done < data/sample_articles.jsonl
echo "Total: $n  Success: $ok  Failed: $fail"
[[ $fail -eq 0 ]]
