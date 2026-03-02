# Docker in This Repo: A Textbook-Style Deep Dive

This document explains, at a systems level, how and why Docker is used in the Milvus-based RAG repository. It is written so you can understand what you built before you change it.

Read this before modifying any Docker configuration, adding services, or debugging infrastructure issues. The goal is not to memorize commands — it is to build a mental model accurate enough that when something breaks, you can reason about where and why.

## Table of Contents

1. What Docker is and what problem it solves
2. The core mental model: images, containers, networks, volumes
3. The lab architecture: who talks to whom and why
4. docker-compose.yml as an orchestration contract
5. Networking in this repo: the internal-only design
6. Data persistence with volumes
7. Startup sequencing vs readiness
8. Resource limits and performance
9. Logging and observability
10. Practical commands for day-to-day work
11. Debugging failure modes methodically
12. Security rationale: boundaries, secrets, and exposure control
13. Appendix: tracing a request end-to-end

---

## 1. What Docker Is and What Problem It Solves

When you build a real system, you are rarely running one program. You are running a vector database, supporting infrastructure, an embedding model, an API, a gateway, and sometimes a UI — all at once, all needing to be compatible versions, all needing to find each other on a network.

Without Docker, you would need to install and configure all of those on your own machine in the correct versions and then keep them compatible. On the next student's machine, the same setup might fail because they have a different OS, a different Python version, or a missing system library.

Docker solves this by packaging each service — its code, dependencies, and runtime environment — into a self-contained unit called an image. When you run the lab with `docker compose up -d`, every student gets the exact same services running in the exact same way, regardless of what is installed on their machine.

That is the core educational reason Docker is used here: it makes the lab reproducible.

### What Docker is not

Docker is not a virtual machine. A VM bundles an entire operating system kernel. Docker containers share the host kernel, which means they start faster and use less memory than full VMs. What you get is an isolated filesystem, its own process space, its own network identity, and reproducible startup — without the overhead of a full OS.

---

## 2. The Core Mental Model: Images, Containers, Networks, Volumes

Before reading about the specific services in this repo, it helps to have these four concepts clearly defined.

### Images

An image is a packaged, read-only artifact: code, dependencies, and runtime environment bundled together. In this repo you use a mix of prebuilt images pulled from registries (such as `nginx:1.27-alpine`, `milvusdb/milvus:v2.4.9`, `quay.io/coreos/etcd:v3.5.5`, and `minio/minio`) and locally built images (such as `ingestion-api` and `gradio-ui`, which are built from Dockerfiles in the repo).

### Containers

A container is a running instance of an image. A useful way to think about it: an image is a blueprint, and a container is the building constructed from that blueprint and currently in use. You can run multiple containers from the same image, stop and restart them, and unless you have attached persistent storage, any changes written inside the container are lost when it is removed.

### Networks

Docker networks create private virtual LANs for containers. In this repo, all services are connected to a network called `internal`. Containers on the same network can reach each other by service name (for example, `milvus:19530`) using Docker's built-in DNS. Containers not connected to a network, or on different networks, cannot reach each other.

This is important: if a service is not listed under `ports:` in `docker-compose.yml`, it is not reachable from your laptop. It is only reachable from other containers on the same network. This is intentional — databases and infrastructure services should not be publicly accessible.

### Volumes

Volumes are Docker-managed persistent storage that lives outside the container filesystem. In this repo, `milvus_data` stores the Milvus segment files, `etcd_data` stores the cluster metadata, `minio_data` stores the raw segment objects, and `ollama_data` stores downloaded models. Because these are volumes, you can stop and recreate containers without losing your ingested documents or downloaded models.

If you run `docker compose down` and then `docker compose up -d`, your data is still there.

---

## 3. The Lab Architecture: Who Talks to Whom and Why

This system is a layered RAG architecture. Each service has exactly one job, and they communicate through well-defined interfaces. Understanding who calls whom is the foundation of being able to debug the system.

**This repo has more services than the Qdrant or Weaviate versions.** Milvus is a distributed-architecture database that requires two supporting services to function. Understanding this three-service cluster is the key architectural difference in this lab.

### etcd (metadata store)

etcd is a distributed key-value store. Milvus uses it to store collection schemas, index configurations, and cluster topology. When you create a collection or define a schema, that definition is written to etcd. Without etcd, Milvus has no memory of what collections exist.

etcd listens on port 2379 for client connections. It is internal-only — never exposed to your laptop.

### MinIO (object storage)

MinIO is an S3-compatible object storage service. Milvus uses it to store segment files — the actual binary data for your vector collections. Think of MinIO as the hard drive for Milvus. When you ingest documents and flush them to storage, the segment files land in MinIO.

MinIO listens on port 9000 (API) and 9001 (console). Both are internal-only in this lab.

### Milvus (vector database)

Milvus is the vector database. It coordinates with etcd for schema management and with MinIO for data persistence. Milvus accepts connections on **gRPC port 19530**, not HTTP REST. This is a key difference from Qdrant and Weaviate — the ingestion API communicates with Milvus using the **pymilvus SDK** over gRPC, not raw HTTP calls.

Milvus stores data in typed collections with explicit schemas. Every field must be declared before ingesting data. Milvus cannot start until both etcd and MinIO are healthy, which is why startup takes 60–90 seconds.

### Embeddings and generation (Ollama)

Ollama serves two roles in this lab. It generates embeddings via `/api/embeddings` (used by both the main ingestion pipeline and the security memory ingestor), and it generates text responses via `/api/generate` (used by the RAG pipeline). Both go through the same Ollama service, eliminating the need for a separate embeddings container.

### ingestion-api (FastAPI)

The ingestion API is the brain of the system. It connects to Milvus using the pymilvus SDK over gRPC, embeds documents and queries via Ollama, and handles both the main RAG pipeline and the security memory endpoints. It imports `milvus_client.py` instead of the `qdrant_client.py` or `weaviate_client.py` you would see in the other lab versions.

### NGINX (edge gateway)

NGINX is the only service exposed on a host port (8088). It sits in front of the ingestion API and does two things: it checks that every incoming request has a valid API key, and it proxies authenticated requests to the ingestion API. Nothing reaches the API without going through NGINX first.

### Gradio UI

The Gradio UI is the browser-based chat interface. It talks to NGINX, not directly to the ingestion API. This means it goes through the same authentication layer as any other client. It displays the answer and the sources retrieved from Milvus.

### The production-like design goal

This lab is designed to mirror how real RAG systems are structured. It has service boundaries, a gateway with authentication, internal-only databases and infrastructure, and a UI that only sees the gateway. Understanding this architecture — including why Milvus needs etcd and MinIO — means you understand the patterns used in production-grade vector search systems.

---

## 4. docker-compose.yml as an Orchestration Contract

The `docker-compose.yml` file is more than a startup script. It is a human-readable contract that documents the entire architecture in one place. It specifies which services exist, which images run them, what environment variables they need, what network they are on, what persistent storage they use, which ports (if any) are exposed to your machine, and what healthchecks determine whether a service is ready.

When you read `docker-compose.yml`, you are reading the architecture. When you change it, you are changing the architecture. That is why it is worth understanding every section rather than treating it as a configuration file to ignore.

The dependency chain in this repo is more complex than in simpler labs:

```
etcd ──┐
       ├──► milvus ──► ingestion-api ──► nginx ──► gradio-ui
minio ─┘
ollama ──────────────► ingestion-api
```

Milvus cannot start until both etcd and MinIO pass their healthchecks. The ingestion API cannot start until Milvus is healthy. This chain means a cold start takes longer than you might expect — budget 90 seconds before everything is ready.

---

## 5. Networking in This Repo: The Internal-Only Design

All services in this repo are on a single bridge network called `internal`. This means they can reach each other by service name, but they are not reachable from outside Docker unless explicitly published.

The only published ports are NGINX (8088) and Gradio (7860). Milvus, etcd, and MinIO are all internal-only.

The most important networking rule to remember: **inside a container, `localhost` refers to the container itself, not your host machine.** If you try to call `milvus:19530` using `localhost` from inside the `ingestion-api` container, it will fail. The correct address is `milvus:19530`, using the service name as the hostname.

**gRPC vs HTTP:** Milvus uses gRPC on port 19530, not HTTP REST. You cannot use `curl` to talk to Milvus directly. All communication goes through the pymilvus SDK. Milvus also exposes an HTTP health endpoint on port 9091 (`/healthz`), which is what the Docker healthcheck uses.

---

## 6. Data Persistence with Volumes

Without volumes, every time you recreate a container its internal filesystem starts fresh. For Milvus, that would mean losing all your ingested documents across three separate services.

Volumes solve this by storing data outside the container in Docker-managed storage. The mappings in `docker-compose.yml` are:

- `etcd_data:/etcd` — etcd's metadata and schema definitions
- `minio_data:/minio_data` — MinIO's raw segment object files
- `milvus_data:/var/lib/milvus` — Milvus's local state and WAL
- `ollama_data:/root/.ollama` — Ollama's downloaded models and cache

These volumes persist across `docker compose down` and `docker compose up -d`. The only way to wipe them is to run `docker compose down -v`, which explicitly removes all volumes. **Be careful with that command** — it deletes all your ingested data, all schema definitions, all stored segments, and all downloaded models. You will need to pull models and re-ingest everything from scratch.

---

## 7. Startup Sequencing vs Readiness

`depends_on` in `docker-compose.yml` controls the order in which Docker starts containers. It does not wait for a service to be fully ready before starting the next one.

This distinction matters especially in this repo because Milvus has a complex startup sequence:

1. etcd must be healthy (accepts client connections and responds to health checks)
2. MinIO must be healthy (S3 API is accepting requests)
3. Milvus can then start — it connects to both etcd and MinIO, loads schemas, and initializes segments
4. Only after Milvus passes its own healthcheck can the ingestion API start

This chain means a **cold start takes 60–90 seconds** on a typical machine. If you run `docker compose ps` immediately after `docker compose up -d`, you will see several services still in the "starting" state. This is normal — wait and check again.

If you see the ingestion API failing to connect to Milvus right after startup, the most likely cause is that Milvus is still initializing. Check `docker logs --tail 50 milvus` and wait for it to report that it is ready before troubleshooting further.

---

## 8. Resource Limits and Performance

All services in this repo have `mem_limit` set. On student machines, uncontrolled containers can consume all available RAM, causing the OS to kill processes or making the system unstable.

This repo requires more RAM than the Qdrant or Weaviate versions because of the three-service Milvus cluster:

- etcd: 512 MB
- MinIO: 1 GB
- Milvus: 8 GB
- Ollama: 8 GB
- ingestion-api: 1 GB
- NGINX: 128 MB
- Gradio: 512 MB

**Total: ~19 GB** — 16 GB is the minimum recommended; 32 GB is comfortable. If you are on a machine with less RAM, Milvus and Ollama are the first candidates to reduce, but reducing Milvus below 4 GB may cause instability.

Common symptoms of memory pressure:
- Milvus exits unexpectedly during ingestion (the OS killed it)
- Ollama embedding calls time out
- etcd becomes unhealthy and Milvus loses its schema

To monitor memory usage in real time:
```bash
docker stats
```

To check logs for a specific container:
```bash
docker logs --tail 200 <container-name>
```

---

## 9. Logging and Observability

When a request fails, the key skill is knowing which layer to look at first. The request path goes: your client → NGINX → ingestion-api → Milvus (via gRPC) and Ollama. The error message you see tells you where the chain broke.

**Common error patterns and what they mean:**

- `502 Bad Gateway` — NGINX cannot reach ingestion-api, or ingestion-api crashed. Check ingestion-api logs first.
- `401 or 403` — API key issue at NGINX. Check that you are passing `X-API-Key` correctly.
- `Timeout` — a slow upstream. On first run, Ollama may take several minutes to load a model. Milvus may still be initializing.
- `MilvusException: collection not found` — the collection was never created, or the collection name in your environment variables doesn't match. Re-run ingestion.
- `grpc._channel._InactiveRpcError` — Milvus is not reachable on port 19530. Check whether Milvus is healthy.
- `dim does not match` — you changed the embedding model but the existing collection was built with a different dimension. Drop and recreate the collection.

**Useful log commands:**
```bash
docker logs --tail 200 edge-nginx
docker logs --tail 200 ingestion-api
docker logs --tail 200 milvus
docker logs --tail 200 milvus-etcd
docker logs --tail 200 milvus-minio
docker logs --tail 200 ollama
```

---

## 10. Practical Commands for Day-to-Day Work

**Start and stop the full stack:**
```bash
docker compose up -d
docker compose down
```

**Rebuild a single service after code changes:**
```bash
docker compose up -d --build ingestion-api
docker compose up -d --build gradio-ui
```

**Check what is running:**
```bash
docker ps
docker compose ps
```

**Open a shell inside a container:**
```bash
docker exec -it ingestion-api sh
docker exec -it edge-nginx sh
```

**Verify Milvus connectivity from inside the network:**
```bash
docker exec -i ingestion-api python - <<'PY'
from pymilvus import connections, utility
connections.connect(host="milvus", port=19530, timeout=10)
print("connected:", utility.get_server_version())
PY
```

**List existing collections:**
```bash
docker exec -i ingestion-api python - <<'PY'
from pymilvus import connections, utility
connections.connect(host="milvus", port=19530, timeout=10)
print(utility.list_collections())
PY
```

**Check collection row count:**
```bash
docker exec -i ingestion-api python - <<'PY'
from pymilvus import connections, Collection
connections.connect(host="milvus", port=19530, timeout=10)
col = Collection("LabDoc")
col.load()
print("rows:", col.num_entities)
PY
```

---

## 11. Debugging Failure Modes Methodically

This section is written as "if you see X, check Y."

### 502 Bad Gateway from NGINX

NGINX cannot get a valid response from ingestion-api. Work through this checklist in order:

1. Check whether ingestion-api is running: `docker ps --filter "name=ingestion-api"`
2. Check whether NGINX can reach it: `docker exec -i edge-nginx wget -qO- http://ingestion-api:8000/health || echo "failed"`
3. Check ingestion-api logs for crashes: `docker logs --tail 200 ingestion-api`

Common causes: an `ImportError` (pymilvus not installed, or a code change), a `SyntaxError`, or an environment variable that fails to parse on startup.

### Milvus gRPC connection refused

The ingestion API cannot reach Milvus on port 19530. Work through this in order:

1. Is Milvus healthy? `docker compose ps milvus`
2. Is etcd healthy? `docker compose ps etcd`
3. Is MinIO healthy? `docker compose ps minio`
4. Check Milvus logs: `docker logs --tail 100 milvus`

If Milvus shows as unhealthy but the container is running, it is likely still initializing — wait 30 seconds and check again. Milvus depends on both etcd and MinIO being fully ready before it can complete its own startup.

### `dim does not match` error during ingestion

You changed the embedding model (or `SECURITY_EMBED_DIM`) but the collection was created with a different vector dimension. The fix is to drop and recreate:

```bash
docker exec -i ingestion-api python - <<'PY'
from pymilvus import connections, utility, Collection
connections.connect(host="milvus", port=19530, timeout=10)
if utility.has_collection("LabDoc"):
    Collection("LabDoc").drop()
    print("Dropped LabDoc")
PY
docker compose up -d --build ingestion-api
```

Then re-ingest your documents.

### Collection exists but queries return empty results

The collection was created but data was never flushed to storage, or the collection was not loaded into memory. Milvus requires an explicit `load()` call before a collection can be searched.

Check whether the collection has data:
```bash
docker exec -i ingestion-api python - <<'PY'
from pymilvus import connections, Collection
connections.connect(host="milvus", port=19530, timeout=10)
col = Collection("LabDoc")
col.load()
print("entities:", col.num_entities)
PY
```

If `entities` is 0, re-run ingestion. If it is greater than 0 but queries still return empty, check that the collection name in your `.env` file matches the collection that was created.

### Gradio UI times out

Check Ollama logs to see if it is still loading a model:
```bash
docker logs --tail 50 ollama
```

If this is the first request after startup, wait a few minutes and try again. Ollama can take 2–5 minutes to load a large model on first request.

---

## 12. Security Rationale: Boundaries, Secrets, and Exposure Control

This repo makes specific choices to teach production-like security habits.

### One exposed front door

Only NGINX is exposed on a host port. Everything else — Milvus, etcd, MinIO, Ollama, the ingestion API — is on the internal network. This reduces the risk of accidentally exposing infrastructure to the internet and forces all traffic through a single authenticated gateway.

### etcd and MinIO are never exposed

In a real production deployment, exposing etcd or MinIO directly would be a serious security risk — they hold your schema definitions and raw data files respectively. Keeping them internal-only is the correct default.

### Secrets live in .env

API keys and configuration values that vary by machine or student are kept in a `.env` file that is not committed to the repo. The `.env.example` file shows students what variables are needed without exposing real values.

If you hardcode secrets in Python files or Dockerfiles and commit them, they become part of the git history permanently — even if you delete them later. Use environment variables.

---

## 13. Appendix: Tracing a Request End-to-End

This is the most useful debugging exercise you can do. Run through these steps in order to verify every layer of the system is working.

### Step A: Verify the gateway is alive

```bash
curl -i http://localhost:8088/proxy-health
```
Expected: `HTTP 200` with body `ok`. If this fails, NGINX is not running or not reachable.

### Step B: Verify the API through the gateway

```bash
EDGE_API_KEY=$(grep -E '^EDGE_API_KEY=' .env | cut -d= -f2-)
curl -i http://localhost:8088/health -H "X-API-Key: $EDGE_API_KEY"
```
Expected: `HTTP 200` with JSON like `{"ok":true,"milvus_ok":true,"uptime_s":123}`. If this fails, the API key may be wrong or ingestion-api is down.

### Step C: Verify Milvus

```bash
curl -sS http://localhost:9091/healthz
```
Expected: HTTP 200. If this fails, Milvus is not running or still initializing.

Check that the collection exists and has data:
```bash
docker exec -i ingestion-api python - <<'PY'
from pymilvus import connections, utility, Collection
connections.connect(host="milvus", port=19530, timeout=10)
cols = utility.list_collections()
print("collections:", cols)
if "LabDoc" in cols:
    col = Collection("LabDoc")
    col.load()
    print("LabDoc entities:", col.num_entities)
PY
```

### Step D: Verify Ollama reachability from inside the network

```bash
docker exec -i ingestion-api python - <<'PY'
import os, urllib.request
base = os.getenv("OLLAMA_BASE_URL", "")
print("OLLAMA_BASE_URL =", base)
print("status =", urllib.request.urlopen(f"{base}/api/tags").status)
PY
```
Expected: `status 200`. If this fails, Ollama is not reachable from inside the ingestion-api container.

### Step E: Ingest a document and retrieve it

**Ingest:**
```bash
curl -i -X POST "http://localhost:8088/ingest" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $EDGE_API_KEY" \
  -d '{
    "title": "Smoke Test Doc",
    "url": "https://example.com/smoke-test",
    "source": "smoke-test",
    "published_date": "2026-01-01",
    "text": "This document exists to verify ingestion, embedding, storage, and retrieval work end-to-end."
  }'
```

**Retrieve:**
```bash
curl -sS -G "http://localhost:8088/debug/retrieve" \
  -H "X-API-Key: $EDGE_API_KEY" \
  --data-urlencode "q=verify ingestion embedding retrieval" | python -m json.tool
```

If retrieval returns results, the full pipeline is working.

**Verify directly in Milvus:**
```bash
docker exec -i ingestion-api python - <<'PY'
from pymilvus import connections, Collection
connections.connect(host="milvus", port=19530, timeout=10)
col = Collection("LabDoc")
col.load()
print("entities:", col.num_entities)
PY
```

A count greater than zero confirms documents were stored successfully.

---

## Closing Note

The architecture in this repo is not Docker for its own sake. It exists to give you a realistic, debuggable system where each layer has a clear responsibility and a clear interface.

Milvus introduces more moving parts than a single-service vector database, but those parts reflect how production vector search systems are actually built — with separate metadata, storage, and compute layers. Once you can trace a request end-to-end and reason about which layer is responsible for which failure, you have the mental model needed to modify the system safely and confidently.
