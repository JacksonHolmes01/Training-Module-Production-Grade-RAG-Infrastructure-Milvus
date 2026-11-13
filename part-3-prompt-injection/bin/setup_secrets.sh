#!/usr/bin/env bash
# Creates every secret this lab needs. Safe to run more than once:
# existing secrets are kept, never overwritten.
#
#   secrets/milvus_root_password.txt    Milvus root password (only milvus-init uses it)
#   secrets/milvus_writer_password.txt  password for user rag_writer (insert only)
#   secrets/milvus_reader_password.txt  password for user rag_reader (search and query only)
#   secrets/minio_user.txt              MinIO's user name   (replaces the default "minioadmin")
#   secrets/minio_password.txt          MinIO's password    (replaces the default "minioadmin")
#   secrets/milvus_user.yaml            Milvus settings: login on, the root password,
#                                       the MinIO credentials, and the access log
set -euo pipefail
cd "$(dirname "$0")/.."

gen() { openssl rand -base64 48 | tr -d '/+=\n' | cut -c1-40; }

mkdir -p secrets
for name in milvus_root_password milvus_writer_password milvus_reader_password minio_password; do
  f="secrets/${name}.txt"
  if [[ -s "$f" ]]; then echo "  kept     $f"; else gen > "$f"; echo "  created  $f"; fi
done
[[ -s secrets/minio_user.txt ]] || printf 'lab-%s' "$(openssl rand -hex 4)" > secrets/minio_user.txt

# Milvus reads this file as configs/user.yaml, on top of its defaults.
# The root password applies the FIRST time Milvus starts with an empty
# database. Changing it later needs Milvus's password-change API.
cat > secrets/milvus_user.yaml <<YAML
common:
  security:
    authorizationEnabled: true
    defaultRootPassword: "$(cat secrets/milvus_root_password.txt)"
minio:
  accessKeyID: "$(cat secrets/minio_user.txt)"
  secretAccessKey: "$(cat secrets/minio_password.txt)"
proxy:
  accessLog:
    # One line per request: who, from where, what, and the result (Part 5)
    enable: true
    minioEnable: false
    localPath: /tmp/milvus_access
    filename: ""
YAML

# Milvus runs as its own user (999), not root, so the files it reads must be
# readable by a user other than you: 644. Part 4, Lesson 8 discusses this
# trade-off. Everything else stays private to you: 600.
chmod 600 secrets/*.txt
chmod 644 secrets/milvus_user.yaml

if [[ ! -f .env ]]; then
  cp .env.example .env
  echo "  created  .env (from .env.example)"
fi
if ! grep -qE '^EDGE_API_KEY=.{32,}' .env; then
  sed -i.bak "s|^EDGE_API_KEY=.*|EDGE_API_KEY=$(gen)|" .env && rm -f .env.bak
  echo "  created  EDGE_API_KEY in .env"
else
  echo "  kept     EDGE_API_KEY in .env"
fi
chmod 600 .env
# Parts 3, 4, and 5 share one model volume, so models download only once
docker volume create secure-ai-milvus_ollama_data >/dev/null
echo "  ready    model volume secure-ai-milvus_ollama_data"
echo "Secrets ready."
