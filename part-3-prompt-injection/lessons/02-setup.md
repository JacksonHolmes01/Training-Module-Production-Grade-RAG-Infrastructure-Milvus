# Lesson 2: Setup

Part 3 is a copy of the Lab 1 chatbot (the main lab in the root of this repository) with the defenses added, all switched off. It also tightens the database:

| Lab 1 | Part 3 |
|---|---|
| Milvus has no login: anything that reaches it can read, write, delete, and drop | Milvus refuses any request without a user name and password, and **roles** decide what each user may do |
| MinIO (Milvus's file storage) uses its famous default login, `minioadmin` / `minioadmin` | MinIO gets a generated user name and password from secret files. The default login never exists |
| etcd and MinIO share a network with the API | etcd and MinIO live on their own **private network**. Only Milvus can reach them |
| One collection for everyone | Each tenant gets its own Milvus **database** (`tenant_lab`), and roles are scoped to it |
| | The API logs in as two users: `rag_reader` may only **search and query** (chat), `rag_writer` may only **insert** (ingest). Neither can delete |
| | The **root password** is used once, by a setup container, then nothing running holds it |


---

## Step 1: Stop Lab 1

```bash
cd ~/Training-Module-Production-Grade-RAG-Infrastructure-Milvus
docker compose down
```

## Step 2: Move into Part 3

```bash
cd ~/Training-Module-Production-Grade-RAG-Infrastructure-Milvus/part-3-prompt-injection
ls
```

```
README.md  attacks  bin  data  docker-compose.yml  gradio-ui  ingestion-api  lessons  nginx  secrets
```

These things are new compared to Lab 1:

| Item | Purpose |
|---|---|
| `attacks/` | The attack cases, the poisoned documents, and `run_attacks.py`, which runs every attack and scores the result |
| `ingestion-api/app/guards.py` | The four defenses |
| `bin/guard.sh` | Turns a defense on or off and restarts the API |
| `bin/milvus.sh` | Sends one request to Milvus as `root`, `writer`, `reader`, or `none`, so you can test what each user may do |
| `ingestion-api/app/milvus_init.py` | Creates the database, the collection, the two users, and their roles with the root password, once |

## Step 3: Secrets, build, and start

```bash
bin/setup_secrets.sh
docker compose up -d --build
```

`setup_secrets.sh` creates Milvus's root password, a password for each of the two API users, MinIO's user name and password, the NGINX API key, and a model volume that Parts 3, 4, and 5 share. Milvus takes about a minute to start the first time.

Check that the setup container did its job and exited:

```bash
docker logs rag-milvus-init
```

```
Created database tenant_lab.
Created collection tenant_lab.docs (768 dimensions, cosine).
Created user rag_reader.
Created user rag_writer.
Created role tenant_lab_reader.
Created role tenant_lab_writer.
Roles granted: rag_reader (search, query), rag_writer (insert only).
```

> **If `rag-milvus-init` says Milvus "rejected the root password":** Milvus saves its root password the first time it starts with empty storage. If you later generate new secrets, the stored password no longer matches. Run `bin/reset_all.sh` to start over with empty storage.

### Settings in a file, not the environment

Milvus reads extra settings from `configs/user.yaml`. `setup_secrets.sh` writes `secrets/milvus_user.yaml`, and `docker-compose.yml` mounts it there. It turns the login on, sets the root password, gives Milvus the MinIO credentials, and switches on Milvus's access log (you will use it in Part 5). Nothing secret is in an environment variable, so nothing secret shows in `docker inspect`.

MinIO reads its credentials from secret files too (`MINIO_ROOT_USER_FILE` and `MINIO_ROOT_PASSWORD_FILE`).

### The users and roles

| User | Role | May |
|---|---|---|
| `root` | built in | Everything. Only `milvus-init` ever uses it |
| `rag_writer` | `tenant_lab_writer` | **Insert** into `tenant_lab.docs`. Not search, not query, not delete |
| `rag_reader` | `tenant_lab_reader` | **Search and query** `tenant_lab.docs`. Never another tenant's database |

### Prove the database is locked

```bash
bin/milvus.sh none   /v2/vectordb/databases/list
bin/milvus.sh reader /v2/vectordb/entities/delete '{"dbName":"tenant_lab","collectionName":"docs","filter":"id in [\"x\"]"}'
bin/milvus.sh writer /v2/vectordb/collections/drop '{"dbName":"tenant_lab","collectionName":"docs"}'
```

```
401
{"code": 1800, "message": "user hasn't authenticated"}
403
{"code": 65535, "message": "rpc error: code = PermissionDenied desc = PrivilegeDelete: permission deny to rag_reader in the `tenant_lab` database"}
403
{"code": 65535, "message": "rpc error: code = PermissionDenied desc = PrivilegeDropCollection: permission deny to rag_writer in the `tenant_lab` database"}
```

No login: refused. The reader cannot delete, and the writer cannot drop the collection.

### Prove the helpers are out of reach

```bash
docker exec rag-api python -c "
import socket
for h, p in [('etcd', 2379), ('minio', 9000), ('milvus', 19530)]:
    try: socket.create_connection((h, p), timeout=3); print(f'{h}:{p} reachable')
    except Exception as e: print(f'{h}:{p} blocked ({type(e).__name__})')"
docker exec rag-minio mc alias set test http://localhost:9000 minioadmin minioadmin
```

```
etcd:2379 blocked (gaierror)
minio:9000 blocked (gaierror)
milvus:19530 reachable
mc: <ERROR> Unable to initialize new alias from the provided credentials. ...
```

From the API container, etcd and MinIO do not even have a name (`gaierror` means "no such host"). And MinIO's default login does not work, even from inside MinIO's own container.

## Step 4: Models and sample data

```bash
bin/pull_models.sh
bin/ingest_sample.sh
```

The first time, this downloads about 1.6 GB. Parts 4 and 5 reuse the same download.

```
Total: 12  Success: 12  Failed: 0
```

## Step 5: Confirm every defense is off

```bash
bin/guard.sh status
```

```
GUARD_INPUT=false
GUARD_INGEST=false
GUARD_PROMPT=false
GUARD_OUTPUT=false
```

The API also reports which guards are on:

```bash
EDGE_API_KEY=$(grep -E '^EDGE_API_KEY=' .env | cut -d= -f2-)
curl -s -H "X-API-Key: $EDGE_API_KEY" http://localhost:8088/health | python3 -m json.tool | grep -A5 guards
```

```
    "guards": {
        "input": false,
        "ingest": false,
        "prompt": false,
        "output": false
    },
```

---

## One setting that makes experiments fair

```
OLLAMA_TEMPERATURE=0
```

**Temperature** controls randomness. At `0`, the model picks its most likely answer every time, so the same attack against the same setup gives the same result. That lets you compare "before" and "after" honestly.

Next: [Direct Attacks: Talking the Model Out of Its Rules](03-direct-attacks.md)
