# Lesson 5: Detection Rules

Searching logs works when you already know something happened. **Detection rules** watch the logs for you and raise an **alert** when something looks like an attack.

---

## The rules

```bash
python3 bin/detect.py --rules
```

```
ID    ON   SEVERITY  RULE                             FIRES WHEN
D1    yes  high      API key brute force              10+ edge_request status 403 from one ip in 60s
D2    yes  medium    Unauthenticated reconnaissance   5+ edge_request status 401 from one ip in 60s
D3    yes  medium    Request flood                    10+ edge_request status 429 from one ip in 60s
D4    yes  high      Prompt injection probing         2+ input_blocked from one ip in 300s
D5    yes  critical  Secret leak blocked (canary)     1+ output_blocked from one ip in 60s
D6    yes  high      Poisoned document rejected       1+ document_blocked from one ip in 60s
D7    yes  low       Oversized requests               2+ edge_request status 413 from one ip in 300s
D8    yes  medium    Schema probing                   3+ validation_error from one ip in 300s
D9    no   medium    Endpoint discovery               5+ edge_request status 404 from one ip in 60s
D10   no   critical  Milvus login guessing            3+ db_auth_failure from one ip in 300s
```

Two rules start **disabled**. You will find out why that matters in Lesson 8.

---

## Anatomy of a rule

Open `detections/rules.json` and look at D1:

```json
{
  "id": "D1",
  "name": "API key brute force",
  "enabled": true,
  "severity": "high",
  "match": {
    "kind": "edge_request",
    "status": 403
  },
  "group_by": "ip",
  "threshold": 10,
  "window_s": 60,
  "why": "Many wrong API keys from one address in a minute: someone is guessing keys.",
  "response": "Block the address at the edge, confirm the real key has not leaked, consider rotating it."
}
```

| Field | Meaning |
|---|---|
| `match` | Which events count. Here: edge requests that got `403` |
| `group_by` | Count separately for each address |
| `threshold` and `window_s` | Fire when **10** matching events arrive within **60 seconds** |
| `severity` | How urgent the alert is |
| `why` and `response` | What the alert means, and what to do about it |

Writing down **why** and **response** with every rule is not decoration. At 3 a.m., whoever receives the alert needs to know what to do without reading the code.

### Thresholds are a trade-off

| Too low | Too high |
|---|---|
| Every typo raises an alert; people learn to ignore them ("alert fatigue") | Real attacks slip under the threshold |

D5 (canary leak) fires on a **single** event, because there is no innocent explanation for the model writing the secret. D1 waits for **10**, because anyone can mistype a key once.

### One attack, one alert

After a rule fires for an address, it stays quiet for that address for one window. A brute force of 1,000 attempts produces one alert, not 100. Remember this; it matters in Lesson 8.

---

## Trigger a rule yourself

Send 12 wrong keys:

```bash
for i in $(seq 1 12); do curl -s -o /dev/null -H "X-API-Key: guess-$i" http://localhost:8088/health; done
python3 bin/detect.py --since 2m --explain
```

### What you will see

```
TIME      SEVERITY  RULE  ALERT                            SOURCE          COUNT
18:45:30  HIGH      D1    API key brute force              172.18.0.1      10
          why:      Many wrong API keys from one address in a minute: someone is guessing keys.
          response: Block the address at the edge, confirm the real key has not leaked, consider rotating it.

1 alert(s) in the last 2m.
```

The alert fired at the **10th** wrong key, not the 12th. Detection happens as soon as the threshold is crossed.

---

## Where real systems differ

This lab runs detections when you ask. Production systems run them **continuously** and send alerts somewhere a person will see them: a chat channel, an on-call pager, a ticket queue. The rule logic (match, group, count, window, threshold) is the same in every major tool, from Splunk to Elastic to cloud providers' security services.

Next: [Planning the Red Team](06-planning.md)
