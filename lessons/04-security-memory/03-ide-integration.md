# Lesson 4.3 — Using Your Security Memory in an IDE (VS Code / Cursor)

> **What you're building:** not another chatbot, but a real workflow where
> your IDE assistant retrieves the right security references and uses them to
> produce grounded, citeable fixes to actual lab files.
>
> **Upgraded capabilities.** Up until now, the AI in this lab could answer
> cybersecurity questions, explain frameworks, and help you understand
> concepts. With the memory and API you built in Lessons 4.1 and 4.2, it can
> now do something more powerful: you can point it at real files in your
> project (a Dockerfile, a config, an API handler) and it will review them
> against actual security standards and suggest specific, sourced improvements.

---

## Learning outcomes

By the end of this lesson, you will:
- Understand what "grounded" security review means and why it matters.
- Know how to use the AI chat panels in VS Code and Cursor.
- Use `/memory/query` to retrieve relevant security guidance for a specific file.
- Feed that guidance into your IDE assistant using the included prompt library.
- Apply the workflow to review and propose fixes to real lab files.
- Know how to keep your memory up to date as standards evolve.

---

## Important note regarding Lesson 4.2

In this lesson, the AI doing the review is Copilot or Cursor through your
chosen IDE, not your chatbot. Your contribution is the retrieval layer — the
`/memory/query` endpoint you built in Lesson 4.2 fetches the security chunks.
Without that, you would just be asking Copilot generic security questions with
no grounded references.

Think of it as a division of labour: your API finds the right standards, and
the IDE AI uses them to review the code.

If you completed the optional section in Lesson 4.2, your own chatbot can take
over the entire workflow. Instead of manually running a curl command and
pasting chunks into Copilot, you would ask your chatbot at
`http://localhost:8088/chat` to review the file directly. Behind the scenes,
your `/chat` endpoint would automatically detect security-related questions,
call `/memory/query`, inject the chunks into the prompt, and send everything
to Ollama.

---

## 1) What does "grounded" mean and why does it matter?

When you ask an AI "is this Dockerfile secure?", it will give you an answer
based entirely on its training data. It might be outdated, vague, or
confidently wrong. There is no way to know which specific standard it draws
from, and you cannot audit it.

**Grounded** means the AI's answer is tied to a specific, retrievable source.
Instead of "the AI said so," you get "the AI said so, and here is the CIS
Docker Benchmark section it pulled from."

This matters in security work because:
- Security standards are versioned and change over time.
- "We followed CIS Benchmark v1.6 section 4.1" is auditable; "the AI said it
  was fine" is not.
- It trains you to think in terms of controls and frameworks.

---

## 2) Opening the AI chat panel in your IDE

### In VS Code

VS Code AI features are powered by GitHub Copilot.

1. Make sure you are signed into your GitHub account (bottom-left corner).
2. Open the chat panel:
   - Press `Ctrl+Alt+I` (Windows/Linux) or `Cmd+Option+I` (Mac), or
   - Click the chat bubble icon in the left sidebar.
3. To open inline chat inside a file: `Ctrl+I` / `Cmd+I`.

You can type `@workspace` at the start of a message to include all project
files as context:

```
@workspace review docker-compose.yml for security issues
```

### In Cursor

1. Open the AI chat panel: `Ctrl+L` / `Cmd+L`.
2. Open inline chat: `Ctrl+K` / `Cmd+K`.
3. Type `@filename` in the chat box to attach a file directly, e.g.
   `@docker-compose.yml`.

### Tips for better responses

- **Be specific.** "Review this file" is vague. "Review for secrets in
  environment variables, exposed ports, and missing resource limits" is clear.
- **Paste context before asking.** Paste the retrieved security chunks first,
  then ask the question.
- **Ask follow-up questions.** "Which CIS Benchmark section says that?" forces
  precision and exposes hallucinations.
- **Ask it to explain reasoning.** "Which specific control does this address?"
  connects fixes to standards.

---

## 3) The core workflow

### Step 1 — Retrieve security context

Open the integrated terminal in your IDE (`Ctrl+`` ` or Terminal > New
Terminal).

Make sure you are in the repo root:

```bash
pwd
# should end with your repo folder name
```

Load your API key:

```bash
EDGE_API_KEY=$(grep -E '^EDGE_API_KEY=' .env | cut -d= -f2-)
```

Query the memory API for the topic you want to review:

```bash
curl -sS -X POST http://localhost:8088/memory/query \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $EDGE_API_KEY" \
  -d '{
    "query": "docker compose security best practices secrets ports privileged mounts",
    "tags": ["docker", "cis"],
    "top_k": 8
  }' > /tmp/security_context.json
```

Preview the results:

```bash
cat /tmp/security_context.json | python3 -m json.tool
```

Look at the `text` fields — these are the security reference chunks your IDE
AI will use. If they look irrelevant, adjust the `query` and retry.

To extract just the text:

```bash
python3 -c "
import json, sys
data = json.load(open('/tmp/security_context.json'))
for r in data['results']:
    print(r['text'])
    print('---')
"
```

### Step 2 — Use the context in your IDE chat

Open the file you want to review in your IDE, then open the AI chat panel.

Paste this prompt template into the chat, filling in the placeholders:

```
I am going to give you a set of security reference chunks retrieved from a
vector database of security standards. After the references, I will share a
file for you to review.

Your job:
- Identify security issues in the file
- For each issue, cite which reference it comes from
- Propose a minimal fix that keeps the lab functional
- If a finding is not supported by the references provided, say so explicitly
  — do not invent citations

References:
[paste your retrieved chunks here]

File to review:
[paste the contents of the file here]
```

Paste the chunk texts from Step 1 into `[paste your retrieved chunks here]`,
and the file contents into `[paste the contents of the file here]`.

**Why "do not invent citations"?** Without this instruction, the AI will
happily cite frameworks it was not given. Explicitly flagging unsupported
claims forces honesty and helps you separate grounded findings from general
suggestions.

---

## 4) The prompt library

Ready-made prompt templates live at:

```
security-memory/prompts/
```

Each template is a `.md` file — read the instructions at the top, then copy
the prompt body into your IDE chat along with your retrieved memory chunks.

**`01-dockerfile-review.md`** — Reviews a `Dockerfile` for insecure base
images, root processes, hardcoded secrets, missing `HEALTHCHECK` directives,
and unnecessary capabilities. Findings mapped to CIS Docker Benchmark and OWASP.

**`02-compose-review.md`** — Reviews `docker-compose.yml` for services
exposing unnecessary host ports, privileged containers, missing resource
limits, insecure volume mounts, and secrets passed as plain environment
variables.

**`03-nginx-review.md`** — Reviews NGINX config for missing security headers,
weak TLS, missing rate limiting, and overly permissive CORS.

**`04-api-auth-review.md`** — Reviews API auth configuration against OWASP
API Security Top 10 (BOLA, broken authentication, excessive data exposure,
missing rate limiting, missing function-level auth).

**`05-dependency-risk-review.md`** — Reviews `requirements.txt` or
`package.json` for known CVEs, abandoned packages, and unpinned versions.

### Step-by-step for any template

1. Decide which file to review and open it in your IDE.
2. Run the appropriate memory query in your terminal (example queries are at
   the top of each template).
3. Preview results with `cat /tmp/security_context.json | python3 -m json.tool`.
4. Open the prompt template from `security-memory/prompts/` in your IDE.
5. Copy the prompt body, open your IDE chat, paste the prompt, then paste or
   attach your memory chunks and the file.
6. Read findings carefully — do not implement everything without thinking.
7. Implement fixes **one at a time**.
8. After each fix, re-run the lab with `docker compose up` and confirm it
   still works before moving to the next fix.

Step 8 is not optional. Security hardening that breaks the lab is not a
success. Fixing one issue at a time lets you pinpoint which change caused a
problem.

### Useful follow-up questions

- "Which CIS Benchmark section specifically says that?" — forces precision or
  reveals the citation is invented.
- "Show me that fix as a unified diff" — exact lines to change.
- "If I make that change, will anything else in the lab break?" — think through
  dependencies first.
- "Are there any nice-to-have recommendations vs. actually required by the
  standard?" — helps prioritise.
- "Rank these findings by severity" — useful when there are many findings.

---

## 5) What "major integration" means for this project

A major integration in this context means four things working together:

1. **A working vector database memory** — Milvus is running, the
   `ExpandedVSCodeMemory` collection exists, and it contains real security
   reference documents. Built in Lesson 4.1.

2. **A stable, queryable API tool** — the `/memory/query` endpoint is live,
   authenticated, and returns structured results. Built in Lesson 4.2.

3. **Instructions and prompts that make it useful** — without a clear workflow
   and prompt library, the memory is just a database nobody uses. This lesson.

4. **Optionally, IDE tool integration** — the most advanced step is
   configuring your IDE to call the memory API automatically. Covered in
   Section 6.

---

## 6) Optional: MCP / automatic tool integration (advanced)

Right now the workflow requires a manual curl command and copy-paste. The next
level is configuring your IDE to call `/memory/query` automatically — no
manual retrieval step needed.

This is done through **MCP (Model Context Protocol)**, which Cursor supports
for connecting external tools to the AI assistant. The endpoints you already
built are exactly the right shape: `/memory/query` is the retrieval tool and
`/chat` is the RAG generation tool.

Optional config examples are under `security-memory/mcp/`. This is not
required to complete the lesson.

---

## 7) Keeping your memory up to date

Security standards evolve. CIS Benchmarks get new versions, OWASP updates its
Top 10, MITRE ATT&CK adds new techniques.

### How to add or update documents

1. Add or replace `.md` or `.txt` files under `security-memory/data/`.
2. Re-run ingestion:

```bash
docker exec -i ingestion-api python3 -m app.security_memory.ingest
```

Ingestion uses **upserts** — existing chunks for a document are updated, new
ones are added, nothing else is touched.

### When you must recreate the collection

Recreate `ExpandedVSCodeMemory` if you change:
- **The embedding model** — different models produce incompatible vector
  spaces; mixing them causes nonsense search results.
- **The embedding dimension** — schema change; Milvus rejects mismatched
  vector lengths.
- **The distance metric** — switching from cosine to L2 makes existing scores
  meaningless.

To recreate with a versioned name for safe rollback:

```bash
docker exec ingestion-api python3 -c "
from pymilvus import connections, utility, Collection
connections.connect(host='milvus', port='19530')
if utility.has_collection('ExpandedVSCodeMemory'):
    Collection('ExpandedVSCodeMemory').drop()
print('Dropped old collection.')
"
# Update SECURITY_COLLECTION in .env to a new name if needed
docker exec -i ingestion-api python3 -m app.security_memory.ingest
```

---

## Checkpoint

You are done when:
- You can open the AI chat panel in VS Code or Cursor.
- You can retrieve relevant security standards via `/memory/query` for a
  specific file.
- You have used the prompt library to produce a grounded security review.
- You have implemented at least one fix and confirmed the lab still runs.
