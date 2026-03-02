# Building Your Own Docker Images

This document teaches you how to create Docker images, not just what they are — using the same patterns you see in the Milvus RAG lab repo.

Before reading this, make sure you have read the Docker Architecture document. This document assumes you understand what images, containers, networks, and volumes are, and how the lab architecture is structured. If anything in Section 1 is unfamiliar, go back and read the architecture document first.

## Table of Contents

1. Images vs containers: the exact difference
2. How Docker builds images: layers and caching
3. Anatomy of a Dockerfile: every instruction explained
4. Choosing a base image: security and size trade-offs
5. Lab: build a FastAPI image step-by-step
6. Designing for fast rebuilds
7. Multi-stage builds
8. Environment variables, .env, and secrets
9. Exposing ports and binding addresses
10. Healthchecks and readiness
11. Tagging and versioning images
12. Debugging broken builds
13. Publishing images (optional)
14. Hardening checklist

---

## 1. Images vs Containers: The Exact Difference

An image is a read-only blueprint: a filesystem snapshot plus metadata describing how to run it. It does not change. It does not run. It just exists as a packaged artifact.

A container is what happens when you run an image. Docker takes the image, adds a writable layer on top, starts the process, and gives it an isolated environment. When you stop and remove the container, that writable layer is gone. The image is untouched.

A useful analogy: an image is a frozen recipe, and a container is the meal you cooked from it. You can cook the same recipe multiple times and get the same result. Eating one meal does not change the recipe.

When you run:
```bash
docker run nginx:1.27-alpine
```

Docker downloads the image if you do not have it, creates a container from it, and starts the main process. The image stays unchanged. You can run it again and get a fresh container.

---

## 2. How Docker Builds Images: Layers and Caching

### Every instruction creates a layer

Docker builds images one instruction at a time. Each instruction in a Dockerfile produces a layer — a snapshot of the filesystem at that point. Layers are stacked on top of each other to form the final image.

Layers are cached. If Docker has already built a layer and nothing that affects it has changed, it reuses the cached version instead of rebuilding it. This is what makes rebuilds fast.

Consider this Dockerfile:

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "-m", "app"]
```

If you change only your application code and rebuild:
- Docker reuses the cached layers for `FROM`, `WORKDIR`, `COPY requirements.txt`, and `RUN pip install`
- It only redoes `COPY . .` and everything after it

If you change `requirements.txt`:
- Docker reuses `FROM` and `WORKDIR`
- It redoes `COPY requirements.txt`, `RUN pip install`, and everything after

### Why caching is a skill

Knowing how to structure a Dockerfile so rebuilds are fast is one of the most practical Docker skills. The rule is simple: put things that change rarely near the top, and things that change often near the bottom. This way, frequent changes only invalidate the last few layers rather than triggering a full rebuild.

---

## 3. Anatomy of a Dockerfile: Every Instruction Explained

### FROM

Every Dockerfile starts with `FROM`. It sets the base image — the starting filesystem and OS libraries your image inherits. Choosing the right base image affects your image size, security, and what system libraries are available.

### WORKDIR

Sets the working directory inside the container for all subsequent instructions. If the directory does not exist, Docker creates it. Using `WORKDIR` is cleaner than writing `RUN cd /app && ...` in every command.

### COPY

Copies files from your computer (the build context) into the image. Use `COPY` by default. It is explicit about what it copies and where it goes.

A `.dockerignore` file (similar to `.gitignore`) tells Docker which files to exclude from the build context. Always create one — it prevents large or sensitive files from being accidentally copied into your image.

### RUN

Executes a command at build time and creates a new layer with the result. Common uses: installing dependencies, creating users, downloading artifacts. Every `RUN` instruction adds a layer, so combine related commands with `&&` when it makes sense.

### ENV

Sets environment variables inside the image. These are baked into the image as defaults. Runtime environment variables (set in `docker-compose.yml` or `.env`) override them. Use `ENV` for things like `PYTHONDONTWRITEBYTECODE=1` that should always be set regardless of how the container is run.

### EXPOSE

Documents which port the container listens on. Important: `EXPOSE` does not publish a port to your host. It is documentation only. Publishing happens with `ports:` in `docker-compose.yml` or `-p` in `docker run`.

### CMD vs ENTRYPOINT

`CMD` sets the default command that runs when the container starts. It can be overridden easily when running the container. `ENTRYPOINT` sets a command that always runs and is harder to override. For teaching repos, `CMD` is usually the friendlier choice because it is easier to experiment with.

---

## 4. Choosing a Base Image: Security and Size Trade-offs

### Common options for Python

`python:3.11-slim` is the recommended default for this lab. It is based on Debian, has most commonly needed libraries, and is small enough for practical use without the dependency pain of Alpine.

`python:3.11-alpine` is smaller but uses musl libc instead of glibc, which can cause compilation failures for packages with native dependencies. It saves space but can cost hours of debugging. **This is especially relevant in this lab because pymilvus has native gRPC dependencies that may fail to compile on Alpine.**

`debian:bookworm-slim` with manual Python install is for advanced cases where you need precise control over the Python version and installed libraries.

### Why image size matters

Smaller images pull faster, build faster, and have fewer installed packages — which means fewer potential vulnerabilities. But smaller base images sometimes require more manual installation work.

In a RAG lab, image size can grow unexpectedly if you:
- bake models into images (do not do this — use volumes instead)
- copy large datasets into the image
- forget `.dockerignore` and copy your entire repo including data directories
- install the full `pymilvus` SDK when only a subset is needed

---

## 5. Lab: Build a FastAPI Image Step-by-Step

This lab recreates the same build pattern used by the `ingestion-api` service, stripped down to the essentials so you can see exactly how it works.

### Create the project structure

Create a new folder called `my-api` with the following layout:

```
my-api/
  app/
    main.py
  requirements.txt
  Dockerfile
  .dockerignore
```

### Create app/main.py

```python
from fastapi import FastAPI

app = FastAPI()

@app.get("/health")
def health():
    return {"ok": True}
```

### Create requirements.txt

```
fastapi==0.115.6
uvicorn[standard]==0.30.6
httpx==0.27.2
pydantic==2.9.2
```

### Create .dockerignore

```
.git
__pycache__
*.pyc
.venv
.env
data
milvus_data
```

This prevents unnecessary files from being sent to Docker during the build. Without it, Docker copies your entire folder including git history, virtual environments, and any data files.

### Create the Dockerfile

```dockerfile
FROM python:3.11-slim

# Prevent Python from writing .pyc files and enable unbuffered output
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Set working directory
WORKDIR /app

# Install dependencies first (cache-friendly)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code last (changes most often)
COPY app ./app

# Document the port
EXPOSE 8000

# Start the server
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Why `--host 0.0.0.0` matters

Inside a container, `127.0.0.1` means "only accessible from inside this container." If you bind uvicorn to `127.0.0.1`, your host machine cannot reach it even if you publish the port. `0.0.0.0` tells uvicorn to listen on all network interfaces inside the container, which is required for port publishing to work.

### Build the image

From inside `my-api/`:
```bash
docker build -t my-api:dev .
```

### Run the container

```bash
docker run --rm -p 8000:8000 my-api:dev
```

### Test it

```bash
curl -sS http://localhost:8000/health
```

Expected: `{"ok": true}`

If you see this, your image is working correctly. You have just built and run a FastAPI container using the same pattern as `ingestion-api`.

---

## 6. Designing for Fast Rebuilds

The single most important rule: copy dependency files first, install them, then copy your application code.

**Good (fast rebuilds):**
```dockerfile
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
```

**Bad (slow rebuilds):**
```dockerfile
COPY . .
RUN pip install -r requirements.txt
```

In the bad version, changing any file in your project invalidates the cache at the `COPY . .` step, which forces `pip install` to re-run every time. In the good version, `pip install` only re-runs when `requirements.txt` changes.

For RAG labs specifically, add these to your `.dockerignore` to avoid accidentally including large files in the build context:

```
milvus_data/
etcd_data/
minio_data/
*.bin
*.gguf
models/
security-memory/data/
```

---

## 7. Multi-Stage Builds

Multi-stage builds let you use one stage to compile or build something, then copy only the final artifacts into a smaller runtime image. This keeps the final image small by leaving behind build tools and intermediate files.

A common example is a frontend build:

```dockerfile
FROM node:20 AS build
WORKDIR /src
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:1.27-alpine
COPY --from=build /src/dist /usr/share/nginx/html
```

The final image contains only NGINX and the compiled frontend. The Node.js runtime and all build dependencies are left behind.

In the current state of this lab you probably do not need multi-stage builds, but they become relevant when you add a compiled frontend, native Python extensions, or a larger toolchain. The pattern is worth knowing before you need it.

---

## 8. Environment Variables, .env, and Secrets

### Three places env vars can appear

**Dockerfile `ENV`** sets defaults baked into the image. These are present in every container run from the image unless overridden.

**Compose `environment:`** sets per-service runtime configuration. These override Dockerfile defaults and are specific to how the service runs in your stack.

**`.env` file** holds values that vary by machine or student, such as API keys, model names, and collection names. Compose reads this file automatically and makes the values available to services via `${VARIABLE_NAME}` syntax.

### What belongs in .env

Values that are different for each developer or student: API keys, model choices, collection names (`MILVUS_COLLECTION`, `SECURITY_COLLECTION`), embed model names, and anything else that should not be hardcoded. Provide a `.env.example` with placeholder values so students know what to fill in.

### What must never be hardcoded

Secrets and machine-specific configuration must not appear in Python files, Dockerfiles, or anywhere else that gets committed to git. Once something is in git history, it is there permanently even if you delete it in a later commit. If you accidentally commit a secret, treat it as compromised and rotate it.

MinIO credentials (`MINIO_ACCESS_KEY`, `MINIO_SECRET_KEY`) are hardcoded in the lab `docker-compose.yml` as `minioadmin` because this is an isolated local lab environment. In a production deployment these would never be hardcoded — they would come from a secrets manager.

---

## 9. Exposing Ports and Binding Addresses

### EXPOSE vs ports:

`EXPOSE` in a Dockerfile is documentation. It tells anyone reading the file which port the service uses, but it does not make the port accessible from your host.

`ports:` in `docker-compose.yml` actually publishes a port, mapping a host port to a container port. For example, `"8088:8088"` means requests to port 8088 on your laptop are forwarded to port 8088 in the NGINX container.

Only publish ports that genuinely need to be accessed from outside Docker. In this repo: NGINX (8088) and Gradio (7860). Milvus (19530), etcd (2379), and MinIO (9000) are all internal-only and should stay that way.

### The 0.0.0.0 rule

Any server running inside a container must bind to `0.0.0.0` (all interfaces), not `127.0.0.1` (loopback only). Binding to `127.0.0.1` inside a container makes the service invisible to everything outside the container, including port publishing. This is a common mistake when adapting code written for local development to run in Docker.

### gRPC and port 19530

Milvus communicates over gRPC, not HTTP. gRPC runs on port 19530 inside the container. The pymilvus SDK handles the gRPC connection transparently — you specify `host` and `port` and the SDK manages the protocol. You cannot use `curl` to talk to gRPC endpoints. Use the pymilvus SDK or the Milvus HTTP API (port 9091) for health checks.

---

## 10. Healthchecks and Readiness

A container being "Up" does not mean the service inside is ready. Startup takes time, and in this repo the startup chain is longer than most: etcd must be ready before MinIO, both must be ready before Milvus, and Milvus must be ready before the ingestion API.

Healthchecks are how Docker knows when a service is actually ready to receive traffic. A good healthcheck makes a real HTTP request to an endpoint your application actually uses, with a reasonable timeout and enough retries to cover slow startup.

The Milvus healthcheck in this repo is a good example:

```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:9091/healthz"]
  interval: 30s
  timeout: 20s
  retries: 10
  start_period: 90s
```

The `start_period: 90s` tells Docker not to count failures during the first 90 seconds of container startup. This prevents Docker from marking Milvus as unhealthy during its normal initialization window.

### A real failure caused by environment variable parsing

If your code does this:

```python
timeout = float(os.getenv("GRADIO_HTTP_TIMEOUT_S", "300"))
```

And Compose passes an empty string for that variable, Python will crash with `ValueError: could not convert string to float: ''`.

Safer:
```python
raw = os.getenv("GRADIO_HTTP_TIMEOUT_S") or "300"
timeout = float(raw)
```

The `or "300"` means an empty string falls back to the default, rather than crashing.

---

## 11. Tagging and Versioning Images

When Docker builds an image without a tag, it gets tagged `latest` by default. Using `latest` for your own builds creates problems: you cannot tell which version is running, you cannot roll back to a previous version, and automated systems may pull a different version than you intended.

Better tagging practices:
```bash
docker build -t ingestion-api:0.1.0 .
docker build -t ingestion-api:dev .
docker build -t ingestion-api:sha-$(git rev-parse --short HEAD) .
```

For a teaching lab, using a version like `dev` or `0.1.0` is enough. The key habit is not using `latest` for images you build yourself, even if it is fine for well-known external images like `nginx:1.27-alpine`.

Note the Milvus infrastructure images use pinned versions (`milvusdb/milvus:v2.4.9`, `quay.io/coreos/etcd:v3.5.5`). This is intentional — these services must be compatible with each other. Never update one without checking the Milvus compatibility matrix.

---

## 12. Debugging Broken Builds

### "ModuleNotFoundError: No module named 'pymilvus'" at runtime

pymilvus is not installed. Check that it is in `requirements.txt` and that `pip install` ran successfully during the build. If you suspect a stale cache:

```bash
docker build --no-cache -t ingestion-api:dev .
```

### "ImportError: cannot import name X"

A function was renamed or removed but something still imports the old name. Update imports and rebuild.

### 502 Bad Gateway from NGINX

NGINX cannot reach the API. The most common causes are that the API container crashed on startup (check logs with `docker logs --tail 200 ingestion-api`) or there is a service name mismatch in the NGINX config.

### Container exits immediately after starting

The main process crashed. Check the exit code with `docker ps -a` and the logs with `docker logs <container-id>`. Common causes in this repo: a missing environment variable, a failed import, or pymilvus failing to connect to Milvus because it was not healthy yet.

### Milvus version mismatch with pymilvus SDK

pymilvus has strict version requirements. If you upgrade the Milvus container image without also upgrading the pymilvus package in `requirements.txt`, you may see gRPC errors or unexpected behavior. Check the [pymilvus compatibility matrix](https://github.com/milvus-io/pymilvus#compatibility) before changing either version.

---

## 13. Publishing Images (Optional)

In most course scenarios students build images locally. But if you want to distribute a pre-built image so students do not need to build it themselves, you can publish it to a registry.

The workflow is:

```bash
# Tag with a registry path
docker tag my-api:dev ghcr.io/<your-org>/my-api:0.1.0

# Push to the registry
docker push ghcr.io/<your-org>/my-api:0.1.0
```

Students can then use the published image in their `docker-compose.yml` by replacing the `build:` section with `image: ghcr.io/<your-org>/my-api:0.1.0`.

GitHub Container Registry (GHCR) is free for public repositories and integrates well with GitHub Actions for automated builds.

Do not publish the Milvus, etcd, or MinIO images — use the official pinned versions from their registries. Only publish images you build yourself (`ingestion-api`, `gradio-ui`).

---

## 14. Hardening Checklist

Once you have a working image, these practices move it closer to production quality.

**Pin your dependencies.** Unpinned dependencies (`fastapi` instead of `fastapi==0.115.6`) can silently break when a new version is released. Pin everything in `requirements.txt`.

**Pin your base image.** `python:3.11-slim` will change over time as Debian releases security patches. For reproducibility, pin to a specific digest or use a dated tag.

**Run as a non-root user.** By default, processes inside containers run as root. This is a security risk if the container is ever compromised. Create a non-root user and switch to it:

```dockerfile
RUN useradd --no-create-home --shell /bin/false appuser
USER appuser
```

Not every service in this repo does this, but it is the right habit to build.

**Keep secrets out of images.** Never `COPY .env` into an image. Never `ENV API_KEY=mysecret` in a Dockerfile. Always inject secrets at runtime via `docker-compose.yml` environment variables reading from `.env`.

**Scan your images.** Tools like Docker Scout and Trivy check your image for known vulnerabilities in installed packages. Run them before publishing:

```bash
docker scout quickview ingestion-api:dev
```

**Use .dockerignore. Always.** It prevents sensitive files, large data directories (`milvus_data/`, `etcd_data/`, `minio_data/`, `security-memory/data/`), and unnecessary files from being included in the build context.
