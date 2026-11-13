"""
milvus_init.py: one-time setup, run by the milvus-init container.

This is the ONLY code that ever holds Milvus's root password. It waits for
Milvus, then makes sure these exist (creating any that are missing):

  - this tenant's database (tenant_<name>) and its "docs" collection,
    indexed for cosine similarity and loaded into memory for search
  - two users, rag_reader and rag_writer, with passwords from secret files
  - two roles, scoped to that one database and collection:
      tenant_<name>_reader  Search and Query
      tenant_<name>_writer  Insert (nothing else: no search, no delete)
  - each role granted to its user

After it exits, nothing running holds the root password.
"""

import os
import sys
import time

import httpx

MILVUS_URL = os.getenv("MILVUS_URL", "http://milvus:19530")
MILVUS_CA_CERT = os.getenv("MILVUS_CA_CERT", "")
APP_TENANT = os.getenv("APP_TENANT", "lab")
EMBED_DIM = int(os.getenv("EMBED_DIM", "768"))
DATABASE = f"tenant_{APP_TENANT}"
COLLECTION = "docs"


def secret(name: str) -> str:
    with open(f"/run/secrets/{name}", encoding="utf-8") as f:
        return f.read().strip()


headers = {"Authorization": f"Bearer root:{secret('milvus_root_password')}"}


def call(c: httpx.Client, path: str, body: dict, allow_codes=()) -> dict:
    r = c.post(f"/v2/vectordb{path}", json=body)
    data = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
    if r.status_code != 200 or (data.get("code", 0) != 0 and data.get("code") not in allow_codes):
        sys.exit(f"{path} failed: HTTP {r.status_code} {r.text[:300]}")
    return data


with httpx.Client(base_url=MILVUS_URL, headers=headers, timeout=60,
                  verify=MILVUS_CA_CERT or True) as c:
    for _ in range(90):
        try:
            r = c.post("/v2/vectordb/databases/list", json={})
            if r.status_code == 200 and r.json().get("code") == 0:
                break
            if r.status_code == 401:
                # Milvus answered, but refused the root password. Milvus saves
                # its root password the FIRST time it starts with empty storage,
                # so new secrets do not change it. Start over with empty storage.
                sys.exit("Milvus rejected the root password in secrets/milvus_root_password.txt. "
                         "It still has the password from an earlier setup. "
                         "Run bin/reset_all.sh (deletes the lab's data), then start again.")
        except (httpx.HTTPError, ValueError):
            pass
        time.sleep(2)
    else:
        sys.exit("Milvus did not become ready.")

    # 1. The tenant's database
    if DATABASE not in (call(c, "/databases/list", {}).get("data") or []):
        call(c, "/databases/create", {"dbName": DATABASE})
        print(f"Created database {DATABASE}.")

    # 2. The collection: explicit fields, a cosine index, loaded for search
    existing = call(c, "/collections/list", {"dbName": DATABASE}).get("data") or []
    if COLLECTION not in existing:
        varchar = lambda n, length: {"fieldName": n, "dataType": "VarChar", "elementTypeParams": {"max_length": length}}
        call(c, "/collections/create", {
            "dbName": DATABASE, "collectionName": COLLECTION,
            "schema": {"autoId": False, "enableDynamicField": False, "fields": [
                {**varchar("id", 64), "isPrimary": True},
                {"fieldName": "vector", "dataType": "FloatVector", "elementTypeParams": {"dim": EMBED_DIM}},
                varchar("title", 512), varchar("url", 1024), varchar("source", 256),
                varchar("published_date", 32), {"fieldName": "tags", "dataType": "JSON"},
                varchar("content", 65535),
            ]},
            "indexParams": [{"fieldName": "vector", "indexName": "vector_idx",
                             "metricType": "COSINE", "indexType": "AUTOINDEX"}],
        })
        print(f"Created collection {DATABASE}.{COLLECTION} ({EMBED_DIM} dimensions, cosine).")
    call(c, "/collections/load", {"dbName": DATABASE, "collectionName": COLLECTION})

    # 3. Users (Milvus stores only a hash of each password)
    users = set(call(c, "/users/list", {}).get("data") or [])
    for user in ("rag_reader", "rag_writer"):
        if user not in users:
            call(c, "/users/create", {"userName": user, "password": secret(f"milvus_{user[4:]}_password")})
            print(f"Created user {user}.")

    # 4. Roles, each limited to this one database and collection
    roles = {
        f"tenant_{APP_TENANT}_reader": ["Search", "Query"],
        f"tenant_{APP_TENANT}_writer": ["Insert"],
    }
    existing_roles = set(call(c, "/roles/list", {}).get("data") or [])
    for role, privileges in roles.items():
        if role not in existing_roles:
            call(c, "/roles/create", {"roleName": role})
            print(f"Created role {role}.")
        for p in privileges:
            call(c, "/roles/grant_privilege", {"roleName": role, "objectType": "Collection",
                                               "objectName": COLLECTION, "privilege": p, "dbName": DATABASE})

    # 5. Give each user its role
    call(c, "/users/grant_role", {"userName": "rag_reader", "roleName": f"tenant_{APP_TENANT}_reader"})
    call(c, "/users/grant_role", {"userName": "rag_writer", "roleName": f"tenant_{APP_TENANT}_writer"})
    print("Roles granted: rag_reader (search, query), rag_writer (insert only).")
