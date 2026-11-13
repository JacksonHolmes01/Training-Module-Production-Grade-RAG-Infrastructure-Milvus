#!/usr/bin/env bash
# Choose how many hardening layers are active, then apply them.
#
# Usage:
#   bin/harden.sh <0-6>      0 = no hardening (the Part 3 setup), 6 = every layer
#   bin/harden.sh status     show which layers are active
#
# Layers (each lesson adds one):
#   1  non-root users            hardening/01-non-root.yml
#   2  no capabilities, limits   hardening/02-capabilities.yml
#   3  read-only filesystems     hardening/03-read-only.yml
#   4  secrets out of env vars   hardening/04-secrets.yml
#   5  internal TLS              hardening/05-internal-tls.yml
#   6  images pinned by digest   hardening/06-pinned.yml  (created by bin/pin_images.sh)
#
# How it works: Docker Compose reads COMPOSE_FILE from .env, so after this
# script runs, EVERY plain `docker compose ...` command uses the same layers.
set -euo pipefail
cd "$(dirname "$0")/.."

LAYERS=(hardening/01-non-root.yml hardening/02-capabilities.yml hardening/03-read-only.yml
        hardening/04-secrets.yml hardening/05-internal-tls.yml hardening/06-pinned.yml)

if [[ "${1:-}" == "status" ]]; then
  grep -E '^COMPOSE_FILE=' .env | cut -d= -f2- | tr ':' '\n' | sed 's/^/  /'
  exit 0
fi

LEVEL="${1:?usage: bin/harden.sh <0-6|status>}"
[[ "$LEVEL" =~ ^[0-6]$ ]] || { echo "level must be 0 to 6"; exit 1; }
if [[ "$LEVEL" == "6" && ! -f hardening/06-pinned.yml ]]; then
  echo "hardening/06-pinned.yml does not exist yet. Run bin/pin_images.sh first (Lesson 9)."; exit 1
fi

CF="docker-compose.yml"
for ((i=0; i<LEVEL; i++)); do CF="$CF:${LAYERS[$i]}"; done

if grep -qE '^COMPOSE_FILE=' .env; then
  sed -i.bak "s|^COMPOSE_FILE=.*|COMPOSE_FILE=${CF}|" .env && rm -f .env.bak
else
  echo "COMPOSE_FILE=${CF}" >> .env
fi

echo "Active layers:"
echo "$CF" | tr ':' '\n' | sed 's/^/  /'
echo "Applying (containers that changed are recreated)..."
docker compose up -d --build --remove-orphans >/dev/null 2>&1 || { docker compose up -d --build --remove-orphans; exit 1; }

KEY="$(grep -E '^EDGE_API_KEY=' .env | cut -d= -f2-)"
for i in $(seq 1 60); do
  # Up = the API answers through NGINX AND reports the database healthy
  if curl -s -H "X-API-Key: $KEY" http://localhost:8088/health 2>/dev/null | grep -q '"ok":true'; then
    echo "Stack is up."; exit 0
  fi
  sleep 3
done
echo "The stack did not come up. Check: docker compose ps -a   and   docker compose logs --tail=30"
exit 1
