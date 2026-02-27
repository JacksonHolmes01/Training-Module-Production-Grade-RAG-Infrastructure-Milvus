# Prompt 05 — Dependency and Supply Chain Risk Review

## Step 2: Retrieve security references

```bash
EDGE_API_KEY=$(grep -E '^EDGE_API_KEY=' .env | cut -d= -f2-)

curl -sS -X POST http://localhost:8088/memory/query \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $EDGE_API_KEY" \
  -d '{
    "query": "software supply chain security dependency pinning sbom vulnerability scanning container image tags",
    "top_k": 10
  }' > /tmp/supply_chain_refs.json
```

## Step 3: Extract the plain text

```bash
python3 -c "
import json
data = json.load(open('/tmp/supply_chain_refs.json'))
for r in data['results']:
    print(r['text'])
    print('---')
"
```

## Step 4: Paste this prompt into your IDE chat

Open `ingestion-api/requirements.txt`, then open the AI chat panel and paste:

```
I am going to give you a set of security reference chunks retrieved from a vector database
of security standards. After the references, I will share a file for you to review.

Your job:
- Identify security issues in the file
- For each issue, cite which reference it comes from
- Propose a minimal fix appropriate for a student lab environment
- If a finding is not supported by the references provided, say so explicitly — do not invent citations

Focus especially on: unpinned dependencies, packages with known CVEs, abandoned or transferred
packages, and Docker images using the `latest` tag instead of a specific version.

References:
[paste your retrieved chunks here]

File to review:
[paste the contents of requirements.txt here, or use @requirements.txt in Cursor]
```

You can repeat this for `docker-compose.yml` to review image tags.

## Step 5: Validate

```bash
docker compose up -d --build
curl -sS -H "X-API-Key: $EDGE_API_KEY" http://localhost:8088/health | python3 -m json.tool
```
