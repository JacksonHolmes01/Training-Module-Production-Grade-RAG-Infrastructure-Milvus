"""
db.py: Milvus access layer (Milvus REST API v2).

Security design:
  - Milvus requires a user name and password for every request, and
    role-based access control (RBAC) decides what each user may do.
  - The ROOT password never reaches this API. It is used once, by the
    milvus-init container, to create the tenant's database, the
    collection, the users, and their roles.
  - This API logs in as two users, each with one role:
      * rag_writer: may only INSERT into this tenant's collection. It
        cannot search, read, delete, or drop anything. Used ONLY by /ingest.
      * rag_reader: may only SEARCH and QUERY this tenant's collection.
        Used by /chat and retrieval.
    If the chat path is ever abused, its login cannot change data, and
    neither login can touch another tenant's database.
  - Passwords are read from Docker secret files, never from env vars.
  - Part 4: traffic to Milvus can be encrypted and verified (MILVUS_CA_CERT).
  - Each tenant gets its own Milvus database (tenant_<name>). The tenant
    comes from server configuration (APP_TENANT), never from the HTTP request.
"""

import json
import os
import logging
import uuid
from typing import Any, Dict, List

import httpx

logger = logging.getLogger("db")

MILVUS_URL = os.getenv("MILVUS_URL", "http://milvus:19530")
APP_TENANT = os.getenv("APP_TENANT", "lab")
EMBED_DIM  = int(os.getenv("EMBED_DIM", "768"))
DATABASE   = f"tenant_{APP_TENANT}"
COLLECTION = "docs"
# Part 4 (Layer 5): with MILVUS_URL=https://... the connection is encrypted,
# and MILVUS_CA_CERT makes the API check Milvus's certificate against our
# own certificate authority, so an impostor cannot pose as the database.
MILVUS_CA_CERT = os.getenv("MILVUS_CA_CERT", "")
FIELDS     = ["id", "title", "url", "source", "published_date", "tags", "content"]


def _secret(name: str) -> str:
    with open(f"/run/secrets/{name}", "r", encoding="utf-8") as f:
        return f.read().strip()


def _client(user: str, secret_name: str) -> httpx.AsyncClient:
    # Milvus accepts "<user>:<password>" as a bearer token
    return httpx.AsyncClient(
        base_url=MILVUS_URL,
        headers={"Authorization": f"Bearer {user}:{_secret(secret_name)}"},
        timeout=30.0,
        verify=MILVUS_CA_CERT or True,
    )


writer: httpx.AsyncClient | None = None
reader: httpx.AsyncClient | None = None


async def open_pools() -> None:
    global writer, reader
    writer = _client("rag_writer", "milvus_writer_password")
    reader = _client("rag_reader", "milvus_reader_password")


async def close_pools() -> None:
    for c in (writer, reader):
        if c is not None:
            await c.aclose()


def _check_dim(vec: List[float]) -> List[float]:
    if len(vec) != EMBED_DIM:
        raise ValueError(f"Embedding has {len(vec)} dimensions, expected {EMBED_DIM}.")
    return [float(x) for x in vec]


async def _call(client: httpx.AsyncClient, path: str, body: Dict[str, Any]) -> Any:
    if path in ("/entities/search", "/entities/query"):
        # "Strong" = always see every insert and delete made so far. Milvus's
        # default lets reads lag a few seconds behind writes.
        body = {"consistencyLevel": "Strong", **body}
    r = await client.post(f"/v2/vectordb{path}",
                          json={"dbName": DATABASE, "collectionName": COLLECTION, **body})
    r.raise_for_status()
    data = r.json()
    # Milvus reports most errors as HTTP 200 with a non-zero "code"
    if data.get("code", 0) != 0:
        raise RuntimeError(f"Milvus error {data.get('code')}: {str(data.get('message', ''))[:200]}")
    return data.get("data")


async def ready() -> bool:
    try:
        await _call(reader, "/entities/query", {"filter": 'id != ""', "outputFields": ["id"], "limit": 1})
        return True
    except Exception as e:
        logger.warning("Milvus not ready: %s", e)
        return False


async def insert_doc(doc: Dict[str, Any], embedding: List[float]) -> Dict[str, Any]:
    row_id = str(uuid.uuid4())
    await _call(writer, "/entities/insert", {"data": [{
        "id": row_id,
        "vector": _check_dim(embedding),
        "title": doc.get("title", ""),
        "url": doc.get("url", ""),
        "source": doc.get("source", ""),
        "published_date": doc.get("published_date", ""),
        "tags": doc.get("tags", []),
        "content": doc["text"],
    }]})
    return {"id": row_id, "tenant": APP_TENANT}


async def search(embedding: List[float], k: int) -> List[Dict[str, Any]]:
    rows = await _call(reader, "/entities/search", {
        "data": [_check_dim(embedding)], "annsField": "vector", "limit": int(k), "outputFields": FIELDS,
    }) or []
    out = []
    for r in rows:
        # With the COSINE metric Milvus returns similarity (higher = closer).
        # Report it as a distance (lower = closer) so it reads the same as other labs.
        sim = float(r.pop("distance", 0.0))
        tags = r.get("tags") or []
        if isinstance(tags, str):
            tags = json.loads(tags or "[]")
        out.append({**r, "tags": tags, "distance": round(1.0 - sim, 4)})
    return out


async def count_docs() -> int:
    rows = await _call(reader, "/entities/query", {"filter": "", "outputFields": ["count(*)"]}) or [{}]
    return int(rows[0].get("count(*)", 0))


async def all_docs(limit: int = 5000) -> List[Dict[str, Any]]:
    """Every stored document for this tenant (read-only login). Used by /debug/scan."""
    rows = await _call(reader, "/entities/query", {
        "filter": 'id != ""', "outputFields": ["id", "title", "content"], "limit": int(limit),
    }) or []
    return [{"id": r.get("id"), "title": r.get("title", ""), "content": r.get("content", "")} for r in rows]
