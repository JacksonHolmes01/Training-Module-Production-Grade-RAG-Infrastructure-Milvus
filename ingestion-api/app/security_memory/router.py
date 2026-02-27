import os
from fastapi import APIRouter, HTTPException, Request
from .schemas import MemoryQueryIn, MemoryQueryOut, MemoryHealthOut
from .store import memory_health, query_memory

router = APIRouter(prefix="/memory", tags=["security-memory"])
EDGE_API_KEY = os.getenv("EDGE_API_KEY", "")


def require_api_key(request: Request):
    if not EDGE_API_KEY:
        raise HTTPException(status_code=500, detail="EDGE_API_KEY is not set on the server.")
    incoming = request.headers.get("X-API-Key", "")
    if not incoming:
        raise HTTPException(status_code=401, detail="Missing X-API-Key header.")
    if incoming != EDGE_API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API key.")


@router.get("/health", response_model=MemoryHealthOut)
async def health(request: Request):
    require_api_key(request)
    return await memory_health()


@router.post("/query", response_model=MemoryQueryOut)
async def query(payload: MemoryQueryIn, request: Request):
    require_api_key(request)
    return await query_memory(payload)
