# Lesson 10: Layer 6: Scan and Pin Your Images

Every layer so far limits what an attacker can do **after** getting in. This lesson looks at how they get in: known vulnerabilities in the software inside your images. Then it locks every image to the exact version you checked.

---

## Part A: Scan

A **CVE** (Common Vulnerabilities and Exposures) is a publicly listed security bug in a specific version of a piece of software. **Trivy** is a free scanner that lists every package inside an image and checks each one against those lists.

```bash
bin/scan_images.sh
```

The first run downloads Trivy's vulnerability database (about a minute).

### What you will see (your numbers will differ)

```
  milvus         CRITICAL   0   HIGH   7   (fix available for 7)
  etcd           CRITICAL   6   HIGH 146   (fix available for 152)
  minio          CRITICAL   7   HIGH 133   (fix available for 140)
  ollama         CRITICAL   0   HIGH  52   (fix available for 52)
  nginx          CRITICAL   4   HIGH  78   (fix available for 82)
  ingestion-api  CRITICAL   0   HIGH  52   (fix available for 5)
  gradio-ui      CRITICAL   6   HIGH  91   (fix available for 49)
```

Notice where the worst findings are: not in Milvus, but in its two helpers. The etcd and MinIO versions Milvus ships with are older than Milvus itself. The services you never think about are often the ones nobody updates, which is one more reason Part 3 put them on a private network that only Milvus can reach.

Your numbers will be different, because new vulnerabilities are published every day. That is the point: **a scan is only true on the day you run it.**

### How Trivy is run safely

Many tutorials run scanners with `-v /var/run/docker.sock:/var/run/docker.sock`. That gives the scanner **full control of Docker**, which is effectively root on your computer. `bin/scan_images.sh` never does that. Instead, every image is exported to a file with `docker save`, and Trivy scans the file. That has two more benefits:
- it scans **exactly** the images on your machine, the ones you actually run
- Trivy never has to download images, so registry download limits (`TOOMANYREQUESTS`) cannot stop the scan. Building this lab, scanning images by name from the registry hit that limit

---

## Part B: Triage, don't panic

Hundreds of findings is normal for real images. The job is to sort them:

| Kind of finding | Example | What to do |
|---|---|---|
| **In a package you chose** | A Python library pinned in `requirements.txt` | Upgrade it. This is fully in your control |
| **In the base image, with a fix** | An operating system library in `python:3.12-slim` | Rebuild on a newer base image, or wait for the image to be updated |
| **No fix exists yet** | A library the distribution has not patched | Track it. Check whether your app even uses it |
| **In a program the container never runs** | A command-line tool installed but unused | Lower priority; consider a smaller base image |

See the details for every image (the 25 most serious per image):

```bash
bin/scan_images.sh --details
```

Look at `ingestion-api` in particular. Most of its findings are operating system packages from the Debian base image, mostly with **no fix yet**. A few are in Python packages **we chose**. Those we can fix today.

---

## Part C: Fix what you control

The API's findings include `starlette`, the web framework underneath FastAPI. The version pinned in `ingestion-api/requirements.txt` is old. Upgrade FastAPI, which brings a patched Starlette with it:

```bash
sed -i.bak -e 's/^fastapi==.*/fastapi==0.162.5/' \
           -e 's/^uvicorn\[standard\]==.*/uvicorn[standard]==0.54.0/' \
           -e 's/^pydantic==.*/pydantic==2.14.3/' ingestion-api/requirements.txt && rm ingestion-api/requirements.txt.bak
cat ingestion-api/requirements.txt
```

Rebuild only the API:

```bash
docker compose up -d --build ingestion-api
```

**An upgrade is a change, so test everything:**

```bash
bin/smoke_test.sh
python3 attacks/run_attacks.py
```

Both should pass exactly as before. Then re-scan:

```bash
bin/scan_images.sh
```

The `ingestion-api` line should drop. All of its remaining findings are in the operating system layer, with no fix published yet.

> **Try it:** `gradio-ui` has many Python findings, most in `gradio` and `pillow`. Upgrading Gradio across major versions can change how the UI code must be written. Try it on your own: change `gradio-ui/requirements.txt`, rebuild with `docker compose up -d --build gradio-ui`, and see what breaks. This is what real dependency upgrades feel like.

---

## Part D: Pin by digest

Your compose files say things like:

```yaml
image: ollama/ollama:0.40.6
```

`0.40.6` is a **tag**: a label the publisher can move to a different image at any time, by accident or because their account was compromised. You scanned one image; next week the same tag could be different software.

A **digest** is a fingerprint of the image's exact contents:

```
ollama/ollama@sha256:265409e1d931028a8f7d5a32bcbafddd7bffbc6cc629d77efe9560adf692a5e7
```

If even one byte changes, the digest changes. Pinning by digest means "run exactly the image I scanned, or nothing."

Generate the pinning layer from the images on your machine:

```bash
bin/pin_images.sh
```

```
Wrote hardening/06-pinned.yml:
  image: milvusdb/milvus@sha256:b9b79b4a284b...
  image: milvusdb/milvus@sha256:b9b79b4a284b...
  image: quay.io/coreos/etcd@sha256:52f17f7e56e4...
  image: milvusdb/minio@sha256:1dce27c494a1...
  image: ollama/ollama@sha256:265409e1d931...
  image: nginxinc/nginx-unprivileged@sha256:7377697a821c...
  BASE_IMAGE: python@sha256:5e2bdb1b0d54...
  BASE_IMAGE: python@sha256:5e2bdb1b0d54...
  BASE_IMAGE: python@sha256:5e2bdb1b0d54...
```

For the images built here, the thing to pin is the **base image** in the Dockerfile. (There are three `BASE_IMAGE` lines because `milvus-init` is built from the same Dockerfile as the API. The Milvus digest appears twice too: once for Milvus, once for `storage-perms`, which borrows the Milvus image.) Both Dockerfiles start with:

```dockerfile
ARG BASE_IMAGE=python:3.12-slim
FROM ${BASE_IMAGE}
```

so the pinning layer can pass in the exact digest.

Apply it:

```bash
bin/harden.sh 6
python3 bin/audit.py
bin/smoke_test.sh
```

### What you will see

Every `pinned` column turns to `pass`, and the total reaches **63 of 63 (100%)**.

---

## Updating, deliberately

Pinning does not mean never updating. It means updating **on purpose**:

1. `docker pull` the new versions you want
2. `bin/scan_images.sh` to see what changed
3. Test: `bin/smoke_test.sh` and `python3 attacks/run_attacks.py`
4. `bin/pin_images.sh` to record the new digests, then `bin/harden.sh 6`

Unpinned images update by surprise. Pinned images update when you have checked them.

Next: [Final Verification](11-verify.md)
