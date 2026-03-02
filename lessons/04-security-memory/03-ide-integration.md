# Lesson 4.3 — Using Your Security Memory in an IDE (VS Code / Cursor)

> **What you're building:** not another chatbot, but a real workflow where your IDE assistant retrieves the right security references and uses them to produce grounded, citeable fixes to actual lab files.

> **Upgraded Capabilities.** Up until now, the AI in this lab could answer cybersecurity questions, explain frameworks, and help you understand concepts. With the memory and API you built in Lessons 4.1 and 4.2, it can now do something more powerful: you can point it at real files in your project — a Dockerfile, a docker-compose.yml, an NGINX config — and it will review them against actual security standards and suggest specific, sourced improvements.

This lesson is where you put that capability to use. It works in both VS Code and Cursor, even if you have not configured any special integrations.

---

## Learning Outcomes

By the end of this lesson, you will:

- Understand what "grounded" security review means and why it matters
- Know how to open and use the AI chat panels in VS Code and Cursor
- Use `/memory/query` to retrieve relevant security guidance for a specific file
- Feed that guidance into your IDE assistant using the included prompt library
- Know how to ask follow-up questions and get the most out of the AI
- Apply the workflow to review and propose fixes to real lab files
- Know how to keep your memory up to date as standards evolve
- Understand what "major integration" means in the context of this project

## Important Note Regarding Lesson 4.2

You may be wondering where the chatbot you built in this lab fits in. In this lesson, the AI doing the review is Copilot or Cursor through your chosen IDE, not your chatbot. However, your contribution is the retrieval layer — the `/memory/query` endpoint you built in Lesson 4.2 is what fetches the security chunks. Without that, you would just be asking Copilot generic security questions with no grounded references.

Think of it as a division of labour: your API finds the right standards, and the IDE AI uses them to review the code.

If you completed the optional section in Lesson 4.2, your own chatbot can take over the entire workflow. Instead of manually running a curl command and pasting chunks into Copilot, you would open your chatbot's chat interface at `http://localhost:7860` and ask it to review the file directly. Behind the scenes, your `/chat` endpoint would automatically detect that the question is security-related, call `/memory/query` to fetch the relevant chunks, inject them into the prompt, and send everything to Ollama to generate a grounded response.

The end result is the same — a security review backed by real standards — but your chatbot is handling every step rather than you doing it manually. This is the more production-ready version of the workflow.

---

## 1) What Does "Grounded" Mean and Why Does It Matter?

When you ask an AI assistant "is this Dockerfile secure?", it will give you an answer, but that answer is based entirely on its training data. It might be outdated, vague, or confidently wrong. There is no way to know which specific standard it is drawing from, and you cannot audit it.

**Grounded** means the AI's answer is tied to a specific, retrievable source. Instead of "the AI said so," you get "the AI said so, and here is the CIS Docker Benchmark section it pulled from."

This matters in security work because:

- Security standards are versioned and change over time — you want to know which version you are working from
- In a real organization, "we followed CIS Benchmark v1.6 section 4.1" is auditable; "the AI said it was fine" is not
- It trains you to think in terms of controls and frameworks, not just instinct

Everything you built in Lessons 4.1 and 4.2 was in service of making this possible.

---

## 2) Opening the AI Chat Panel in Your IDE

### In VS Code

VS Code's AI features are powered by **GitHub Copilot**. If your course account has Copilot enabled:

1. Open VS Code and make sure you are signed into your GitHub account (bottom left corner)
2. Open the chat panel in one of these ways:
   - Press `Ctrl+Alt+I` (Windows/Linux) or `Cmd+Option+I` (Mac)
   - Click the chat bubble icon in the left sidebar
   - Go to **View > Chat** in the top menu
3. The chat panel will appear on the right side of your screen

You can also open **inline chat** directly inside a file by pressing `Ctrl+I` (Windows/Linux) or `Cmd+I` (Mac). This is useful for asking about a specific line or block of code without switching to the side panel.

One useful VS Code feature: type `@workspace` at the start of a message to tell Copilot to consider all the files in your project. For example: `@workspace review docker-compose.yml for security issues`.

### In Cursor

1. Open Cursor and make sure your project folder is open (`File > Open Folder`)
2. Open the AI chat panel:
   - Press `Ctrl+L` (Windows/Linux) or `Cmd+L` (Mac) to open the chat sidebar
   - Press `Ctrl+K` (Windows/Linux) or `Cmd+K` (Mac) to open inline chat
3. Cursor has an **Add to context** feature — you can type `@` followed by a filename to reference it directly. For example, typing `@docker-compose.yml` attaches that file's contents so the AI can read it. This is more reliable than copy-pasting large files.

### Tips for getting good responses from either IDE

**Be specific about what you want.** "Review this file" is vague. "Review this file for secrets in environment variables, exposed ports, and missing resource limits" gives the AI a clear checklist.

**Paste context before asking.** If you have retrieved security chunks from memory, paste them into the chat before your question. Tell the AI explicitly: "Use only the references below when identifying issues." This keeps answers grounded.

**Ask follow-up questions.** If a finding is unclear, ask "why does that matter?" or "can you show me what the fix would look like as a diff?" If you disagree with something, push back: "are you sure that is required by CIS, or is that your own inference?"

**Ask it to explain its reasoning.** If the AI proposes a fix, ask "which specific control does this address?" This forces it to connect the fix back to a standard.

**Use the file context features.** In Cursor, use `@filename`. In VS Code, use `@workspace`. These prevent the AI from making assumptions about code it has not actually read.

---

## 3) The Core Workflow

This is the workflow you will use throughout this lesson. Retrieve context from your memory API, then use it in your IDE chat.

### Step 1 — Retrieve Security Context from Memory

Open the integrated terminal in your IDE. In both VS Code and Cursor, press `Ctrl+`` ` (backtick) or go to **Terminal > New Terminal**.

Make sure you are in the repo root folder (the one that contains `docker-compose.yml` and `.env`). Confirm with:

```bash
pwd
```

If you are not there, navigate:

```bash
cd /path/to/your/repo
```

First, load your API key:

```bash
EDGE_API_KEY=$(grep -E '^EDGE_API_KEY=' .env | cut -d= -f2-)
```

Then query the memory API for the topic you want to review. Here is an example for reviewing a `docker-compose.yml`:

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

Breaking this down:

- `query` — be specific. Mention the kinds of issues you're concerned about. The more specific the query, the more relevant the chunks.
- `tags` — narrows search to specific frameworks. Leave out entirely to search everything.
- `top_k: 8` — return 8 most relevant chunks. For thorough review, 6 to 10 is a good range.
- `> /tmp/security_context.json` — saves results to a file so you don't have to copy-paste output.

**Note on scores:** Milvus returns cosine similarity scores directly. A score of 0.90 means very strong semantic match. A score of 0.60 means weak match. If your scores are consistently low, your query doesn't match the corpus well — try rephrasing or removing the tag filter.

To preview what came back:

```bash
cat /tmp/security_context.json | python -m json.tool
```

Look at the `text` fields in each result — these are the actual security reference chunks your AI will use. If they look irrelevant, adjust your query and run it again.

To extract just the chunk text:

```bash
python3 -c "
import json
data = json.load(open('/tmp/security_context.json'))
for r in data['results']:
    print(r['text'])
    print('---')
"
```

### Step 2 — Use the Context in Your IDE Chat

Open the file you want to review in your IDE. Then open the AI chat panel.

In the chat text box, paste this prompt:

```
I am going to give you a set of security reference chunks retrieved from a vector database of security standards. After the references, I will share a file for you to review.

Your job:
- Identify security issues in the file
- For each issue, cite which reference it comes from
- Propose a minimal fix that keeps the lab functional
- If a finding is not supported by the references provided, say so explicitly — do not invent citations

References:
[paste your retrieved chunks here]

File to review:
[paste the contents of the file here]
```

To get the chunk text, run the extraction command above and copy the output where it says `[paste your retrieved chunks here]`. Then open your target file, select all with `Ctrl+A` / `Cmd+A`, copy it, and paste it where it says `[paste the contents of the file here]`.

**Why "say so explicitly — do not invent citations"?** Without this instruction the AI will happily cite frameworks it was not given, or make up section numbers. Explicitly telling it to flag unsupported claims forces honesty and helps you separate grounded findings from general suggestions.

Once the AI responds, use the follow-up techniques from Section 2 to dig in — ask why a finding matters, ask for the fix as a diff, or challenge anything you are unsure about.

---

## 4) The Prompt Library

Rather than constructing prompts from scratch every time, this repo includes ready-made prompt templates for the most common review scenarios. They live at:

```
security-memory/prompts/
```

Each template is a `.md` file you open in VS Code or Cursor, read the instructions at the top, then copy the prompt body into your IDE chat along with your retrieved memory chunks.

### What each template covers

**`01-dockerfile-review.md`**
Use this when reviewing a `Dockerfile`. The template instructs the AI to check for insecure base images, processes running as root, secrets hardcoded in `ENV` or `ARG` instructions, missing `HEALTHCHECK` directives, and unnecessary packages or capabilities. Findings are mapped to CIS Docker Benchmark and OWASP controls.

To use it: run a memory query with `tags: ["docker", "cis"]`, open `01-dockerfile-review.md`, copy the prompt body, paste into your IDE chat, then follow with your retrieved chunks and `Dockerfile` contents.

**`02-compose-review.md`**
Use this when reviewing `docker-compose.yml`. The template checks for services exposing ports that should stay internal, containers running in `privileged` mode, missing resource limits (`mem_limit`), insecure volume mounts, and secrets passed as plain environment variables.

To use it: run a memory query with `tags: ["docker", "cis"]`, open `02-compose-review.md`, copy the prompt, paste with retrieved chunks and `docker-compose.yml` contents.

**`03-nginx-review.md`**
Use this when reviewing an NGINX configuration file. The template checks for missing HTTP security headers, weak TLS configuration, missing rate limiting on public endpoints, and overly permissive CORS settings.

To use it: run a memory query with `tags: ["owasp"]` or without tags, open `03-nginx-review.md`, paste with retrieved chunks and NGINX config.

**`04-api-auth-review.md`**
Use this when reviewing API authentication code or configuration. The template checks against OWASP API Security Top 10 — broken object-level authorization, broken authentication, excessive data exposure, missing rate limiting, and missing function-level authorization.

To use it: run a memory query with `tags: ["owasp"]`, open `04-api-auth-review.md`, paste relevant auth code alongside retrieved chunks.

**`05-dependency-risk-review.md`**
Use this when reviewing `requirements.txt` or similar dependency files. The template flags packages with known CVEs, packages pinned to vulnerable versions, unpinned packages, and abandoned packages.

To use it: run a memory query without tags or with `tags: ["owasp"]`, open `05-dependency-risk-review.md`, paste your dependency file alongside retrieved chunks.

### Step-by-step for any template

1. Decide which file you want to review and open it in your IDE
2. Run the appropriate memory query in your terminal (example queries are at the top of each template)
3. Preview results with `cat /tmp/security_context.json | python -m json.tool` to confirm the chunks look relevant
4. Open the prompt template from `security-memory/prompts/` in your IDE
5. Read the instructions at the top, then copy the prompt body
6. Open your IDE chat panel, paste the prompt, then paste or attach your memory chunks and the file being reviewed
7. Read through the AI's findings carefully — do not implement everything without thinking. Ask follow-up questions for anything unclear
8. Implement fixes one at a time
9. After each fix, re-run the lab with `docker compose up -d` and confirm it still works

**Step 9 is not optional.** Security hardening that breaks the lab is not a success. Fixing one issue at a time lets you pinpoint which change caused a problem if something stops working.

### Getting more out of the AI with follow-up questions

After the AI gives its initial review, these follow-ups tend to be useful:

- "Which CIS Benchmark section specifically says that?" — forces the AI to be precise, or to admit it doesn't have a citation
- "Show me that fix as a unified diff" — gives you exact lines to change, easier to implement correctly
- "If I make that change, will anything else in the lab break?" — prompts the AI to think through dependencies
- "Are there any fixes you recommended that are nice-to-have versus actually required by the standard?" — helps you prioritize
- "Rank these findings by severity" — useful when there are many findings

---

## 5) What "Major Integration" Means for This Project

You may have heard this project described as a "major integration." Here is what that actually means in practice.

A major integration in this context means four things working together:

**A working vector database memory:** Milvus is running (with its etcd and MinIO dependencies), the `ExpandedVSCodeMemory` collection exists with a typed schema and HNSW cosine index, and it contains real security reference documents. This is what you built in Lesson 4.1.

**A stable, queryable API tool:** the `/memory/query` endpoint is live, authenticated, and returns structured results with cosine similarity scores that can be fed directly into prompts. This is what you built in Lesson 4.2.

**Instructions and prompts that make it useful:** without a clear workflow and prompt library, the memory is just a database nobody uses. The prompts and workflow in this lesson turn it into a practical security tool.

**Optionally, IDE or tool integration:** the most advanced step is configuring your IDE to call the memory API automatically. This is covered in Section 6 and is a nice-to-have, not a requirement.

You are not being asked to invent new AI or build something from scratch. You are being asked to connect the pieces you have already built into something genuinely useful for security work, and to practice using it on real lab files.

---

## 6) Optional: MCP / Automatic Tool Integration (Advanced)

Right now the workflow requires you to manually run a curl command and paste the results into your IDE. That works, but it adds friction. The next level is configuring your IDE to call `/memory/query` automatically whenever you ask a security question — no manual retrieval step needed.

This is done through **MCP (Model Context Protocol)**, a standard that Cursor supports for connecting external tools to the AI assistant. When configured, the IDE calls your memory API as a tool in the background, retrieves the relevant chunks, and injects them into the prompt without any manual steps.

The endpoints you already built are exactly the right shape for this. If you want to explore this, the repo includes optional configuration examples under:

```
security-memory/mcp/
```

This is not required to complete the lesson. The manual workflow in Section 3 achieves the same learning goal — MCP just removes the friction once you are comfortable with the concepts.

---

## 7) Keeping Your Memory Up to Date

Security standards evolve. CIS Benchmarks get new versions, OWASP updates its Top 10, MITRE ATT&CK adds new techniques. If you never update your memory, it will gradually go stale.

### How to add or update documents

1. Add or replace `.md` or `.txt` files under `security-memory/data/` in the appropriate subfolder
2. Re-run ingestion:

```bash
docker exec -i ingestion-api python -m app.security_memory.ingest
```

**Important Milvus-specific note:** Unlike Qdrant which supports content-hash upserts, Milvus auto-assigns INT64 IDs and has no built-in deduplication by content. Re-running ingestion on a file that already exists will create duplicate chunks. To avoid duplicates when updating existing documents, drop and recreate the collection first:

```bash
docker exec -i ingestion-api python - <<'PY'
from pymilvus import connections, utility, Collection
import os
connections.connect(
    host=os.getenv("MILVUS_HOST", "milvus"),
    port=int(os.getenv("MILVUS_PORT", "19530")),
    timeout=10,
)
name = os.getenv("SECURITY_COLLECTION", "ExpandedVSCodeMemory")
if utility.has_collection(name):
    Collection(name).drop()
    print(f"Dropped: {name}")
PY

docker exec -i ingestion-api python -m app.security_memory.ingest
```

### When do you need to recreate the collection?

**Always** recreate if you change:

- The embedding model (different models produce incompatible vector spaces)
- The embedding dimension (`SECURITY_EMBED_DIM`) — Milvus will reject vectors of the wrong size
- The distance metric — cosine scores become meaningless if switched to L2
- The schema — Milvus does not support adding fields to an existing collection

If you do need a new collection, update `SECURITY_COLLECTION` in your `.env` file to a versioned name (e.g., `ExpandedVSCodeMemory_v2`) so the old collection stays intact as a fallback.

---

## 8) What You Are Actually Learning Here

When you run a memory query, pick a prompt template, and ask your IDE to review a `docker-compose.yml`, you are practicing things that matter in real security work.

**Retrieval grounding:** you are learning to always anchor security claims to a specific source. This is how professional security assessments work — every finding cites a control, a benchmark, or a standard.

**Controls frameworks:** NIST, CIS, OWASP, and MITRE are not just acronyms. They are the shared vocabulary that security teams use to communicate, prioritize, and audit. Working with them in a hands-on context is much more effective than reading about them in a textbook.

**Secure configuration review:** reviewing a `Dockerfile` or `nginx.conf` against a benchmark is a real skill used in penetration testing, cloud security audits, and DevSecOps pipelines. You are practicing it in a low-stakes environment where you can make mistakes and see the results.

**Change management:** the requirement to re-run the lab after every fix is not bureaucracy. It is teaching you that security changes have to be validated. Hardening that breaks functionality is not hardening — it is an outage.

**Distributed infrastructure literacy:** unlike Qdrant and Weaviate which run as single containers, Milvus requires etcd and MinIO to function. You have been working with a three-service cluster throughout this lesson set. Understanding why each layer exists — metadata, object storage, compute — is the same pattern used in production-grade vector search systems at scale.

---

## Checkpoint

You are done when you can:

- Open the AI chat panel in VS Code or Cursor
- Retrieve relevant security standards via `/memory/query` for a specific file
- Use the prompt library to produce a grounded security review in your IDE
- Implement at least one fix and confirm the lab still runs correctly after the change
