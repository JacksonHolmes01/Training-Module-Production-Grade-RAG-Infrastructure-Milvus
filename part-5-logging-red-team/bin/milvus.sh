#!/usr/bin/env bash
# Send one request to Milvus as a given user, from inside the lab network.
# Milvus has no published port, so this runs the request from the API container.
# Every Milvus REST call is a POST to /v2/vectordb/<area>/<action> with a JSON body.
#
# Usage: bin/milvus.sh <root|writer|reader|none> <path> [json-body]
# Examples:
#   bin/milvus.sh reader /v2/vectordb/collections/list '{"dbName":"tenant_lab"}'
#   bin/milvus.sh reader /v2/vectordb/collections/drop '{"dbName":"tenant_lab","collectionName":"docs"}'   (refused)
#   bin/milvus.sh root   /v2/vectordb/entities/delete '{"dbName":"tenant_lab","collectionName":"docs","filter":"id in [\"<id>\"]"}'
set -euo pipefail
cd "$(dirname "$0")/.."
WHO="${1:?usage: bin/milvus.sh <root|writer|reader|none> <path> [json]}"
P="${2:?path}"; BODY="${3:-}"; [[ -n "$BODY" ]] || BODY="{}"
case "$WHO" in
  root)   CRED="root:$(cat secrets/milvus_root_password.txt)" ;;
  writer) CRED="rag_writer:$(cat secrets/milvus_writer_password.txt)" ;;
  reader) CRED="rag_reader:$(cat secrets/milvus_reader_password.txt)" ;;
  none)   CRED="" ;;
  *) echo "user must be root, writer, reader, or none"; exit 1 ;;
esac
URL="$(docker exec rag-api printenv MILVUS_URL)"
CA=""; docker exec rag-api test -f /run/secrets/tls_ca_crt 2>/dev/null && CA=/run/secrets/tls_ca_crt
# The credential travels on stdin (line 1), so it never appears in a process list.
{ printf '%s\n' "$CRED"; printf '%s' "$BODY"; } | docker exec -i rag-api python -c '
import json, sys, httpx
url, path, ca = sys.argv[1:4]
cred = sys.stdin.readline().strip()
body = sys.stdin.read()
h = {"Content-Type": "application/json"}
if cred:
    h["Authorization"] = "Bearer " + cred
r = httpx.post(url + path, headers=h, content=body, verify=ca or True, timeout=30)
print(r.status_code)
try:
    print(json.dumps(r.json(), indent=2)[:4000])
except Exception:
    print(r.text[:2000])
' "$URL" "$P" "$CA"
