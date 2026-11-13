# Lesson 4: Thinking Like an Attacker Inside a Container

The audit is a list of settings. This lesson shows what those settings mean in practice.

Imagine an attacker found a bug in a library the API uses, and can now run commands inside the `rag-api` container. `docker exec` runs commands inside a container as its normal user, which is exactly the position that attacker would be in.

---

## Run the demo

```bash
bin/attacker_demo.sh
```

### What you will see

```
Attacker inside rag-api. Can they...
  run as root?                                 YES  uid 0 (root)
  plant a backdoor in the app's code?          YES  main.py modified
  drop a tool in /var/tmp and run it?          YES  tool ran
  run a program from /tmp?                     YES  tool ran
  install packages (apt-get)?                  YES  package lists downloaded
  change file ownership (CAP_CHOWN)?           YES  chown worked
  open raw network sockets (CAP_NET_RAW)?      YES  raw socket opened
  read the API key from the environment?       YES  EDGE_API_KEY=wIyrm6...

Without even entering the container, anyone who can run docker commands can:
  read the API key with docker inspect      YES
```

Everything worked. Read each line as an attacker's next step:

| Capability | What an attacker does with it |
|---|---|
| Root | Anything below, without needing tricks |
| Modify app code | Plant a backdoor in `main.py` that logs every user's question or leaks the API key. It runs every time the API handles a request |
| Drop and run tools | Bring their own scanner, tunnel, or crypto-miner |
| Install packages | Pull in any software from the internet |
| Change ownership | Take over files belonging to other processes |
| Raw sockets | Craft network packets to scan or spoof other containers |
| Read the key | Call the API directly, skipping the UI, from anywhere |

The last line is not even an attack inside the container. Anyone who can run `docker` commands on the host (a teammate, a CI job, a compromised monitoring tool) can read every environment variable:

```bash
docker inspect rag-api --format '{{range .Config.Env}}{{println .}}{{end}}' | grep EDGE_API_KEY | cut -c1-22
```

```
EDGE_API_KEY=wIyrm6Sx2
```

(Printed cut short on purpose. Never put a full secret on your screen.)

---

## Undo the backdoor

The demo really did modify the running API's code:

```bash
docker exec rag-api tail -1 /app/app/main.py
```

```
# backdoor
```

Restarting does **not** remove it: changes inside a container survive a restart. Recreate the container from its image:

```bash
docker compose up -d --force-recreate ingestion-api
docker exec rag-api tail -1 /app/app/main.py
```

The last line is back to normal code. Recreating replaces the container's filesystem with a fresh copy of the image, which is a useful property you will make permanent in Lesson 7.

---

## Keep these results

Each of the next four lessons turns some `YES` answers into `no`. Re-run `bin/attacker_demo.sh` after every layer and watch them change.

Next: [Layer 1: Non-Root Users](05-non-root.md)
