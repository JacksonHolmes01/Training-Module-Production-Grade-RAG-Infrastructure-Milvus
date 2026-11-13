#!/usr/bin/env bash
# Turn a prompt injection defense on or off, then restart the API.
#
# Usage:
#   bin/guard.sh <input|ingest|prompt|output|all> <on|off>
#   bin/guard.sh status
set -euo pipefail
cd "$(dirname "$0")/.."

if [[ "${1:-}" == "status" ]]; then
  grep -E '^GUARD_' .env
  exit 0
fi

NAME="${1:?usage: bin/guard.sh <input|ingest|prompt|output|all> <on|off>}"
STATE="${2:?usage: bin/guard.sh <name> <on|off>}"
case "$STATE" in on) VAL=true ;; off) VAL=false ;; *) echo "state must be on or off"; exit 1 ;; esac

if [[ "$NAME" == "all" ]]; then NAMES=(input ingest prompt output); else NAMES=("$NAME"); fi
for n in "${NAMES[@]}"; do
  case "$n" in input|ingest|prompt|output) ;; *) echo "unknown guard: $n"; exit 1 ;; esac
  VAR="GUARD_$(echo "$n" | tr '[:lower:]' '[:upper:]')"
  sed -i.bak "s/^${VAR}=.*/${VAR}=${VAL}/" .env && rm -f .env.bak
done

echo "Restarting the API with:"
grep -E '^GUARD_' .env | sed 's/^/  /'
docker compose up -d ingestion-api >/dev/null 2>&1
for i in $(seq 1 60); do
  if docker inspect -f '{{.State.Health.Status}}' rag-api 2>/dev/null | grep -q healthy; then
    echo "API is ready."; exit 0
  fi
  sleep 2
done
echo "API did not become healthy. Check: docker compose logs ingestion-api --tail=30"; exit 1
