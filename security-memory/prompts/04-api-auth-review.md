# Prompt 04 — FastAPI Ingestion API Security Review

## Step 2: Retrieve security references

```bash
EDGE_API_KEY=$(grep -E '^EDGE_API_KEY=' .env | cut -d= -f2-)

curl -sS -X POST http://localhost:8088/memory/query \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $EDGE_API_KEY" \
  -d '{
    "query": "api key authentication input validation rate limiting logging secrets fastapi security",
    "top_k": 10
  }' > /tmp/api_security_refs.json
```

## Step 3: Extract the plain text

```bash
python3 -c "
import json
data = json.load(open('/tmp/api_security_refs.json'))
for r in data['results']:
    print(r['text'])
    print('---')
"
```

## Step 4: Paste this prompt into your IDE chat

Open `ingestion-api/app/main.py`, then open the AI chat panel and paste:

```
I am going to give you a set of security reference chunks retrieved from a vector database
of security standards. After the references, I will share a file for you to review.

Your job:
- Identify security issues in the file
- For each issue, cite which reference it comes from
- Propose a minimal fix that keeps the lab functional
- If a finding is not supported by the references provided, say so explicitly — do not invent citations

Focus especially on: input validation gaps (size and type limits), authentication bypass risks,
secrets appearing in logs, and any endpoints missing auth checks.

References:
[paste your retrieved chunks here]

File to review:
[paste the contents of ingestion-api/app/main.py here, or use @main.py in Cursor]
```

## Step 5: Implement and validate

```bash
docker compose up -d --build ingestion-api
curl -sS -H "X-API-Key: $EDGE_API_KEY" http://localhost:8088/health | python3 -m json.tool
```
