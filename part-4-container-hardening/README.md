# Part 4: Container Hardening

Parts 1 to 3 controlled who can **talk to** the system. Part 4 asks: **if an attacker gets code running inside a container anyway, how much damage can they do?**

You will audit every container, play the attacker inside one, then add six hardening layers one at a time, re-measuring after each and proving the system still works.

---

## The scoreboard you will build

| Layers on | Audit score | Attacker actions that work |
|---|---|---|
| None | 22 of 63 (34%) | 8 of 8 |
| + 1 non-root users | 28 of 63 (44%) | 3 |
| + 2 no capabilities, no escalation, process limits | 46 of 63 (73%) | 3 |
| + 3 read-only filesystems | 53 of 63 (84%) | 1 |
| + 4 secrets out of environment variables | 56 of 63 (88%) | 0 |
| + 5 encrypted, verified API-to-database traffic | 56 of 63 (88%) | 0 |
| + 6 images scanned and pinned by digest | 63 of 63 (100%) | 0 |

---

## Lessons (read in order)

1. [Why Harden Containers?](lessons/01-overview.md)
2. [Setup](lessons/02-setup.md)
3. [Auditing the Containers](lessons/03-audit.md)
4. [Thinking Like an Attacker Inside a Container](lessons/04-attacker-demo.md)
5. [Layer 1: Non-Root Users](lessons/05-non-root.md)
6. [Layer 2: Capabilities, Escalation, and Limits](lessons/06-capabilities.md)
7. [Layer 3: Read-Only Filesystems](lessons/07-read-only.md)
8. [Layer 4: Secrets Out of Environment Variables](lessons/08-secrets.md)
9. [Layer 5: Encrypted, Verified Traffic Between Services](lessons/09-internal-tls.md)
10. [Layer 6: Scan and Pin Your Images](lessons/10-scan-and-pin.md)
11. [Final Verification](lessons/11-verify.md)
12. [Conclusion](lessons/12-conclusion.md)

---

## Quick start

```bash
bin/setup_secrets.sh
docker compose up -d --build
bin/pull_models.sh
bin/ingest_sample.sh
python3 bin/audit.py
bin/harden.sh 5
bin/pin_images.sh && bin/harden.sh 6
python3 bin/audit.py
```

## Requirements
- Part 3 completed (Part 4 reuses its downloaded models)
- Docker with Compose **v2.24 or newer** (for `!override` in the hardening files)
- `python3` and `openssl` on your computer

---

License: code is MIT, lessons are CC BY-SA 4.0. See [README-LICENSE.md](../README-LICENSE.md).
