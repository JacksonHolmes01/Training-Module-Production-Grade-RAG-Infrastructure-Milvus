# Lesson 4: Searching the Logs

Logs nobody can search might as well not exist. `bin/logs.py` reads the lab's logs from Docker, turns each line into an **event**, and lets you filter them.

---

## Make some activity first

Generate a little normal and abnormal traffic:

```bash
EDGE_API_KEY=$(grep -E '^EDGE_API_KEY=' .env | cut -d= -f2-)
bin/smoke_test.sh > /dev/null
for i in 1 2 3; do curl -s -o /dev/null -H "X-API-Key: wrong-key-$i" http://localhost:8088/health; done
curl -s -o /dev/null http://localhost:8088/admin
curl -s -o /dev/null -X POST http://localhost:8088/ingest -H "X-API-Key: $EDGE_API_KEY" \
  -H "Content-Type: application/json" -d '{"text": "hello", "tenant": "someone-else"}'
```

---

## The big picture

```bash
python3 bin/logs.py --summary
```

### What you will see (your counts will differ)

```
42 events since 15m

By kind:
  edge_request         28
  api_request          9
  validation_error     2
  input_blocked        2
  ...

Edge requests by status:
  200  14
  401  2
  403  4
  422  1
  ...
```

A summary is the first thing to look at: a sudden jump in `403` or `input_blocked` is visible at a glance.

---

## Answer specific questions

### "Who used a wrong API key?"

```bash
python3 bin/logs.py --kind edge_request --status 403
```

```
18:42:01  edge_request      172.18.0.1      9b2e01aa  GET /health -> 403
18:42:01  edge_request      172.18.0.1      51cd7f30  GET /health -> 403
18:42:01  edge_request      172.18.0.1      e0a4c9d1  GET /health -> 403
```

### "Did anyone try to set a field they should not?"

```bash
python3 bin/logs.py --kind validation_error
```

```
18:42:02  validation_error  172.18.0.1      70ce12f4  tenant
```

The log names the field (`tenant`) but not the value that was sent.

### "Have any prompt injections been blocked?"

```bash
python3 bin/logs.py --kind input_blocked
```

### "What happened in the last hour?"

```bash
python3 bin/logs.py --since 1h --summary
```

---

## Event kinds

| Kind | Comes from | Means |
|---|---|---|
| `edge_request` | NGINX | A request reached the edge |
| `api_request` | API | The API handled a request |
| `input_blocked` | API | A chat message was rejected by the injection screen |
| `output_blocked` | API | An answer was withheld because it leaked the canary |
| `output_filtered` | API | Links or images were removed from an answer |
| `document_blocked` | API | A document was rejected at ingest |
| `validation_error` | API | A request had missing, wrong, or forbidden fields |
| `db_auth_failure` | Milvus | A request to Milvus with no password or a wrong one |
| `db_forbidden` | Milvus | A valid Milvus user tried something its role does not allow |

How it works: `bin/seclog.py` runs `docker compose logs --timestamps` and parses each line. Real systems ship logs to a central store (Elasticsearch, Loki, Splunk, a cloud logging service) instead, so they survive containers being deleted and can be searched across many servers. The ideas are identical.

Next: [Detection Rules](05-detection-rules.md)
