# Lesson 08 — The Gradio UI

> **Goal:** use the browser chat interface, understand the source citations
> panel, and debug UI-specific issues.

---

## Opening the UI

Navigate to `http://localhost:7860` in your browser. You should see a chat
interface with a message input at the bottom and a sources panel on the right
(or below, depending on viewport size).

If the page is blank or shows a connection error, check:

```bash
docker compose logs gradio | tail -20
```

---

## What the UI sends

The Gradio app is a thin client. Every message you type becomes a POST request
to NGINX:

```
POST http://nginx:80/chat
X-API-Key: <from GRADIO_API_KEY env var>
{"message": "your question here"}
```

The response `{ "answer": "...", "sources": [...] }` is rendered in the chat
window.

Because Gradio goes through NGINX, it exercises the same auth path as a curl
command. This means Gradio will show a 401 error if `EDGE_API_KEY` in `.env`
does not match what NGINX expects.

---

## Reading the sources panel

Each answer includes a sources section showing:
- **Title** of the retrieved document
- **URL** (if provided during ingestion)
- **Cosine score** — similarity between your question and the source (0–1,
  higher is more similar)
- **Snippet** — the first `RAG_MAX_SOURCE_CHARS` characters of the stored text

If the sources panel is empty, retrieval returned no results — check that you
have ingested documents (Lesson 06).

---

## Debugging order

When something goes wrong in the UI, work from the outside in:

### 1. Is NGINX reachable?

```bash
curl -s -o /dev/null -w "%{http_code}" http://localhost:8088/health \
  -H "X-API-Key: $(grep EDGE_API_KEY .env | cut -d= -f2-)"
```

Expected: `200`. If `000` (no connection), NGINX is not running:

```bash
docker compose restart nginx
```

### 2. Is the API working?

```bash
EDGE_API_KEY=$(grep -E '^EDGE_API_KEY=' .env | cut -d= -f2-)
curl -s -X POST http://localhost:8088/chat \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $EDGE_API_KEY" \
  -d '{"message": "test"}' | python3 -m json.tool
```

If this works but the UI does not, the problem is in the Gradio container
itself.

### 3. Check Gradio logs

```bash
docker compose logs gradio
```

Look for auth errors (`401`) or connection refused to `nginx`.

### 4. Key mismatch

If Gradio shows `401 Unauthorized`, the `EDGE_API_KEY` in `.env` may have
changed after Gradio started:

```bash
docker compose restart gradio
```

---

## Restarting just the UI

```bash
docker compose restart gradio
```

This does not affect Milvus, Ollama, or any stored data.

---

## Checkpoint

You are done when:
- The Gradio UI loads at `http://localhost:7860`.
- You can type a question and receive a grounded answer with sources.
- You understand what a 401 in the UI means and how to fix it.

Continue to **[Lesson 09 — Operations](09-operations.md)**.
