# Security Memory Tool Reference — Milvus Edition

Complete reference for the `/memory/health` and `/memory/query` API endpoints.

---

## Authentication

Both endpoints require the same API key used for all other endpoints:

```
X-API-Key: <your EDGE_API_KEY>
```

---

## GET /memory/health

Returns the health status of the `ExpandedVSCodeMemory` collection in Milvus.

### Request

```bash
EDGE_API_KEY=$(grep -E '^EDGE_API_KEY=' .env | cut -d= -f2-)
curl -s http://localhost:8088/memory/health \
  -H "X-API-Key: $EDGE_API_KEY" | python -m json.tool
```

### Response

```json
{
  "ok": true,
  "collection": "ExpandedVSCodeMemory",
  "milvus_host": "milvus:19530",
  "points_count": 183,
  "note": null
}
```

### Response fields

| Field | Type | Description |
|-------|------|-------------|
| `ok` | bool | `true` if Milvus is reachable and the collection exists |
| `collection` | string | Collection name (from `SECURITY_COLLECTION` env var) |
| `milvus_host` | string | Milvus host and port used by this service |
| `points_count` | int or null | Number of entities in the collection; null if unavailable |
| `note` | string or null | Human-readable guidance if the collection is empty |

### When `ok` is false

Milvus is unreachable or the gRPC connection failed. Check:
```bash
docker compose ps milvus
docker logs --tail 50 milvus
```

### When `points_count` is 0 or null

The collection exists but has no data. Run the ingestor:
```bash
docker exec -i ingestion-api python -m app.security_memory.ingest
```

---

## POST /memory/query

Performs semantic similarity search over the security corpus.

### Request

```bash
EDGE_API_KEY=$(grep -E '^EDGE_API_KEY=' .env | cut -d= -f2-)
curl -s -X POST http://localhost:8088/memory/query \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $EDGE_API_KEY" \
  -d '{
    "query": "Docker containers running as root",
    "tags": ["docker", "cis"],
    "top_k": 3
  }' | python -m json.tool
```

### Request body

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `query` | string | yes | The search question or statement |
| `tags` | array of strings | no | Filter to chunks tagged with any of these values |
| `top_k` | integer | no | Number of results (default: `SECURITY_TOP_K` env var, default 6) |

### Response

```json
{
  "query": "Docker containers running as root",
  "collection": "ExpandedVSCodeMemory",
  "top_k": 3,
  "results": [
    {
      "score": 0.887,
      "title": "CIS Docker Benchmark",
      "source": "cis",
      "tags": ["cis", "docker"],
      "text": "4.1 Ensure a user for the container has been created...",
      "chunk_index": 12,
      "doc_path": "/securitymemory/data/cis/cis-docker-benchmark.md"
    }
  ]
}
```

### Response fields

| Field | Type | Description |
|-------|------|-------------|
| `query` | string | The original query |
| `collection` | string | Collection searched |
| `top_k` | integer | Number of results returned |
| `results` | array | Matched chunks, ordered by descending score |
| `results[].score` | float | Cosine similarity in [0, 1]; Milvus returns similarity directly for COSINE metric |
| `results[].title` | string | Document title |
| `results[].source` | string | Subfolder name |
| `results[].tags` | array | Tags inferred from file path |
| `results[].text` | string | Chunk text |
| `results[].chunk_index` | integer | Position in original document |
| `results[].doc_path` | string | Full path inside container |

### Score interpretation

Milvus returns cosine similarity scores directly when using the `COSINE` metric (unlike Weaviate which returns distance). A score of 1.0 means identical vectors. Scores above 0.85 indicate strong semantic similarity. Scores below 0.5 indicate weak or no semantic relationship.

This is different from the Qdrant and Weaviate versions: in those, `store.py` converts a distance to a score. In this Milvus version, `hit.score` is already a similarity value and no conversion is needed.

### Tag filtering behavior

Tags use a boolean `OR` filter — a chunk matches if it contains **any** of the requested tags. For example, `"tags": ["docker", "kubernetes"]` returns chunks tagged with docker, chunks tagged with kubernetes, or chunks tagged with both.

The filter is implemented as a Milvus boolean expression using `LIKE`:

```python
expr = 'tags like \'%"docker"%\' or tags like \'%"kubernetes"%\''
```

This works because tags are stored as a JSON array string (e.g. `'["cis","docker"]'`). The `LIKE` pattern `%"docker"%` matches any string containing the exact substring `"docker"` (including the quotes), which prevents partial matches — searching for `"cis"` will not match `"cisco"`.

---

## Error Responses

| Status | Meaning | Common cause |
|--------|---------|--------------|
| 401 | Missing API key | No `X-API-Key` header |
| 403 | Wrong API key | Key doesn't match `EDGE_API_KEY` |
| 500 | Internal error | Milvus unreachable, collection not found, embedding failed |
| 504 | Timeout | Ollama too slow to embed the query, or Milvus query timed out |

For 500 errors, check:
```bash
docker logs --tail 50 ingestion-api
docker logs --tail 50 milvus
docker logs --tail 50 ollama
```

---

## Common Query Patterns

### Broad security search (no tag filter)

```json
{
  "query": "secrets management in containerized environments",
  "top_k": 5
}
```

### Framework-specific lookup

```json
{
  "query": "least privilege principle",
  "tags": ["nist", "cis"],
  "top_k": 4
}
```

### Attack technique research

```json
{
  "query": "lateral movement techniques in cloud environments",
  "tags": ["mitre", "cloud"],
  "top_k": 6
}
```

### Application security review

```json
{
  "query": "input validation and injection prevention",
  "tags": ["owasp", "appsec"],
  "top_k": 5
}
```

---

## Using Results in an IDE Workflow

1. Copy the `text` field from one or more results
2. Paste into your IDE chat alongside your code or config
3. Ask the AI to review against the retrieved standard

Example prompt:
```
Here are relevant CIS Docker Benchmark controls:

<paste text fields here>

Please review my Dockerfile against these controls and identify any violations.
```

See `security-memory/prompts/` for pre-built prompt templates for common review scenarios.
