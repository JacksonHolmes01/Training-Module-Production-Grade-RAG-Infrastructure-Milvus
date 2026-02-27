"""
milvus_client.py  —  Milvus vector store client (replaces qdrant_client.py)

Key architectural differences from Qdrant:
  - Milvus uses gRPC (port 19530) not HTTP REST for data-plane ops.
  - pymilvus SDK replaces raw httpx calls.
  - Collections need an explicit schema with typed fields (unlike Qdrant's
    schemaless payload approach).
  - IDs must be int64 or string; we use a 64-bit hash of a UUID string.
  - "Segment" flushing is managed by Milvus internally; we call flush()
    after bulk inserts for durability guarantees.
  - Index creation (IVF_FLAT / HNSW etc.) is a separate step from
    collection creation.  We auto-build an HNSW index on first insert
    if none exists.
"""

import os
import uuid
import hashlib
import logging
from typing import Dict, Any, List

from pymilvus import (
    connections,
    utility,
    Collection,
    CollectionSchema,
    FieldSchema,
    DataType,
)
from .embeddings import embed_texts as local_embed_texts

logger = logging.getLogger("milvus_client")

# ----------------------------- #
# Config                        #
# ----------------------------- #
MILVUS_HOST       = os.getenv("MILVUS_HOST", "milvus")
MILVUS_PORT       = int(os.getenv("MILVUS_PORT", "19530"))
MILVUS_COLLECTION = os.getenv("MILVUS_COLLECTION", "LabDoc")

# Vector dimension MUST match the embedding model output size.
# nomic-embed-text → 768, all-MiniLM-L6-v2 → 384
EMBEDDINGS_DIM = int(os.getenv("EMBEDDINGS_DIM", "768"))

# HNSW index parameters — tunable via ENV for students to experiment
HNSW_M           = int(os.getenv("MILVUS_HNSW_M", "16"))
HNSW_EF_CONSTRUCT = int(os.getenv("MILVUS_HNSW_EF_CONSTRUCTION", "200"))


# ----------------------------- #
# Connection management         #
# ----------------------------- #

def _connect() -> None:
    """Establish (or reuse) the Milvus gRPC connection."""
    try:
        connections.connect(
            alias="default",
            host=MILVUS_HOST,
            port=MILVUS_PORT,
            timeout=30,
        )
    except Exception as exc:
        logger.error(f"Milvus connection failed: {exc}")
        raise


# ----------------------------- #
# Readiness                     #
# ----------------------------- #

async def ready() -> bool:
    """Return True if Milvus is reachable and the server is healthy."""
    try:
        _connect()
        # utility.get_server_version() raises if server is unreachable
        utility.get_server_version()
        return True
    except Exception as exc:
        logger.warning(f"Milvus ready() check failed: {exc}")
        return False


# ----------------------------- #
# Schema helpers                #
# ----------------------------- #

def _build_schema() -> CollectionSchema:
    """
    Define the Milvus collection schema.

    Fields:
      - id         : INT64, primary key (auto-id disabled so we control IDs)
      - text        : VARCHAR(65535) — the original document text
      - title       : VARCHAR(1024)
      - url         : VARCHAR(2048)
      - source      : VARCHAR(512)
      - published_date: VARCHAR(64)
      - tags        : VARCHAR(2048) — JSON-encoded list for now
      - embedding   : FLOAT_VECTOR — the semantic embedding

    Milvus requires a primary key field and at least one vector field.
    All other fields are metadata (equivalent to Qdrant payload).
    """
    fields = [
        FieldSchema(name="id",             dtype=DataType.INT64,         is_primary=True, auto_id=False),
        FieldSchema(name="embedding",      dtype=DataType.FLOAT_VECTOR,  dim=EMBEDDINGS_DIM),
        FieldSchema(name="text",           dtype=DataType.VARCHAR,        max_length=65535),
        FieldSchema(name="title",          dtype=DataType.VARCHAR,        max_length=1024),
        FieldSchema(name="url",            dtype=DataType.VARCHAR,        max_length=2048),
        FieldSchema(name="source",         dtype=DataType.VARCHAR,        max_length=512),
        FieldSchema(name="published_date", dtype=DataType.VARCHAR,        max_length=64),
        FieldSchema(name="tags",           dtype=DataType.VARCHAR,        max_length=2048),
    ]
    return CollectionSchema(
        fields=fields,
        description="RAG lab document collection — Milvus version",
        enable_dynamic_field=True,   # allows extra payload fields without schema changes
    )


def _ensure_index(collection: Collection) -> None:
    """
    Create an HNSW vector index if one does not already exist.

    HNSW is the recommended index for cosine similarity search.
    Parameters M and ef_construction are exposed as ENV vars so students
    can experiment with accuracy/speed tradeoffs.
    """
    if collection.has_index():
        return
    index_params = {
        "metric_type": "COSINE",
        "index_type":  "HNSW",
        "params": {
            "M":              HNSW_M,
            "efConstruction": HNSW_EF_CONSTRUCT,
        },
    }
    collection.create_index(field_name="embedding", index_params=index_params)
    logger.info(
        f"Created HNSW index on '{MILVUS_COLLECTION}' "
        f"(M={HNSW_M}, efConstruction={HNSW_EF_CONSTRUCT}, metric=COSINE)"
    )


# ----------------------------- #
# Collection lifecycle          #
# ----------------------------- #

async def ensure_collection() -> Collection:
    """
    Create the Milvus collection (and HNSW index) if they don't exist,
    then load it into memory for search.

    Milvus requires an explicit load() call before queries — this is
    analogous to Qdrant's implicit ready state but is an explicit step
    in Milvus's lifecycle model.
    """
    _connect()

    if not utility.has_collection(MILVUS_COLLECTION):
        schema = _build_schema()
        collection = Collection(name=MILVUS_COLLECTION, schema=schema)
        logger.info(f"Created Milvus collection: {MILVUS_COLLECTION}")
    else:
        collection = Collection(name=MILVUS_COLLECTION)

    _ensure_index(collection)
    collection.load()          # load segments into memory (required before search)
    return collection


# ----------------------------- #
# Embeddings                    #
# ----------------------------- #

async def embed_texts(texts: List[str]) -> List[List[float]]:
    """Local embeddings — delegates to embeddings.py."""
    return await local_embed_texts(texts)


# ----------------------------- #
# ID generation                 #
# ----------------------------- #

def _make_id() -> int:
    """
    Generate a deterministic INT64 ID from a fresh UUID.
    Milvus primary keys must be int64 (or string); we derive one by
    taking the first 8 bytes of the UUID's bytes as a big-endian int
    and masking to positive int64 range.
    """
    raw = uuid.uuid4().bytes
    return int.from_bytes(raw[:8], "big") & 0x7FFFFFFFFFFFFFFF


# ----------------------------- #
# Insert                        #
# ----------------------------- #

async def insert_doc(doc: Dict[str, Any]) -> Dict[str, Any]:
    """
    Embed + insert one document into Milvus.

    Returns a dict with 'result' and the generated 'id'.

    Milvus insert() takes columnar data (list-per-field) rather than
    Qdrant's row-oriented list of point dicts.
    """
    collection = await ensure_collection()

    if hasattr(doc, "model_dump"):
        doc = doc.model_dump(mode="json")

    text = (doc.get("text") or "").strip()
    vec  = (await embed_texts([text]))[0]

    import json
    point_id = _make_id()
    data = [
        [point_id],
        [vec],
        [text[:65535]],
        [(doc.get("title") or "")[:1024]],
        [(doc.get("url")   or "")[:2048]],
        [(doc.get("source") or "")[:512]],
        [(doc.get("published_date") or "")[:64]],
        [json.dumps(doc.get("tags") or [])[:2048]],
    ]

    mr = collection.insert(data)
    collection.flush()   # ensure segment is persisted + visible to search

    return {"result": "inserted", "id": str(point_id), "milvus_pk": mr.primary_keys}
