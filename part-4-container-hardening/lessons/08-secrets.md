# Lesson 8: Layer 4: Secrets Out of Environment Variables

Milvus's passwords and MinIO's credentials have been files since Part 3. The edge API key has not: three containers receive it as `EDGE_API_KEY` in their environment.

## Why environment variables leak

An environment variable is visible to:
- every process in the container (`env`, `/proc/1/environ`)
- anyone who can run `docker inspect` on the host, with no need to enter the container
- crash reports, debug pages, and error trackers, which often dump the environment
- child processes, which inherit it automatically

A file mounted read-only is visible only to processes that open that specific path, and never appears in `docker inspect`.

---

## Read the layer

Open `hardening/04-secrets.yml`.

### The API and the UI read the key from a file

```yaml
  ingestion-api:
    environment: !override
      ...                                   # everything from docker-compose.yml, except EDGE_API_KEY
      EDGE_API_KEY_FILE: /run/secrets/edge_api_key
    secrets:
      - ...
      - edge_api_key
```

Both apps already support this. In `ingestion-api/app/main.py`:

```python
def _read_key() -> str:
    path = os.getenv("EDGE_API_KEY_FILE", "")
    if path:
        with open(path, "r", encoding="utf-8") as f:
            return f.read().strip()
    return os.getenv("EDGE_API_KEY", "")
```

The `_FILE` convention (a variable that holds a **path**, not a value) is widely used. MinIO uses it (`MINIO_ROOT_PASSWORD_FILE`), and Milvus reads all its settings, passwords included, from a mounted file (`configs/user.yaml`). That is why the audit never found a database password. This layer gives the API key the same treatment.

> **Why `!override` lists every variable again.** Docker Compose has a quirk: once an earlier layer (Layer 1) has added environment variables to a service, a later `!reset` can no longer remove a variable from the base file. Replacing the whole list with `!override` is the reliable way. Building this lab, the first version used `!reset`, and the audit caught that the key was still there.

### NGINX checks the key against a file

NGINX normally takes the key from its environment and pastes it into its config at startup. Layer 4 swaps in a different config, `nginx/templates-keyfile/default.conf.template`:

```nginx
map $http_x_api_key $edge_key_ok {
    default 0;
    include /etc/nginx/secrets/edge_key.map;
}
...
        if ($edge_key_ok = 0) {
            return 403 '{"error":"invalid API key"}';
        }
```

`secrets/edge_key.map` holds one line: the key, then `1`. It is mounted read-only. This is the same `map` technique as the Chroma gateway's token list.

---

## Apply it

```bash
bin/harden.sh 4
bin/smoke_test.sh
```

## Verify

```bash
for c in rag-api rag-nginx rag-ui; do
  printf "%-10s " "$c"
  docker inspect $c --format '{{range .Config.Env}}{{println .}}{{end}}' | grep -q '^EDGE_API_KEY=' \
    && echo "key in environment" || echo "no key in environment"
done
```

```
rag-api    no key in environment
rag-nginx  no key in environment
rag-ui     no key in environment
```

## Audit and attack

```bash
python3 bin/audit.py
bin/attacker_demo.sh
```

The audit reaches **56 of 63 (88%)**: only `pinned` is left. Every line of the attacker demo is now `no`.

---

## The honest trade-off: file permissions

The secret files are created with permission `644` (readable by every user on your computer). The containers now run as users 101, 999, and 10001, and a file mounted from your computer keeps your computer's owner and permissions. On Linux, a `600` file owned by you is unreadable to user 10001 inside the container.

So there is a trade-off:

| Option | Container can read it | Other users on your computer can read it |
|---|:-:|:-:|
| `600`, owned by you | Only if the container runs as root | No |
| `644` (this lab) | Yes | **Yes** |
| Owned by the container's user ID (needs `sudo chown 10001`) | Yes | No |

On a personal laptop, `644` is a reasonable choice. On a shared server, use a real secrets system (Docker Swarm secrets, Kubernetes secrets, or a vault), which can set the owner and permissions on each secret for each container.

Next: [Layer 5: Encrypted, Verified Traffic Between Services](09-internal-tls.md)
