# Lesson 3: Auditing the Containers

Before changing anything, measure. `bin/audit.py` inspects every running container in this lab and checks nine things.

---

## Run the audit

```bash
python3 bin/audit.py --explain
```

### What you will see

```
Project: secure-ai-milvus-part4

CONTAINER          non-root     no-caps no-escalate   read-only no-env-keys   mem-limit   pid-limit       ports      pinned   SCORE
-----------------------------------------------------------------------------------------------------------------------------------
rag-api                FAIL        FAIL        FAIL        FAIL        FAIL        pass        FAIL        pass        FAIL     2/9
rag-etcd               FAIL        FAIL        FAIL        FAIL        pass        pass        pass        pass        FAIL     4/9
rag-milvus             pass        FAIL        FAIL        FAIL        pass        pass        pass        pass        FAIL     5/9
rag-minio              FAIL        FAIL        FAIL        FAIL        pass        pass        pass        pass        FAIL     4/9
rag-nginx              FAIL        FAIL        FAIL        FAIL        FAIL        pass        FAIL        pass        FAIL     2/9
rag-ollama             FAIL        FAIL        FAIL        FAIL        pass        pass        FAIL        pass        FAIL     3/9
rag-ui                 FAIL        FAIL        FAIL        FAIL        FAIL        pass        FAIL        pass        FAIL     2/9
-----------------------------------------------------------------------------------------------------------------------------------
Total: 22 of 63 checks pass (34%)
```

followed by an explanation of every failure.

---

## The nine checks

| Check | Passes when | Where the setting lives |
|---|---|---|
| `non-root` | The container starts as a user other than root | `user:` in compose, or `USER` in a Dockerfile |
| `no-caps` | Every Linux capability is dropped | `cap_drop: [ALL]` |
| `no-escalate` | Processes cannot gain privileges | `security_opt: ["no-new-privileges:true"]` |
| `read-only` | The container's own filesystem cannot be changed | `read_only: true` |
| `no-env-keys` | No secret-looking value is in an environment variable | Secrets mounted as files |
| `mem-limit` | A memory limit is set | `mem_limit:` |
| `pid-limit` | A process-count limit is set | `pids_limit:` |
| `ports` | Nothing is published, or only to `127.0.0.1` | `ports:` |
| `pinned` | The image is pinned by digest | `image: name@sha256:...` |

The audit reads only what Docker reports (`docker inspect`). It changes nothing.

---

## What the baseline tells you

- **Two checks already pass everywhere:** memory limits and localhost-only ports. Both were set in Part 3
- **Milvus, etcd, and MinIO** pass `pid-limit` because Part 3 gave them one; the others never got one
- **Milvus already passes `non-root`.** Its official image runs as its own user, `milvus` (999), out of the box. Every other container runs as root
- Every container keeps its capabilities and has a writable filesystem
- **Three containers** (`rag-api`, `rag-nginx`, `rag-ui`) have `EDGE_API_KEY` in their environment

### A false alarm worth understanding

The audit skips one variable on purpose:

```python
NOT_SECRET = {"GPG_KEY", "MINIO_UPDATE_MINISIGN_PUBKEY"}
```

- The official Python image sets `GPG_KEY` to the **public** fingerprint used to verify the Python download.
- MinIO's image sets `MINIO_UPDATE_MINISIGN_PUBKEY` to the **public** key it uses to check that its own updates are genuine.

Both names match the "secret" pattern, but both values are meant to be public. Check for yourself instead of trusting the list:

```bash
docker inspect rag-minio --format '{{range .Config.Env}}{{println .}}{{end}}' | grep -E 'KEY|PASSWORD'
```

```
MINIO_ROOT_PASSWORD_FILE=minio_password
MINIO_ACCESS_KEY_FILE=access_key
MINIO_SECRET_KEY_FILE=secret_key
MINIO_KMS_SECRET_KEY_FILE=kms_master_key
MINIO_UPDATE_MINISIGN_PUBKEY=RWTx5Zr1tiHQLwG9keckT0c45M3AGeHD6IvimQHpyRywVWGbP1aVSGav
```

The `_FILE` variables hold the **names** of secret files, not secrets. The last one is a public key. The first version of this lab's audit flagged MinIO for it, and reading the value showed it was safe. Every security tool needs rules like this, and each one should say **why** it exists, so the next person does not have to guess.

---

## Start a scoreboard

| Layers on | Audit score |
|---|---|
| None | 22 of 63 (34%) |
| + 1 non-root | |
| + 2 capabilities | |
| + 3 read-only | |
| + 4 secrets | |
| + 5 internal TLS | |
| + 6 pinned | |

Next: [Thinking Like an Attacker Inside a Container](04-attacker-demo.md)
