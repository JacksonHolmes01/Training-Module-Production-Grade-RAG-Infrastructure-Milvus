# Lab 1 — Production-Grade RAG Infrastructure (Milvus Edition)

This is the **Milvus version** of Lab 1. It is architecturally identical to the Qdrant version except the vector database has been replaced with **Milvus standalone**.

If you are comparing the two labs, see [ARCHITECTURE-DELTA.md](ARCHITECTURE-DELTA.md).

---

# What You Will Build

By the end of this lab, you will have:

- A private vector database (**Milvus**, backed by etcd + MinIO)
- A validated ingestion API (FastAPI)
- A local LLM (Ollama) generating grounded answers
- An authentication gateway (NGINX)
- A browser-based chat UI (Gradio)
- A cybersecurity-focused dataset powering retrieval

---

# System Components

## Milvus — Vector Database

Milvus stores:
- **Vector fields** — numeric embeddings for semantic similarity
- **Scalar fields** — structured metadata (title, source, tags, etc.)
- **Segments** — the physical data files stored in MinIO

Milvus requires a typed schema defined upfront. Unlike Qdrant's schemaless payload model, you must declare every field before ingesting data.

Milvus also depends on two supporting services:
- **etcd** — stores collection schemas and cluster metadata
- **MinIO** — stores segment files (persistent object storage, S3-compatible)

Milvus is internal-only. It is never exposed to the host machine.

---

## FastAPI — Application Layer

FastAPI is the core logic layer. It handles ingestion, retrieval, and generation.

The key file replacing `qdrant_client.py` is `milvus_client.py`. It uses the `pymilvus` SDK over gRPC (port 19530) instead of raw HTTP REST calls.

---

## Ollama — Local Language Model

Unchanged from the Qdrant version. Ollama runs a local LLM and embedding model inside Docker.

---

## NGINX — Edge Gateway

Unchanged. NGINX enforces API key authentication at the network boundary.

---

## Gradio — Browser UI

Unchanged. Gradio communicates with NGINX → FastAPI and has no knowledge of the vector DB backend.

---

# Quick Start

## 1. Prerequisites

- Docker + Docker Compose v2
- 16GB+ RAM recommended (Milvus standalone + Ollama)
- At least 20GB free disk (Milvus + Ollama models)

## 2. Setup

```bash
cp .env.example .env
# Edit .env — set EDGE_API_KEY to a long random string
nano .env
```

## 3. Start Services

```bash
docker compose up -d
```

Milvus takes 60–90 seconds to be healthy because it waits for etcd and MinIO.

Monitor startup:
```bash
docker compose ps
docker compose logs milvus --tail=50
```

## 4. Pull Ollama Models

```bash
# Pull LLM
docker exec -i ollama ollama pull llama3.2:1b

# Pull embedding model
docker exec -i ollama ollama pull nomic-embed-text
```

## 5. Ingest Sample Data

```bash
EDGE_API_KEY=$(grep -E '^EDGE_API_KEY=' .env | cut -d= -f2-)

while IFS= read -r line; do
  [[ -z "$line" ]] && continue
  curl -s -X POST "http://localhost:8088/ingest" \
    -H "Content-Type: application/json" \
    -H "X-API-Key: $EDGE_API_KEY" \
    -d "$line" | python -m json.tool
done < data/sample_articles.jsonl
```

## 6. Ingest Security Memory

```bash
docker exec -i ingestion-api python -m app.security_memory.ingest
```

## 7. Open the UI

Navigate to: http://localhost:7860

---

# Verify the System

```bash
EDGE_API_KEY=$(grep -E '^EDGE_API_KEY=' .env | cut -d= -f2-)

# Health
curl -s http://localhost:8088/health | python -m json.tool

# Test retrieval
curl -sS -G "http://localhost:8088/debug/retrieve" \
  -H "X-API-Key: $EDGE_API_KEY" \
  --data-urlencode "q=network security best practices" | python -m json.tool

# Full chat
curl -s -X POST "http://localhost:8088/chat" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $EDGE_API_KEY" \
  -d '{"message": "What are the key principles of network segmentation?"}' \
  | python -m json.tool
```

---

# Lessons

Go to [lessons/00-lesson-index.md](lessons/00-lesson-index.md) and work through the lessons in order.

The most important lesson for the Milvus migration is [Lesson 5](lessons/05-milvus-schema-and-vectorization.md), which explains the schema model and collection lifecycle in detail.
