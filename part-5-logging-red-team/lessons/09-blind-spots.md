# Lesson 9: Blind Spots

Two steps remain undetected. One could be caught with better rules. The other cannot be caught with the logs this lab collects at all. Knowing which is which is the point.

---

## R01: Low and slow

A single injection attempt, then silence. Real attackers do this deliberately: one probe per hour, or one per day, from different addresses, so no threshold is ever crossed.

The logs **did** record it:

```bash
python3 bin/logs.py --since 30m --kind input_blocked
```

R01's attempt is there: a single line, a few seconds before the burst of three from R05. (Earlier lines may be your own practice from Lesson 3.) It is in the logs; it just never added up to an alert.

### How defenders catch low-and-slow activity

| Technique | Idea |
|---|---|
| **Longer windows** | Count over 24 hours or 7 days, not 5 minutes |
| **Different grouping** | Group by API key or user account, not address: attackers change addresses more easily than stolen credentials |
| **Daily reports** | A human reviews a summary of every blocked event once a day, no threshold at all |
| **Baselines** | Alert when a key's behavior differs from its own history, even at low volume |

> **Try it:** add a rule D11 to `detections/rules.json` that fires on **1** `input_blocked` within **86400** seconds (one day), with severity `low`. Re-score. Does R01 show up now? What happens to R05, and why?

---

## R12: The attacker inside the container

Look at what R12 actually did:

```
R12  Attacker inside a container    commands inside rag-api -> ['ok', 'blocked', 'blocked', 'ok']
```

It ran `id`, tried to modify the app's code, tried to install packages, and read the process environment. Part 4's hardening blocked the dangerous two. But search the logs:

```bash
python3 bin/logs.py --since 30m --summary
```

There is **nothing** from R12. No request went through NGINX, so the edge did not see it. The API did not handle a request, so the API did not log it. A command run inside a container is invisible to application logs.

### What can see it

| Tool type | Examples | Sees |
|---|---|---|
| **Runtime security** | Falco, Tetragon, cloud runtime protection | Every new process, file write, and network connection inside every container, as it happens |
| **Linux audit logging** | `auditd` | System calls on the host, including those made by containers |
| **Container platform logs** | Kubernetes audit logs | Who ran `exec` into which container |

A typical runtime security rule: "**alert if any process other than `uvicorn` starts inside `rag-api`.**" That one line would have caught every command R12 ran.

Installing and running these tools is beyond this lab, but the lesson stands: **each kind of log has a field of view.** Application logs see requests. They cannot see what happens beside the application.

---

## Final scorecard

| Step | Status | Why |
|---|---|---|
| R02 to R11 | Detected | Logged and covered by an enabled rule |
| R01 | Logged, not alerted | Below every threshold; needs longer windows or daily review |
| R12 | **Not logged at all** | Outside the field of view of application logs; needs runtime security |

The two misses are different kinds of problems. One is a **tuning** problem: the data is there. The other is a **visibility** problem: the data does not exist. Reports should say which is which, because the fixes are completely different.

---

## Try it: a rule for a stolen token

`bin/seclog.py` already turns Milvus's `HttpError403` answers into `db_forbidden` events, but no rule watches them. A `403` from Milvus means a **valid** user tried something its role does not allow, for example the chat's `rag_reader` trying to drop the collection. The real API never does that, so even one is suspicious.

1. Cause one: `bin/milvus.sh reader /v2/vectordb/collections/drop '{"dbName":"tenant_lab","collectionName":"docs"}'`
2. Find it: `python3 bin/logs.py --since 5m --kind db_forbidden`
3. Add rule `D11` to `detections/rules.json` (copy D10, match `{"kind": "db_forbidden"}`, threshold `1`)
4. Check it fires: `python3 bin/detect.py --since 5m`

Next: [Writing the Report](10-report.md)
