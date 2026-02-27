# Production-Grade RAG Infrastructure — Milvus Edition

This lab teaches you to build, run, and understand a production-quality
Retrieval-Augmented Generation (RAG) system using **Milvus** as the vector
database. Every service runs locally inside Docker; nothing requires a cloud
account.

---

## Lessons

| # | File | What you learn |
|---|------|----------------|
| 01 | [01-overview.md](01-overview.md) | System architecture, service responsibilities, data flow |
| 02 | [02-setup.md](02-setup.md) | First boot, `.env` config, health checks |
| 03 | [03-compose-architecture.md](03-compose-architecture.md) | Docker Compose deep-dive: networks, volumes, resource limits |
| 04 | [04-nginx-auth.md](04-nginx-auth.md) | NGINX edge proxy, API-key enforcement, defence in depth |
| 05 | [05-milvus-schema-and-vectorization.md](05-milvus-schema-and-vectorization.md) | Milvus collection lifecycle, typed schema, HNSW indexing |
| 06 | [06-ingestion.md](06-ingestion.md) | Ingest documents via the API, verify storage, test retrieval |
| 07 | [07-rag-pipeline.md](07-rag-pipeline.md) | Pull an Ollama model, trace the RAG pipeline, tune `RAG_TOP_K` |
| 08 | [08-gradio-ui.md](08-gradio-ui.md) | Use the Gradio chat UI, read source citations, debug the stack |
| 09 | [09-operations.md](09-operations.md) | Health endpoints, log inspection, failure drills, reset procedure |
| 10 | [10-conclusion.md](10-conclusion.md) | Architecture review, production gap analysis, next steps |

### Security-Memory sub-module

| # | File | What you learn |
|---|------|----------------|
| 4.1 | [04-security-memory/01-corpus-ingestion.md](04-security-memory/01-corpus-ingestion.md) | Build a security-standards corpus in a separate Milvus collection |
| 4.2 | [04-security-memory/02-api-tool.md](04-security-memory/02-api-tool.md) | Expose `/memory/query` as an authenticated API tool |
| 4.3 | [04-security-memory/03-ide-integration.md](04-security-memory/03-ide-integration.md) | Use the memory API for grounded security reviews in VS Code / Cursor |

---

## Quick orientation

```
milvus-rag/
├── docker-compose.yml          # All services (NGINX, ingestion-api, Milvus cluster, Ollama, Gradio)
├── .env                        # Secrets and tuning knobs — never commit this
├── ingestion-api/
│   ├── app/
│   │   ├── main.py             # FastAPI routes
│   │   ├── milvus_client.py    # Milvus connection, schema, collection lifecycle
│   │   ├── rag.py              # Retrieval + prompt building + Ollama generation
│   │   ├── embeddings.py       # text → vector (Ollama nomic-embed-text)
│   │   └── security_memory/    # Security-memory sub-module
│   └── requirements.txt
├── lessons/                    # You are here
└── ARCHITECTURE-DELTA.md       # Side-by-side Qdrant → Milvus comparison
```

Start with **Lesson 01** for the big picture, or jump straight to **Lesson 02**
if you want to get the stack running first.
