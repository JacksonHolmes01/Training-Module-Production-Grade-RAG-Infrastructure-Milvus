# Lesson 04 — NGINX Auth and the Edge Proxy Pattern

> **Goal:** understand how the API-key check works, why it lives in NGINX
> rather than the application, and how to test and extend it.

---

## The edge proxy pattern

In this lab, **NGINX is the only service that touches the outside world**.
Every other service — ingestion-api, Milvus, Ollama, etcd, MinIO — lives on
the `rag_internal` Docker network with no host port bindings.

```
Internet / your laptop
        │
        │  :8088 (HTTP)
        ▼
    ┌─────────┐
    │  NGINX  │  ← validates X-API-Key header
    └────┬────┘
         │  internal DNS: ingestion-api:8000
         ▼
  ┌──────────────┐
  │ ingestion-api│  ← never exposed directly
  └──────────────┘
```

This is a standard *defence-in-depth* pattern. Even if there is a bug in the
FastAPI application that accidentally skips auth, an attacker cannot reach it
without first passing the NGINX key check.

---

## How the API-key check works

The NGINX config (`nginx/nginx.conf`) uses the `auth_request` module or a
simple `if` block to enforce the key. The simplified logic is:

```nginx
server {
    listen 80;

    location / {
        if ($http_x_api_key != "${EDGE_API_KEY}") {
            return 401 '{"error":"unauthorized"}';
        }
        proxy_pass http://ingestion-api:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_hide_header X-API-Key;   # strip before forwarding
    }
}
```

Key points:
- The key is compared in the NGINX layer — `ingestion-api` never sees an
  unauthenticated request.
- `proxy_hide_header X-API-Key` strips the secret before forwarding, so it
  does not leak into application logs.
- The key value is injected from `.env` at container startup.

---

## HTTP status codes

| Code | Meaning | When you see it |
|------|---------|-----------------|
| 200 | OK | Correct key, request processed |
| 401 | Unauthorized | Missing or wrong `X-API-Key` |
| 403 | Forbidden | Key correct, but resource access denied (rare here) |
| 502 | Bad gateway | NGINX can reach the container but it returned an error |
| 503 | Service unavailable | `ingestion-api` is down or not yet healthy |

---

## Testing the auth layer

Load your key from `.env`:

```bash
EDGE_API_KEY=$(grep -E '^EDGE_API_KEY=' .env | cut -d= -f2-)
```

### Should succeed (correct key)

```bash
curl -s -o /dev/null -w "%{http_code}" http://localhost:8088/health \
  -H "X-API-Key: $EDGE_API_KEY"
# Expected: 200
```

### Should fail (no key)

```bash
curl -s -o /dev/null -w "%{http_code}" http://localhost:8088/health
# Expected: 401
```

### Should fail (wrong key)

```bash
curl -s -o /dev/null -w "%{http_code}" http://localhost:8088/health \
  -H "X-API-Key: totally-wrong"
# Expected: 401
```

---

## Rotating the API key

1. Edit `.env` and change `EDGE_API_KEY` to a new value.
2. Restart NGINX and Gradio (the two services that read the key):

```bash
docker compose restart nginx gradio
```

No other service needs to restart — Milvus, Ollama, and ingestion-api do not
use the edge key.

---

## What the API key does NOT protect against

- An attacker who is already inside the Docker network (e.g., a compromised
  container). Network segmentation and container hardening handle that.
- Brute force if the key is short. Always use at least 32 random hex chars.
- Replay attacks over plain HTTP. For production, terminate TLS at NGINX.

---

## Adding a second route with different auth

If you wanted an unauthenticated public route (e.g., `/healthz` for a load
balancer), you would add it before the auth check:

```nginx
location = /healthz {
    proxy_pass http://ingestion-api:8000/health;
    # no key check
}

location / {
    if ($http_x_api_key != "${EDGE_API_KEY}") {
        return 401;
    }
    proxy_pass http://ingestion-api:8000;
}
```

---

## NGINX logs

```bash
docker compose logs nginx
```

Each request shows the source IP, method, path, status code, and bytes. Use
this to confirm that rejected requests (401) are being blocked at the proxy
and never reaching the application.

---

## Checkpoint

You should now be able to:
- Explain why NGINX sits in front of ingestion-api.
- Get a 401 by sending a request without a key.
- Get a 200 by sending the correct key.
- Explain what `proxy_hide_header X-API-Key` does.

Continue to **[Lesson 05 — Milvus Schema and Vectorization](05-milvus-schema-and-vectorization.md)**.
