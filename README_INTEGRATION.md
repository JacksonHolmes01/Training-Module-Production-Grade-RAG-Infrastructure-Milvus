# Security Memory Integration — Milvus Edition

This document describes the `security_memory` module that is already wired into this repo's `ingestion-api`. Unlike the Qdrant and Weaviate versions of this lab, the security memory code lives directly in `ingestion-api/app/security_memory/` and is registered with the FastAPI app on startup — no patch step is required.

---

## What it adds

Two new API endpoints are available once the stack is running:

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/memory/health` | `GET` | Check collection status and object count |
| `/memory/query` | `POST` | Semantic search over the security corpus |

Both endpoints require the same `X-API-Key` header as all other endpoints.

---

## Architecture

```
security-memory/data/   ← source documents (mounted read-only into container)
        │
        ▼
app.security_memory.ingest  ← chunks, embeds via Ollama, inserts into Milvus
        │
        ▼
Milvus collection: ExpandedVSCodeMemory
  schema:
    id           INT64       auto primary key
    embedding    FLOAT_VECTOR[768]  nomic-embed-text output
    text         VARCHAR[65535]     chunk text
    title        VARCHAR[1024]      document title
    source       VARCHAR[512]       subfolder name (e.g. "cis", "owasp")
    tags         VARCHAR[2048]      JSON-encoded list e.g. ["cis","docker"]
    chunk_index  INT64              position within original document
    doc_path     VARCHAR[2048]      path relative to data dir
  index: HNSW cosine
        │
        ▼
app.security_memory.store   ← query_memory(), memory_health()
        │
        ▼
app.security_memory.router  ← /memory/health, /memory/query (registered in main.py)
```

The main `LabDoc` collection uses Milvus with Ollama-generated embeddings for the general RAG pipeline. The `ExpandedVSCodeMemory` collection is a completely separate Milvus collection with its own typed schema, index, and embedding pipeline. The two collections are independent — you can drop and recreate either one without affecting the other.

---

## Key differences from Qdrant and Weaviate versions

| Aspect | Qdrant | Weaviate | Milvus |
|--------|--------|----------|--------|
| API style | REST/HTTP | GraphQL + REST | gRPC via pymilvus SDK |
| Schema | Schemaless payload | Class with properties | Typed collection schema |
| Filtering | Structured filter object | GraphQL WHERE clause | SQL-like boolean expression |
| Tags storage | Native array field | text[] property | JSON string in VARCHAR |
| Tag filter | `should: [{key: "tags", match: {value: ...}}]` | `operator: Equal` on text[] | `tags like '%"docker"%'` |
| Insert | REST PUT /points | REST POST /batch/objects | pymilvus `collection.insert()` |
| ID generation | UUID (explicit) | UUID5 (deterministic) | Auto INT64 (Milvus assigns) |
| Integration | patches/ folder | patches/ folder | Already wired in main.py |

---

## Running the ingestor

Make sure the stack is fully healthy first — Milvus takes 60–90 seconds on a cold start:

```bash
docker compose ps
```

All services should show `healthy` or `running`. Then:

```bash
docker exec -i ingestion-api python -m app.security_memory.ingest
```

Progress output:
```
[security-memory] Created Milvus collection: ExpandedVSCodeMemory
[security-memory] upserted 32 chunks so far...
[security-memory] upserted 64 chunks so far...
[security-memory] ingest complete: files=6 chunks=183 collection=ExpandedVSCodeMemory
```

Ingestion time depends on the number of documents and Ollama embedding speed. Ollama embeds one chunk at a time, so large corpora can take several minutes to over an hour.

---

## Verifying the collection

Check health via the API:

```bash
EDGE_API_KEY=$(grep -E '^EDGE_API_KEY=' .env | cut -d= -f2-)
curl -s http://localhost:8088/memory/health \
  -H "X-API-Key: $EDGE_API_KEY" | python -m json.tool
```

Expected response shape:
```json
{
  "ok": true,
  "collection": "ExpandedVSCodeMemory",
  "milvus_host": "milvus:19530",
  "points_count": 183,
  "note": null
}
```

Check directly in Milvus via pymilvus:

```bash
docker exec -i ingestion-api python - <<'PY'
from pymilvus import connections, Collection
connections.connect(host="milvus", port=19530, timeout=10)
col = Collection("ExpandedVSCodeMemory")
col.load()
print("entities:", col.num_entities)
PY
```

---

## Running a query

```bash
EDGE_API_KEY=$(grep -E '^EDGE_API_KEY=' .env | cut -d= -f2-)
curl -s -X POST http://localhost:8088/memory/query \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $EDGE_API_KEY" \
  -d '{
    "query": "Docker containers running as root",
    "tags": ["docker", "cis"],
    "top_k": 3
  }' | python -m json.tool
```

The `tags` field is optional. If omitted, the query searches the entire collection. If provided, it filters to documents whose `tags` JSON string contains at least one of the specified values.

---

## Dropping and recreating the collection

If you change the embedding model or `SECURITY_EMBED_DIM`, you must recreate the collection — old and new vectors are not comparable:

```bash
docker exec -i ingestion-api python - <<'PY'
from pymilvus import connections, utility, Collection
connections.connect(host="milvus", port=19530, timeout=10)
if utility.has_collection("ExpandedVSCodeMemory"):
    Collection("ExpandedVSCodeMemory").drop()
    print("Dropped ExpandedVSCodeMemory")
else:
    print("Collection does not exist")
PY

docker exec -i ingestion-api python -m app.security_memory.ingest
```

---

## Environment variables

All variables are passed in by `docker-compose.yml`. Reference values are in `.env.example`.

| Variable | Default | Purpose |
|----------|---------|---------|
| `MILVUS_HOST` | `milvus` | Milvus service hostname |
| `MILVUS_PORT` | `19530` | Milvus gRPC port |
| `OLLAMA_BASE_URL` | `http://ollama:11434` | Ollama service URL |
| `SECURITY_COLLECTION` | `ExpandedVSCodeMemory` | Milvus collection name |
| `SECURITY_TOP_K` | `6` | Default results per query |
| `SECURITY_CHUNK_CHARS` | `1200` | Characters per chunk |
| `SECURITY_CHUNK_OVERLAP` | `200` | Overlap between chunks |
| `SECURITY_EMBED_MODEL` | `nomic-embed-text` | Ollama embedding model |
| `SECURITY_EMBED_DIM` | `768` | Embedding vector dimension |
| `SECURITY_DATA_DIR` | `/securitymemory/data` | Mounted corpus path (inside container) |
