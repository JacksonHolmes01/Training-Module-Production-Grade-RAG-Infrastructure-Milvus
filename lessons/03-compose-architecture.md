# Lesson 03 — Docker Compose Architecture

> **Goal:** understand every section of `docker-compose.yml` — why each
> service is defined the way it is and what would break if you changed it.

---

## File structure at a glance

```yaml
services:
  etcd          # Milvus metadata coordination
  minio         # Milvus object storage
  milvus        # Vector database (depends on etcd + minio)
  ingestion-api # FastAPI app (depends on milvus)
  nginx         # Edge proxy (depends on ingestion-api)
  ollama        # LLM + embeddings
  gradio        # Browser UI

networks:
  rag_internal  # Private network — all services

volumes:
  milvus_data   # Milvus segment files (inside MinIO)
  etcd_data     # etcd WAL and snapshots
  minio_data    # MinIO buckets
  ollama_data   # Downloaded LLM weights
```

---

## The Milvus cluster (three services)

Milvus in standalone mode is not a single binary — it delegates two concerns
to purpose-built tools:

### `etcd`
Distributed key-value store that Milvus uses to track:
- Collection schemas (field names, types, dimensions)
- Segment metadata (which segments exist, their IDs)
- Index configurations

```yaml
etcd:
  image: quay.io/coreos/etcd:v3.5.5
  environment:
    ETCD_AUTO_COMPACTION_MODE: revision
    ETCD_AUTO_COMPACTION_RETENTION: "1000"
    ETCD_QUOTA_BACKEND_BYTES: "4294967296"   # 4 GB
  volumes:
    - etcd_data:/etcd
  mem_limit: 512m
```

**Why compaction settings?** etcd stores every revision of every key. Without
compaction it grows unboundedly. `revision` mode compacts when the revision
count exceeds 1000.

### `minio`
S3-compatible object storage that holds the actual segment data — the raw
float vectors and scalar fields written to disk.

```yaml
minio:
  image: minio/minio:RELEASE.2023-03-20T20-16-18Z
  environment:
    MINIO_ACCESS_KEY: minioadmin
    MINIO_SECRET_KEY: minioadmin
  command: minio server /minio_data
  volumes:
    - minio_data:/minio_data
  mem_limit: 1g
```

> **Production note:** change `MINIO_ACCESS_KEY` and `MINIO_SECRET_KEY` to
> secrets before any real deployment.

### `milvus`
The query engine. Depends on both etcd and minio being healthy before it starts.

```yaml
milvus:
  image: milvusdb/milvus:v2.4.6
  command: ["milvus", "run", "standalone"]
  environment:
    ETCD_ENDPOINTS: etcd:2379
    MINIO_ADDRESS: minio:9000
  depends_on:
    etcd:
      condition: service_healthy
    minio:
      condition: service_started
  volumes:
    - milvus_data:/var/lib/milvus
  mem_limit: 8g
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:9091/healthz"]
    interval: 15s
    timeout: 10s
    retries: 10
    start_period: 90s
  ports: []   # intentionally NOT exposed to host
```

**`start_period: 90s`** gives Milvus time to connect to etcd and MinIO before
health checks start counting failures. On slower machines you may need to
increase this to 120s.

**No host port mapping** — Milvus is only reachable from other containers on
`rag_internal`. This is intentional: gRPC on 19530 should never be directly
accessible from the internet.

---

## `ingestion-api`

```yaml
ingestion-api:
  build: ./ingestion-api
  env_file: .env
  depends_on:
    milvus:
      condition: service_healthy
  networks:
    - rag_internal
  mem_limit: 2g
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
    interval: 10s
    retries: 5
    start_period: 30s
```

- `env_file: .env` injects all your `.env` variables as environment variables.
- `depends_on: milvus: condition: service_healthy` means Docker will not start
  `ingestion-api` until Milvus passes its own health check.
- No `ports` — traffic must flow through NGINX.

---

## `nginx`

```yaml
nginx:
  image: nginx:1.25-alpine
  ports:
    - "8088:80"
  volumes:
    - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
  depends_on:
    - ingestion-api
  networks:
    - rag_internal
```

The only service (besides Gradio) with a host port binding. Everything you
send to `localhost:8088` hits NGINX first.

---

## `ollama`

```yaml
ollama:
  image: ollama/ollama:latest
  volumes:
    - ollama_data:/root/.ollama
  networks:
    - rag_internal
  mem_limit: 8g
  # GPU passthrough (optional):
  # deploy:
  #   resources:
  #     reservations:
  #       devices:
  #         - capabilities: [gpu]
```

Models are stored in the `ollama_data` volume so they survive `docker compose
down` (without `-v`).

---

## `gradio`

```yaml
gradio:
  build: ./gradio
  ports:
    - "7860:7860"
  environment:
    API_BASE: http://nginx:80
    EDGE_API_KEY: ${EDGE_API_KEY}
  depends_on:
    - nginx
  networks:
    - rag_internal
```

Gradio reads `EDGE_API_KEY` from the environment (which comes from `.env`) and
injects it into every request to NGINX. The `API_BASE` uses the internal
hostname `nginx:80`, not `localhost:8088`.

---

## Networks

```yaml
networks:
  rag_internal:
    driver: bridge
```

A single internal bridge network. Every service joins it. This means:
- Services resolve each other by name (`milvus`, `ollama`, `ingestion-api`).
- No service is reachable from the host unless it explicitly maps a port.
- Milvus, etcd, MinIO, and Ollama have zero host exposure.

---

## Volumes

| Volume | What it stores | Lost if removed |
|--------|---------------|-----------------|
| `milvus_data` | Milvus write-ahead log + local cache | Index rebuild needed |
| `etcd_data` | Collection schemas, segment metadata | Milvus cannot start |
| `minio_data` | Raw vector segments | All indexed data lost |
| `ollama_data` | Downloaded model weights | Re-download required |

> `docker compose down -v` removes all volumes. Use it only for a true reset.
> `docker compose down` (no `-v`) keeps data between restarts.

---

## Resource limits

| Service | `mem_limit` | Why |
|---------|-------------|-----|
| `milvus` | 8 GB | Loads HNSW index into RAM for search |
| `ollama` | 8 GB | LLM inference is memory-bound |
| `ingestion-api` | 2 GB | FastAPI + pymilvus client |
| `etcd` | 512 MB | Metadata only, low footprint |
| `minio` | 1 GB | Disk I/O, not memory-bound |

Reduce `milvus` and `ollama` limits if your machine has less than 16 GB
available to Docker, but expect slower search and generation.

---

## Dependency chain

```
etcd  ──┐
         ├──▶  milvus  ──▶  ingestion-api  ──▶  nginx  ──▶  (you)
minio ──┘
```

Docker Compose respects `depends_on` with `condition: service_healthy`, so
the chain enforces correct startup order automatically.

---

## Checkpoint

You should now understand:
- Why Milvus needs three containers and what each one stores.
- Why no internal services expose host ports.
- What `depends_on: condition: service_healthy` does.
- Which volumes hold critical data and what you lose if you delete them.

Continue to **[Lesson 04 — NGINX Auth](04-nginx-auth.md)**.
