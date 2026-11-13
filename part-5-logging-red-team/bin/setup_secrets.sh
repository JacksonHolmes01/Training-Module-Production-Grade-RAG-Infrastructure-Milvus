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
#   secrets/milvus_user_tls.yaml        the same, plus TLS (Layer 5)
#   secrets/tls_ca.*, milvus_server.*   certificate authority and Milvus's certificate (Layer 5)
set -euo pipefail
cd "$(dirname "$0")/.."

gen() { openssl rand -base64 48 | tr -d '/+=\n' | cut -c1-40; }

mkdir -p secrets
for name in milvus_root_password milvus_writer_password milvus_reader_password minio_password; do
  f="secrets/${name}.txt"
  if [[ -s "$f" ]]; then echo "  kept     $f"; else gen > "$f"; echo "  created  $f"; fi
done
[[ -s secrets/minio_user.txt ]] || printf 'lab-%s' "$(openssl rand -hex 4)" > secrets/minio_user.txt

# ---------------------------------------------------------------
# A private certificate authority (CA) and a certificate for Milvus,
# used for encrypted, verified API-to-database traffic (Lesson 9).
# ---------------------------------------------------------------
if [[ -s secrets/tls_ca.crt && -s secrets/milvus_server.crt ]]; then
  echo "  kept     TLS certificates"
else
  openssl req -x509 -newkey rsa:2048 -nodes -days 365 -subj "/CN=Secure AI Lab CA" \
    -addext "basicConstraints=critical,CA:TRUE" -addext "keyUsage=critical,keyCertSign,cRLSign" \
    -keyout secrets/tls_ca.key -out secrets/tls_ca.crt 2>/dev/null
  openssl req -newkey rsa:2048 -nodes -subj "/CN=milvus" \
    -keyout secrets/milvus_server.key -out secrets/milvus_server.csr 2>/dev/null
  printf 'subjectAltName=DNS:milvus\nextendedKeyUsage=serverAuth\n' > secrets/milvus_server.ext
  openssl x509 -req -in secrets/milvus_server.csr -CA secrets/tls_ca.crt -CAkey secrets/tls_ca.key \
    -CAcreateserial -days 365 -extfile secrets/milvus_server.ext -out secrets/milvus_server.crt 2>/dev/null
  rm -f secrets/milvus_server.csr secrets/milvus_server.ext secrets/tls_ca.srl
  echo "  created  TLS certificate authority and Milvus certificate"
fi

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

# Layer 5 (Lesson 9): the same settings plus TLS. Milvus serves HTTPS with the
# certificate below and refuses plain connections.
cat secrets/milvus_user.yaml > secrets/milvus_user_tls.yaml
cat >> secrets/milvus_user_tls.yaml <<YAML
tls:
  serverPemPath: /run/secrets/milvus_server_crt
  serverKeyPath: /run/secrets/milvus_server_key
  caPemPath: /run/secrets/tls_ca_crt
YAML
# Milvus allows TLS only when the REST API has a port of its own
sed -i.bak 's/^proxy:$/proxy:\n  http:\n    port: 19531/' secrets/milvus_user_tls.yaml && rm -f secrets/milvus_user_tls.yaml.bak
if ! grep -q 'port: 19531' secrets/milvus_user_tls.yaml; then
  python3 - <<'PY2'
p = "secrets/milvus_user_tls.yaml"; s = open(p).read()
s = s.replace("proxy:\n", "proxy:\n  http:\n    port: 19531\n", 1)
open(p, "w").write(s)
PY2
fi
# tlsMode belongs under common.security, next to the login settings
sed -i.bak 's/^    authorizationEnabled: true$/    authorizationEnabled: true\n    tlsMode: 1/' secrets/milvus_user_tls.yaml && rm -f secrets/milvus_user_tls.yaml.bak
if ! grep -q 'tlsMode: 1' secrets/milvus_user_tls.yaml; then
  python3 - <<'PY'
p = "secrets/milvus_user_tls.yaml"; s = open(p).read()
s = s.replace("    authorizationEnabled: true\n", "    authorizationEnabled: true\n    tlsMode: 1\n", 1)
open(p, "w").write(s)
PY
fi

# Mode 644: in Part 4 every container runs as a non-root user (999 for
# Milvus, 10001 for the others), so the files must be readable by a user
# other than you. See lessons/08-secrets.md for the trade-off.
chmod 644 secrets/*.txt secrets/*.yaml

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

# ---------------------------------------------------------------
# Edge API key: lives in .env for your own scripts (curl, the attack
# harness), and in secrets/ as files for the containers (Lesson 8).
# ---------------------------------------------------------------
KEY="$(grep -E '^EDGE_API_KEY=' .env | cut -d= -f2-)"
printf '%s' "$KEY" > secrets/edge_api_key.txt
printf '"%s" 1;\n' "$KEY" > secrets/edge_key.map
chmod 644 secrets/edge_api_key.txt secrets/edge_key.map
echo "  wrote    secrets/edge_api_key.txt and secrets/edge_key.map"

# Parts 3, 4, and 5 share one model volume, so models download only once
docker volume create secure-ai-milvus_ollama_data >/dev/null
echo "  ready    model volume secure-ai-milvus_ollama_data"
echo "Secrets ready."
chmod 600 secrets/tls_ca.key
