# Lesson 4.2 — The Memory API Tool

> **What you're building:** the `/memory/query` and `/memory/health` endpoints
> that expose your security corpus as an authenticated, structured API tool.

---

## The two endpoints

| Endpoint | Method | What it does |
|----------|--------|--------------|
| `/memory/health` | GET | Reports whether the `ExpandedVSCodeMemory` collection is loaded |
| `/memory/query` | POST | Semantic search over the security corpus |

Both are protected by the `X-API-Key` header through NGINX (same as the main API).

---

## `/memory/health`

```bash
EDGE_API_KEY=$(grep -E '^EDGE_API_KEY=' .env | cut -d= -f2-)

curl -s http://localhost:8088/memory/health \
  -H "X-API-Key: $EDGE_API_KEY" | python3 -m json.tool
```

Expected:

```json
{
  "status": "ok",
  "collection": "ExpandedVSCodeMemory",
  "row_count": 183
}
```

`row_count` is 0 if you have not yet run the ingestor (Lesson 4.1).

Under the hood this calls `collection.get_collection_stats()` via pymilvus —
a lightweight metadata read that does not require a search.

---

## `/memory/query`

```bash
curl -s -X POST http://localhost:8088/memory/query \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $EDGE_API_KEY" \
  -d '{
    "query": "docker containers should not run as root",
    "tags": ["docker", "cis"],
    "top_k": 5
  }' | python3 -m json.tool
```

### Request fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `query` | string | Yes | Natural-language search query |
| `tags` | array of strings | No | Filter to chunks whose `tags` contain all listed values |
| `top_k` | integer | No (default: 5) | Number of results to return |

### Response shape

```json
{
  "results": [
    {
      "text": "CIS Docker Benchmark 4.1: Ensure that a user for the container has been created...",
      "source_doc": "cis-docker-benchmark.md",
      "tags": ["cis", "docker"],
      "chunk_index": 12,
      "score": 0.91
    },
    ...
  ]
}
```

`score` is the cosine similarity between your query embedding and the chunk
embedding (0–1, higher = more similar).

---

## How tag filtering works in Milvus

Milvus does not support native array fields for filtering in v2.4, so tags are
stored as a JSON-encoded VARCHAR. The filter expression uses `like`:

```python
# In store.py
if tags:
    exprs = [f'tags like \'%"{t}"%\'' for t in tags]
    expr = " and ".join(exprs)
```

For `tags=["docker", "cis"]` this becomes:

```
tags like '"%docker%"' and tags like '"%cis%"'
```

This is an O(n) string scan and is slower than a native index. For large
collections consider storing tags as separate boolean fields or upgrading to
Milvus v2.5+ with array field support.

---

## How the query is executed in `store.py`

```python
async def query_memory(query: str, tags: list, top_k: int):
    # 1. Embed the query
    vectors = await embed_texts([query])

    # 2. Build optional tag filter
    expr = build_tag_expr(tags)  # SQL-like boolean string

    # 3. HNSW cosine search
    results = collection.search(
        data=[vectors[0]],
        anns_field="embedding",
        param={"metric_type": "COSINE", "params": {"ef": max(top_k * 4, 64)}},
        limit=top_k,
        expr=expr,
        output_fields=["text", "source_doc", "tags", "chunk_index"],
    )
    # 4. Normalise and return
    ...
```

---

## Optional: integrate memory into the main chat

If you want the `/chat` endpoint to automatically retrieve security chunks for
security-related questions, add this to `rag.py` (optional extension):

```python
SECURITY_KEYWORDS = ["cve", "owasp", "cis", "nist", "mitre", "vulnerability",
                     "exploit", "privilege", "authentication", "authorization"]

async def is_security_question(message: str) -> bool:
    lower = message.lower()
    return any(k in lower for k in SECURITY_KEYWORDS)

# In the /chat handler:
if await is_security_question(message):
    sec_sources = await query_memory(message, tags=[], top_k=3)
    sources = sec_sources + sources  # prepend security context
```

This is optional and not included in the base code.

---

## Smoke test

```bash
# Health check
curl -sf http://localhost:8088/memory/health \
  -H "X-API-Key: $EDGE_API_KEY" | python3 -m json.tool

# Query with tags
curl -sf -X POST http://localhost:8088/memory/query \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $EDGE_API_KEY" \
  -d '{"query":"API broken authentication","tags":["owasp"],"top_k":3}' \
  | python3 -m json.tool

# Query without tags (search everything)
curl -sf -X POST http://localhost:8088/memory/query \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $EDGE_API_KEY" \
  -d '{"query":"container image hardening","top_k":5}' \
  | python3 -m json.tool
```

---

## Troubleshooting

### `row_count: 0` in `/memory/health`

You have not run the ingestor. Go back to Lesson 4.1:

```bash
docker exec -i ingestion-api python3 -m app.security_memory.ingest
```

### Empty `results` array despite having data

- Check that your `tags` filter matches the tags actually stored. Run a
  query without `tags` first to confirm data exists.
- The collection may not be loaded. Restart ingestion-api:

```bash
docker compose restart ingestion-api
```

### `collection not found: ExpandedVSCodeMemory`

The collection was dropped or never created. Run ingestion again.

---

## Checkpoint

You are done when:
- `/memory/health` returns `"status": "ok"` with a non-zero `row_count`.
- `/memory/query` returns relevant security chunks for a test query.
- Tag filtering works (query with `tags: ["docker"]` returns only Docker-related chunks).

Continue to **[Lesson 4.3 — IDE Integration](03-ide-integration.md)**.
