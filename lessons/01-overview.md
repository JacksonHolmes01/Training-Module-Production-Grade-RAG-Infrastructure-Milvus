# Lesson 01 — System Overview

> **Goal:** understand every service in the stack, what it does, and how data
> flows from a user's question to a grounded answer.

---

## The big picture

```
User
 │  HTTP + API-Key
 ▼
NGINX (edge proxy, port 8088)
 │  strips key, forwards internally
 ▼
ingestion-api (FastAPI, internal port 8000)
 ├── POST /ingest   → Ollama embed → Milvus insert
 └── POST /chat     → Ollama embed → Milvus search → Ollama generate
        ▲                                ▲
        │                                │
   Ollama (LLM +                  Milvus standalone
   embeddings, port 11434)        (vector DB, port 19530)
                                   etcd  (metadata)
                                   MinIO (object storage)
```

The **Gradio UI** (port 7860) is a thin browser client that calls NGINX just
like any other client.

---

## Service responsibilities

### NGINX
- Single entry point for all external traffic (port 8088).
- Validates the `X-API-Key` header; rejects requests with 401 if missing or
  wrong.
- Reverse-proxies validated requests to `ingestion-api:8000` on the internal
  Docker network.
- Never talks to Milvus directly.

### ingestion-api (FastAPI)
- Owns all business logic: ingestion, retrieval, prompt construction, and
  generation.
- Talks to **Ollama** for both embedding (nomic-embed-text) and generation
  (llama3.2 or your chosen model).
- Talks to **Milvus** via the `pymilvus` SDK (gRPC, port 19530).
- Exposes debug endpoints (`/debug/retrieve`, `/debug/prompt`,
  `/debug/ollama`) so you can inspect each pipeline stage independently.

### Milvus (three-container cluster)
Milvus is a purpose-built vector database. In this lab it runs in
*standalone* mode, which bundles all services but still requires three
containers:

| Container | Role |
|-----------|------|
| `milvus` | Query engine, HNSW index, gRPC API (port 19530) |
| `etcd` | Distributed metadata store (collection schemas, index configs) |
| `minio` | S3-compatible object storage (raw segment data) |

All three must be healthy before `ingestion-api` starts.

**Why three containers?** Milvus separates compute (the search engine), coordination (etcd), and storage (MinIO). This mirrors real production deployments and lets each layer scale independently.

### Ollama
- Runs large language models locally on CPU (or GPU if available).
- Serves two roles: embedding (`nomic-embed-text`) and text generation
  (e.g., `llama3.2:1b`).
- Models are pulled on demand and cached in a Docker volume (`ollama_data`).
- Port 11434 is **not** exposed to the host — only `ingestion-api` reaches it
  on the internal network.

### Gradio UI
- Browser-based chat interface served on port 7860.
- Sends requests to NGINX (including the API key), so it exercises the full
  security path.
- Shows source citations alongside each answer.

---

## Ports at a glance

| Service | Host port | Internal address | Who connects |
|---------|-----------|------------------|--------------|
| NGINX | **8088** | `nginx:80` | You, Gradio UI |
| Gradio | **7860** | `gradio:7860` | You (browser) |
| Milvus | *not exposed* | `milvus:19530` | ingestion-api only |
| Ollama | *not exposed* | `ollama:11434` | ingestion-api only |
| etcd | *not exposed* | `etcd:2379` | Milvus only |
| MinIO | *not exposed* | `minio:9000` | Milvus only |

Only NGINX and Gradio are reachable from your laptop. Everything else is
isolated on the `rag_internal` Docker network.

---

## Data flow: ingestion

1. You POST a document to `http://localhost:8088/ingest` with your API key.
2. NGINX validates the key and forwards to `ingestion-api:8000/ingest`.
3. `ingestion-api` calls Ollama (`nomic-embed-text`) to produce a 768-dim
   float vector.
4. The vector, text, and metadata are inserted into the `LabDoc` collection in
   Milvus via `pymilvus`.
5. Milvus writes the segment to MinIO and updates the HNSW index. etcd records
   the schema change.

## Data flow: RAG chat

1. You POST a question to `http://localhost:8088/chat`.
2. NGINX validates the key → `ingestion-api:8000/chat`.
3. The question is embedded with Ollama (`nomic-embed-text`).
4. `pymilvus` searches the `LabDoc` collection — HNSW cosine search returns
   the top-k most similar documents.
5. A prompt is constructed: `[system rules] + [retrieved context] + [question]`.
6. The prompt is sent to Ollama for generation (`llama3.2:1b` or your model).
7. The answer plus source metadata is returned to the caller.

---

## Milvus vs Qdrant — what changed architecturally

If you are familiar with the Qdrant version of this lab, the key differences are:

- **Protocol**: Qdrant uses REST (HTTP). Milvus uses gRPC via the `pymilvus`
  SDK — there is no curl-friendly HTTP API for data operations.
- **Schema**: Qdrant is schemaless. Milvus requires a typed schema
  (VARCHAR, INT64, FLOAT_VECTOR) defined before any data is inserted.
- **Collection lifecycle**: Milvus collections must be **created → indexed →
  loaded** before you can search. Missing the load step causes silent failures.
- **Infrastructure footprint**: Qdrant is a single container. Milvus requires
  three (`milvus`, `etcd`, `minio`).
- **Startup time**: Expect 60–90 seconds for the Milvus cluster to become
  healthy, vs ~5 seconds for Qdrant.

See `ARCHITECTURE-DELTA.md` for a full side-by-side comparison.

---

## Checkpoint

You should now be able to answer:
- What does NGINX do, and why is it between the user and the API?
- Why does Milvus need three containers?
- What is the difference between the ingestion and chat data flows?
- Which ports are exposed to your laptop, and why are the others hidden?

Continue to **[Lesson 02 — Setup](02-setup.md)**.
