#!/usr/bin/env bash
set -euo pipefail

echo "WARNING: This will delete all Milvus data (vectors), etcd metadata,"
echo "MinIO segments, and Ollama model weights."
echo ""
read -rp "Are you sure? Type 'yes' to continue: " CONFIRM
if [ "$CONFIRM" != "yes" ]; then
  echo "Aborted."
  exit 0
fi

echo "Stopping containers..."
docker compose down

echo "Removing data volumes..."
docker volume rm -f \
  "$(basename "$PWD")_milvus_data" \
  "$(basename "$PWD")_etcd_data" \
  "$(basename "$PWD")_minio_data" \
  "$(basename "$PWD")_ollama_data" \
  2>/dev/null || true

echo "Reset complete. Run 'docker compose up -d' to start fresh."
