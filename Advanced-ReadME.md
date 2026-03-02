# Advanced Topics — Milvus RAG Lab

This document covers topics beyond the core lab: performance tuning, scaling, index selection, production hardening, and the architectural decisions made in this repo. Read this after completing all lessons.

---

## Table of Contents

1. Why Milvus instead of a simpler vector database
2. The three-service cluster: etcd, MinIO, and Milvus
3. Understanding Milvus collections and schemas
4. Index types: HNSW vs IVF_FLAT vs FLAT
5. Distance metrics: cosine vs L2 vs IP
6. Scaling and production considerations
7. Security hardening checklist
8. Performance tuning
9. Observability and monitoring
10. Extending the lab

---

## 1. Why Milvus Instead of a Simpler Vector Database

Qdrant and Weaviate can be run as a single container. Milvus requires three services: etcd for metadata, MinIO for object storage, and Milvus itself. That complexity is a deliberate educational choice.

Milvus reflects how large-scale vector search is actually deployed in production. When you need to store hundreds of millions of vectors, run multiple search replicas, and persist data reliably across restarts, the separation of concerns between metadata (etcd), storage (MinIO), and compute (Milvus) becomes critical. Understanding why each layer exists makes you a better systems engineer even if you eventually use a simpler database for smaller workloads.

The key trade-off: Milvus has higher operational complexity and resource requirements, but it offers stronger production semantics — typed schemas, explicit indexing, columnar insert, and a mature gRPC API.

---

## 2. The Three-Service Cluster: etcd, MinIO, and Milvus

### etcd

etcd is a distributed key-value store used as the metadata backbone of Milvus. It stores:
- Collection schemas (field names, types, dimensions)
- Index configurations
- Segment metadata (which segments exist, their state)
- Cluster membership and routing information

If etcd goes down, Milvus loses its schema definitions and cannot process requests. etcd must be healthy before Milvus starts.

### MinIO

MinIO is an S3-compatible object storage service. Milvus uses it to store segment files — the actual binary data for your collections. When you call `collection.flush()`, Milvus writes segment files to MinIO. When Milvus restarts, it reads segment files from MinIO to restore the collection state.

If MinIO goes down, Milvus can still serve queries from in-memory data, but new data cannot be flushed to persistent storage and restarts will lose un-flushed data.

### Milvus standalone

Milvus standalone is the single-node mode used in this lab. It bundles the proxy, query node, data node, and index node into one process, making it suitable for development and small deployments. A production deployment would run these as separate services.

---

## 3. Understanding Milvus Collections and Schemas

A collection in Milvus is roughly equivalent to a table in a relational database. Unlike Qdrant's schemaless payload model or Weaviate's flexible property definitions, **Milvus requires a fully typed schema defined upfront**. You cannot add fields to a collection after it is created.

Every collection must have:
- Exactly one primary key field (INT64 with `auto_id=True`, or a user-managed primary key)
- Exactly one vector field (`FLOAT_VECTOR` with a fixed dimension)
- Any number of scalar fields (`VARCHAR`, `INT64`, `FLOAT`, `BOOL`, etc.)

The dimension of the vector field must match the embedding model you use. In this lab, `nomic-embed-text` produces 768-dimensional vectors, so all collections use `dim=768`. If you switch to a different embedding model, you must drop and recreate the collection.

### Schema design decisions in this lab

The `LabDoc` collection uses:
- `embedding: FLOAT_VECTOR[768]` for semantic search
- `text`, `title`, `url`, `source`, `published_date` as `VARCHAR` scalar fields

The `ExpandedVSCodeMemory` collection adds:
- `tags: VARCHAR[2048]` — a JSON-encoded list stored as a string
- `chunk_index: INT64` — position of the chunk in the original document
- `doc_path: VARCHAR[2048]` — relative path to the source file

Tags are stored as a JSON string rather than a native array because Milvus `VARCHAR` fields have straightforward `LIKE` filtering, making tag queries simple to implement without requiring a more complex data type.

---

## 4. Index Types: HNSW vs IVF_FLAT vs FLAT

Milvus requires you to explicitly create an index on the vector field. The index type affects search speed and memory usage.

### HNSW (Hierarchical Navigable Small World)

Used in this lab. HNSW builds a multi-layer graph where each node is connected to its nearest neighbors. Search traverses the graph from a coarse layer down to a fine layer, finding approximate nearest neighbors quickly.

Parameters:
- `M`: number of bidirectional links per node (higher = better recall, more memory)
- `efConstruction`: size of the dynamic candidate list during construction (higher = better index quality, slower build)
- `ef` at query time: size of the dynamic candidate list during search (higher = better recall, slower query)

This lab uses `M=16, efConstruction=200` which is a reasonable default for a development corpus.

### IVF_FLAT (Inverted File with Flat Storage)

Clusters vectors into `nlist` partitions using k-means. Search first finds the closest `nprobe` cluster centroids, then searches those clusters with exact comparison. Faster than FLAT for large collections, less accurate than HNSW for the same memory budget.

### FLAT

Brute-force exact search. Guarantees 100% recall but scales poorly. Only practical for very small collections (fewer than ~10,000 vectors). Good for testing whether your results are correct before switching to an approximate index.

**Which to use:** HNSW is the best default for most workloads in this lab. Switch to IVF_FLAT if your collection grows very large (millions of vectors) and memory is constrained.

---

## 5. Distance Metrics: Cosine vs L2 vs IP

Milvus supports three distance metrics. The choice must match how your embeddings are trained.

**Cosine similarity** measures the angle between two vectors. It is invariant to vector magnitude, making it ideal for text embeddings where the direction of the vector encodes semantic meaning, not its length. This lab uses `COSINE` for both collections. Milvus returns cosine distance (0 = identical, 2 = opposite), which `store.py` converts to a similarity score via `1.0 - distance`.

**L2 (Euclidean distance)** measures the straight-line distance between two points. It is sensitive to vector magnitude. Use L2 when your embeddings are normalized or when magnitude carries meaning.

**IP (Inner Product)** computes the dot product. When vectors are normalized to unit length, IP equals cosine similarity. Use IP when your model is trained with a max-inner-product objective (e.g., some recommendation models).

**The important rule:** the distance metric in the index must match the metric used during training of the embedding model. `nomic-embed-text` is trained with cosine similarity, so `COSINE` is the correct choice.

---

## 6. Scaling and Production Considerations

The lab runs Milvus standalone with all components in one process. A production deployment separates these concerns.

### Milvus cluster mode

In cluster mode, Milvus splits into independent services:
- **Proxy**: handles client connections and request routing
- **Query nodes**: serve search and retrieval requests from in-memory data
- **Data nodes**: handle ingestion, flush, and compaction
- **Index nodes**: build indexes asynchronously

This separation allows you to scale query capacity independently of ingestion capacity. For read-heavy workloads, add more query nodes. For write-heavy workloads, add more data nodes.

### etcd in production

In production, etcd should run as a 3-node or 5-node cluster for fault tolerance. A single etcd node is a single point of failure — if it goes down, Milvus loses its metadata store and cannot process requests.

### MinIO in production

In production, MinIO should run in distributed mode across multiple nodes with erasure coding for data durability. The single-node MinIO in this lab is appropriate for development only.

### Resource sizing

A rule of thumb for Milvus:
- Load index + raw vectors into memory: ~2x the raw vector data size
- For 1 million 768-dimensional float32 vectors: ~3 GB raw + ~6 GB with HNSW index
- Add overhead for the Milvus process itself: ~1–2 GB

---

## 7. Security Hardening Checklist

The lab makes several choices that are appropriate for local development but would need to change in production.

**MinIO credentials:** The lab uses `minioadmin/minioadmin`. In production, use long random credentials stored in a secrets manager.

**Milvus authentication:** The lab runs without Milvus authentication. Milvus supports username/password authentication via `COMMON_SECURITY_AUTHORIZATIONENABLED`. Enable this in production.

**etcd encryption:** etcd supports TLS encryption for client connections. The lab uses unencrypted connections. In production, enable TLS for etcd client and peer connections.

**Network exposure:** Milvus gRPC (19530), etcd (2379), and MinIO (9000) are all internal-only in this lab. In production, these should never be exposed to the public internet.

**NGINX API key length:** The `EDGE_API_KEY` should be at least 32 random bytes (64 hex characters). The `.env.example` shows how to generate one with `openssl rand -hex 32`.

---

## 8. Performance Tuning

### Ingestion throughput

The bottleneck in this lab is Ollama embedding speed — embeddings are generated one chunk at a time. Options to improve throughput:

- Increase the batch size in `ingest.py` if you have enough Ollama memory headroom
- Run a dedicated embedding model server (TEI or vLLM) instead of Ollama for parallel embedding
- Pre-compute embeddings offline and load them directly into Milvus

### Query latency

If search latency is too high:
- Increase `ef` in the HNSW search params (better recall at the cost of speed)
- Reduce `top_k` if you do not need many results
- Ensure the collection is loaded into memory (`collection.load()`) — an unloaded collection will load on first query, causing high initial latency
- Add a warm-up query on startup to pre-load the index

### Memory management

Milvus loads collections into memory when `collection.load()` is called. In this lab, collections are loaded on every query. For a production service, load once at startup and keep the collection in memory throughout the service lifetime.

---

## 9. Observability and Monitoring

### Container-level monitoring

```bash
docker stats
```

Watch for:
- Milvus memory usage growing during ingestion (normal)
- Ollama memory spiking during first model load (normal)
- Any container hitting its `mem_limit` and restarting

### Application-level health

```bash
EDGE_API_KEY=$(grep -E '^EDGE_API_KEY=' .env | cut -d= -f2-)
curl -s http://localhost:8088/health -H "X-API-Key: $EDGE_API_KEY" | python -m json.tool
```

The `/health` endpoint reports `milvus_ok` (whether the gRPC connection to Milvus is healthy), uptime, and request counts.

### Milvus metrics

Milvus exposes Prometheus metrics on port 9091 at `/metrics`. If you add a Prometheus + Grafana stack to your `docker-compose.yml`, you can visualize query latency, throughput, memory usage, and segment statistics.

### Log aggregation

All services write to stdout, which Docker captures. For a persistent log trail:

```bash
docker compose logs --since 1h > debug.log
```

---

## 10. Extending the Lab

### Adding new security documents

Add `.md` or `.txt` files under `security-memory/data/` in the appropriate subfolder, then re-run ingestion:

```bash
docker exec -i ingestion-api python -m app.security_memory.ingest
```

The ingestor will add new chunks. Note that Milvus does not support true upsert by content hash — re-running ingestion will add duplicate chunks if the file already exists. To avoid duplicates, drop and recreate the collection before re-ingesting.

### Adding a new scalar field to the schema

1. Add the new `FieldSchema` to the schema definition in both `store.py` and `ingest.py`
2. Drop the existing collection
3. Re-run ingestion

Milvus does not support schema migration on existing collections.

### Switching embedding models

1. Pull the new model: `docker exec -it ollama ollama pull <model-name>`
2. Update `SECURITY_EMBED_MODEL` and `SECURITY_EMBED_DIM` in your `.env`
3. Drop and recreate the collection (different models produce incompatible vector spaces)
4. Re-run ingestion

### Adding a reranker

After retrieval, you can add a cross-encoder reranker to improve result quality. The reranker takes the top-k chunks from Milvus and scores each one against the query more precisely, returning a reranked subset. This is a common production pattern for improving RAG precision without sacrificing retrieval recall.
