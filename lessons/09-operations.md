# Lesson 09 — Operations

> **Goal:** use the health endpoints, read logs, run failure drills, and know
> how to reset the stack cleanly.

---

## 1) Health endpoints

### Stack health (via NGINX)

```bash
EDGE_API_KEY=$(grep -E '^EDGE_API_KEY=' .env | cut -d= -f2-)

curl -s http://localhost:8088/health \
  -H "X-API-Key: $EDGE_API_KEY" | python3 -m json.tool
```

Expected:

```json
{
  "status": "ok",
  "milvus_ok": true
}
```

`milvus_ok: false` means `ingestion-api` cannot reach Milvus. See the
troubleshooting section below.

### Direct container health

```bash
# ingestion-api
docker inspect ingestion-api --format '{{.State.Health.Status}}'

# Milvus
docker inspect milvus --format '{{.State.Health.Status}}'
```

Expected: `healthy` for both.

---

## 2) Log inspection

```bash
# Tail all logs
docker compose logs -f

# Single service
docker compose logs -f ingestion-api
docker compose logs -f milvus
docker compose logs -f nginx

# Last 50 lines
docker compose logs --tail=50 milvus
```

### What to look for in ingestion-api

| Log line | Meaning |
|----------|---------|
| `connected to milvus:19530` | pymilvus gRPC connection OK |
| `collection 'LabDoc' ready` | Schema created or verified |
| `HNSW index ready` | Index built on `embedding` field |
| `collection 'LabDoc' loaded` | In-memory search ready |
| `milvus insert ok — 1 row` | Successful document write |

### What to look for in Milvus

| Log pattern | Meaning |
|-------------|---------|
| `etcd endpoints: etcd:2379` | Connected to metadata store |
| `Milvus Proxy successfully started` | gRPC API ready |
| `collection LabDoc loaded` | Collection is searchable |

---

## 3) Failure drills

These drills teach you what breaks when each service goes down, and what the
recovery path looks like.

### Drill A — Stop Ollama

```bash
docker compose stop ollama
```

Expected behaviour:
- `/health` still returns `200` (Milvus is independent of Ollama).
- `/chat` returns a 500 or timeout because embedding fails.
- `/debug/retrieve` also fails (embedding step).

Recover:

```bash
docker compose start ollama
```

Wait ~15 seconds for Ollama to reinitialise, then retry `/chat`.

---

### Drill B — Stop Milvus

```bash
docker compose stop milvus
```

Expected behaviour:
- `ingestion-api` health check starts failing (`milvus_ok: false`).
- `/ingest` and `/chat` return 500 errors.
- NGINX returns 502 (Bad Gateway) once ingestion-api goes unhealthy.

Recover:

```bash
docker compose start milvus
```

Milvus takes 60–90 seconds to reinitialise. `ingestion-api` will automatically
reconnect — watch the logs:

```bash
docker compose logs -f ingestion-api | grep milvus
```

You should see `connected to milvus:19530` and `collection 'LabDoc' loaded`.

---

### Drill C — Stop etcd (while Milvus is running)

```bash
docker compose stop etcd
```

Expected behaviour:
- Milvus loses its metadata connection. New collection operations and schema
  changes will fail.
- Existing loaded collections may continue serving queries briefly (in-memory)
  but will degrade over time.
- Milvus will eventually report unhealthy.

Recover:

```bash
docker compose start etcd
docker compose restart milvus
```

---

### Drill D — Restart ingestion-api only

```bash
docker compose restart ingestion-api
```

Expected behaviour:
- ~5-second downtime.
- On restart, `ingestion-api` re-runs `ensure_collection()`:
  create → index → load.
- All stored data is preserved (it lives in Milvus / MinIO).
- `/health` returns `milvus_ok: true` once restart completes.

---

## 4) Smoke test script

Save as `/tmp/smoke_test.sh`:

```bash
#!/usr/bin/env bash
set -e
KEY=$(grep -E '^EDGE_API_KEY=' .env | cut -d= -f2-)
BASE="http://localhost:8088"

echo "=== Health ==="
curl -sf "$BASE/health" -H "X-API-Key: $KEY" | python3 -m json.tool

echo "=== Ingest ==="
curl -sf -X POST "$BASE/ingest" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $KEY" \
  -d '{"text":"smoke test document for operational verification","title":"Smoke Test","tags":["ops"]}' \
  | python3 -m json.tool

echo "=== Retrieve ==="
curl -sf -X POST "$BASE/debug/retrieve" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $KEY" \
  -d '{"query":"smoke test","k":1}' | python3 -m json.tool

echo "=== Chat ==="
curl -sf -X POST "$BASE/chat" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $KEY" \
  -d '{"message":"what is a smoke test document?"}' | python3 -m json.tool

echo "=== All checks passed ==="
```

```bash
bash /tmp/smoke_test.sh
```

---

## 5) Reset procedures

### Soft reset — restart all services, keep data

```bash
docker compose restart
```

### Hard reset — delete all data and start fresh

```bash
docker compose down -v
docker compose up -d
```

This deletes:
- All documents in Milvus (MinIO + etcd volumes).
- Downloaded Ollama models (you will need to `ollama pull` again).

### Partial reset — reset Milvus only, keep Ollama models

```bash
docker compose down
docker volume rm $(docker volume ls -q | grep -E 'milvus_data|etcd_data|minio_data')
docker compose up -d
```

---

## 6) Monitoring Milvus memory usage

HNSW indexes are loaded entirely into RAM. For large collections, memory is the
primary constraint:

```bash
docker stats milvus --no-stream
```

If Milvus memory usage approaches its `mem_limit` (8 GB by default), it will
be OOM-killed. Solutions:
- Increase `mem_limit` in `docker-compose.yml`.
- Add more RAM to Docker Desktop resources.
- Use the `IVF_FLAT` index type (disk-resident, lower memory, slower queries).

---

## Checkpoint

You are done when:
- You can explain what `/health` tells you about the stack.
- You have run at least two failure drills and recovered cleanly.
- The smoke test script passes end-to-end.

Continue to **[Lesson 10 — Conclusion](10-conclusion.md)**.
