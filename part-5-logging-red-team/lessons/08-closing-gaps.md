# Lesson 8: Closing the Gaps

Four steps went unnoticed. Investigate each one the way a blue team would: first, **did the logs see it at all?**

---

## R10: Endpoint discovery

```bash
python3 bin/logs.py --since 15m --status 404
```

```
18:31:47  edge_request      172.18.0.1      9a7d...    GET /admin -> 404
18:31:47  api_request       172.18.0.1      9a7d...    GET /admin -> 404
18:31:47  edge_request      172.18.0.1      2c1f...    GET /.env -> 404
...
```

The logs saw **every** request. Someone with a valid key tried `/admin`, `/.env`, `/backup.sql`, `/graphql`. The data was there; nothing was watching for it. Rule D9 exists for exactly this, and it is **disabled**.

## R11: Database credential guessing

```bash
python3 bin/logs.py --since 15m --kind db_auth_failure
```

```
05:58:21  db_auth_failure   172.19.0.7                user=Unknown /v2/vectordb/databases/list -> 401
05:58:21  db_auth_failure   172.19.0.7                user=Unknown /v2/vectordb/databases/list -> 401
...
```

Five failed logins from `172.19.0.7`, an address **inside** the Docker network. That is one of the most serious signals in the whole lab: only containers on the private network can even reach Milvus, and the real services always log in correctly, so a wrong password means something inside is compromised. Rule D10 is **disabled** too.

### Why would rules be disabled?

In real systems this happens all the time:
- a rule was noisy once, someone turned it off "temporarily," and nobody turned it back on
- a new log source was added, but nobody wrote rules for it
- a rule was written but never tested, so nobody noticed it was off

**Logging without detection is a gap that feels like coverage.**

---

## Enable the two rules

```bash
python3 bin/detect.py --enable D9
python3 bin/detect.py --enable D10
```

## Re-score the same campaign

You do not need to attack again. `coverage.py` re-applies the current rules to the logs of the saved run:

```bash
python3 bin/coverage.py
```

### What you will see

```
R10   Endpoint discovery             YES       D9 Endpoint discovery
R11   Database credential guessing   YES       D10 Milvus login guessing
R12   Attacker inside a container    no        -
------------------------------------------------------------------------------
Detection coverage: 10 of 12 attack steps (83%)
```

Re-scoring old activity with new rules is a real practice called **retro-hunting**: when you write a new detection, run it over past logs to find attacks that already happened.

---

## Experiment: catch R01 by lowering a threshold?

R01 was a single blocked injection, below D4's threshold of 2. What if the threshold were 1?

Open `detections/rules.json`, find D4, change `"threshold": 2` to `"threshold": 1`, save, and re-score:

```bash
python3 bin/coverage.py | grep -E "R01|R05|coverage"
```

### What you will see

```
R01   Low-and-slow injection         YES       D4 Prompt injection probing
R05   Prompt injection burst         no        -
Detection coverage: 10 of 12 attack steps (83%)
```

R01 is now caught, but **R05 disappeared**. D4 fired on R01's single attempt, then went quiet for that address for its 5-minute window, so the burst a few seconds later raised nothing new. The blind spot moved; it did not close.

Two lessons in one experiment:
- **Every tuning change has side effects.** Re-measure everything, not just the case you meant to fix
- **Quiet periods hide follow-up activity.** Real tools usually still record suppressed events and attach them to the open alert, so a responder sees "1 alert, 4 events" rather than nothing

Change D4 back to `"threshold": 2` before continuing.

## Scorecard

| Coverage run | Detected |
|---|---|
| Initial rules | 8 of 12 (66%) |
| + D9 and D10 enabled | 10 of 12 (83%) |
| D4 threshold 1 (experiment) | 10 of 12, different gap |

Next: [Blind Spots](09-blind-spots.md)
