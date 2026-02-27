# MITRE ATT&CK — Container and Cloud Techniques

Source: MITRE ATT&CK Framework v14
Framework: MITRE
Tags: mitre, attack, containers, cloud, threat-model

---

## TA0001 — Initial Access

### T1190 — Exploit Public-Facing Application
Adversaries exploit vulnerabilities in internet-facing applications. For containerised APIs: unpatched dependencies, injection vulnerabilities, and authentication bypasses are common entry points.

**Mitigation:**
- Scan all public-facing applications for known CVEs.
- Apply patches promptly.
- Use a WAF or API gateway to filter malicious requests.
- Implement input validation to prevent injection attacks.

### T1078 — Valid Accounts
Adversaries use stolen or leaked credentials to authenticate as legitimate users. For APIs: leaked API keys (in public git repositories, logs, or error messages) grant attackers authenticated access.

**Mitigation:**
- Scan source control for accidental secret commits (e.g., git-secrets, truffleHog).
- Rotate any key that has been potentially exposed.
- Implement alerting for authentication from unexpected locations.

---

## TA0002 — Execution

### T1059 — Command and Script Interpreter
Adversaries execute commands within containers. If a container is compromised, attackers may use the shell to execute payloads, install tools, or move laterally.

**Mitigation:**
- Use minimal base images without package managers or shells where possible.
- Do not install debugging tools (curl, wget, bash) in production images.
- Use read-only root filesystems: `read_only: true` in docker-compose.yml.

### T1610 — Deploy Container
Adversaries may deploy malicious containers on a compromised Docker host. Unrestricted Docker socket access allows full host control.

**Mitigation:**
- Never mount `/var/run/docker.sock` into containers unless absolutely required.
- If socket access is required, use a proxy (e.g., Tecnativa Docker Socket Proxy) that restricts allowed operations.

---

## TA0003 — Persistence

### T1525 — Implant Internal Image
Adversaries modify container images or registries to establish persistence. Backdoored images survive container restarts.

**Mitigation:**
- Use Docker Content Trust to verify image signatures.
- Pull images from trusted, private registries rather than public Docker Hub.
- Run periodic vulnerability scans on deployed images.

### T1053.007 — Scheduled Task/Job: Container Orchestration Job
Adversaries use cron jobs or orchestration schedules to maintain persistence inside containers.

**Mitigation:**
- Audit all cron and scheduled task configurations in container images.
- Run containers with read-only root filesystems to prevent modification.

---

## TA0004 — Privilege Escalation

### T1611 — Escape to Host
Adversaries exploit container vulnerabilities to escape into the host OS. Privileged containers, host network mode, and dangerous volume mounts are common escape vectors.

**Mitigation:**
- Never use `privileged: true`.
- Avoid `network_mode: host` and `pid: host`.
- Do not mount sensitive host directories (`/`, `/proc`, `/dev`).
- Keep the container runtime up to date.
- Use seccomp and AppArmor profiles.

### T1078.001 — Valid Accounts: Default Accounts
Default credentials (e.g., MinIO `minioadmin:minioadmin`) allow immediate access if the service is exposed.

**Mitigation:**
- Change all default credentials before deployment.
- Ensure internal services (like MinIO) are not exposed on host ports.
- Use strong, randomly generated credentials for all service accounts.

---

## TA0005 — Defence Evasion

### T1562.001 — Impair Defences: Disable or Modify Tools
Adversaries disable security monitoring inside containers. If a container runs as root, it can disable auditd, modify log configurations, or kill security agents.

**Mitigation:**
- Run containers as non-root.
- Use read-only root filesystems.
- Run security agents as a separate privileged process, not inside the target container.

---

## TA0006 — Credential Access

### T1552.001 — Unsecured Credentials: Credentials in Files
Adversaries search compromised containers for credentials stored in files: `.env` files, config files, shell history.

**Mitigation:**
- Never copy `.env` files or other secret files into Docker images.
- Use multi-stage builds to ensure secrets are not in the final image layer.
- Use Docker secrets or environment variable injection at runtime.
- Ensure `.env` is in `.gitignore`.

### T1552.007 — Unsecured Credentials: Container API
The Docker API exposes the ability to read container environment variables. An exposed Docker socket gives attackers access to all environment variables across all running containers.

**Mitigation:**
- Do not expose the Docker socket to containers.
- Audit which containers have access to the Docker socket.

---

## TA0007 — Discovery

### T1613 — Container and Resource Discovery
Adversaries enumerate containers, images, and services running on a host. An exposed Docker API (port 2375) allows full enumeration without authentication.

**Mitigation:**
- Never expose the Docker daemon on a host port.
- Use TLS client authentication if remote Docker API access is required.
- Use network segmentation to limit access to management interfaces.

---

## TA0008 — Lateral Movement

### T1552.007 — Container Service Discovery
Adversaries pivot from one compromised container to others on the same network. All containers on a default Docker bridge network can communicate with each other.

**Mitigation:**
- Create separate Docker networks for services that do not need to communicate.
- Use `--icc=false` to disable inter-container communication by default.
- Explicitly link only the service pairs that need to talk.

---

## TA0010 — Exfiltration

### T1048 — Exfiltration Over Alternative Protocol
Adversaries exfiltrate data over protocols not normally monitored: DNS, ICMP, non-standard ports.

**Mitigation:**
- Restrict outbound network access from containers to only required destinations.
- Use egress filtering at the network level.
- Monitor outbound traffic for anomalies.
