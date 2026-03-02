# Lesson 4.1 — Building a "Security AI Memory" with Milvus (Local Vector Database)

> **Objective:** Build a local, self-hosted retrieval memory system that
> stores cybersecurity standards and best practices (NIST, CIS, MITRE,
> OWASP, Docker hardening, etc.) in Milvus as searchable embeddings.
>
> **Why this matters:** The RAG assistant (and IDE integrations) should
> answer security questions using grounded frameworks and controls
> rather than generating unsupported responses.

------------------------------------------------------------------------

## Learning Outcomes

By the end of this lesson, students should be able to:

- Explain what "AI memory" means in the context of this project (and what it does not mean)
- Organize a security corpus inside `security-memory/data/`
- Ingest that corpus into a dedicated Milvus collection (`ExpandedVSCodeMemory`)
- Verify ingestion worked successfully
- Understand how chunking, overlap, tags, and top-k influence retrieval quality

------------------------------------------------------------------------

## 1) Mental Model (Project Context)

### What "AI memory" means here

In this lab, **AI memory = retrieval memory**. It is **not**:

- A fine-tuned model
- A system where the model "remembers everything forever"
- A database of model-generated thoughts

It *is*:

- A curated reference corpus
- Vector embeddings of that corpus
- A searchable Milvus collection
- A retrieval pipeline that feeds relevant chunks into an LLM

The model itself is unchanged. The improvement comes from providing higher-quality context.

------------------------------------------------------------------------

## 2) What Milvus Stores

Unlike Qdrant's schemaless "points" or Weaviate's flexible class properties, **Milvus requires a fully typed schema defined before any data is inserted**. Think of it like a table in a relational database — every field must be declared upfront.

Each row stored in the `ExpandedVSCodeMemory` collection contains:

1. **`id`** — an INT64 primary key, auto-assigned by Milvus
2. **`embedding`** — a FLOAT_VECTOR[768] (the semantic meaning of the chunk)
3. **`text`** — the actual chunk text (VARCHAR)
4. **`title`** — document title derived from the filename (VARCHAR)
5. **`source`** — the subfolder name, e.g. `cis`, `owasp` (VARCHAR)
6. **`tags`** — a JSON-encoded list stored as a string, e.g. `["cis","docker"]` (VARCHAR)
7. **`chunk_index`** — position of this chunk within its source document (INT64)
8. **`doc_path`** — full path to the source file inside the container (VARCHAR)

The vector enables similarity search. The scalar fields provide context returned to the LLM and user.

**Why typed schemas matter:** if you change the embedding model (which changes the vector dimension), or add a new field, you must drop and recreate the collection. You cannot alter a Milvus schema after it is created.

------------------------------------------------------------------------

## 3) End-to-End Flow

Security documents (.md / .txt)\
→ chunking (split into smaller pieces)\
→ embeddings via Ollama (convert chunks into 768-dimensional vectors)\
→ Milvus columnar insert (store vectors + typed metadata)\
→ `collection.flush()` (persist segments to MinIO storage)

User question\
→ embed the question via Ollama\
→ Milvus HNSW cosine similarity search (top-k chunks)\
→ retrieved chunks passed into LLM\
→ grounded answer

This architecture mirrors production-grade RAG systems. The Milvus-specific step worth noting is `flush()` — unlike Qdrant and Weaviate, Milvus requires an explicit flush to persist data from memory to the underlying MinIO object storage.

------------------------------------------------------------------------

## 4) Folder Structure

```
security-memory/
  data/
    nist/
    cis/
    mitre/
    owasp/
  scripts/
  prompts/
  docs/
  mcp/
  slides/
```

This folder is intentionally separated from the main lab data. The original lab validates that the RAG pipeline functions correctly. This expanded memory system provides structured reference knowledge stored in its own dedicated Milvus collection.

------------------------------------------------------------------------

## 5) Adding Datasets

The `security-memory/data/` directory contains the security corpus.

### Recommended File Types

- `.md` (preferred — preserves structure)
- `.txt`

### Avoid

- Raw PDFs (convert to text first)
- Large unstructured file dumps

### Suggested Organization

```
security-memory/data/
  nist/nist-csf.md
  cis/cis-controls-v8.md
  mitre/attack-enterprise.md
  owasp/owasp-top10.md
  cis/cis-docker-benchmark.md
```

This organization improves clarity and filtering. The subfolder name becomes the `source` field and also drives automatic tag inference — a file under `cis/` gets the tag `cis`, a file under `cis/` with `docker` in its filename gets both `cis` and `docker`.

Files already exist in this folder but feel free to add your own to increase the RAG system's cybersecurity capability.

------------------------------------------------------------------------

## 6) Separate Milvus Collection

Instead of mixing content into the main `LabDoc` collection, this implementation uses a dedicated collection:

```
SECURITY_COLLECTION=ExpandedVSCodeMemory
```

This separation prevents retrieval noise and keeps the security corpus isolated. In Milvus, a collection is roughly equivalent to a table — you can have many collections, each with its own schema and index, and querying one never touches another.

------------------------------------------------------------------------

## 7) Environment Variables for Retrieval Control

These are already set in `docker-compose.yml` and `.env.example`:

```
SECURITY_COLLECTION=ExpandedVSCodeMemory
SECURITY_TOP_K=6
SECURITY_CHUNK_CHARS=1200
SECURITY_CHUNK_OVERLAP=200
SECURITY_EMBED_MODEL=nomic-embed-text
SECURITY_EMBED_DIM=768
```

### Parameter Meanings

- `SECURITY_TOP_K` → number of chunks retrieved per query
- `SECURITY_CHUNK_CHARS` → size of each chunk in characters
- `SECURITY_CHUNK_OVERLAP` → overlap between adjacent chunks
- `SECURITY_EMBED_DIM` → must match the embedding model's output dimension

Larger chunks provide more context. Smaller chunks improve precision. Overlap prevents boundary context loss.

**Important:** `SECURITY_EMBED_DIM` must exactly match the dimension produced by `SECURITY_EMBED_MODEL`. For `nomic-embed-text` that is 768. If you switch models, update this value and recreate the collection — Milvus will reject vectors of the wrong dimension.

Open your `.env` file and confirm these values are present before running ingestion.

------------------------------------------------------------------------

## 8) Running Ingestion

At this stage, the security corpus exists on disk inside:

```
security-memory/data/
```

However, Milvus does **not** automatically index these files. The documents must be:

1. Read from disk
2. Split into chunks
3. Converted into embeddings via Ollama
4. Inserted into the `ExpandedVSCodeMemory` collection using the pymilvus SDK
5. Flushed to MinIO storage

This entire pipeline is handled by the ingestion module.

------------------------------------------------------------------------

### Why Container Mode Is Required

Run ingestion inside the running `ingestion-api` container:

```bash
docker exec -i ingestion-api python -m app.security_memory.ingest
```

This is required (not just recommended) because:

- The container already has access to Milvus at `milvus:19530` via the internal Docker network
- Milvus uses **gRPC on port 19530**, not HTTP — you cannot call it with curl from your laptop
- The pymilvus SDK is installed inside the container
- It avoids platform and DNS inconsistencies
- It guarantees alignment with how the API connects to Milvus

**Why is gRPC relevant here?** Unlike Qdrant (REST on 6333) and Weaviate (REST on 8080), Milvus communicates over gRPC. The pymilvus SDK handles this transparently, but it means Milvus is not accessible from your laptop the same way — only containers on the internal Docker network can reach it.

Based on the size of the corpus being ingested, ingestion could take anywhere from minutes to 1–2 hours. Each chunk requires a separate Ollama embedding call.

To check if ingestion is occurring, open a new terminal tab and run:

```bash
docker stats
```

If ingestion is active, Ollama CPU usage should be high.

You can also run:

```bash
docker logs -f ingestion-api
```

in a new tab to see chunking progress, embedding calls, and activity logs.

*If these are active and Ollama CPU use is high, don't cancel the ingestion — it's just taking some time.*

------------------------------------------------------------------------

### What Happens During Ingestion

When this command runs, the following occurs:

1. The script scans `security-memory/data/` recursively for `.md` and `.txt` files
2. Each file is read and normalized (CRLF → LF, collapsed whitespace)
3. Tags are inferred from the file path
4. The content is split into overlapping fixed-size chunks
5. Each chunk is embedded via Ollama (`nomic-embed-text`)
6. Chunks are collected into batches of 32
7. Each batch is inserted into Milvus using **columnar format** — all values for each field are passed as a list, not row-by-row
8. `collection.flush()` is called to persist segment files to MinIO

**Columnar insert** is a Milvus-specific pattern. Instead of inserting one record at a time like a SQL INSERT, you pass all values for each field as a separate list:

```python
data = [
    [vec1, vec2, ...],          # embeddings (list of vectors)
    ["chunk text 1", "chunk text 2", ...],  # text
    ["Title 1", "Title 2", ...],            # title
    ...
]
collection.insert(data)
```

This is how Milvus stores data internally (column-oriented segments) and is required by the SDK.

If ingestion completes without errors, vectors should now exist inside Milvus. If errors occur:

- Check `docker logs ingestion-api`
- Confirm Milvus is running and healthy: `docker compose ps milvus`
- Confirm etcd and MinIO are healthy (Milvus depends on both)
- Verify `SECURITY_EMBED_DIM` matches the model

------------------------------------------------------------------------

## 9) Verifying Ingestion

Ingestion completing without error does **not** guarantee that data was stored correctly. Verification is required.

------------------------------------------------------------------------

### Option 1: pymilvus Direct Check

Since Milvus uses gRPC (not HTTP), there is no browser dashboard like Qdrant's. Verify directly using the pymilvus SDK from inside the container:

```bash
docker exec -i ingestion-api python - <<'PY'
from pymilvus import connections, Collection, utility
import os

connections.connect(
    host=os.getenv("MILVUS_HOST", "milvus"),
    port=int(os.getenv("MILVUS_PORT", "19530")),
    timeout=10,
)

collection_name = os.getenv("SECURITY_COLLECTION", "ExpandedVSCodeMemory")

if not utility.has_collection(collection_name):
    print(f"ERROR: collection '{collection_name}' does not exist")
else:
    col = Collection(collection_name)
    col.load()
    print(f"Collection: {collection_name}")
    print(f"Entities:   {col.num_entities}")
    print(f"Schema fields: {[f.name for f in col.schema.fields]}")
PY
```

Interpretation:

- `Entities > 0` → ingestion succeeded
- `Entities = 0` → collection exists but no data was inserted
- `ERROR: collection does not exist` → ingestion did not run or collection name mismatch

------------------------------------------------------------------------

### Option 2: API Health Check

```bash
EDGE_API_KEY=$(grep -E '^EDGE_API_KEY=' .env | cut -d= -f2-)
curl -sS http://localhost:8088/memory/health \
  -H "X-API-Key: $EDGE_API_KEY" | python -m json.tool
```

Expected response:

```json
{
  "ok": true,
  "collection": "ExpandedVSCodeMemory",
  "milvus_host": "milvus:19530",
  "points_count": 183,
  "note": null
}
```

- `ok: true` → Milvus is reachable and the collection exists
- `points_count > 0` → ingestion succeeded
- `points_count: 0` → re-run ingestion
- `ok: false` → Milvus is not reachable; check `docker compose ps milvus`

------------------------------------------------------------------------

### Option 3: Sample a Few Chunks

```bash
docker exec -i ingestion-api python - <<'PY'
from pymilvus import connections, Collection
import os

connections.connect(
    host=os.getenv("MILVUS_HOST", "milvus"),
    port=int(os.getenv("MILVUS_PORT", "19530")),
    timeout=10,
)

col = Collection(os.getenv("SECURITY_COLLECTION", "ExpandedVSCodeMemory"))
col.load()

results = col.query(
    expr="chunk_index == 0",
    output_fields=["title", "source", "tags", "doc_path"],
    limit=10,
)
for r in results:
    print(f"  {r['source']:12} | {r['title'][:40]:40} | tags={r['tags']}")
PY
```

This confirms metadata was stored correctly alongside the vectors.

------------------------------------------------------------------------

## 10) Smoke Test Retrieval

Ingestion verifies storage. Retrieval testing verifies usability.

```bash
EDGE_API_KEY=$(grep -E '^EDGE_API_KEY=' .env | cut -d= -f2-)
curl -i -sS -X POST http://localhost:8088/memory/query \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $EDGE_API_KEY" \
  -d '{"query":"what is OWASP A01", "tags":["owasp"], "top_k":5}'
```

This simulates how a real RAG system queries Milvus.

------------------------------------------------------------------------

### Expected Behavior

The response should contain:

- `results` with at least one OWASP-related chunk
- `score` values — in this Milvus version, scores are **cosine similarity** values between 0 and 1 (higher = better match). This is different from some other databases that return distance — no conversion is needed here.
- `title`, `source`, `tags`, and `text` fields for each result

------------------------------------------------------------------------

### What This Test Confirms

This validates:

- The embeddings service (Ollama) is operational
- Vectors were stored correctly in Milvus
- The HNSW cosine index is working
- The gRPC connection from ingestion-api to Milvus is stable
- Metadata scalar fields are retrievable alongside vectors

If zero results appear:

- Ingestion may not have run
- The collection name may be incorrect (check `SECURITY_COLLECTION` in `.env`)
- The embeddings service may not be ready
- The query may not match corpus content — try a broader query without `tags`

------------------------------------------------------------------------

## When You Must Recreate the Collection

If you change any of the following, you must drop and recreate the collection — existing vectors and new vectors will be incompatible:

- The embedding model (different models produce vectors in different spaces)
- The embedding dimension (`SECURITY_EMBED_DIM`)
- The distance metric (cosine scores become meaningless if switched to L2)
- The schema (adding or removing fields)

To recreate:

```bash
docker exec -i ingestion-api python - <<'PY'
from pymilvus import connections, utility, Collection
import os

connections.connect(
    host=os.getenv("MILVUS_HOST", "milvus"),
    port=int(os.getenv("MILVUS_PORT", "19530")),
    timeout=10,
)

name = os.getenv("SECURITY_COLLECTION", "ExpandedVSCodeMemory")
if utility.has_collection(name):
    Collection(name).drop()
    print(f"Dropped: {name}")
else:
    print("Collection does not exist — nothing to drop.")
PY

docker exec -i ingestion-api python -m app.security_memory.ingest
```

------------------------------------------------------------------------

## Completion Checklist

The lesson is complete when all of the following are true:

- `security-memory/data/` contains structured reference documents
- Ingestion runs successfully without errors
- `ExpandedVSCodeMemory` exists in Milvus with `num_entities > 0`
- API health check returns `ok: true` and `points_count > 0`
- Retrieval smoke test returns relevant chunks with meaningful scores
- Retrieved chunks contain metadata (title, source, tags, text)

At this point:

- The security corpus is indexed in Milvus
- The HNSW cosine index is built and loaded
- The retrieval system is validated
- The memory layer is ready for API exposure

------------------------------------------------------------------------

[Lesson 2](02-api-tool.md)
