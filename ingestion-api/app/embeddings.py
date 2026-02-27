"""
embeddings.py — text → float vector via Ollama (nomic-embed-text)

Why Ollama instead of sentence-transformers?
  - Keeps the dependency list minimal (no torch/transformers).
  - Consistent with the generation layer (both use Ollama).
  - nomic-embed-text produces 768-dim vectors, matching the Milvus schema.
  - Ollama handles model caching and CPU/GPU dispatch automatically.

embed_texts() is an async coroutine. Call sites in rag.py and store.py
await it directly:

    vectors = await embed_texts(["hello world"])
"""

import os
import httpx
import logging
from typing import List

logger = logging.getLogger("embeddings")

OLLAMA_BASE_URL    = os.getenv("OLLAMA_BASE_URL", "http://ollama:11434").rstrip("/")
OLLAMA_EMBED_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")
EMBEDDINGS_DIM     = int(os.getenv("EMBEDDINGS_DIM", "768"))


async def embed_texts(texts: List[str]) -> List[List[float]]:
    """
    Embed a list of strings using Ollama's /api/embed endpoint.
    Returns a list of float vectors (one per input string).

    Raises RuntimeError if Ollama returns no embeddings -- usually means
    the model has not been pulled yet:
        docker exec ollama ollama pull nomic-embed-text
    """
    payload = {"model": OLLAMA_EMBED_MODEL, "input": texts}
    async with httpx.AsyncClient(timeout=60.0) as client:
        r = await client.post(f"{OLLAMA_BASE_URL}/api/embed", json=payload)
        r.raise_for_status()
        data = r.json()

    # Ollama >=0.1.32 returns {"embeddings": [[...], [...]]}
    embeddings = data.get("embeddings") or []

    if not embeddings:
        raise RuntimeError(
            f"Ollama returned no embeddings for model '{OLLAMA_EMBED_MODEL}'. "
            "Run: docker exec ollama ollama pull nomic-embed-text"
        )

    return embeddings
