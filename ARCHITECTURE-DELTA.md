# Milvus Conversion — Architecture Delta & Curriculum Guide

This document explains what changed architecturally, what the code differences mean, and what students learn differently in the Milvus version of the lab.

---

## 1. Architectural Differences

### Services Added (Milvus requires a cluster of 3 instead of 1)

| Service | Purpose | Qdrant equivalent |
|---|---|---|
| `milvus` | Vector database (standalone mode) | `qdrant` |
| `etcd` | Metadata/config store for Milvus | _(none — Qdrant is self-contained)_ |
| `minio` | Object storage for segment files | _(none — Qdrant uses local disk only)_ |

**Why does Milvus need etcd + MinIO?**

Milvus is architected for distributed, multi-node deployments. Even in standalone mode it externalises:
- **etcd** → stores collection schemas, index configs, and segment metadata
- **MinIO** → stores the actual vector segment files (persistent object storage)

This adds infrastructure complexity but also teaches a production pattern: separating compute from storage.

---

### Protocol Difference

| Layer | Qdrant | Milvus |
|---|---|---|
| Data plane (insert/search) | REST HTTP on port 6333 | gRPC on port 19530 |
| Health check | `GET /healthz` (HTTP) | `utility.get_server_version()` (gRPC) |
| Client library | `httpx` (raw HTTP) | `pymilvus` SDK |

In the Qdrant version, all API calls used `httpx` directly against the REST API — students could read raw HTTP calls and understand exactly what was happening.

In the Milvus version, a Python SDK (`pymilvus`) abstracts the gRPC transport. This is closer to how production teams use Milvus, but means understanding the SDK's abstractions rather than raw wire format.

---

### Schema Model Difference

| Concept | Qdrant | Milvus |
|---|---|---|
| Document structure | Schemaless JSON payload | Typed columnar schema |
| Adding new fields | No migration needed | Drop + recreate collection |
| Field types | Inferred from JSON | Must be declared (VARCHAR, INT64, etc.) |
| Primary key type | UUID string | INT64 or string |
| Metadata filtering | Structured filter object (JSON) | Boolean expression string (SQL-like) |

---

### Index Lifecycle

Qdrant creates an index automatically on collection creation. Milvus separates:
1. Collection creation (schema only)
2. Index creation (algorithm + params)
3. Collection load (move into memory)
4. Search/Insert

This explicit lifecycle is a teaching opportunity: students learn **why** each step exists and what fails if steps are skipped.

---

## 2. Code Change Map

| File | Qdrant version | Milvus version | Change type |
|---|---|---|---|
| `ingestion-api/app/qdrant_client.py` | Uses `httpx` REST calls | Replaced by `milvus_client.py` using `pymilvus` SDK | Full rewrite |
| `ingestion-api/app/rag.py` | `httpx.post(…/points/search)` | `collection.search()` via pymilvus | Retrieval section rewritten |
| `ingestion-api/app/main.py` | Imports `qdrant_client` | Imports `milvus_client` | Import + response key change |
| `ingestion-api/app/security_memory/store.py` | Qdrant REST health + search | Milvus SDK health + search | Full rewrite |
| `ingestion-api/app/security_memory/ingest.py` | Qdrant REST upsert | Milvus columnar insert | Upsert section rewritten |
| `ingestion-api/requirements.txt` | No extra DB client | Added `pymilvus==2.4.9` | Dependency added |
| `docker-compose.yml` | 1 DB service | 3 DB services (milvus + etcd + minio) | Services added |
| `.env.example` | `QDRANT_URL`, `QDRANT_COLLECTION` | `MILVUS_HOST`, `MILVUS_PORT`, `MILVUS_COLLECTION` | ENV vars renamed |

---

## 3. ENV Variable Changes

### Removed

```env
QDRANT_URL=http://qdrant:6333
QDRANT_COLLECTION=LabDoc
```

### Added

```env
MILVUS_HOST=milvus
MILVUS_PORT=19530
MILVUS_COLLECTION=LabDoc
```

### Why port 19530?

Milvus uses gRPC on `19530` for data operations. There is also an HTTP API on `9091` used only for health checks. The pymilvus SDK always connects on `19530`.

---

## 4. Curriculum Delta — What Students Learn Differently

### Topic 1: Vector Database Client Models

**Qdrant lesson:** Students call the Qdrant REST API directly using `httpx`. The code is transparent — every HTTP call is visible, every JSON payload is readable. This is excellent for teaching the *shape* of vector database operations.

**Milvus lesson:** Students use the `pymilvus` SDK which abstracts gRPC. The operations are the same conceptually, but the implementation hides the transport layer. Students learn to read SDK documentation instead of API documentation. This is the pattern they'll encounter in most production Milvus deployments.

**New concept introduced:** SDK-vs-REST trade-offs in infrastructure client design.

---

### Topic 2: Schema Design

**Qdrant lesson:** Students never define a schema. They ingest whatever JSON they want; Qdrant stores it. The lesson is about how schemaless design provides flexibility.

**Milvus lesson:** Students must define every field upfront in `_build_schema()`. They learn:
- What fields to include and why
- How to choose field types (VARCHAR max_length, INT64, FLOAT_VECTOR dim)
- What happens when the schema doesn't match ingested data
- How to perform a schema migration (drop + recreate + re-ingest)

**New concept introduced:** Schema-first design, migration planning, type-safe document stores.

---

### Topic 3: Infrastructure Complexity

**Qdrant lesson:** One container. Start it, it works. Students focus on the application layer.

**Milvus lesson:** Three containers with dependencies: milvus → etcd + minio. Students learn:
- How to read `depends_on` with `condition: service_healthy`
- What etcd does (distributed key-value metadata store)
- What MinIO does (S3-compatible object storage)
- How to debug startup failures across a dependency chain

**New concept introduced:** Multi-service dependency management, storage architecture separation.

---

### Topic 4: Collection Lifecycle Management

**Qdrant lesson:** Collections are always ready after creation.

**Milvus lesson:** Students must learn the four-step lifecycle (create → index → load → search) and understand what fails if steps are skipped. This teaches:
- Why memory management matters at scale
- How to check collection load status
- How to reload a collection after a restart

**New concept introduced:** Explicit resource lifecycle in distributed systems.

---

### Topic 5: Metadata Filtering Syntax

**Qdrant lesson:** Filters are structured JSON objects:
```json
{"must": [{"key": "tags", "match": {"any": ["docker"]}}]}
```

**Milvus lesson:** Filters are boolean expression strings (SQL-like):
```python
expr='tags like \'%"docker"%\''
```

Students learn both approaches and can reason about trade-offs: structured vs. string-based filter languages, and how the choice affects query composition in code.

---

## 5. Troubleshooting: Milvus-Specific Issues

### Milvus won't start

Check etcd and MinIO first:

```bash
docker compose logs milvus-etcd --tail=50
docker compose logs milvus-minio --tail=50
```

### Collection not found after restart

Milvus persists collection metadata in etcd and data in MinIO. After restart, collections exist but are not loaded into memory. The `ensure_collection()` function handles this by calling `collection.load()` on every startup.

### Dimension mismatch error on insert

```
Error: collection field embedding has dim 768, but the provided vector has dim 384
```

Your embedding model changed. You must drop the collection (see Lesson 5 Step 3.2), fix `EMBEDDINGS_DIM` in `.env`, and re-ingest.

### "gRPC timeout" during search

The collection may not be loaded. Run:

```bash
docker exec -i ingestion-api python - <<'PY'
from pymilvus import connections, Collection
import os
connections.connect(host="milvus", port=19530)
Collection(os.getenv("MILVUS_COLLECTION", "LabDoc")).load()
print("Loaded")
PY
```

---

## 6. What Stays the Same

The following are **identical** between the Qdrant and Milvus versions:

- NGINX edge gateway and API key enforcement
- Ollama LLM and embedding service integration
- FastAPI endpoint structure (`/ingest`, `/chat`, `/health`, `/debug/*`)
- Gradio UI (it talks to NGINX — completely unaware of the DB backend)
- Security memory feature (same API, different store implementation)
- Prompt building and detail-level classification logic
- Docker Compose network segmentation (internal-only DB)
- `.env`-driven configuration pattern

This makes the two labs directly comparable. Students can run a side-by-side diff of `qdrant_client.py` vs `milvus_client.py` and see exactly what a vector DB swap entails at the code level.
