# Lesson 6: Layer 2: Capabilities, Escalation, and Limits

Lesson 5's demo already showed `chown` and raw sockets failing. So why another layer?

Because "not root right now" is not the same as "cannot become powerful." This layer removes the ways back up.

---

## What capabilities are

Linux splits root's power into about 40 separate **capabilities**. For example:

| Capability | Allows |
|---|---|
| `CAP_CHOWN` | Change any file's owner |
| `CAP_NET_RAW` | Craft raw network packets (spoofing, scanning) |
| `CAP_SETUID` | Switch to any user, including root |
| `CAP_DAC_OVERRIDE` | Ignore file permissions entirely |
| `CAP_SYS_CHROOT` | Change the root directory |

Docker gives every container a default set of about 14. A non-root process does not **use** them, but they stay in the container's **bounding set**: the ceiling of what any process in the container could ever get. A program marked **setuid** (like `su` or `passwd`) runs with root's power no matter who starts it, and can pick those capabilities back up.

## See it for yourself

The kernel reports a process's capabilities in `/proc/1/status`:

```bash
docker exec rag-api grep -E "CapBnd|NoNewPrivs" /proc/1/status
echo "pids.max: $(docker exec rag-api cat /sys/fs/cgroup/pids.max)"
```

### What you will see (Layer 1 only)

```
CapBnd:	00000000a80425fb
NoNewPrivs:	0
pids.max: max
```

- `CapBnd` is a bit mask. `a80425fb` means 14 capabilities are still available in principle
- `NoNewPrivs: 0` means a setuid program **can** raise a process's privileges
- `pids.max: max` means there is no limit on the number of processes. A "fork bomb" (a program that copies itself endlessly) could freeze the host

---

## Read the layer

Open `hardening/02-capabilities.yml`:

```yaml
x-locked-down: &locked-down
  cap_drop: [ALL]
  security_opt: ["no-new-privileges:true"]
  pids_limit: 256

services:
  etcd: *locked-down
  minio: *locked-down
  milvus:
    cap_drop: [ALL]
    security_opt: ["no-new-privileges:true"]
  milvus-init: *locked-down
  ollama: *locked-down
  ingestion-api: *locked-down
  nginx: *locked-down
  gradio-ui: *locked-down
```

- `cap_drop: [ALL]` empties the bounding set. No process in the container can ever hold a capability
- `no-new-privileges:true` makes setuid programs powerless: they run with the privileges of whoever started them
- `pids_limit: 256` caps the number of processes. Milvus runs many worker threads, so it does not use the anchor's 256; it keeps the limit of 512 it was given in `docker-compose.yml`

`x-locked-down` with `&` and `*` is a YAML **anchor**: the settings are written once and reused for every service. Repeating security settings by hand is how one service ends up forgotten.

> **Order matters.** This layer requires Layer 1. Without it, etcd and MinIO would still run as root over data folders owned by root, and many images that start as root need capabilities such as `CAP_SETUID` to switch users. Starting as an ordinary user (Layer 1) means no service needs any capability. `storage-perms`, the one root container, already got its own minimal capability list in Layer 1.

---

## Apply it

```bash
bin/harden.sh 2
bin/smoke_test.sh
```

Look again:

```bash
docker exec rag-api grep -E "CapBnd|NoNewPrivs" /proc/1/status
echo "pids.max: $(docker exec rag-api cat /sys/fs/cgroup/pids.max)"
```

```
CapBnd:	0000000000000000
NoNewPrivs:	1
pids.max: 256
```

Every bit in the bounding set is zero, escalation is blocked, and processes are capped.

## Audit

```bash
python3 bin/audit.py
```

`no-caps`, `no-escalate`, and `pid-limit` pass everywhere: **46 of 63 (73%)**.

## Attack again

```bash
bin/attacker_demo.sh
```

The answers look the same as after Layer 1. That is expected. This layer closes doors the demo does not try: escalation through setuid programs, a bug in the kernel that needs a capability, and resource exhaustion. You verified those with `/proc/1/status` instead. **Not every defense shows up in the same test**, which is why you use several kinds of evidence.

Next: [Layer 3: Read-Only Filesystems](07-read-only.md)
