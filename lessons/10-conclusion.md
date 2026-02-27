# Lesson 10 — Conclusion

> **Goal:** review the full architecture, understand the production gaps, and
> know what you would change before putting this in front of real users.

---

## Architecture review

You have built a seven-service RAG stack that demonstrates real production
patterns:

```
Browser / curl
      │
      ▼
  NGINX :8088          ← single entry point, API-key enforcement
      │
      ▼
ingestion-api          ← all business logic; no direct external access
   ├── /ingest         →  embed (Ollama)  →  write (Milvus)
   ├── /chat           →  embed + search (Milvus)  →  generate (Ollama)
   └── /debug/*        →  staged pipeline inspection
      │            │
      ▼            ▼
   Milvus        Ollama
  (3 containers) (1 container)
  etcd / minio   nomic-embed-text
                 llama3.2:1b
```

---

## Data flow layers

| Layer | Technology | Responsibility |
|-------|-----------|----------------|
| Edge | NGINX | Auth, routing, TLS termination (TLS not configured here) |
| Application | FastAPI | Validation, orchestration, business logic |
| Embedding | Ollama (nomic-embed-text) | text → float vector |
| Storage | Milvus (standalone) | ANN search, HNSW index |
| Metadata | etcd | Collection schemas, segment catalog |
| Object storage | MinIO | Raw segment data (the actual vectors) |
| Generation | Ollama (llama3.2:1b) | prompt → answer |

---

## Security controls you implemented

| Control | Where | What it does |
|---------|-------|--------------|
| API-key auth | NGINX | Rejects unauthenticated requests at the edge |
| Network isolation | Docker bridge `rag_internal` | Milvus/Ollama unreachable from host |
| Header stripping | NGINX `proxy_hide_header` | Key not logged by the application |
| No root processes | Container defaults | Reduces blast radius of a compromise |
| Secret in `.env` | Not hardcoded | Key not committed to git |

---

## Performance tradeoffs

### HNSW index

- **Pros:** very fast queries (milliseconds), high recall at reasonable ef values.
- **Cons:** entire index loaded into RAM; memory grows with collection size.
- **Tuning:** increase `ef` in search params for higher recall; decrease for
  lower latency.

### Flat (exact) search alternative

Set `index_type: "FLAT"` in `milvus_client.py` for exact nearest-neighbour.
Higher recall but O(n) scan — impractical for > ~100K vectors.

### Ollama on CPU

- Embedding (`nomic-embed-text`): ~100–300 ms per batch on CPU.
- Generation (`llama3.2:1b`): 10–60 seconds on CPU depending on prompt length.
- GPU passthrough (uncomment in `docker-compose.yml`) drops generation to 2–5s.

---

## Known failure modes

| Failure | Symptom | Recovery |
|---------|---------|----------|
| Milvus OOM | Container restart loop | Increase `mem_limit`, add RAM |
| etcd unavailable | New schema ops fail | Restart etcd then milvus |
| MinIO corruption | Segment load errors | Full reset with `down -v` |
| Ollama timeout | 500 on `/chat` | Restart ollama, re-pull model |
| Collection not loaded | Empty search results | Restart ingestion-api |
| API key rotation missed | 401 from Gradio | `docker compose restart gradio` |

---

## What you would change before production

This lab is intentionally educational. Before deploying to real users:

**Authentication**
- Replace static API key with JWT or OAuth 2.0.
- Rotate keys automatically.
- Add per-user rate limiting at NGINX.

**TLS**
- Configure NGINX with a real certificate (Let's Encrypt or internal CA).
- All external traffic should be HTTPS.

**Milvus**
- Switch from standalone to distributed cluster for horizontal scaling.
- Back MinIO with persistent cloud storage (S3, GCS).
- Enable Milvus authentication (user/password or RBAC).

**Observability**
- Add structured logging with trace IDs.
- Metrics (Prometheus + Grafana).
- Alerting on `milvus_ok: false`.

**Embeddings**
- Move embeddings to a dedicated service with autoscaling.
- Pin the embedding model version — changing it invalidates the entire index.

**Secrets management**
- Replace `.env` with Vault, AWS Secrets Manager, or Kubernetes Secrets.
- Never store secrets in Docker environment variables in production.

---

## What you learned

By completing this lab, you have:

- Built a complete RAG pipeline from scratch, locally, without cloud services.
- Learned how Milvus separates compute (query engine), coordination (etcd),
  and storage (MinIO) — and why.
- Practised the Milvus collection lifecycle: create → index → load → search.
- Used NGINX as an authenticated edge proxy — the same pattern used in
  production API gateways.
- Traced a RAG pipeline stage-by-stage using debug endpoints.
- Run failure drills and recovered cleanly.
- Built a grounded security-memory tool using a separate Milvus collection.

---

## Next steps

- Complete the **Security Memory sub-module** (Lessons 4.1–4.3) to build a
  domain-specific memory for security standards.
- Try replacing `llama3.2:1b` with a larger model (`mistral:7b`,
  `llama3.1:8b`) and observe the quality difference.
- Add a new collection for a different domain (legal references, API docs)
  and build a second retrieval endpoint.
- Read `ARCHITECTURE-DELTA.md` to understand every specific change made from
  the Qdrant version.

---

*You have completed the core lab. Well done.*
