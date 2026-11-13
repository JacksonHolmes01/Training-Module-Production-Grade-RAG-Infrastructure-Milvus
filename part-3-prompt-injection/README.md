# Part 3: Prompt Injection Attacks and Defenses

In Lab 1 (the main lab in the root of this repository) you built a RAG chatbot and noticed something uncomfortable: the model's rules, the retrieved documents, and the user's question are all just text in one prompt. The model cannot reliably tell instructions from data.

In Part 3 you exploit that. You will make the chatbot ignore its rules, leak a secret from its prompt, adopt a new persona, send users to a fake login page, and smuggle data out through an image. Along the way you lock Milvus down: a login on every request, a root password nothing running holds, roles that limit each login to one tenant and one kind of action, and its two helper services (etcd and MinIO) walled off on a private network with no default passwords. Then you add four layers of defense, one at a time, and **measure** what each one stops.

---

## The scoreboard you will build

Measured on `llama3.2:1b` with the default settings in this lab:

| Defenses on | Attacks that succeed |
|---|---|
| None | 7 of 8 |
| + Input screening | 4 of 8 |
| + Prompt hardening and data sanitization | 1 of 8 |
| + Output filtering | 0 of 8 |
| + Ingest screening | Poisoned documents rejected at the door |

One attack, a disguised override written in French, gets through on some runs even with every defense on. Lesson 10 explains why it is the hardest kind to stop.

---

## Lessons (read in order)

1. [What Prompt Injection Is](lessons/01-overview.md)
2. [Setup](lessons/02-setup.md)
3. [Direct Attacks: Talking the Model Out of Its Rules](lessons/03-direct-attacks.md)
4. [Indirect Attacks: Poisoned Documents](lessons/04-indirect-attacks.md)
5. [Measuring the Baseline](lessons/05-baseline.md)
6. [Defense 1: Input Screening](lessons/06-input-guard.md)
7. [Defense 2: Prompt Hardening and Data Sanitization](lessons/07-prompt-guard.md)
8. [Defense 3: Output Filtering](lessons/08-output-guard.md)
9. [Defense 4: Ingest Screening and Cleanup](lessons/09-ingest-guard.md)
10. [Operating the Defenses](lessons/10-operations.md)
11. [Conclusion](lessons/11-conclusion.md)

---

## Quick start

```bash
bin/setup_secrets.sh
docker compose up -d --build
bin/pull_models.sh
bin/ingest_sample.sh
python3 attacks/run_attacks.py --plant
```

## Requirements
- Lab 1 completed (the main lab in the root of this repository)
- Docker with Compose v2, 8 GB RAM free for Docker
- `python3` on your computer (standard library only)

---

> **Ethics note.** These techniques are taught so you can defend systems you own or are authorized to test. Do not use them against systems you do not have permission to test.

License: code is MIT, lessons are CC BY-SA 4.0. See [README-LICENSE.md](../README-LICENSE.md).
