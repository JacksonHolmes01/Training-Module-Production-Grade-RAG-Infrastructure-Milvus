#!/usr/bin/env bash
# Pretend an attacker found a bug that lets them run commands inside the
# API container (for example, a vulnerable library). `docker exec` runs each
# command as the container's normal user, exactly as that attacker would.
#
# Usage: bin/attacker_demo.sh
set -uo pipefail
cd "$(dirname "$0")/.."
C=rag-api

try() {  # try <description> <command>
  if out=$(docker exec "$C" sh -c "$2" 2>&1); then
    printf "  %-44s YES  %s\n" "$1" "$(echo "$out" | head -1 | cut -c1-40)"
  else
    printf "  %-44s no   %s\n" "$1" "$(echo "$out" | tail -1 | cut -c1-40)"
  fi
}

echo "Attacker inside $C. Can they..."
try "run as root?"                          'test "$(id -u)" = 0 && echo "uid 0 (root)" || { echo "uid $(id -u)"; false; }'
try "plant a backdoor in the app's code?"   'echo "# backdoor" >> /app/app/main.py && echo "main.py modified"'
try "drop a tool in /var/tmp and run it?"   'printf "#!/bin/sh\necho tool ran\n" > /var/tmp/tool && chmod +x /var/tmp/tool && /var/tmp/tool'
try "run a program from /tmp?"              'printf "#!/bin/sh\necho tool ran\n" > /tmp/tool && chmod +x /tmp/tool && /tmp/tool'
try "install packages (apt-get)?"           'apt-get update -qq >/dev/null 2>&1 && echo "package lists downloaded"'
try "change file ownership (CAP_CHOWN)?"    'chown 0:0 /tmp && echo "chown worked"'
try "open raw network sockets (CAP_NET_RAW)?" 'python -c "import socket; socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_ICMP)" && echo "raw socket opened"'
try "read the API key from the environment?" 'env | grep -q "^EDGE_API_KEY=" && echo "EDGE_API_KEY=$(env | sed -n "s/^EDGE_API_KEY=\(.\{6\}\).*/\1/p")..."'

echo
echo "Without even entering the container, anyone who can run docker commands can:"
if docker inspect "$C" --format '{{range .Config.Env}}{{println .}}{{end}}' | grep -q '^EDGE_API_KEY='; then
  echo "  read the API key with docker inspect      YES"
else
  echo "  read the API key with docker inspect      no"
fi
