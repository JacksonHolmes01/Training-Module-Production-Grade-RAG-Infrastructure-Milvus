# Lesson 4.1 — Building the Security Corpus in Milvus

> **What you're building:** a separate Milvus collection called
> `ExpandedVSCodeMemory` that stores chunked security-standard documents
> (NIST, CIS, OWASP, MITRE) and can be queried by semantic similarity.

---

## Why a separate collection?

The main `LabDoc` collection is for arbitrary documents ingested through the
API. The security memory uses its own typed collection (`ExpandedVSCodeMemory`)
so you can:
- Store security-framework metadata (`tags`, `chunk_index`, `source_doc`).
- Query only security content without polluting general RAG results.
- Manage the corpus independently (update CIS Benchmarks without touching
  your general knowledge base).

In Milvus, a collection is roughly equivalent to a table — you can have many
collections, each with its own schema and index.

---

## Collection schema

`store.py` defines the `ExpandedVSCodeMemory` schema:

| Field | Type | Purpose |
|-------|------|---------|
| `id` | INT64, auto | Primary key |
| `embedding` | FLOAT_VECTOR[768] | nomic-embed-text output |
| `text` | VARCHAR[65535] | The chunk text |
| `source_doc` | VARCHAR[512] | Filename / document title |
| `chunk_index` | INT64 | Position of chunk in original document |
| `tags` | VARCHAR[2048] | JSON-encoded list, e.g. `["cis","docker"]` |

---

## The source data

Security reference documents live under `security-memory/data/`:

```
security-memory/data/
├── cis/
│   ├── cis-docker-benchmark.md
│   └── cis-kubernetes-benchmark.md
├── owasp/
│   ├── owasp-api-security-top10.md
│   └── owasp-top10.md
├── nist/
│   └── nist-800-53-controls-subset.md
└── mitre/
    └── mitre-attack-techniques.md
```

Add your own `.md` or `.txt` files to the appropriate subfolder before running
ingestion. The ingestor will chunk them automatically.

---

## How chunking works

`ingest.py` splits each document into overlapping fixed-size chunks:

```python
CHUNK_SIZE    = 512   # characters per chunk
CHUNK_OVERLAP = 64    # characters of overlap between adjacent chunks
```

Overlap prevents a sentence from being split across two chunks in a way that
loses context. Adjust these values in `ingest.py` if your documents have very
long or very short paragraphs.

---

## Running the ingestor

Make sure the stack is running and healthy:

```bash
EDGE_API_KEY=$(grep -E '^EDGE_API_KEY=' .env | cut -d= -f2-)
curl -s http://localhost:8088/health -H "X-API-Key: $EDGE_API_KEY" \
  | python3 -m json.tool
```

Then ingest the security corpus:

```bash
docker exec -i ingestion-api python3 -m app.security_memory.ingest
```

You will see progress output like:

```
Processing: security-memory/data/cis/cis-docker-benchmark.md
  → 47 chunks ingested
Processing: security-memory/data/owasp/owasp-api-security-top10.md
  → 31 chunks ingested
...
Total: 183 chunks across 6 documents
```

---

## Verifying the collection

```bash
docker exec ingestion-api python3 -c "
from pymilvus import Collection, connections
connections.connect(host='milvus', port='19530')
col = Collection('ExpandedVSCodeMemory')
col.load()
print('Row count:', col.num_entities)

# Sample a few chunks
res = col.query(
    expr='chunk_index == 0',
    output_fields=['source_doc', 'tags', 'text'],
    limit=5,
)
for r in res:
    print(r['source_doc'], '|', r['tags'], '|', r['text'][:80])
"
```

---

## Test a semantic query

```bash
docker exec ingestion-api python3 -c "
import asyncio
from app.security_memory.store import query_memory

results = asyncio.run(query_memory(
    query='Docker containers running as root',
    tags=['docker', 'cis'],
    top_k=3,
))
for r in results:
    print('Score:', round(r['score'], 3))
    print('Source:', r['source_doc'])
    print('Text:', r['text'][:120])
    print('---')
"
```

---

## Updating or adding documents

To add a new document or update an existing one:

1. Add or replace the file under `security-memory/data/`.
2. Re-run ingestion:

```bash
docker exec -i ingestion-api python3 -m app.security_memory.ingest
```

The ingestor uses **upserts** — existing chunks for a document are replaced,
new chunks are added, and nothing else is touched.

## When you must recreate the collection

If you change any of the following, drop and recreate the collection:

- The embedding model (different models produce incompatible vector spaces).
- The embedding dimension (schema change; Milvus will reject mismatched vectors).
- The distance metric (cosine scores become meaningless if switched to L2).

To recreate:

```bash
docker exec ingestion-api python3 -c "
from pymilvus import Collection, connections, utility
connections.connect(host='milvus', port='19530')
if utility.has_collection('ExpandedVSCodeMemory'):
    Collection('ExpandedVSCodeMemory').drop()
    print('Dropped.')
"
docker exec -i ingestion-api python3 -m app.security_memory.ingest
```

---

## Checkpoint

You are done when:
- `col.num_entities` shows more than 0 chunks.
- A semantic query for `'Docker containers running as root'` returns relevant
  CIS Benchmark chunks.

Continue to **[Lesson 4.2 — The Memory API Tool](02-api-tool.md)**.
