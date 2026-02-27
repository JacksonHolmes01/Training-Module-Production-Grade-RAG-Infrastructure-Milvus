# Lesson 06 — Document Ingestion

> **Goal:** ingest documents through the API, verify they are stored in
> Milvus, and test retrieval before enabling the full RAG pipeline.

---

## How ingestion works

```
POST /ingest  (your curl or script)
      │
      ▼
ingestion-api validates request body (FastAPI schema)
      │
      ▼
Ollama: text → 768-dim float vector (nomic-embed-text)
      │
      ▼
pymilvus: insert row into LabDoc collection
  • id (INT64, hash of UUID)
  • embedding (FLOAT_VECTOR[768])
  • text (VARCHAR)
  • title, url, source, published_date, tags (VARCHAR)
      │
      ▼
Milvus: flush segment to MinIO, update HNSW index
```

---

## 1) Load your API key

```bash
EDGE_API_KEY=$(grep -E '^EDGE_API_KEY=' .env | cut -d= -f2-)
```

---

## 2) Ingest a single document

```bash
curl -s -X POST http://localhost:8088/ingest \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $EDGE_API_KEY" \
  -d '{
    "text": "Docker containers package an application and its dependencies into an isolated unit. Each container shares the host OS kernel but has its own filesystem and network namespace.",
    "title": "Docker Fundamentals",
    "url": "https://docs.docker.com/get-started/",
    "source": "Docker docs",
    "tags": ["docker", "containers", "fundamentals"]
  }' | python3 -m json.tool
```

Expected response:

```json
{
  "status": "ok",
  "milvus": {
    "insert_count": 1,
    "ids": [3894729183746251234]
  }
}
```

`ids` contains the INT64 primary key assigned by Milvus.

---

## 3) Ingest a small batch (sample dataset)

Save this as `/tmp/sample_docs.sh` and run it:

```bash
#!/usr/bin/env bash
EDGE_API_KEY=$(grep -E '^EDGE_API_KEY=' .env | cut -d= -f2-)
BASE="http://localhost:8088"

ingest() {
  curl -s -X POST "$BASE/ingest" \
    -H "Content-Type: application/json" \
    -H "X-API-Key: $EDGE_API_KEY" \
    -d "$1" | python3 -m json.tool
}

ingest '{
  "text": "Kubernetes orchestrates containerised workloads. A Pod is the smallest deployable unit and can contain one or more containers sharing the same network namespace.",
  "title": "Kubernetes Pods",
  "url": "https://kubernetes.io/docs/concepts/workloads/pods/",
  "source": "Kubernetes docs",
  "tags": ["kubernetes", "pods", "orchestration"]
}'

ingest '{
  "text": "NGINX is a high-performance web server and reverse proxy. It can terminate TLS, enforce rate limits, and route traffic to upstream services based on path or host.",
  "title": "NGINX Overview",
  "url": "https://nginx.org/en/docs/",
  "source": "nginx.org",
  "tags": ["nginx", "proxy", "webserver"]
}'

ingest '{
  "text": "The OWASP API Security Top 10 lists the most critical API vulnerabilities. Broken Object Level Authorization (BOLA) is consistently ranked first because APIs frequently expose endpoints that handle object identifiers without proper access control.",
  "title": "OWASP API Security Top 10",
  "url": "https://owasp.org/API-Security/",
  "source": "OWASP",
  "tags": ["security", "owasp", "api"]
}'

ingest '{
  "text": "Vector databases store high-dimensional float vectors alongside metadata. They support approximate nearest-neighbour (ANN) search, which finds semantically similar items without comparing every stored vector.",
  "title": "Vector Databases Explained",
  "url": "https://zilliz.com/learn/vector-database",
  "source": "Zilliz",
  "tags": ["milvus", "vector-db", "embeddings"]
}'
```

```bash
bash /tmp/sample_docs.sh
```

---

## 4) Verify documents are in Milvus

Use the Python SDK to count and inspect stored rows:

```bash
docker exec ingestion-api python3 -c "
from pymilvus import Collection, connections
connections.connect(host='milvus', port='19530')
col = Collection('LabDoc')
col.load()
print('Row count:', col.num_entities)

# Query first 3 entries (no vectors, just text fields)
res = col.query(
    expr='id > 0',
    output_fields=['title', 'source', 'tags'],
    limit=3,
)
for r in res:
    print(r)
"
```

---

## 5) Test retrieval without generation

The `/debug/retrieve` endpoint runs the embed+search step and returns the raw
results before any prompt is built:

```bash
curl -s -X POST http://localhost:8088/debug/retrieve \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $EDGE_API_KEY" \
  -d '{"query": "what is a Kubernetes pod?", "k": 3}' \
  | python3 -m json.tool
```

You should see the top-3 most relevant documents with their cosine similarity
scores (higher = more similar):

```json
[
  {
    "title": "Kubernetes Pods",
    "score": 0.91,
    "snippet": "Kubernetes orchestrates containerised workloads..."
  },
  ...
]
```

---

## 6) Common ingestion errors

### 422 Unprocessable Entity

FastAPI rejected the request body. Run the curl with `-v` to see the
validation error:

```bash
curl -v -X POST http://localhost:8088/ingest \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $EDGE_API_KEY" \
  -d '{"text": ""}'
```

`text` must be non-empty. `title`, `url`, `source`, and `tags` are optional
but must be correct types if provided (`tags` must be a JSON array).

### `milvus insert failed: collection not loaded`

The collection exists but was not loaded into memory before the insert. This
can happen if ingestion-api restarted mid-flight. Fix:

```bash
docker compose restart ingestion-api
```

`ingestion-api` runs `ensure_collection()` on startup, which creates → indexes
→ loads the collection.

### Embedding error / Ollama timeout

If Ollama is still starting or the embedding model is not ready:

```bash
docker compose logs ollama | tail -20
```

Wait for Ollama to finish initialising and retry.

---

## 7) Clearing all data

To reset the collection (delete all vectors):

```bash
docker exec ingestion-api python3 -c "
from pymilvus import Collection, connections, utility
connections.connect(host='milvus', port='19530')
if utility.has_collection('LabDoc'):
    Collection('LabDoc').drop()
    print('Collection dropped.')
"
```

Then restart ingestion-api to recreate it:

```bash
docker compose restart ingestion-api
```

---

## Checkpoint

You are ready to move on when:
- `/ingest` returns `"status": "ok"` for each document.
- `col.num_entities` shows the expected row count in Milvus.
- `/debug/retrieve` returns relevant results for a test query.

Continue to **[Lesson 07 — The RAG Pipeline](07-rag-pipeline.md)**.
