# Lesson 7: Running the Campaign

Red team hat on.

---

## Run it

```bash
python3 bin/redteam.py
```

This takes 2 to 3 minutes.

### What you will see

```
Red-team campaign against YOUR lab. About 2 to 3 minutes.

R01  Low-and-slow injection         one injection attempt -> HTTP 400
R02  Reconnaissance                 8 requests with no key -> [401]
R03  API key brute force            15 random keys -> [403]
R04  Request flood                  60 simultaneous requests -> 21 ok, 39 rate-limited
R05  Prompt injection burst         3 injection messages -> [400, 400, 400]
R06  Canary leak                    leak hidden in a normal question -> HTTP 200 (answer withheld if the canary leaked)
R07  Data poisoning                 3 poisoned documents -> [422, 422, 422]
R08  Oversized payloads             2 requests over 1 MB -> [413, 413]
R09  Schema probing                 3 malformed documents -> [422, 422, 422]
R10  Endpoint discovery             8 guessed paths with the real key -> [404]
R11  Database credential guessing   5 root password guesses against Milvus from inside the network -> ['401']
R12  Attacker inside a container    commands inside rag-api -> ['ok', 'blocked', 'blocked', 'ok']

Campaign finished. Record saved to redteam/runs/run-20261112-183112.json
```

Read the attacker's view first. **Every attack failed.** The defenses from Lab 1 and Parts 3 and 4 held: keys were rejected, injections blocked, poison refused, payloads capped, the guessed root passwords refused (including Milvus's default, `Milvus`), and inside the container only harmless commands (`id`, reading its own environment) worked.

But "the attack failed" is not the same as "we noticed." Blue team hat on.

---

## Score the blue team

```bash
python3 bin/coverage.py
```

### What you will see

```
Run: run-20261112-183112.json   Rules enabled: D1, D2, D3, D4, D5, D6, D7, D8

STEP  ATTACK                         DETECTED  ALERTS
------------------------------------------------------------------------------
R01   Low-and-slow injection         no        -
R02   Reconnaissance                 YES       D2 Unauthenticated reconnaissance
R03   API key brute force            YES       D1 API key brute force
R04   Request flood                  YES       D3 Request flood
R05   Prompt injection burst         YES       D4 Prompt injection probing
R06   Canary leak                    YES       D5 Secret leak blocked (canary)
R07   Data poisoning                 YES       D6 Poisoned document rejected
R08   Oversized payloads             YES       D7 Oversized requests
R09   Schema probing                 YES       D8 Schema probing
R10   Endpoint discovery             no        -
R11   Database credential guessing   no        -
R12   Attacker inside a container    no        -
------------------------------------------------------------------------------
Detection coverage: 8 of 12 attack steps (66%)
```

Compare with your prediction from Lesson 6.

### How "detected" is decided

`bin/coverage.py` re-reads the logs from the start of the run (and ignores anything earlier, like your practice traffic from Lessons 3 to 5), applies the **currently enabled** rules, and checks each step's time window. A step counts as detected only if a rule **meant for that attack** fired while it was running. An unrelated alert that happened to fire at the same moment does not count. That is luck, not coverage.

### If your number is one lower

R06 is only detected when the model actually **leaks** the secret and the output filter blocks it. Small models are not consistent: on some runs `llama3.2:1b` refuses instead, nothing is blocked, and R06 shows `no`. Your coverage is then 7 of 12 (and 9 of 12 after Lesson 8). That is not a detection failure. The attack failed before there was anything to catch. Run the campaign again and R06 usually comes back.

---

## Look at the alerts the blue team received

```bash
python3 bin/detect.py --since 10m
```

Eight alerts, one per detected step, in the order the attacks happened. A defender watching this list in real time would see the attack unfold: reconnaissance, then key guessing, then a flood, then injection attempts, then poisoning. That **sequence** tells a story no single alert does.

## Scorecard

| Coverage run | Detected |
|---|---|
| Initial rules | 8 of 12 (66%) |

Next: [Closing the Gaps](08-closing-gaps.md)
