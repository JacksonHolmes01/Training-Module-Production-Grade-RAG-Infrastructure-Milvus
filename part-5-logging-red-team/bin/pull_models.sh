#!/usr/bin/env bash
# Downloads the LLM and the embedding model into the Ollama container.
set -euo pipefail
cd "$(dirname "$0")/.."
LLM="$(grep -E '^OLLAMA_MODEL=' .env | cut -d= -f2-)"
EMB="$(grep -E '^OLLAMA_EMBED_MODEL=' .env | cut -d= -f2-)"
for m in "${LLM:-llama3.2:1b}" "${EMB:-nomic-embed-text}"; do
  echo "Pulling $m ..."
  docker exec rag-ollama ollama pull "$m"
done
docker exec rag-ollama ollama list
