# Sample Security Reference Notes

Source: Lab sample data
Framework: General
Tags: sample, general, security

---

## API Key Security Best Practices

API keys should be treated as passwords. They grant access to services and must be protected accordingly.

**Generation:** Use cryptographically secure random number generators. Python: `secrets.token_hex(32)` generates 256 bits of entropy. Never use short, predictable, or reused values.

**Storage:** Store API keys in environment variables or secrets management systems, never in source code or configuration files committed to version control. The `.gitignore` file should always include `.env`.

**Transmission:** Only transmit API keys over HTTPS. Plain HTTP transmissions can be intercepted and the key stolen. Never include API keys in URLs (they appear in server logs and browser history).

**Rotation:** Rotate API keys regularly and immediately upon any suspected compromise. Ensure your system supports key rotation without downtime.

**Logging:** Never log API keys, even partially. Logs are often stored insecurely and shared with third parties for debugging. Use request IDs for tracing instead.

---

## Docker Compose Security Patterns

**Environment variables:** Use `.env` files for secrets. Never hardcode secrets in `docker-compose.yml` directly. The `.env` file must be in `.gitignore`.

**Port exposure:** Only expose ports that external clients need to reach. Internal service-to-service communication should stay on Docker internal networks with no host port bindings.

**Resource limits:** Always set `mem_limit` and `cpus` for production services. Without limits, a single runaway container can take down the entire host.

**Restart policies:** Use `restart: unless-stopped` or `restart: on-failure` to ensure services recover from crashes automatically.

**Named volumes:** Use named volumes instead of bind mounts for persistent data. Named volumes are managed by Docker and isolated from the host filesystem. Bind mounts expose host paths to containers.

---

## NGINX Reverse Proxy Security

**Auth enforcement:** Implement authentication at the proxy layer (NGINX), not only in the application. This creates defence in depth — even if the application has an auth bypass bug, the proxy blocks unauthenticated requests.

**Timeouts:** Set generous timeouts for AI/LLM workloads (300s+). LLM generation on CPU can take 60+ seconds. Insufficient timeouts cause 504 Gateway Timeout errors that look like application failures.

**server_tokens:** Set `server_tokens off` to prevent NGINX from advertising its version in response headers. Version disclosure helps attackers identify applicable CVEs.

**client_max_body_size:** Limit request body size to prevent large-payload DoS attacks. For text API workloads, 2m–10m is usually sufficient.

**Rate limiting:** Use `limit_req_zone` and `limit_req` to limit request rates per IP. This is a basic but effective mitigation against brute-force and DoS attacks.

---

## Vector Database Security Considerations

**Network exposure:** Vector databases should never be directly exposed to the internet. Access should be mediated by an application layer that enforces authentication and authorisation.

**Data at rest:** Vectors encode semantic information about the source text. Even without storing the original text, vectors can be inverted (approximately) to recover the original content. Treat the vector store as sensitive data.

**Access control:** Implement collection-level access control. Different collections may have different sensitivity levels. In Milvus, use role-based access control (RBAC) in production deployments.

**Backup:** Vector indexes are expensive to rebuild. Back up the underlying object storage (MinIO/S3) and etcd metadata on a regular schedule.
