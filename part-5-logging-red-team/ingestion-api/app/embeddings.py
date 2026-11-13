"""
embeddings.py: text -> vector using Ollama's embedding endpoint.

nomic-embed-text returns 768-dimensional vectors, which matches the
vector(768) column created in db/init/01-init.sh.
"""

import os
from typing import List

import httpx

OLLAMA_BASE_URL    = os.getenv("OLLAMA_BASE_URL", "http://ollama:11434").rstrip("/")
OLLAMA_EMBED_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")


async def embed_texts(texts: List[str]) -> List[List[float]]:
    payload = {"model": OLLAMA_EMBED_MODEL, "input": texts}
    async with httpx.AsyncClient(timeout=120.0) as client:
        r = await client.post(f"{OLLAMA_BASE_URL}/api/embed", json=payload)
        r.raise_for_status()
        data = r.json()

    embeddings = data.get("embeddings") or []
    if len(embeddings) != len(texts):
        raise RuntimeError(
            f"Ollama returned no embeddings for model '{OLLAMA_EMBED_MODEL}'. "
            "Run: bin/pull_models.sh"
        )
    return embeddings
