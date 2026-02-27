# CIS Docker Benchmark — Selected Controls

Source: CIS Docker Benchmark v1.6.0
Framework: CIS (Center for Internet Security)
Tags: docker, cis, containers, hardening

---

## 1. Host Configuration

### 1.1 — Keep Docker up to date
Ensure the Docker engine version is current. Older versions contain known CVEs that have been patched in newer releases. Check with `docker version` and compare against the latest release notes.

### 1.2 — Audit Docker daemon activity
Configure auditd rules to log Docker daemon activity:
```
-w /usr/bin/dockerd -k docker
-w /var/lib/docker -k docker
-w /etc/docker -k docker
```

---

## 2. Docker Daemon Configuration

### 2.1 — Do not use privileged containers
Privileged containers have root access to the host and bypass namespacing. Never use `privileged: true` in production. If specific capabilities are required, grant them individually with `cap_add`.

### 2.2 — Restrict container communication
By default, all containers on a bridge network can communicate with each other. Use `--icc=false` (inter-container communication disabled) and explicitly define only the network links you need.

### 2.3 — Do not use the default bridge network
The default bridge network lacks network segmentation. Create named networks so containers can communicate only with the services they need.

### 2.4 — Enable user namespace support
User namespace remapping isolates root inside a container from root on the host. Without it, a container breakout runs as root on the host.

---

## 3. Docker Daemon Configuration Files

### 3.1 — Verify daemon.json permissions
The Docker daemon configuration file (`/etc/docker/daemon.json`) should be owned by root with permissions `0644`. World-writable daemon configs allow privilege escalation.

### 3.2 — Set log level to at least INFO
```json
{ "log-level": "info" }
```
DEBUG logging may expose sensitive environment variables and secrets in logs.

---

## 4. Container Images and Build Files

### 4.1 — Create a user for the container
Running containers as root inside the container is the most common Docker security mistake. Even without `--privileged`, root inside the container has more capabilities than a non-root user.

Always create a non-root user in your Dockerfile:
```dockerfile
RUN useradd -m appuser
USER appuser
```

Or use an existing unprivileged user if the base image provides one (e.g., `nobody`, `www-data`).

### 4.2 — Use trusted base images
Use official images from Docker Hub verified publishers or images from your organisation's private registry. Unverified third-party base images may contain backdoors or malware.

Always pin to a specific digest or tag rather than `latest`:
```dockerfile
FROM python:3.11.9-slim  # pinned, not FROM python:latest
```

### 4.3 — Do not install unnecessary packages
Every installed package is an attack surface. Use multi-stage builds to keep final images lean. Run `apt-get clean && rm -rf /var/lib/apt/lists/*` after package installs.

### 4.4 — Scan and rebuild container images periodically
Run vulnerability scans (e.g., `docker scout`, Trivy, Grype) against your images in CI. Rebuild images when base image patches are released.

### 4.5 — Enable HEALTHCHECK
Containers without a health check run forever even when the application inside has crashed. Docker Compose will not restart a container that has no health check unless restart policies are set.

```dockerfile
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1
```

### 4.6 — Use COPY not ADD
`ADD` can fetch remote URLs and auto-extract archives, which introduces unexpected behaviour. Use `COPY` unless you specifically need `ADD`'s extra capabilities.

### 4.7 — Do not store secrets in Dockerfiles
Environment variables set in `ENV` or `ARG` in a Dockerfile are visible in the image layers. Use Docker secrets, mounted secret files at runtime, or environment injection at deploy time.

---

## 5. Container Runtime

### 5.1 — Do not disable AppArmor profile
AppArmor restricts container capabilities at the kernel level. Do not add `--security-opt apparmor=unconfined`.

### 5.2 — Do not disable SELinux security options
If the host uses SELinux, do not disable it for containers with `--security-opt label=disable`.

### 5.3 — Verify capabilities
Drop all capabilities and add back only what is needed:
```yaml
cap_drop:
  - ALL
cap_add:
  - NET_BIND_SERVICE
```

### 5.4 — Do not use sensitive host system directories as container volumes
Mounting sensitive host directories (`/`, `/boot`, `/etc`, `/proc`) into containers exposes the host filesystem. Use named volumes for persistent data instead.

### 5.5 — Do not run SSH within containers
Containers should be debugged with `docker exec`. Running SSH inside a container adds an attack vector and complicates key management.

### 5.6 — Restrict container memory usage
Unbounded memory allows a container to exhaust host memory. Set resource limits:
```yaml
mem_limit: 512m
```

### 5.7 — Set CPU priority appropriately
Prevent runaway containers from monopolising the CPU with `cpus` or `cpu_shares` in docker-compose.yml.

### 5.8 — Bind container ports to specific interfaces
Binding to `0.0.0.0` (all interfaces) exposes the port to every network interface. Bind to `127.0.0.1` for local-only services:
```yaml
ports:
  - "127.0.0.1:8000:8000"  # localhost only
```

### 5.9 — Do not share the host's IPC namespace
`ipc: host` shares the host IPC namespace, allowing container processes to communicate with host processes via shared memory.

### 5.10 — Do not share the host's network namespace
`network_mode: host` removes all network isolation. Only use it if there is a specific performance reason and you understand the implications.

### 5.11 — Do not share the host's process namespace
`pid: host` allows the container to see and signal all processes on the host, which breaks the isolation model.

---

## 6. Docker Security Operations

### 6.1 — Enable Docker Content Trust
Docker Content Trust (DCT) cryptographically signs images:
```bash
export DOCKER_CONTENT_TRUST=1
```
With DCT enabled, Docker will refuse to pull unsigned images.

### 6.2 — Use a centralised and remote logging driver
Configure containers to ship logs to a centralised system (syslog, fluentd, Splunk) rather than relying on the local Docker log driver, which can fill disk or be lost on container restart.
