# Lesson 4.2 — Expose Your Security Memory as an API Tool

> **What you're building:** a small set of API endpoints that turn your `ExpandedVSCodeMemory` Milvus collection into something your IDE and AI assistant can actually *call* as a tool.
>
> **IDE** stands for **Integrated Development Environment** — it's the application you write code in (VS Code, for example). IDEs can be extended with AI tools that call APIs like the one you're building here.
>
> This is the step that bridges "we have a Milvus collection full of security knowledge" to "my IDE can pull up the right standard and cite it while reviewing my code."

---

## Learning Outcomes

By the end of this lesson, you will:

- Understand what a "retrieval tool contract" means and why the request/response shape matters
- Test the `/memory/health` and `/memory/query` endpoints that are already wired into this repo
- Understand how Milvus tag filtering differs from Qdrant and Weaviate
- (Optional) Connect memory retrieval results into your `/chat` pipeline

---

## 1) What Is a "Tool Contract" and Why Does It Matter?

Before writing any code, it helps to understand what we're building conceptually.

A **tool contract** is simply an agreement about how your API behaves — what it expects as input, and what it promises to return. This matters a lot in AI systems because the LLM (or your IDE extension) will be calling this endpoint programmatically. If the response shape is unpredictable or inconsistent, the tool breaks.

Think of it like a vending machine: you press B4, you always get the same thing. Your API should work the same way.

### Request Shape

When something (your IDE, your assistant, a script) wants to query security memory, it sends:

```json
{
  "query": "review this docker-compose for security issues",
  "tags": ["docker", "cis"],
  "top_k": 6
}
```

- `query` — the natural language question or topic you're searching for
- `tags` — optional filters to narrow results to specific frameworks (e.g., only CIS, only OWASP)
- `top_k` — how many chunks to return (more = more context, but also more noise)

### Response Shape

The API returns a structured list of matching chunks:

```json
{
  "query": "...",
  "collection": "ExpandedVSCodeMemory",
  "top_k": 6,
  "results": [
    {
      "score": 0.887,
      "title": "CIS Docker Benchmark",
      "source": "cis",
      "tags": ["docker", "cis"],
      "chunk_index": 12,
      "doc_path": "/securitymemory/data/cis/cis-docker-benchmark.md",
      "text": ".... chunk text ...."
    }
  ]
}
```

**Why is this shape useful?**

- `results[*].text` is the actual content you paste into a prompt or show to a user
- `tags` and `doc_path` tell you *where* the answer came from — making results explainable and auditable, not just "the AI said so"
- `score` is the similarity score from Milvus — **in this version, scores are cosine similarity values between 0 and 1, where higher means a stronger match**. This is different from some databases that return distance values. No conversion is needed.

---

## 2) What Files Power This Endpoint

This repo already has a complete `security_memory` package wired into the ingestion API. Unlike the Qdrant and Weaviate versions of this lab where these files live in a `patches/` folder, in this Milvus version they live directly inside the API:

```
ingestion-api/app/security_memory/
  router.py
  schemas.py
  store.py
  ingest.py
  __init__.py
```

Here's what each file is responsible for:

**`router.py`** — defines the FastAPI endpoints (`/memory/health` and `/memory/query`). This is the "front door" of the tool — it receives HTTP requests and hands them off to `store.py`.

**`schemas.py`** — defines the Pydantic models that describe what valid requests and responses look like. Pydantic will automatically validate incoming data and return clear error messages if something is malformed.

**`store.py`** — the core logic. It connects to Milvus via the pymilvus SDK over gRPC, embeds the query via Ollama, then calls `collection.search()` with HNSW parameters to find the closest matching chunks. It also powers the `/memory/health` check by connecting to Milvus and reporting collection entity count.

**`ingest.py`** — the ingestion script you ran in Lesson 4.1. It lives here so you can re-run it inside the container if you add new documents to `security-memory/data/`.

**`__init__.py`** — an empty file that tells Python "this folder is a package." Without it, the imports won't work.

**`main.py`** already contains this line, which registers all memory endpoints on startup:

```python
from .security_memory.router import router as memory_router
app.include_router(memory_router)
```

> **All of these files already exist in the repo** — you don't need to create or copy anything. This is already wired in.

---

## 3) How Milvus Tag Filtering Works

Tag filtering in this Milvus version works differently from Qdrant and Weaviate, and it's worth understanding before you start testing.

In Qdrant, tags are stored as a native array field and filtered with a structured filter object:
```python
filter = {"should": [{"key": "tags", "match": {"value": "docker"}}]}
```

In Weaviate, tags are a `text[]` property filtered with GraphQL operands.

In **Milvus**, tags are stored as a **JSON string** inside a VARCHAR field — for example `'["cis","docker"]'`. Filtering uses a **SQL-like boolean expression** with `LIKE`:

```python
expr = 'tags like \'%"docker"%\' or tags like \'%"cis"%\''
```

The `%"docker"%` pattern (with quotes inside) prevents partial matches — `"cis"` won't accidentally match `"cisco"` because the double quotes are part of the stored JSON.

This is an `OR` filter — a chunk matches if it contains **any** of the requested tags. A chunk tagged `["cis","docker"]` will match a query for either `"cis"` or `"docker"`.

---

## 4) Test Your Endpoints

All requests go through NGINX, which enforces your API key. First, pull your key from `.env`:

```bash
EDGE_API_KEY=$(grep -E '^EDGE_API_KEY=' .env | cut -d= -f2-)
```

This command reads your `.env` file, finds the line starting with `EDGE_API_KEY=`, and stores the value in a shell variable so you don't have to copy-paste it manually.

### Test 1: Health Check

```bash
curl -sS -H "X-API-Key: $EDGE_API_KEY" \
  http://localhost:8088/memory/health | python -m json.tool
```

You should see something like:

```json
{
  "ok": true,
  "collection": "ExpandedVSCodeMemory",
  "milvus_host": "milvus:19530",
  "points_count": 183,
  "note": null
}
```

If `ok` is `false` — Milvus is not reachable. Check `docker compose ps milvus` and `docker logs milvus`.

If `points_count` is 0 — ingestion hasn't run yet. Go back to Lesson 4.1 and re-run ingestion.

If `note` is not null — the collection is empty and the note will tell you how to fix it.

### Test 2: Query

```bash
curl -sS -X POST http://localhost:8088/memory/query \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $EDGE_API_KEY" \
  -d '{"query":"what is broken access control", "tags":["owasp"], "top_k": 5}' \
  | python -m json.tool
```

You should get back a list of results with real text from your OWASP documents and scores between 0 and 1.

If results are empty:
- Check that your OWASP docs were ingested
- Try removing `tags` entirely to search the full collection
- Try a broader query like `"access control vulnerabilities"`

### Test 3: Verify Tag Filtering

Try a query with multiple tags to confirm the OR behavior:

```bash
curl -sS -X POST http://localhost:8088/memory/query \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $EDGE_API_KEY" \
  -d '{"query":"container privilege escalation", "tags":["docker","cis","kubernetes"], "top_k": 4}' \
  | python -m json.tool
```

Results should include chunks from any of those three frameworks.

---

## 5) Optional: Connect Memory to Your `/chat` Endpoint

Once `/memory/query` is working, you can connect it to your existing `/chat` endpoint so that security questions are automatically answered using your curated standards rather than just the model's training data.

**The idea:** before the prompt is built, check whether the question is security-related. If it is, fetch relevant chunks from memory and inject them into the prompt as additional context. If not, the chat works exactly as before.

---

**Step 1 — Add the security classifier function**

Open `ingestion-api/app/main.py`. Scroll to the line that reads `# Core chat implementation` and place this function directly above it:

```python
async def is_security_related(message: str) -> bool:
    """
    Asks Ollama to classify whether the message is security-related.
    Returns True if yes, False if no.
    """
    prompt = (
        "Your only job is to decide if the following message is related to "
        "cybersecurity, infrastructure security, secure coding, or security frameworks "
        "(OWASP, CIS, NIST, MITRE, etc.).\n"
        "Reply with only the word YES or NO. No explanation.\n\n"
        f"Message: {message}"
    )
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.post(
                f"{OLLAMA_BASE_URL}/api/generate",
                json={"model": OLLAMA_MODEL, "prompt": prompt, "stream": False}
            )
            r.raise_for_status()
            answer = (r.json().get("response") or "").strip().upper()
            return answer.startswith("YES")
    except Exception:
        # If the classifier fails for any reason, default to False
        # so the chat still works normally
        return False
```

Breaking this down:

- This uses the same `OLLAMA_BASE_URL`, `OLLAMA_MODEL`, and `/api/generate` endpoint your existing `ollama_generate` function already uses.
- The `try/except` block means if Ollama is slow or unavailable, the function returns `False` and the chat continues normally.
- `answer.startswith("YES")` is defensive — even if the model adds a stray word, it still works correctly.

---

**Step 2 — Add the memory fetch function**

Directly below `is_security_related`, add this second function:

```python
async def get_memory_context(query: str, top_k: int = 4) -> str:
    """
    Calls /memory/query and returns the retrieved chunks as a formatted
    string ready to inject into a prompt.
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.post(
                "http://localhost:8000/memory/query",
                json={"query": query, "top_k": top_k}
            )
            r.raise_for_status()
            data = r.json()
            if not data.get("results"):
                return ""
            chunks = []
            for result in data["results"]:
                chunks.append(f"[{result['title']} | {result['source']}]\n{result['text']}")
            return "\n\n".join(chunks)
    except Exception:
        # If memory fetch fails, return empty string so chat still works
        return ""
```

- `top_k: int = 4` means fetch 4 chunks by default.
- Like the classifier, this has a `try/except` so a memory failure never breaks the chat endpoint.
- The `for` loop labels each chunk with its title and source so the AI can cite where information came from.

> **Note:** `http://localhost:8000/memory/query` works here because both functions live inside the same `ingestion-api` container, where `localhost` refers to itself. This is an internal call that never goes through NGINX, so no API key is needed.

---

**Step 3 — Update `_chat_impl` to use both functions**

Find the `_chat_impl` function. It currently starts like this:

```python
async def _chat_impl(
    message: str,
    rid: str,
    detail_level: Optional[Literal["basic", "standard", "advanced"]] = None,
):
    t0 = time.time()
    # 1) Retrieve
    t_retr0 = time.time()
    sources = await asyncio.wait_for(retrieve_sources(message), timeout=RETRIEVE_TIMEOUT_S)
```

Add the security check right at the top before the retrieve step:

```python
async def _chat_impl(
    message: str,
    rid: str,
    detail_level: Optional[Literal["basic", "standard", "advanced"]] = None,
):
    t0 = time.time()

    # 0) Security memory injection (optional enhancement)
    if await is_security_related(message):
        memory_context = await get_memory_context(message)
    else:
        memory_context = ""

    # 1) Retrieve
    t_retr0 = time.time()
    sources = await asyncio.wait_for(retrieve_sources(message), timeout=RETRIEVE_TIMEOUT_S)
```

Then find the `build_prompt` call a few lines down:

```python
prompt = await asyncio.wait_for(
    asyncio.to_thread(build_prompt, message, sources, detail_level),
    timeout=PROMPT_TIMEOUT_S,
)
```

Replace it with this:

```python
enriched_message = (
    f"Security reference material:\n{memory_context}\n\nQuestion: {message}"
    if memory_context else message
)
prompt = await asyncio.wait_for(
    asyncio.to_thread(build_prompt, enriched_message, sources, detail_level),
    timeout=PROMPT_TIMEOUT_S,
)
```

This prepends the memory chunks to the message before it reaches `build_prompt`. The rest of `_chat_impl` — the Ollama call, the timing, and the response shape — stays completely unchanged.

---

## 6) Security Note: Keep These Endpoints Behind the API Key Gate

The memory endpoints contain curated security reference material that took effort to assemble. Even though the documents themselves aren't secrets, in a real organization this kind of governance material would be access-controlled.

This repo already enforces authentication via an API key header checked by NGINX. Make sure your memory endpoints follow the same rules:

- **Do not** expose `ingestion-api` directly on a host port — traffic should always go through `edge-nginx`
- **Do not** disable or bypass the `X-API-Key` check for convenience during testing (use the `$EDGE_API_KEY` variable instead)

If you're unsure whether your endpoints are protected, re-read the NGINX config to confirm that all `/memory/*` paths require the key.

---

## Checkpoint

You're done when all of the following are true:

- `/memory/health` returns `ok: true` through `http://localhost:8088`
- `/memory/query` returns relevant, non-empty results with scores between 0 and 1
- Tag filtering narrows results as expected
- The base lab still works (chat, ingest, and retrieval are unaffected)

[Lesson 3](03-ide-integration.md)
