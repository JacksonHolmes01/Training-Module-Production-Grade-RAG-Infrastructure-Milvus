# Lesson 11: Final Verification

Every layer is on. Before calling it done, prove three things: the containers are hardened, the attacker is contained, and the system still does its job.

---

## 1. The audit

```bash
python3 bin/audit.py
```

```
CONTAINER          non-root     no-caps no-escalate   read-only no-env-keys   mem-limit   pid-limit       ports      pinned   SCORE
-----------------------------------------------------------------------------------------------------------------------------------
rag-api                pass        pass        pass        pass        pass        pass        pass        pass        pass     9/9
rag-etcd               pass        pass        pass        pass        pass        pass        pass        pass        pass     9/9
rag-milvus             pass        pass        pass        pass        pass        pass        pass        pass        pass     9/9
rag-minio              pass        pass        pass        pass        pass        pass        pass        pass        pass     9/9
rag-nginx              pass        pass        pass        pass        pass        pass        pass        pass        pass     9/9
rag-ollama             pass        pass        pass        pass        pass        pass        pass        pass        pass     9/9
rag-ui                 pass        pass        pass        pass        pass        pass        pass        pass        pass     9/9
-----------------------------------------------------------------------------------------------------------------------------------
Total: 63 of 63 checks pass (100%)
```

## 2. The attacker

```bash
bin/attacker_demo.sh
```

```
Attacker inside rag-api. Can they...
  run as root?                                 no   uid 10001
  plant a backdoor in the app's code?          no   Read-only file system
  drop a tool in /var/tmp and run it?          no   Read-only file system
  run a program from /tmp?                     no   Permission denied
  install packages (apt-get)?                  no
  change file ownership (CAP_CHOWN)?           no   Operation not permitted
  open raw network sockets (CAP_NET_RAW)?      no   Operation not permitted
  read the API key from the environment?       no

Without even entering the container, anyone who can run docker commands can:
  read the API key with docker inspect      no
```

Every `YES` from Lesson 4 is now `no`.

## 3. The system still works

```bash
bin/smoke_test.sh
python3 attacks/run_attacks.py
```

The smoke test passes, and the Part 3 attack suite gives the same result as before hardening (0 of 8, occasionally 1). Container hardening did not weaken the prompt injection defenses, and the prompt injection defenses did not need any changes to run hardened.

Open http://localhost:7860 and ask a question to see it with your own eyes.

---

## Your scoreboard

| Layers on | Audit score | Attacker demo `YES` answers |
|---|---|---|
| None | 22 of 63 (34%) | 8 of 8 |
| + 1 non-root | 28 of 63 (44%) | 3 |
| + 2 capabilities, escalation, limits | 46 of 63 (73%) | 3 |
| + 3 read-only | 53 of 63 (84%) | 1 |
| + 4 secrets out of env | 56 of 63 (88%) | 0 |
| + 5 internal TLS | 56 of 63 (88%) | 0 |
| + 6 pinned by digest | 63 of 63 (100%) | 0 |

Notice that two layers did not move one of the numbers at all: Layer 2 left the attacker demo unchanged, and Layer 5 left the audit unchanged. Each still closed real gaps, which you verified with `/proc/1/status` and a plain-HTTP request that Milvus refused. **A single scorecard never tells the whole story.**

---

## Going back

`bin/harden.sh` works in both directions. To see the difference again at any time:

```bash
bin/harden.sh 0
bin/attacker_demo.sh
bin/harden.sh 6
```

Next: [Conclusion](12-conclusion.md)
