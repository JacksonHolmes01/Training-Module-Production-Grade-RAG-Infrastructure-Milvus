"""
main.py — FastAPI application entry point (Milvus version)

Only the import and /health endpoint changed relative to the Qdrant version:
  - qdrant_client  →  milvus_client
  - /health now reports milvus_ok instead of qdrant_ok
  - /ingest response key changed from "qdrant" to "milvus"

All routing, auth, timing, and debug endpoints are structurally identical
so students can compare the two codebases diff-by-diff.
"""

import os
import time
import uuid
import asyncio
import logging
from typing import Optional, Literal

from .security_memory.router import router as memory_router

from fastapi import FastAPI, HTTPException, Request, Query
from fastapi.responses import PlainTextResponse

from .schemas import ArticleIn, ChatIn
from .milvus_client import ready, ensure_collection, insert_doc
from .rag import retrieve_sources, build_prompt, ollama_generate

# ----------------------------- #
# Logging                       #
# ----------------------------- #
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger("ingestion-api")

# ----------------------------- #
# Config                        #
# ----------------------------- #
EDGE_API_KEY         = os.getenv("EDGE_API_KEY", "")
RETRIEVE_TIMEOUT_S   = float(os.getenv("RETRIEVE_TIMEOUT_S", "10"))
PROMPT_TIMEOUT_S     = float(os.getenv("PROMPT_TIMEOUT_S", "5"))
OLLAMA_TIMEOUT_S     = float(os.getenv("OLLAMA_TIMEOUT_S", "120"))
CHAT_TOTAL_TIMEOUT_S = float(os.getenv("CHAT_TOTAL_TIMEOUT_S", "180"))

# ----------------------------- #
# App + counters                #
# ----------------------------- #
app = FastAPI(title="Lab 1 Milvus RAG API")
app.include_router(memory_router)

START        = time.time()
INGEST_COUNT = 0
CHAT_COUNT   = 0
ERROR_COUNT  = 0


# ----------------------------- #
# Middleware: request id        #
# ----------------------------- #
@app.middleware("http")
async def add_request_id(request: Request, call_next):
    request.state.request_id = request.headers.get("X-Request-Id", str(uuid.uuid4()))
    return await call_next(request)


# ----------------------------- #
# Auth helper                   #
# ----------------------------- #
def require_api_key(request: Request):
    if not EDGE_API_KEY:
        raise HTTPException(status_code=500, detail="EDGE_API_KEY is not set on the server.")
    incoming = request.headers.get("X-API-Key", "")
    if not incoming:
        raise HTTPException(status_code=401, detail="Missing X-API-Key header.")
    if incoming != EDGE_API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API key.")


# ----------------------------- #
# Health + metrics              #
# ----------------------------- #
@app.get("/health")
async def health():
    mv_ok = await ready()
    return {
        "ok":        bool(mv_ok),
        "milvus_ok": bool(mv_ok),
        "uptime_s":  int(time.time() - START),
        "ingested":  INGEST_COUNT,
        "chats":     CHAT_COUNT,
        "errors":    ERROR_COUNT,
    }


@app.get("/metrics", response_class=PlainTextResponse)
def metrics():
    return (
        f"ingestion_api_ingested_total {INGEST_COUNT}\n"
        f"ingestion_api_chats_total {CHAT_COUNT}\n"
        f"ingestion_api_errors_total {ERROR_COUNT}\n"
    )


# ----------------------------- #
# Ingest                        #
# ----------------------------- #
@app.post("/ingest")
async def ingest(article: ArticleIn, request: Request):
    """Validate and ingest a document into Milvus."""
    global INGEST_COUNT, ERROR_COUNT
    require_api_key(request)
    rid = getattr(request.state, "request_id", str(uuid.uuid4()))
    try:
        await asyncio.wait_for(ensure_collection(), timeout=15)
        doc = article.model_dump(mode="json")
        res = await asyncio.wait_for(insert_doc(doc), timeout=20)
        INGEST_COUNT += 1
        return {"status": "ok", "milvus": res}
    except asyncio.TimeoutError:
        ERROR_COUNT += 1
        logger.error(f"[{rid}] /ingest: TIMEOUT")
        raise HTTPException(status_code=504, detail="Ingest timed out.")
    except Exception as e:
        ERROR_COUNT += 1
        logger.exception(f"[{rid}] /ingest: ERROR {type(e).__name__}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ----------------------------- #
# Core chat implementation      #
# ----------------------------- #
async def _chat_impl(
    message: str,
    rid: str,
    detail_level: Optional[Literal["basic", "standard", "advanced"]] = None,
):
    t0 = time.time()

    t_retr0 = time.time()
    sources = await asyncio.wait_for(retrieve_sources(message), timeout=RETRIEVE_TIMEOUT_S)
    t_retr  = (time.time() - t_retr0) * 1000

    t_pr0   = time.time()
    prompt  = await asyncio.wait_for(
        asyncio.to_thread(build_prompt, message, sources, detail_level),
        timeout=PROMPT_TIMEOUT_S,
    )
    t_pr    = (time.time() - t_pr0) * 1000

    t_llm0  = time.time()
    answer  = await asyncio.wait_for(ollama_generate(prompt), timeout=OLLAMA_TIMEOUT_S)
    t_llm   = (time.time() - t_llm0) * 1000

    total   = (time.time() - t0) * 1000
    return {
        "answer":  answer,
        "sources": sources,
        "_timing_ms": {
            "retrieve": round(t_retr, 1),
            "prompt":   round(t_pr,   1),
            "generate": round(t_llm,  1),
            "total":    round(total,  1),
        },
        "_prompt_chars": len(prompt),
    }


# ----------------------------- #
# Chat                          #
# ----------------------------- #
@app.post("/chat")
async def chat(payload: ChatIn, request: Request):
    """RAG endpoint: retrieve sources → build prompt → generate via Ollama."""
    global CHAT_COUNT, ERROR_COUNT
    require_api_key(request)
    rid = getattr(request.state, "request_id", str(uuid.uuid4()))
    try:
        result = await asyncio.wait_for(
            _chat_impl(payload.message, rid, getattr(payload, "detail_level", None)),
            timeout=CHAT_TOTAL_TIMEOUT_S,
        )
        CHAT_COUNT += 1
        return {"answer": result["answer"], "sources": result["sources"]}
    except asyncio.TimeoutError:
        ERROR_COUNT += 1
        logger.error(f"[{rid}] /chat: TOTAL TIMEOUT after {CHAT_TOTAL_TIMEOUT_S}s")
        raise HTTPException(status_code=504, detail="Chat timed out.")
    except Exception as e:
        ERROR_COUNT += 1
        logger.exception(f"[{rid}] /chat: ERROR {type(e).__name__}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ----------------------------- #
# Debug endpoints               #
# ----------------------------- #
@app.get("/debug/retrieve")
async def debug_retrieve(request: Request, q: str = Query(min_length=2, max_length=2000)):
    require_api_key(request)
    rid = getattr(request.state, "request_id", str(uuid.uuid4()))
    try:
        sources = await asyncio.wait_for(retrieve_sources(q), timeout=RETRIEVE_TIMEOUT_S)
        return {"query": q, "sources": sources}
    except asyncio.TimeoutError:
        logger.error(f"[{rid}] /debug/retrieve: TIMEOUT")
        raise HTTPException(status_code=504, detail="Retrieve timed out.")
    except Exception as e:
        logger.exception(f"[{rid}] /debug/retrieve: ERROR {type(e).__name__}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/debug/prompt")
async def debug_prompt(payload: ChatIn, request: Request):
    require_api_key(request)
    rid = getattr(request.state, "request_id", str(uuid.uuid4()))
    try:
        sources = await asyncio.wait_for(retrieve_sources(payload.message), timeout=RETRIEVE_TIMEOUT_S)
        prompt  = await asyncio.wait_for(
            asyncio.to_thread(build_prompt, payload.message, sources, getattr(payload, "detail_level", None)),
            timeout=PROMPT_TIMEOUT_S,
        )
        return {"prompt": prompt, "sources": sources, "prompt_chars": len(prompt)}
    except asyncio.TimeoutError:
        logger.error(f"[{rid}] /debug/prompt: TIMEOUT")
        raise HTTPException(status_code=504, detail="Prompt build timed out.")
    except Exception as e:
        logger.exception(f"[{rid}] /debug/prompt: ERROR {type(e).__name__}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/debug/chat")
async def debug_chat(payload: ChatIn, request: Request):
    """Full RAG with timing — useful for diagnosing latency."""
    require_api_key(request)
    rid = getattr(request.state, "request_id", str(uuid.uuid4()))
    try:
        result = await asyncio.wait_for(
            _chat_impl(payload.message, rid, getattr(payload, "detail_level", None)),
            timeout=CHAT_TOTAL_TIMEOUT_S,
        )
        return result
    except asyncio.TimeoutError:
        logger.error(f"[{rid}] /debug/chat: TOTAL TIMEOUT after {CHAT_TOTAL_TIMEOUT_S}s")
        raise HTTPException(status_code=504, detail="debug/chat timed out.")
    except Exception as e:
        logger.exception(f"[{rid}] /debug/chat: ERROR {type(e).__name__}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/debug/ollama")
async def debug_ollama(payload: ChatIn, request: Request):
    """Bypass retrieval — test Ollama generation directly."""
    require_api_key(request)
    try:
        answer = await asyncio.wait_for(ollama_generate(payload.message), timeout=OLLAMA_TIMEOUT_S)
        return {
            "ok":             True,
            "ollama_base_url": os.getenv("OLLAMA_BASE_URL", ""),
            "ollama_model":    os.getenv("OLLAMA_MODEL", ""),
            "answer":          answer,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
