# Lesson 02 — Setup and First Boot

> **Goal:** get the full stack running and verify every service is healthy
> before writing a single line of application code.

---

## Prerequisites

- Docker Desktop (Mac/Windows) or Docker Engine + Compose plugin (Linux)
  — version 24+ recommended.
- At least **16 GB RAM** available to Docker. Milvus alone needs ~4–8 GB.
- ~10 GB free disk space (Ollama model + MinIO segment data).
- `git`, `curl`, and a terminal.

---

## 1) Clone and enter the repo

```bash
git clone https://github.com/YOUR-FORK/milvus-rag-lab.git
cd milvus-rag-lab
```

---

## 2) Create your `.env` file

Copy the example and fill it in:

```bash
cp .env.example .env
```

Open `.env` in any editor. The required variables are:

```ini
# API key enforced by NGINX — use something long and random
EDGE_API_KEY=change-me-please

# Milvus connection (matches docker-compose service names)
MILVUS_HOST=milvus
MILVUS_PORT=19530
MILVUS_COLLECTION=LabDoc

# Ollama
OLLAMA_BASE_URL=http://ollama:11434
OLLAMA_MODEL=llama3.2:1b

# RAG tuning
RAG_TOP_K=4
RAG_MAX_SOURCE_CHARS=800
```

Generate a secure API key if you do not have one:

```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

Paste the output as the value of `EDGE_API_KEY`.

> **Never commit `.env` to git.** It is already listed in `.gitignore`.

---

## 3) Start the stack

```bash
docker compose up -d
```

Docker will pull images on the first run (~3–5 minutes depending on your
connection). On subsequent starts it will reuse cached layers.

---

## 4) Wait for Milvus to become healthy

Milvus takes **60–90 seconds** to initialise its etcd metadata and MinIO
storage layers. Watch the health status:

```bash
watch -n 5 'docker compose ps --format "table {{.Name}}\t{{.Status}}"'
```

Wait until all five core services show `healthy` or `running`:

```
NAME              STATUS
milvus            healthy
etcd              healthy
minio             running
ingestion-api     healthy
nginx             running
ollama            running
gradio            running
```

Press `Ctrl+C` to stop watching.

If you do not have `watch`, poll manually:

```bash
docker compose ps
```

---

## 5) Verify every service

### 5a — ingestion-api health

```bash
EDGE_API_KEY=$(grep -E '^EDGE_API_KEY=' .env | cut -d= -f2-)

curl -s http://localhost:8088/health \
  -H "X-API-Key: $EDGE_API_KEY" | python3 -m json.tool
```

Expected response:

```json
{
  "status": "ok",
  "milvus_ok": true
}
```

`milvus_ok: true` means `ingestion-api` successfully connected to Milvus,
created (or verified) the `LabDoc` collection, built the HNSW index, and
loaded the collection into memory.

### 5b — Milvus gRPC port

```bash
docker exec ingestion-api python3 -c "
from pymilvus import connections, utility
connections.connect(host='milvus', port='19530')
print('Collections:', utility.list_collections())
"
```

Expected: `Collections: ['LabDoc']` (or `[]` before the API first starts).

### 5c — Ollama

```bash
curl -s http://localhost:8088/debug/ollama \
  -H "X-API-Key: $EDGE_API_KEY" | python3 -m json.tool
```

If Ollama has no model pulled yet you will see an empty or error response —
that is fine at this stage. Model pulling is covered in Lesson 07.

### 5d — Gradio UI

Open `http://localhost:7860` in your browser. You should see the chat
interface (it may show an error until a model is pulled).

---

## 6) Read the logs

```bash
# All services
docker compose logs -f

# Just ingestion-api
docker compose logs -f ingestion-api

# Just Milvus
docker compose logs -f milvus
```

Look for these lines in `ingestion-api` logs on a successful start:

```
INFO  milvus_client  connected to milvus:19530
INFO  milvus_client  collection 'LabDoc' ready (created or verified)
INFO  milvus_client  HNSW index ready on 'embedding'
INFO  milvus_client  collection 'LabDoc' loaded into memory
```

If you see `connection refused` or `timeout`, Milvus is still initialising —
wait another 30 seconds and check again.

---

## Common issues

### `connection refused` to port 19530

Milvus is still starting. Run `docker compose ps` — if `milvus` shows
`starting` or `unhealthy`, wait and retry. If it stays unhealthy:

```bash
docker compose logs milvus | tail -40
```

Look for `etcd connection failed` — if so, etcd started after Milvus. Restart:

```bash
docker compose restart milvus
```

### `milvus_ok: false` in `/health`

The ingestion-api connected to Milvus but could not create or load the
collection. Check:

```bash
docker compose logs ingestion-api | grep -i "milvus\|error\|collection"
```

### Out of memory / OOM killed

Milvus is memory-intensive. If Docker Desktop is set to less than 8 GB RAM,
Milvus will be OOM-killed. Increase Docker Desktop memory in Settings →
Resources → Memory.

### `EDGE_API_KEY` not found

Make sure your `.env` file is in the same directory as `docker-compose.yml`
and you ran `docker compose up` from that directory.

---

## Stopping and restarting

```bash
# Stop everything (keeps volumes / data)
docker compose down

# Stop and delete all data (fresh start)
docker compose down -v

# Restart a single service
docker compose restart ingestion-api
```

---

## Checkpoint

You are ready to continue when:
- `docker compose ps` shows all services running or healthy.
- `/health` returns `"milvus_ok": true`.
- You can exec into `ingestion-api` and list Milvus collections.

Continue to **[Lesson 03 — Compose Architecture](03-compose-architecture.md)**.
