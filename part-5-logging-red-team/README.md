# Part 5: Logging, Detection, and Red-Teaming

Parts 1 to 4 built defenses. Part 5 asks the question every security team eventually faces: **when an attack happens, will we know?**

You will add structured logging across the system, write detection rules, run a scripted 12-step red-team campaign against your own lab, measure how many attacks your detections noticed, close the gaps you can, and write a findings report on the ones you cannot.

---

## The scoreboard you will build

| Detection rules | Attack steps detected |
|---|---|
| Initial (8 rules on) | 8 of 12 (66%) |
| + endpoint discovery and Milvus login guessing | 10 of 12 (83%) |

The two that remain are different kinds of problems: one is a **tuning** problem (the logs saw it, no alert fired), the other a **visibility** problem (no log can see it). Lesson 9 explains both.

---

## Lessons (read in order)

1. [From Prevention to Detection](lessons/01-overview.md)
2. [Setup](lessons/02-setup.md)
3. [What to Log, and What Never to Log](lessons/03-what-to-log.md)
4. [Searching the Logs](lessons/04-searching-logs.md)
5. [Detection Rules](lessons/05-detection-rules.md)
6. [Planning the Red Team](lessons/06-planning.md)
7. [Running the Campaign](lessons/07-campaign.md)
8. [Closing the Gaps](lessons/08-closing-gaps.md)
9. [Blind Spots](lessons/09-blind-spots.md)
10. [Writing the Report](lessons/10-report.md)
11. [Conclusion](lessons/11-conclusion.md)

---

## Quick start

```bash
bin/setup_secrets.sh
docker compose up -d --build
bin/ingest_sample.sh
python3 bin/redteam.py
python3 bin/coverage.py --report
```

## Requirements
- Part 4 completed (Part 5 reuses the models downloaded in Part 3)
- Docker with Compose v2.24 or newer, 8 GB RAM free for Docker
- `python3` and `openssl` on your computer

---

> **Only run the red-team campaign against your own lab.** See [redteam/PLAYBOOK.md](redteam/PLAYBOOK.md) for the rules of engagement.

License: code is MIT, lessons are CC BY-SA 4.0. See [README-LICENSE.md](../README-LICENSE.md).
