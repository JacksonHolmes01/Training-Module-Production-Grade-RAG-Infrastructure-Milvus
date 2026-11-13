# Lesson 1: From Prevention to Detection

## Where you are

Over four parts you built a RAG chatbot and protected it in layers:

| Part | Protects against |
|---|---|
| 1 | Unauthorized database access |
| 2 | Direct access to internal services; misuse of credentials |
| 3 | Prompt injection and data poisoning |
| 4 | Damage after an attacker gets code running inside a container |

All of that is **prevention**. Part 5 answers the question every security team eventually faces:

> **When an attack happens, will we know?**

Prevention fails eventually. A new prompt injection technique, a leaked key, a bug in a library. When it does, the difference between a minor incident and a disaster is usually **how quickly someone notices**.

---

## What you will build

1. **Structured logs.** Every request and every security decision becomes one JSON line, with a request id that follows it across services
2. **Search.** `bin/logs.py` answers questions like "who failed to authenticate in the last hour?"
3. **Detections.** `detections/rules.json` defines ten rules; `bin/detect.py` turns logs into alerts
4. **A red-team campaign.** `bin/redteam.py` runs 12 real attack techniques against your lab
5. **A score.** `bin/coverage.py` checks which attacks your detections noticed
6. **A report.** A findings report you could hand to a team

---

## Red team, blue team

| Team | Role |
|---|---|
| **Red team** | Plays the attacker. Tries techniques a real attacker would use |
| **Blue team** | Plays the defender. Watches logs and alerts, and responds |

In this lab you play both: you run the campaign, then switch hats and check what you caught.

---

## The measure: detection coverage

Parts 3 and 4 measured how many attacks **succeeded**. Part 5 measures how many attacks were **noticed**:

> **Detection coverage = attack steps that raised an alert ÷ total attack steps**

You will start at 8 of 12, improve it, and end with an honest account of what logs can never see.

---

## A note on ethics

Everything in Part 5 runs against **your own lab**, on **your own computer**. `redteam/PLAYBOOK.md` writes that down as formal rules of engagement, the way a real engagement would. Read it before Lesson 7.

Next: [Setup](02-setup.md)
