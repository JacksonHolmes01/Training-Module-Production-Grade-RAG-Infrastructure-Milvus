#!/usr/bin/env bash
# Stops everything and deletes ALL data (database and downloaded models).
# Secrets in secrets/ and .env are kept.
set -euo pipefail
cd "$(dirname "$0")/.."
read -r -p "This deletes all documents and models. Type 'reset' to continue: " ans
[[ "$ans" == "reset" ]] || { echo "Cancelled."; exit 1; }
docker compose down -v
echo "Reset complete. Start again with: docker compose up -d --build"
