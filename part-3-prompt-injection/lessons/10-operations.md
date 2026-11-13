# Lesson 10: Operating the Defenses

A defense you cannot see working is a defense you cannot trust. This lesson covers how to watch the guards, tune them, and understand their limits.

---

## Security events

Every time a guard acts, the API writes one line of JSON to its log:

```bash
docker compose logs ingestion-api | grep security_event | tail -5
```

```
WARNING:security:{"security_event": "input_blocked", "request_id": "...", "score": 3, "reasons": ["override-instructions"]}
WARNING:security:{"security_event": "output_blocked", "request_id": "...", "reasons": ["canary-leak"]}
WARNING:security:{"security_event": "document_blocked", "request_id": "...", "title": "Reporting Phishing Emails", "score": 8, "reasons": [...]}
```

| Event | Meaning |
|---|---|
| `input_blocked` | A chat message was rejected |
| `document_blocked` | A document was rejected at ingest |
| `output_blocked` | An answer was withheld (canary leak) |
| `output_filtered` | Images or links were removed from an answer |

One JSON object per line is easy for log tools to search and count. Part 5 builds alerts and dashboards on these events.

**What is not logged:** the user's full message, or the full answer. Logs are read by many people and kept for a long time. Logging every chat would turn your logs into a second copy of every user's private questions.

---

## Counters

```bash
EDGE_API_KEY=$(grep -E '^EDGE_API_KEY=' .env | cut -d= -f2-)
curl -s -H "X-API-Key: $EDGE_API_KEY" http://localhost:8088/health | python3 -m json.tool
```

```
    "blocked_inputs": 3,
    "blocked_documents": 3,
    "blocked_outputs": 1,
    "filtered_outputs": 0
```

A sudden jump in `blocked_inputs` from one client is a sign someone is probing your system.

---

## Tuning

| Setting in `.env` | Default | Effect |
|---|---|---|
| `GUARD_INPUT_THRESHOLD` | 3 | Lower = blocks more attacks **and** more real users |
| `GUARD_DOC_THRESHOLD` | 2 | Used for ingest screening and sentence sanitization |
| `ALLOWED_LINK_DOMAINS` | `example.org` | Comma-separated domains whose links survive the output filter |

After changing any of these, run `bin/guard.sh all on` to restart the API, then **re-run the whole attack suite and the false-positive checks**.

---

## Why results can vary

You may have noticed `obfuscated-override` flip between `resisted` and `ATTACK SUCCEEDED` across runs. Temperature is 0, so why?

The hardened prompt uses a **random boundary tag** every request (`<DATA-5C1E09A2>`, then `<DATA-91B04E7F>`, ...). A different tag is a slightly different prompt, and a slightly different prompt can tip a borderline decision.

That attack is the one **no deterministic layer covers**:
- It is in French, so the English patterns miss it
- Its goal (`PWNED`) is not a secret or a link, so the output filter ignores it

Whether it works comes down to the model's judgment on that particular prompt. **A defense that depends on the model is a coin flip; a defense that does not is a wall.** Where possible, prefer walls.

---

## Turn the debug endpoints off

`/debug/prompt` shows your full prompt design and `/debug/scan` lists flagged documents. Both are useful to defenders and to attackers. In any real deployment:

```bash
sed -i.bak 's/^ENABLE_DEBUG_ENDPOINTS=.*/ENABLE_DEBUG_ENDPOINTS=false/' .env && rm .env.bak
bin/guard.sh all on
```

Turn them back on (`true`) if you want to keep experimenting.

---

## Stop and reset

```bash
docker compose down        # stop, keep data
docker compose down -v     # delete the database (models are kept for Parts 4 and 5)
```

Next: [Conclusion](11-conclusion.md)
