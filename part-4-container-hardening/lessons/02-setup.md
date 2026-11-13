# Lesson 2: Setup

Part 4 starts from the finished Part 3 system: the RAG chatbot with all four prompt injection guards **on**. It reuses the models you downloaded in Part 3.

---

## Step 1: Stop Part 3

```bash
cd ~/Training-Module-Production-Grade-RAG-Infrastructure-Milvus/part-3-prompt-injection
docker compose down
```

## Step 2: Move into Part 4

```bash
cd ~/Training-Module-Production-Grade-RAG-Infrastructure-Milvus/part-4-container-hardening
ls
```

```
README.md  attacks  bin  data  db  docker-compose.yml  gradio-ui  hardening  ingestion-api  lessons  nginx  secrets
```

New in Part 4:

| Item | Purpose |
|---|---|
| `hardening/` | The six hardening layers, one file each |
| `bin/audit.py` | Scores every container against the hardening checklist |
| `bin/attacker_demo.sh` | Acts like an attacker inside the API container |
| `bin/harden.sh` | Turns hardening layers on (`bin/harden.sh 3` = layers 1 to 3) |
| `bin/scan_images.sh` | Scans every image for known vulnerabilities |
| `bin/pin_images.sh` | Pins every image to the exact version you scanned |

## Step 3: Secrets, build, and start

```bash
bin/setup_secrets.sh
docker compose up -d --build
```

`setup_secrets.sh` now also creates:
- `secrets/edge_api_key.txt` and `secrets/edge_key.map`: the API key as files (Lesson 8)
- `secrets/tls_ca.crt`, `secrets/milvus_server.crt`, `secrets/milvus_server.key`: a private certificate authority and a certificate for Milvus, and `secrets/milvus_user_tls.yaml`, Milvus's settings with TLS turned on (Lesson 9)

## Step 4: Models and data

```bash
bin/pull_models.sh
bin/ingest_sample.sh
```

> Download models **now**, before hardening. From Lesson 5 on, the models are mounted read-only, so they cannot be changed from inside the Ollama container, including by you.

## Step 5: Confirm it works

```bash
bin/smoke_test.sh
python3 attacks/run_attacks.py
```

The smoke test passes, and the attack suite shows the Part 3 result with every guard on (0 of 8, occasionally 1).

## Step 6: Confirm no hardening is active

```bash
bin/harden.sh status
```

```
  docker-compose.yml
```

Only the base file. That is your starting point.

---

## How `bin/harden.sh` works

Docker Compose reads a setting called `COMPOSE_FILE` from `.env`. It lists which compose files to combine. `bin/harden.sh 2` sets it to:

```
COMPOSE_FILE=docker-compose.yml:hardening/01-non-root.yml:hardening/02-capabilities.yml
```

and restarts whatever changed. Because the setting lives in `.env`, **every** plain `docker compose` command (`ps`, `logs`, `down`) uses the same layers automatically.

Next: [Auditing the Containers](03-audit.md)
