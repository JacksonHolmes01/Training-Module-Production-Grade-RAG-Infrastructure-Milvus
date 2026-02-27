#!/usr/bin/env bash
set -euo pipefail

if [ ! -f .env ]; then
  echo "Missing .env. Run: cp .env.example .env"
  exit 1
fi

MODEL=$(grep -E '^OLLAMA_MODEL=' .env | cut -d= -f2- | tr -d '\r')
EMBED_MODEL=$(grep -E '^OLLAMA_EMBED_MODEL=' .env | cut -d= -f2- | tr -d '\r')
EMBED_MODEL="${EMBED_MODEL:-nomic-embed-text}"

if [ -z "$MODEL" ]; then
  echo "OLLAMA_MODEL not set in .env"
  exit 1
fi

echo "Pulling generation model: $MODEL"
docker exec ollama ollama pull "$MODEL"

echo "Pulling embedding model: $EMBED_MODEL"
docker exec ollama ollama pull "$EMBED_MODEL"

echo ""
echo "Models ready:"
docker exec ollama ollama list
