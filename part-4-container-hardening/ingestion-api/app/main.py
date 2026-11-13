"""
main.py: FastAPI entry point for the Part 3 RAG API (prompt injection lab).

Routes
  GET  /health           database + counters + which guards are on
  POST /ingest           validate -> [GUARD_INGEST] -> embed -> insert (writer role)
  POST /chat             [GUARD_INPUT] -> retrieve (reader role) -> prompt
                         [GUARD_PROMPT] -> generate -> [GUARD_OUTPUT]
  GET  /debug/retrieve   retrieval only                     (ENABLE_DEBUG_ENDPOINTS)
  POST /debug/prompt     show the exact messages sent       (ENABLE_DEBUG_ENDPOINTS)
  GET  /debug/scan       scan STORED documents for injection (ENABLE_DEBUG_ENDPOINTS)

Every time a guard fires, a single-line JSON "security_event" is written
to the log, so blocked attacks can be found, counted, and investigated.
"""

import asyncio
import hmac
import json
import logging
import os
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Query, Request

from . import db, guards
from .embeddings import embed_texts
from .rag import build_messages, ollama_chat, render, retrieve_sources
from .schemas import ArticleIn, ChatIn

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger("rag-api")
security_log = logging.getLogger("security")

def _read_key() -> str:
    """Prefer a mounted secret file (Part 4) over an environment variable.
    Environment variables are visible in `docker inspect` to anyone who can
    run Docker commands; a file mounted read-only from secrets/ is not."""
    path = os.getenv("EDGE_API_KEY_FILE", "")
    if path:
        with open(path, "r", encoding="utf-8") as f:
            return f.read().strip()
    return os.getenv("EDGE_API_KEY", "")


EDGE_API_KEY         = _read_key()
ENABLE_DEBUG         = os.getenv("ENABLE_DEBUG_ENDPOINTS", "false").lower() == "true"
RETRIEVE_TIMEOUT_S   = float(os.getenv("RETRIEVE_TIMEOUT_S", "30"))
CHAT_TOTAL_TIMEOUT_S = float(os.getenv("CHAT_TOTAL_TIMEOUT_S", "300"))

START = time.time()
COUNTS = {
    "ingested": 0, "chats": 0, "errors": 0,
    "blocked_inputs": 0, "blocked_documents": 0, "blocked_outputs": 0, "filtered_outputs": 0,
}


def security_event(kind: str, rid: str, **details) -> None:
    security_log.warning(json.dumps({"security_event": kind, "request_id": rid, **details}))


@asynccontextmanager
async def lifespan(_: FastAPI):
    await db.open_pools()
    logger.info("Guards: %s", guards.status())
    yield
    await db.close_pools()


app = FastAPI(title="Secure AI Lab: Prompt Injection", lifespan=lifespan)


@app.middleware("http")
async def add_request_id(request: Request, call_next):
    request.state.request_id = request.headers.get("X-Request-Id") or str(uuid.uuid4())
    response = await call_next(request)
    response.headers["X-Request-Id"] = request.state.request_id
    return response


def require_api_key(request: Request) -> None:
    if not EDGE_API_KEY:
        raise HTTPException(status_code=500, detail="Server misconfigured.")
    incoming = request.headers.get("X-API-Key", "")
    if not incoming:
        raise HTTPException(status_code=401, detail="Missing X-API-Key header.")
    if not hmac.compare_digest(incoming, EDGE_API_KEY):
        raise HTTPException(status_code=403, detail="Invalid API key.")


def require_debug() -> None:
    if not ENABLE_DEBUG:
        raise HTTPException(status_code=404, detail="Not found.")


def _fail(rid: str, where: str, e: Exception) -> HTTPException:
    COUNTS["errors"] += 1
    logger.exception("[%s] %s failed: %s", rid, where, type(e).__name__)
    return HTTPException(status_code=500, detail=f"Internal error. Request id: {rid}")


@app.get("/health")
async def health():
    ok = await db.ready()
    return {
        "ok": ok,
        "db_ok": ok,
        "tenant": db.APP_TENANT,
        "guards": guards.status(),
        "uptime_s": int(time.time() - START),
        **COUNTS,
    }


@app.post("/ingest", dependencies=[Depends(require_api_key)])
async def ingest(article: ArticleIn, request: Request):
    rid = request.state.request_id
    verdict = guards.screen_document(f"{article.title}\n{article.text}")
    if verdict.blocked:
        COUNTS["blocked_documents"] += 1
        security_event("document_blocked", rid, title=article.title[:80],
                       score=verdict.score, reasons=verdict.reasons)
        raise HTTPException(
            status_code=422,
            detail={"error": "document rejected by injection screening",
                    "reasons": verdict.reasons, "request_id": rid},
        )
    try:
        vec = (await embed_texts([article.text]))[0]
        res = await db.insert_doc(article.model_dump(), vec)
        COUNTS["ingested"] += 1
        return {"status": "ok", **res}
    except Exception as e:
        raise _fail(rid, "/ingest", e)


@app.post("/chat", dependencies=[Depends(require_api_key)])
async def chat(payload: ChatIn, request: Request):
    rid = request.state.request_id

    # Layer 1: screen the user's message
    verdict = guards.screen_input(payload.message)
    if verdict.blocked:
        COUNTS["blocked_inputs"] += 1
        security_event("input_blocked", rid, score=verdict.score, reasons=verdict.reasons)
        raise HTTPException(
            status_code=400,
            detail={"error": "message rejected by injection screening",
                    "reasons": verdict.reasons, "request_id": rid},
        )

    async def _run():
        sources = await asyncio.wait_for(retrieve_sources(payload.message), RETRIEVE_TIMEOUT_S)
        messages = build_messages(payload.message, sources, payload.detail_level)  # layer 3
        answer = await ollama_chat(messages)
        return answer, sources

    try:
        answer, sources = await asyncio.wait_for(_run(), CHAT_TOTAL_TIMEOUT_S)
    except asyncio.TimeoutError:
        COUNTS["errors"] += 1
        raise HTTPException(status_code=504, detail=f"Chat timed out. Request id: {rid}")
    except Exception as e:
        raise _fail(rid, "/chat", e)

    # Layer 4: check the answer before the user sees it
    filtered = {}
    if guards.GUARD_OUTPUT:
        check = guards.filter_output(answer)
        if check.blocked:
            COUNTS["blocked_outputs"] += 1
            security_event("output_blocked", rid, reasons=check.reasons)
        elif check.reasons:
            COUNTS["filtered_outputs"] += 1
            security_event("output_filtered", rid, reasons=check.reasons)
        answer = check.text
        filtered = {"output_filter": check.reasons}

    COUNTS["chats"] += 1
    return {"answer": answer, "sources": sources, **filtered}


@app.get("/debug/retrieve", dependencies=[Depends(require_api_key), Depends(require_debug)])
async def debug_retrieve(request: Request, q: str = Query(min_length=2, max_length=2000)):
    try:
        return {"query": q, "sources": await retrieve_sources(q)}
    except Exception as e:
        raise _fail(request.state.request_id, "/debug/retrieve", e)


@app.post("/debug/prompt", dependencies=[Depends(require_api_key), Depends(require_debug)])
async def debug_prompt(payload: ChatIn, request: Request):
    try:
        sources = await retrieve_sources(payload.message)
        messages = build_messages(payload.message, sources, payload.detail_level)
        # Hide the canary: debug output is still output
        text = render(messages).replace(guards.CANARY, "INTERNAL-REF-[hidden]")
        return {"prompt": text, "prompt_chars": len(text), "hardened": guards.GUARD_PROMPT}
    except Exception as e:
        raise _fail(request.state.request_id, "/debug/prompt", e)


@app.get("/debug/scan", dependencies=[Depends(require_api_key), Depends(require_debug)])
async def debug_scan(request: Request):
    """Score every stored document with the ingest screen, whether or not
    GUARD_INGEST is on. Finds poison that got in before the guard existed."""
    try:
        docs = await db.all_docs()
        flagged = []
        for d in docs:
            v = guards.screen_document(f"{d['title']}\n{d['content']}")
            if v.score >= guards.DOC_THRESHOLD:
                flagged.append({"id": d["id"], "title": d["title"], "score": v.score, "reasons": v.reasons})
        return {"scanned": len(docs), "flagged": flagged}
    except Exception as e:
        raise _fail(request.state.request_id, "/debug/scan", e)
