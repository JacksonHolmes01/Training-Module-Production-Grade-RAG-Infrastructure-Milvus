#!/usr/bin/env bash
set -euo pipefail

SERVICE="${1:-}"

if [ -n "$SERVICE" ]; then
  docker compose logs -f --tail=200 "$SERVICE"
else
  docker compose logs -f --tail=200
fi
