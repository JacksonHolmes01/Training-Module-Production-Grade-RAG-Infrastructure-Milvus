# Prompt 03 — NGINX Reverse Proxy Security Review

## Step 2: Retrieve security references

```bash
EDGE_API_KEY=$(grep -E '^EDGE_API_KEY=' .env | cut -d= -f2-)

curl -sS -X POST http://localhost:8088/memory/query \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $EDGE_API_KEY" \
  -d '{
    "query": "nginx reverse proxy security auth enforcement timeouts headers rate limiting",
    "top_k": 10
  }' > /tmp/nginx_security_refs.json
```

## Step 3: Extract the plain text

```bash
python3 -c "
import json
data = json.load(open('/tmp/nginx_security_refs.json'))
for r in data['results']:
    print(r['text'])
    print('---')
"
```

## Step 4: Paste this prompt into your IDE chat

Open `nginx/templates/default.conf.template`, then open the AI chat panel and paste:

```
I am going to give you a set of security reference chunks retrieved from a vector database
of security standards. After the references, I will share a file for you to review.

Your job:
- Identify security issues in the file
- For each issue, cite which reference it comes from
- Propose a minimal fix that keeps the lab functional
- If a finding is not supported by the references provided, say so explicitly — do not invent citations

Focus especially on: auth enforcement for protected routes, request timeouts, headers that
leak sensitive information, and rate limiting.

References:
[paste your retrieved chunks here]

File to review:
[paste the contents of nginx/templates/default.conf.template here, or use @default.conf.template in Cursor]
```

## Step 5: Implement and validate

```bash
docker compose restart nginx
curl -sS http://localhost:8088/proxy-health
curl -sS -H "X-API-Key: $EDGE_API_KEY" http://localhost:8088/health | python3 -m json.tool
```
