"""
rag.py — Retrieval + Generation pipeline (Milvus version)

Changes from Qdrant version:
  - retrieve_sources() uses pymilvus Collection.search() instead of
    the Qdrant REST API.
  - Search returns pymilvus SearchResult objects; we normalise them into
    the same dict shape so build_prompt() and callers are unchanged.
  - Metadata (tags) stored as JSON string must be decoded on read.
"""

import os
import re
import json
import logging
import asyncio
from typing import Any, Dict, List, Optional, Literal

from .embeddings import embed_texts
from .milvus_client import ensure_collection

logger = logging.getLogger("rag")

# ----------------------------- #
# Config                        #
# ----------------------------- #
MILVUS_COLLECTION  = os.getenv("MILVUS_COLLECTION", "LabDoc")
RAG_TOP_K          = int(os.getenv("RAG_TOP_K", "4"))
RAG_MAX_SOURCE_CHARS = int(os.getenv("RAG_MAX_SOURCE_CHARS", "800"))
OLLAMA_BASE_URL    = os.getenv("OLLAMA_BASE_URL", "http://ollama:11434").rstrip("/")
OLLAMA_MODEL       = os.getenv("OLLAMA_MODEL", "llama3.1")

import httpx

DetailLevel = Literal["basic", "standard", "advanced"]


# ----------------------------- #
# Complexity / detail routing   #
# ----------------------------- #

def classify_detail_level(message: str) -> DetailLevel:
    m = (message or "").strip()
    if not m:
        return "basic"
    lower = m.lower()

    has_code_block = "```" in m
    has_cli        = bool(re.search(r"\b(docker|kubectl|curl|pip|conda|apt-get|brew)\b", lower))
    has_logs       = bool(re.search(r"\b(traceback|exception|stack trace|error:|warn\[)\b", lower))
    has_protocols  = bool(re.search(r"\b(http|https|grpc|tcp|udp|oauth|jwt)\b", lower))
    has_acronyms   = bool(re.search(r"\b(RAG|LLM|API|SDK|TLS|SSL|CVE|XSS|CSRF|SQLi|RBAC|IAM)\b", m))
    long_or_multi  = len(m) > 180 or m.count("?") >= 2 or m.count("\n") >= 3

    advanced_score = sum([
        2 if has_code_block else 0,
        2 if has_cli        else 0,
        2 if has_logs       else 0,
        1 if has_protocols  else 0,
        1 if has_acronyms   else 0,
        1 if long_or_multi  else 0,
    ])

    if advanced_score >= 3:
        return "advanced"
    if len(m) <= 60 and not (has_cli or has_logs or has_protocols or has_acronyms or has_code_block):
        return "basic"
    return "standard"


def _detail_instructions(level: DetailLevel) -> str:
    if level == "basic":
        return (
            "Write for a beginner.\n"
            "- Keep it short (3–8 sentences).\n"
            "- Explain jargon in plain language.\n"
            "- Prefer bullets.\n"
            "- Avoid deep implementation details unless asked.\n"
        )
    if level == "advanced":
        return (
            "Write for a technical audience.\n"
            "- Be precise.\n"
            "- Include concrete steps, commands, and edge cases when helpful.\n"
            "- Mention security/reliability considerations if relevant.\n"
            "- If you make assumptions, state them.\n"
        )
    return (
        "Write at an intermediate level.\n"
        "- Clear explanation with practical guidance.\n"
        "- Use bullets and short sections.\n"
        "- Include commands only when they add real value.\n"
    )


# ----------------------------- #
# Retrieval (Milvus)            #
# ----------------------------- #

async def retrieve_sources(query: str, k: Optional[int] = None) -> List[Dict[str, Any]]:
    """
    Retrieve top-k documents from Milvus using HNSW cosine similarity search.

    Key Milvus difference: search() requires the collection to be loaded
    into memory first (handled by ensure_collection / milvus_client).
    Search params (ef) are tunable and affect recall vs. latency.
    """
    k = k or RAG_TOP_K

    # 1) Embed query (embed_texts is always a coroutine)
    vectors = await embed_texts([query])
    qvec    = vectors[0]

    # 2) Milvus search — run in thread pool to avoid blocking the event loop
    #    (pymilvus is a synchronous SDK)
    def _search() -> List[Dict[str, Any]]:
        # ensure_collection is async; run it in a fresh event loop isolated
        # from the outer loop (which owns this thread via asyncio.to_thread).
        collection = asyncio.run(ensure_collection())
        search_params = {
            "metric_type": "COSINE",
            "params": {"ef": max(k * 4, 64)},   # ef >= top_k for HNSW accuracy
        }
        output_fields = ["text", "title", "url", "source", "published_date", "tags"]
        results = collection.search(
            data=[qvec],
            anns_field="embedding",
            param=search_params,
            limit=k,
            output_fields=output_fields,
        )
        sources: List[Dict[str, Any]] = []
        for hit in results[0]:
            entity  = hit.entity
            raw_tags = entity.get("tags") or "[]"
            try:
                tags = json.loads(raw_tags)
            except (json.JSONDecodeError, TypeError):
                tags = []
            full_text = entity.get("text") or ""
            sources.append({
                "title":          entity.get("title") or "",
                "url":            entity.get("url")   or "",
                "source":         entity.get("source") or "",
                "published_date": entity.get("published_date") or "",
                "tags":           tags,
                "distance":       float(hit.score),   # cosine similarity (0–1)
                "snippet":        full_text[:RAG_MAX_SOURCE_CHARS],
            })
        return sources

    return await asyncio.to_thread(_search)


# ----------------------------- #
# Prompt building               #
# ----------------------------- #

def build_prompt(
    user_message: str,
    sources: List[Dict[str, Any]],
    detail_level: Optional[DetailLevel] = None,
) -> str:
    level: DetailLevel = detail_level or classify_detail_level(user_message)
    ctx_lines: List[str] = []
    for i, s in enumerate(sources, start=1):
        title   = s.get("title", "")
        url     = s.get("url", "")
        snippet = s.get("snippet", "")
        ctx_lines.append(f"[{i}] {title} ({url})\n{snippet}")

    context = "\n\n".join(ctx_lines) if ctx_lines else "(no sources retrieved)"

    return (
        "You are a retrieval-augmented assistant.\n"
        "Rules:\n"
        "1) Use ONLY the provided Sources for factual claims.\n"
        "2) If Sources are insufficient, say what is missing and what you would check next.\n"
        "3) When you cite a source, cite it inline like [1], [2].\n"
        "4) Do not invent URLs, quotes, or document titles.\n\n"
        f"Response style:\n{_detail_instructions(level)}\n"
        f"Detail level selected: {level}\n\n"
        f"Sources:\n{context}\n\n"
        f"User question:\n{user_message}\n\n"
        "Answer:\n"
    )


# ----------------------------- #
# Ollama generation             #
# ----------------------------- #

async def ollama_generate(prompt: str) -> str:
    req = {"model": OLLAMA_MODEL, "prompt": prompt, "stream": False}
    async with httpx.AsyncClient(timeout=180.0) as client:
        r = await client.post(f"{OLLAMA_BASE_URL}/api/generate", json=req)
        r.raise_for_status()
        data = r.json()
    return (data.get("response") or "").strip()
