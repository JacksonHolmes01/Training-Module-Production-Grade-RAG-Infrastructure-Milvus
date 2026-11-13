# Lesson 7: Layer 3: Read-Only Filesystems

After Layer 2, the attacker cannot change the app's code, but they can still **bring their own tools**: `/var/tmp` and `/tmp` are writable by every user, and anything written there can be run.

A **read-only root filesystem** means nothing in the container can be changed at all, except the specific folders you choose.

---

## Read the layer

Open `hardening/03-read-only.yml`:

```yaml
  ingestion-api:
    read_only: true
    tmpfs:
      - /tmp:noexec,nosuid,size=64m
```

- `read_only: true` makes every file in the container's image unchangeable, for every user, including root
- `tmpfs` mounts a small folder **in memory**. Programs that need scratch space get it, and it vanishes when the container stops
- `noexec` means nothing in that folder can be run as a program. Scratch space is for data, not tools
- `nosuid` means setuid bits on files there are ignored
- `size=64m` stops scratch space from filling memory

Data volumes (the database's data, Ollama's models) are separate mounts and are not affected by `read_only`. The database can still save data; it just cannot change its own program files.

### Each service needs different scratch folders

| Service | Writable folders | Why |
|---|---|---|
| etcd | `/tmp` | etcd keeps all its data in its data volume |
| minio | `/tmp` (owned by 10001) | MinIO keeps its data in its volume; `/tmp` doubles as its home folder |
| milvus | `/tmp` (owned by 999) | Milvus writes temporary files, and its access log, to `/tmp` |
| milvus-init | `/tmp` | Python's temporary files |
| ollama | `/tmp` (**without** `noexec`) | Ollama unpacks its model runner programs into `/tmp` and runs them |
| ingestion-api | `/tmp` | Python's temporary files |
| nginx | `/tmp`, `/etc/nginx/conf.d` | NGINX writes its cache files to `/tmp` and renders its config into `conf.d` at startup |
| gradio-ui | `/tmp` | Gradio's upload and cache folder |

Finding this list is the real work of this layer. The method: turn on `read_only`, start the service, read its error, add exactly the folder it complained about, repeat.

### A failure worth seeing

While this lab was being built, the first version of this layer gave NGINX a plain `tmpfs` for `/etc/nginx/conf.d`. The container started, reported **Up**, and served nothing. Its log said:

```
20-envsubst-on-templates.sh: ERROR: /etc/nginx/templates exists, but /etc/nginx/conf.d is not writable
```

A new `tmpfs` belongs to root, and NGINX now runs as user 101 (Layer 1). NGINX could not write its config, so it started with **no config at all**. The fix:

```yaml
      - /etc/nginx/conf.d:uid=101,gid=101,mode=0755
```

The lesson: **"the container is running" is not "the service works."** Only the smoke test caught this.

---

## Apply it

```bash
bin/harden.sh 3
bin/smoke_test.sh
```

## Prove the filesystem is locked

```bash
docker exec rag-api sh -c 'touch /app/test 2>&1; touch /var/tmp/test 2>&1; touch /tmp/test && echo "/tmp is writable (scratch space)"'
```

```
touch: cannot touch '/app/test': Read-only file system
touch: cannot touch '/var/tmp/test': Read-only file system
/tmp is writable (scratch space)
```

## Audit

```bash
python3 bin/audit.py
```

`read-only` passes everywhere: **53 of 63 (84%)**.

## Attack again

```bash
bin/attacker_demo.sh
```

```
  drop a tool in /var/tmp and run it?          no   Read-only file system
  run a program from /tmp?                     no   Permission denied
```

The attacker can write a file to `/tmp`, but `noexec` stops it from running. Only one `YES` remains: the API key in the environment.

### A bonus: every restart is a clean slate

With a read-only filesystem, nothing an attacker does inside the container survives a restart: `/tmp` is in memory, and everything else could not be changed in the first place. Compare that with Lesson 4, where the backdoor survived until you recreated the container.

Next: [Layer 4: Secrets Out of Environment Variables](08-secrets.md)
