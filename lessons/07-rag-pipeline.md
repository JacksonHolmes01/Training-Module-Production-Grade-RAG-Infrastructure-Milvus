# Lesson 07 — The RAG Pipeline

> **Goal:** pull an Ollama model, trace every stage of the
> retrieve-prompt-generate pipeline, and tune `RAG_TOP_K`.

---

## 1) Pull an Ollama model

The stack uses Ollama for both **embedding** (`nomic-embed-text`) and
**generation** (e.g., `llama3.2:1b`). Pull them now:

```bash
# Generation model (~800 MB)
docker exec ollama ollama pull llama3.2:1b

# Embedding model (~274 MB) — used by ingestion-api automatically
docker exec ollama ollama pull nomic-embed-text
```

Watch the download progress. Both models are cached in the `ollama_data`
volume so you only download them once.

Confirm they are available:

```bash
docker exec ollama ollama list
```

Expected output:

```
NAME                    ID              SIZE    MODIFIED
llama3.2:1b             ...             815 MB  ...
nomic-embed-text        ...             274 MB  ...
```

---

## 2) The RAG pipeline in code

The pipeline lives in `ingestion-api/app/rag.py`. The three stages are:

### Stage 1 — Retrieve (`retrieve_sources`)

```
question string
       │
       ▼
embed_texts([question])  →  768-dim float vector  (Ollama nomic-embed-text)
       │
       ▼
Collection.search(
    data=[vector],
    anns_field="embedding",
    param={"metric_type": "COSINE", "params": {"ef": max(k*4, 64)}},
    limit=k,
    output_fields=[text, title, url, ...]
)
       │
       ▼
List[Dict]  —  top-k documents with cosine scores
```

`ef` (the HNSW exploration factor) controls recall vs. speed. Higher ef
examines more candidates and improves recall at the cost of latency.
`ef = max(k*4, 64)` is a safe default.

### Stage 2 — Build prompt (`build_prompt`)

```
[system rules]
[detail-level instructions]  ← auto-detected from question complexity
[source 1 title + snippet]
[source 2 title + snippet]
...
[user question]
Answer:
```

The detail level classifier (`classify_detail_level`) looks for code blocks,
CLI commands, error traces, and question length to pick *basic*, *standard*,
or *advanced* response style automatically.

### Stage 3 — Generate (`ollama_generate`)

```
POST http://ollama:11434/api/generate
{
  "model": "llama3.2:1b",
  "prompt": "<built prompt>",
  "stream": false
}
```

Returns the model's response as a string.

---

## 3) Trace each stage with debug endpoints

Make sure you have at least a few documents ingested (Lesson 06) before
running these.

### Debug: retrieval only

```bash
EDGE_API_KEY=$(grep -E '^EDGE_API_KEY=' .env | cut -d= -f2-)

curl -s -X POST http://localhost:8088/debug/retrieve \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $EDGE_API_KEY" \
  -d '{"query": "how does a reverse proxy work?", "k": 3}' \
  | python3 -m json.tool
```

You should see a list of source dicts with `title`, `score`, and `snippet`.
If results are empty or irrelevant, check that you ingested related documents
and that the `nomic-embed-text` model is loaded in Ollama.

### Debug: retrieval + prompt (no generation)

```bash
curl -s -X POST http://localhost:8088/debug/prompt \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $EDGE_API_KEY" \
  -d '{"query": "how does a reverse proxy work?"}' \
  | python3 -m json.tool
```

The response includes the full prompt string that would be sent to Ollama.
Read it to confirm the retrieved sources are relevant.

### Debug: generation only (no retrieval)

```bash
curl -s -X POST http://localhost:8088/debug/ollama \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $EDGE_API_KEY" \
  -d '{"prompt": "In one sentence, what is a vector database?"}' \
  | python3 -m json.tool
```

Confirms Ollama is reachable and generating. Isolates generation failures from
retrieval failures.

---

## 4) Full end-to-end chat

```bash
curl -s -X POST http://localhost:8088/chat \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $EDGE_API_KEY" \
  -d '{"message": "What is NGINX and how is it used here?"}' \
  | python3 -m json.tool
```

Expected response shape:

```json
{
  "answer": "NGINX is a high-performance web server and reverse proxy. In this lab...",
  "sources": [
    {
      "title": "NGINX Overview",
      "url": "https://nginx.org/en/docs/",
      "score": 0.88,
      "snippet": "..."
    }
  ]
}
```

---

## 5) Tune `RAG_TOP_K`

`RAG_TOP_K` controls how many documents are retrieved and injected into the
prompt. Edit `.env`:

```ini
RAG_TOP_K=4   # default
```

Then restart ingestion-api:

```bash
docker compose restart ingestion-api
```

| Value | Effect |
|-------|--------|
| 1–2 | Faster, less context. Risk of missing relevant documents. |
| 4 (default) | Good balance for a small corpus. |
| 8–10 | More context, but prompt length grows. May exceed model context window. |

For `llama3.2:1b` (4K context), keep `RAG_TOP_K` ≤ 6 with short snippets.
Larger models handle higher values.

`RAG_MAX_SOURCE_CHARS` (default 800) caps each retrieved snippet. Reducing it
allows higher `RAG_TOP_K` without overflowing the context window.

---

## 6) Debugging a silent / empty answer

If the chat endpoint returns an empty or evasive answer:

1. **Check retrieval** — run `/debug/retrieve`. If it returns empty, either
   no documents match or the collection is empty.

2. **Check the prompt** — run `/debug/prompt`. Look for `(no sources retrieved)`.
   If so, ingestion may have failed.

3. **Check Ollama** — run `/debug/ollama` with a simple prompt. If it fails,
   the model may not be pulled or Ollama is out of memory.

4. **Check Milvus collection is loaded**:

```bash
docker exec ingestion-api python3 -c "
from pymilvus import Collection, connections
connections.connect(host='milvus', port='19530')
col = Collection('LabDoc')
col.load()
print('Row count:', col.num_entities)
"
```

If `num_entities` is 0, the collection is empty — re-run ingestion from
Lesson 06.

---

## Checkpoint

You are done when:
- `ollama list` shows both `llama3.2:1b` and `nomic-embed-text`.
- `/debug/retrieve` returns relevant results.
- `/chat` returns a grounded answer with source citations.

Continue to **[Lesson 08 — Gradio UI](08-gradio-ui.md)**.
