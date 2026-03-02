# Security Memory Architecture — Milvus Edition

This document explains how the security memory system is designed and how it fits into the broader lab architecture.

---

## Overview

The security memory is a separate Milvus collection (`ExpandedVSCodeMemory`) that stores chunked cybersecurity reference documents. It is queried independently of the main `LabDoc` collection used for general RAG, allowing you to target security-specific knowledge without polluting general retrieval results.

---

## Component Map

```
security-memory/data/           Host machine (mounted read-only into container)
        │
        ▼ (docker volume mount)
/securitymemory/data/           Inside ingestion-api container
        │
        ▼
app.security_memory.ingest      Chunking, embedding via Ollama, columnar insert into Milvus
        │
        ▼
Milvus: ExpandedVSCodeMemory    Typed collection, HNSW cosine index
        │
        ▼
app.security_memory.store       query_memory(), memory_health()
        │
        ▼
app.security_memory.router      /memory/health, /memory/query FastAPI endpoints
        │
        ▼
NGINX edge gateway              Authenticates X-API-Key before forwarding
        │
        ▼
Client (curl, IDE, MCP)         Queries the security memory
```

---

## Collection Schema

The `ExpandedVSCodeMemory` collection is defined with a typed schema in both `store.py` and `ingest.py`:

| Field | Milvus Type | Max Length | Purpose |
|-------|-------------|------------|---------|
| `id` | INT64 (auto PK) | — | Auto-assigned primary key |
| `embedding` | FLOAT_VECTOR | dim=768 | nomic-embed-text output |
| `text` | VARCHAR | 65535 | The chunk text |
| `title` | VARCHAR | 1024 | Document title (derived from filename) |
| `source` | VARCHAR | 512 | Subfolder name (e.g. "cis", "owasp") |
| `tags` | VARCHAR | 2048 | JSON-encoded list e.g. `["cis","docker"]` |
| `chunk_index` | INT64 | — | Position of chunk in original document |
| `doc_path` | VARCHAR | 2048 | Relative file path |

### Why tags are stored as JSON strings

Milvus `VARCHAR` fields support `LIKE` filtering, making tag queries straightforward:

```python
# Match any chunk tagged with "docker" OR "cis"
expr = 'tags like \'%"docker"%\' or tags like \'%"cis"%\''
```

A production system would use a JSON_CONTAINS expression or a separate scalar index for more efficient tag filtering, but the LIKE approach works correctly for the corpus sizes in this lab.

---

## Index Configuration

The embedding field uses an **HNSW cosine index**:

```python
index_params = {
    "metric_type": "COSINE",
    "index_type": "HNSW",
    "params": {"M": 16, "efConstruction": 200},
}
```

HNSW was chosen because:
- It provides the best recall/latency trade-off for corpora of this size (~100–1000 chunks)
- Cosine distance is appropriate for text embeddings from `nomic-embed-text`
- The parameters (`M=16, efConstruction=200`) are conservative defaults suitable for development

At query time, `ef=max(top_k * 4, 64)` is used to balance recall and speed.

---

## Embedding Pipeline

Both ingestion and query use the same Ollama embedding endpoint:

```
POST http://ollama:11434/api/embeddings
{
  "model": "nomic-embed-text",
  "prompt": "<text to embed>"
}
```

**One request per chunk** — Ollama does not support batched embeddings in this configuration. This means ingestion speed is proportional to corpus size: a 200-chunk corpus takes roughly 200 Ollama round trips.

The embedding dimension is 768. If you change models, update `SECURITY_EMBED_DIM` and recreate the collection.

---

## Differences from Qdrant and Weaviate Versions

| Aspect | Qdrant | Weaviate | Milvus |
|--------|--------|----------|--------|
| Collection/class creation | REST PUT | REST POST /v1/schema | pymilvus SDK (gRPC) |
| Insert | REST PUT /points | REST POST /batch/objects | `collection.insert()` columnar |
| Flush/persist | Implicit | Implicit | Explicit `collection.flush()` |
| ID management | UUID5 (explicit) | UUID5 (explicit) | Auto INT64 (Milvus assigns) |
| Tag filter | Structured filter object | GraphQL operands | SQL-like boolean LIKE expression |
| Search | REST POST /points/search | GraphQL nearVector | pymilvus `collection.search()` |
| Integration | patches/ folder | patches/ folder | Already in ingestion-api/app/ |

---

## Data Flow: Ingestion

1. `ingest.py` scans `SECURITY_DATA_DIR` recursively for `.md` and `.txt` files
2. Each file is normalized (CRLF → LF, collapsed whitespace) and split into overlapping chunks of `SECURITY_CHUNK_CHARS` characters with `SECURITY_CHUNK_OVERLAP` overlap
3. Tags are inferred from the file path (e.g. a file under `cis/` gets tagged `["cis"]`)
4. Chunks are embedded in batches of 32 via Ollama
5. Each batch is inserted into Milvus using columnar format and flushed to MinIO storage
6. IDs are auto-assigned by Milvus — re-ingesting the same file will create duplicate chunks (drop and recreate the collection to avoid this)

## Data Flow: Query

1. `store.py` receives a `MemoryQueryIn` with `query`, optional `tags`, optional `top_k`
2. The query text is embedded via Ollama (single request)
3. A Milvus `collection.search()` is issued with `nearVector`, `limit=top_k`, and optional `expr` for tag filtering
4. Results are mapped to `MemoryChunk` objects with `score = float(hit.score)` (Milvus returns cosine similarity directly for the COSINE metric)
5. Results are returned as `MemoryQueryOut`

---

## Deployment Notes

The `security-memory/data/` directory is mounted into the container as a read-only volume:

```yaml
volumes:
  - ./security-memory/data:/securitymemory/data:ro
```

The `:ro` flag ensures the container cannot modify the source documents. The ingestor reads from this path at ingestion time. The store module reads from Milvus at query time and never accesses the filesystem directly.
