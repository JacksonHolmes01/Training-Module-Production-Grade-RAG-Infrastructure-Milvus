# Lesson 2: Setup

Part 5 starts from the finished Part 4 system: every prompt injection guard on, and hardening layers 1 to 5 on. It adds structured logging to the API and NGINX, and turns on Milvus's own access log.

---

## Step 1: Stop Part 4

```bash
cd ~/Training-Module-Production-Grade-RAG-Infrastructure-Milvus/part-4-container-hardening
docker compose down
```

## Step 2: Move into Part 5

```bash
cd ~/Training-Module-Production-Grade-RAG-Infrastructure-Milvus/part-5-logging-red-team
ls
```

```
README.md  attacks  bin  data  db  detections  docker-compose.yml  gradio-ui  hardening  ingestion-api  lessons  nginx  redteam  secrets
```

New in Part 5:

| Item | Purpose |
|---|---|
| `detections/rules.json` | The detection rules. You will read, enable, and tune them |
| `bin/logs.py` | Search the logs |
| `bin/detect.py` | Turn logs into alerts |
| `bin/redteam.py` | Run the red-team campaign |
| `bin/coverage.py` | Score detection coverage; write a findings report |
| `redteam/PLAYBOOK.md` | Rules of engagement and the campaign plan |

## Step 3: Secrets, build, and start

```bash
bin/setup_secrets.sh
docker compose up -d --build
```

## Step 4: Models and data

Part 5 reuses the models you downloaded in Part 3. Check they are there:

```bash
docker exec rag-ollama ollama list
```

```
NAME                       ID              SIZE      MODIFIED
nomic-embed-text:latest    0a109f422b47    274 MB    ...
llama3.2:1b                baf6a787fdff    1.3 GB    ...
```

> `bin/pull_models.sh` will **fail** here, and that is Part 4 working: the models are mounted read-only. If the list is empty, download them with hardening off, then turn it back on:
> `bin/harden.sh 0 && bin/pull_models.sh && bin/harden.sh 5`

Load the sample documents:

```bash
bin/ingest_sample.sh
```

## Step 5: Confirm it works and is hardened

```bash
bin/smoke_test.sh
python3 bin/audit.py | tail -1
bin/harden.sh status
```

```
All smoke tests passed.
Total: 40 of 45 checks pass (88%)
  docker-compose.yml
  hardening/01-non-root.yml
  hardening/02-capabilities.yml
  hardening/03-read-only.yml
  hardening/04-secrets.yml
  hardening/05-internal-tls.yml
```

Only `pinned` is missing from the audit, because digest pinning (Layer 6) is generated per computer. Run `bin/pin_images.sh && bin/harden.sh 6` if you want it; nothing in Part 5 depends on it.

Next: [What to Log, and What Never to Log](03-what-to-log.md)
