"""
security_memory/store.py — Security memory store (Milvus version)

Changes from Qdrant version:
  - _ensure_collection() uses pymilvus SDK with explicit schema.
  - query_memory() uses collection.search() with HNSW cosine params.
  - Tag filtering uses Milvus boolean expression syntax instead of
    Qdrant's filter object syntax.
  - Metadata fields are typed VARCHAR columns (not a schemaless payload).
"""

import os
import json
import asyncio
from typing import List, Dict, Any, Optional

import httpx
from pymilvus import (
    connections,
    utility,
    Collection,
    CollectionSchema,
    FieldSchema,
    DataType,
)

from .schemas import MemoryQueryIn, MemoryQueryOut, MemoryChunk, MemoryHealthOut

# ----------------------------- #
# Config                        #
# ----------------------------- #
MILVUS_HOST     = os.getenv("MILVUS_HOST", "milvus")
MILVUS_PORT     = int(os.getenv("MILVUS_PORT", "19530"))
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://ollama:11434").rstrip("/")
SECURITY_EMBED_MODEL  = os.getenv("SECURITY_EMBED_MODEL", "nomic-embed-text")
SECURITY_COLLECTION   = os.getenv("SECURITY_COLLECTION", "ExpandedVSCodeMemory")
SECURITY_TOP_K        = int(os.getenv("SECURITY_TOP_K", "6"))
SECURITY_EMBED_DIM    = int(os.getenv("SECURITY_EMBED_DIM", "768"))


# ----------------------------- #
# Connection                    #
# ----------------------------- #

def _connect() -> None:
    connections.connect(alias="default", host=MILVUS_HOST, port=MILVUS_PORT, timeout=30)


# ----------------------------- #
# Schema                        #
# ----------------------------- #

def _build_security_schema() -> CollectionSchema:
    fields = [
        FieldSchema(name="id",          dtype=DataType.INT64,        is_primary=True, auto_id=True),
        FieldSchema(name="embedding",   dtype=DataType.FLOAT_VECTOR, dim=SECURITY_EMBED_DIM),
        FieldSchema(name="text",        dtype=DataType.VARCHAR,       max_length=65535),
        FieldSchema(name="title",       dtype=DataType.VARCHAR,       max_length=1024),
        FieldSchema(name="source",      dtype=DataType.VARCHAR,       max_length=512),
        FieldSchema(name="tags",        dtype=DataType.VARCHAR,       max_length=2048),   # JSON list
        FieldSchema(name="chunk_index", dtype=DataType.INT64),
        FieldSchema(name="doc_path",    dtype=DataType.VARCHAR,       max_length=2048),
    ]
    return CollectionSchema(fields=fields, description="Security memory corpus")


# ----------------------------- #
# Embeddings (Ollama)           #
# ----------------------------- #

async def _embed(text: str) -> List[float]:
    timeout = httpx.Timeout(180.0, connect=30.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        r = await client.post(
            f"{OLLAMA_BASE_URL}/api/embeddings",
            json={"model": SECURITY_EMBED_MODEL, "prompt": text},
        )
        r.raise_for_status()
        data = r.json()
        emb  = data.get("embedding")
        if not emb or not isinstance(emb, list):
            raise ValueError(f"Unexpected Ollama embeddings response: {data}")
        return emb


# ----------------------------- #
# Collection lifecycle          #
# ----------------------------- #

async def _ensure_collection() -> Collection:
    _connect()
    if not utility.has_collection(SECURITY_COLLECTION):
        schema     = _build_security_schema()
        collection = Collection(name=SECURITY_COLLECTION, schema=schema)
        # Create HNSW cosine index
        collection.create_index(
            field_name="embedding",
            index_params={
                "metric_type": "COSINE",
                "index_type":  "HNSW",
                "params":      {"M": 16, "efConstruction": 200},
            },
        )
    else:
        collection = Collection(name=SECURITY_COLLECTION)
    collection.load()
    return collection


# ----------------------------- #
# Health                        #
# ----------------------------- #

async def memory_health() -> MemoryHealthOut:
    try:
        _connect()
        ok         = True
        exists     = utility.has_collection(SECURITY_COLLECTION)
        points     = None
        if exists:
            col    = Collection(name=SECURITY_COLLECTION)
            col.load()
            stats  = col.get_collection_stats()
            # stats["row_count"] is a string in some SDK versions
            try:
                points = int(stats.get("row_count", 0))
            except (TypeError, ValueError):
                points = None
    except Exception as exc:
        ok     = False
        points = None

    note = None
    if points in (0, None):
        note = (
            "Collection appears empty. Run: "
            "docker exec -i ingestion-api python -m app.security_memory.ingest"
        )

    return MemoryHealthOut(
        ok=ok,
        collection=SECURITY_COLLECTION,
        milvus_host=f"{MILVUS_HOST}:{MILVUS_PORT}",
        points_count=points,
        note=note,
    )


# ----------------------------- #
# Query                         #
# ----------------------------- #

async def query_memory(payload: MemoryQueryIn) -> MemoryQueryOut:
    """
    Vector similarity search with optional tag filtering.

    Milvus filter syntax uses boolean expressions (SQL-like):
        tags like '%docker%'
    rather than Qdrant's structured filter object.

    Because tags are stored as a JSON string, we use LIKE to check for
    each requested tag substring.  A production system would normalise
    tags into a JSON_CONTAINS expression or use a separate scalar index.
    """
    collection = await _ensure_collection()
    top_k      = payload.top_k or SECURITY_TOP_K
    qvec       = await _embed(payload.query)

    # Build Milvus filter expression for tag filtering
    expr: Optional[str] = None
    if payload.tags:
        # Match any document whose tags JSON string contains at least one requested tag
        clauses = [f'tags like \'%"{tag}"%\'' for tag in payload.tags]
        expr    = " or ".join(clauses)

    def _search() -> List[MemoryChunk]:
        search_params = {
            "metric_type": "COSINE",
            "params":      {"ef": max(top_k * 4, 64)},
        }
        output_fields = ["text", "title", "source", "tags", "chunk_index", "doc_path"]
        results = collection.search(
            data=[qvec],
            anns_field="embedding",
            param=search_params,
            limit=top_k,
            expr=expr,
            output_fields=output_fields,
        )
        chunks: List[MemoryChunk] = []
        for hit in results[0]:
            e = hit.entity
            raw_tags = e.get("tags") or "[]"
            try:
                tags = json.loads(raw_tags)
            except (json.JSONDecodeError, TypeError):
                tags = []
            chunks.append(
                MemoryChunk(
                    score=float(hit.score),
                    title=str(e.get("title") or ""),
                    source=str(e.get("source") or ""),
                    tags=tags,
                    text=str(e.get("text") or ""),
                    chunk_index=int(e.get("chunk_index") or 0),
                    doc_path=str(e.get("doc_path") or ""),
                )
            )
        return chunks

    results = await asyncio.to_thread(_search)

    return MemoryQueryOut(
        query=payload.query,
        collection=SECURITY_COLLECTION,
        top_k=top_k,
        results=results,
    )
