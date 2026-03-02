# Security Corpus Dataset Guide — Milvus Edition

This document explains what data lives in `security-memory/data/`, how it is organized, and how to add, update, or remove documents.

---

## Directory Structure

```
security-memory/data/
├── cis/
│   ├── cis-docker-benchmark.md
│   └── cis-kubernetes-benchmark.md
├── owasp/
│   ├── owasp-api-security-top10.md
│   └── owasp-top10.md
├── nist/
│   └── nist-800-53-controls-subset.md
└── mitre/
    └── mitre-attack-techniques.md
```

The subfolder name becomes the `source` field for all documents in that folder. It is also used for automatic tag inference — a file under `cis/` gets the tag `cis` added automatically.

---

## Automatic Tag Inference

`ingest.py` infers tags by checking whether known keywords appear in the file path:

```python
TAG_KEYS = [
    "nist", "cis", "mitre", "owasp", "docker", "kubernetes",
    "linux", "cloud", "iam", "sdlc", "appsec", "containers",
]
```

A file at `security-memory/data/cis/cis-docker-benchmark.md` matches both `cis` and `docker`, so it gets `tags = ["cis", "docker"]`. These tags are stored as a JSON string in the Milvus `tags` VARCHAR field and used to filter queries.

You can add your own tag keywords by editing the `TAG_KEYS` list in `ingest.py`.

---

## Supported File Formats

The ingestor processes `.md` (Markdown) and `.txt` (plain text) files. All other file types are silently skipped.

Markdown formatting (headers, bullet points, code blocks) is preserved as text — it is not stripped. This is intentional: header text like `## CIS Control 2.1` provides useful context in retrieved chunks.

---

## Chunking Parameters

| Parameter | Default | Controlled by |
|-----------|---------|---------------|
| Chunk size | 1200 characters | `SECURITY_CHUNK_CHARS` env var |
| Overlap | 200 characters | `SECURITY_CHUNK_OVERLAP` env var |

Overlap prevents a sentence from being split across two chunks in a way that loses context. For example, if a sentence starts at character 1150 of a chunk, the next chunk will start at character 1000, ensuring that sentence appears complete in one chunk.

**Tuning guidance:**
- If your documents have short dense paragraphs (like a controls list), smaller chunks (600–800 chars) may give better retrieval precision
- If your documents have long flowing explanations, larger chunks (1500–2000 chars) preserve more context per result
- Always change `SECURITY_EMBED_DIM` too if you change the embedding model

---

## Adding New Documents

1. Create a subfolder under `security-memory/data/` if needed (e.g. `security-memory/data/soc2/`)
2. Add your `.md` or `.txt` file to the appropriate subfolder
3. Re-run ingestion:

```bash
docker exec -i ingestion-api python -m app.security_memory.ingest
```

**Important:** Milvus does not support true content-hash upserts. Re-running ingestion will add new chunks on top of existing ones, creating duplicates for files that already exist. If you are updating an existing file, drop and recreate the collection first:

```bash
docker exec -i ingestion-api python - <<'PY'
from pymilvus import connections, utility, Collection
connections.connect(host="milvus", port=19530, timeout=10)
if utility.has_collection("ExpandedVSCodeMemory"):
    Collection("ExpandedVSCodeMemory").drop()
    print("Dropped. Re-run ingest to rebuild.")
PY

docker exec -i ingestion-api python -m app.security_memory.ingest
```

---

## Verifying Document Coverage

After ingestion, check what was stored:

```bash
docker exec -i ingestion-api python - <<'PY'
from pymilvus import connections, Collection
connections.connect(host="milvus", port=19530, timeout=10)
col = Collection("ExpandedVSCodeMemory")
col.load()
print("Total chunks:", col.num_entities)

# Sample first chunks per document
res = col.query(
    expr='chunk_index == 0',
    output_fields=['title', 'source', 'tags', 'doc_path'],
    limit=20,
)
for r in res:
    print(f"  {r['source']:12} | {r['title'][:40]:40} | tags={r['tags']}")
PY
```

---

## Recommended Corpus Additions

The starter corpus covers the most commonly referenced frameworks. Consider adding:

| Document | Subfolder | Tags |
|----------|-----------|------|
| NIST SP 800-190 (Container Security) | `nist/` | nist, containers, docker |
| CIS AWS Foundations Benchmark | `cis/` | cis, cloud |
| OWASP Docker Top 10 | `owasp/` | owasp, docker, containers |
| MITRE D3FEND | `mitre/` | mitre |
| SOC 2 Type II Controls Summary | `soc2/` | soc2, cloud, iam |
| PCI DSS Requirement Summary | `pci/` | pci |

Keep individual files under ~50,000 characters for reasonable ingestion times. For very large documents (e.g. full NIST 800-53), use a pre-chunked subset focused on the controls most relevant to your use case.

---

## Removing Documents

Milvus does not support deleting rows by source document in this schema (there is no unique document identifier — IDs are auto-assigned integers). The safest approach is to drop and recreate the entire collection:

1. Remove or replace the file under `security-memory/data/`
2. Drop the collection and re-ingest (see commands above)

If you need fine-grained deletion, add a `doc_hash` VARCHAR field to the schema and use `collection.delete(expr=f'doc_hash == "{hash}"')` — but this requires a schema change and collection recreation.
