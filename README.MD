# Municipal AI — El Paso Code of Ordinances

Question-answering RAG app over the El Paso municipal code (Week 14 capstone).

**Team:** Stephen McKitrick ([@Bigessfour](https://github.com/Bigessfour)) · Guy Sharp ([@gsharp23](https://github.com/gsharp23)) · Stewart Anderson ([@Stubud7](https://github.com/Stubud7))

## Day 1 lab goals (front and center)

Day 1 is two labs: **Lab 1a — Project Foundation & CI**, and **Lab 1b — OCR ingest with caching**. Together they give us a shared repo with automated quality gates and a reliable text extract of the ordinances PDF.

### Lab 1a — Foundation & Continuous Integration

**By the end, we should have:**

- A local Git repository connected to a remote GitHub repository
- A standard Python project structure with a virtual environment
- A GitHub Actions workflow that automatically runs on every push

**We should be able to:**

- Initialize a new project and connect it to GitHub
- Manage Python dependencies with a `requirements.txt` file
- Explain the purpose of a CI (Continuous Integration) workflow
- Verify the status of a GitHub Actions run

### Lab 1b — OCR extraction & caching

**By the end, we should have:**

- An `ingest.py` script that performs OCR on a PDF to extract text
- A `.txt` cache file (`full_text_ocr.txt`) that stores OCR results
- An updated `requirements.txt` with dependencies for advanced PDF processing

**We should be able to:**

- Explain the difference between basic text extraction and OCR
- Implement a file-based caching system in Python
- Use the `unstructured` library to perform OCR on a PDF document

---

## Source PDF workaround (Day 1)

The Week 14 curriculum `Resources/EP_Ordinances.pdf` was **not usable** for OCR (bogus/corrupt file in the repo resources folder). We sourced the real **El Paso Code of Ordinances** PDF externally, ran OCR once (including EC2 Spot offload), and shared the result as `full_text_ocr.txt` via Git LFS.

**The ~72 MB PDF is no longer in the repo** (removed to save clone/LFS space for collaborators). Day 2+ only needs `full_text_ocr.txt`. If you must re-run OCR, put a local PDF at `source_data/EP_Ordinances.pdf` (gitignored) — see `source_data/README.md`.

## Catch-up for collaborators

### 1. Clone and install Git LFS

Git LFS stores:

| File / folder       | Approx. size | Purpose                                     |
| ------------------- | ------------ | ------------------------------------------- |
| `full_text_ocr.txt` | ~7.6 MB      | Day 1 OCR cache for Day 2+                  |
| `chroma_db/`        | ~107 MB      | Day 2 vector DB (Ollama `nomic-embed-text`) |

```bash
brew install git-lfs
git lfs install
git clone https://github.com/Bigessfour/municipal-ai.git
cd municipal-ai
git lfs pull
```

Confirm LFS assets are real (not tiny pointer stubs):

```bash
ls -lh full_text_ocr.txt
ls -lh chroma_db/chroma.sqlite3
du -sh chroma_db
```

### Troubleshooting: `chroma_db` missing or “hidden”

**Use the app repo, not the challenges repo.** Clone [Bigessfour/municipal-ai](https://github.com/Bigessfour/municipal-ai) directly. The nested `municipal-ai/` copy inside `aico-challenges-w14` does **not** include `chroma_db/`.

```bash
git remote -v   # must show github.com/Bigessfour/municipal-ai.git
git pull origin main
git lfs install
git lfs pull
ls -lh chroma_db/chroma.sqlite3   # ~59 MB (133 bytes = LFS not pulled)
```

**VS Code / Cursor hiding the folder?** The folder may exist on disk but be hidden in the sidebar. Check terminal first:

```bash
ls -la chroma_db
```

If terminal shows files but the explorer does not, this repo includes `.vscode/settings.json` to force `chroma_db` visible. After `git pull`, reload the window (`Cmd+Shift+P` → **Developer: Reload Window**).

Also check user settings manually:

1. **Explorer: Exclude Git Ignore** → off
2. **Files: Exclude** → remove any `**/chroma_db`, `**/*.sqlite3`, or `**/*.bin` entries

### 2. Python environment

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

**macOS OCR dependencies** (only needed if you re-run OCR):

```bash
brew install poppler tesseract
```

### 3. Run OCR ingest (Lab 1b)

With `full_text_ocr.txt` already present from LFS, ingest is an instant **cache hit**:

```bash
python ingest.py
```

- Cache hit: loads shared `full_text_ocr.txt` immediately (~8M characters).
- Cache miss (if you delete the file): OCR runs in **10-page batches** (hours with `hi_res`); resumes via `full_text_ocr.progress.json` if interrupted.

Lab reference: `aico-echo/Module03-CICD/Week14-CICDPipeline/Day01/labs/02-lab-Ingest_using_OCR.md`

## Team enhancements (Day 1)

### El Paso PDF + Git LFS workaround

|          |                                                                                                                |
| -------- | -------------------------------------------------------------------------------------------------------------- |
| Problem  | The Week 14 `Resources/EP_Ordinances.pdf` was a bogus file — OCR failed or produced garbage                    |
| Fix      | Sourced the real El Paso ordinances PDF externally, OCR’d once, shared `full_text_ocr.txt` via LFS             |
| Delivery | PDF was temporarily LFS-tracked; **removed from repo** later to save space — collaborators use OCR cache only  |
| Path     | Local-only if needed: `source_data/EP_Ordinances.pdf` (gitignored). Shared artifact: `full_text_ocr.txt` (LFS) |

### EC2 Spot OCR offload (compute workaround)

Full `hi_res` OCR on **2,542 pages** saturated a MacBook Pro (M5): long wall-clock, high CPU/RAM, machine heat/fan load, and we could not leave the laptop running overnight. We offloaded the job to **EC2 Spot** so generation of `full_text_ocr.txt` could finish unattended.

#### What we launched

| Setting               | Value                                                                                                                  |
| --------------------- | ---------------------------------------------------------------------------------------------------------------------- |
| AWS account / profile | Code Platoon · `codeplatoon` · `us-east-1`                                                                             |
| Purchase option       | **Spot** (`one-time`, interrupt → terminate)                                                                           |
| AMI                   | Ubuntu 24.04 (`ami-052355af2a014bd2c`) — Deep Learning GPU AMI blocked for our use case below                          |
| Instance type         | **`c5.xlarge`** (4 vCPU, 8 GiB)                                                                                        |
| Key pair              | `stephen-key`                                                                                                          |
| VPC / subnet          | Default VPC · public subnet `subnet-002827af9379deb64` (`us-east-1a`)                                                  |
| Security group        | `municipal-ai-ocr` (`sg-0ee365f18ea667ecb`) — SSH/22 from Stephen’s public IP only                                     |
| Storage               | 80 GB **gp3** root volume                                                                                              |
| Name tag              | `municipal-ai-ocr` · instance `i-0885869c1c8cb0e83`                                                                    |
| Bootstrap             | User-data + manual install: `poppler-utils`, `tesseract-ocr`, `libgl1`, Python venv, `pip install -r requirements.txt` |
| Job transfer          | SCP tarball (chunked `ingest.py`, LFS PDF, `.env` / `HF_TOKEN`, resume progress) — private GH clone avoided            |
| Run style             | `nohup python ingest.py > ingest_ocr.log 2>&1 &` (laptop can shut down)                                                |
| Output pull           | SCP `full_text_ocr.txt` → local; backup `s3://municipal-ai-ocr-388691194728/`                                          |
| Cleanup               | Validated SHA locally, then **terminated** the Spot instance                                                           |

#### AMI / IAM configuration (what we wanted vs what class policy allows)

| Intent         | Result                                                                                                                                                                         |
| -------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Preferred AMI  | Deep Learning OSS Nvidia Driver AMI GPU PyTorch (Ubuntu 24.04)                                                                                                                 |
| Preferred type | `g4dn.xlarge` / `g5.xlarge` Spot for YOLOX/`hi_res` GPU accel                                                                                                                  |
| Blocker        | IAM identity policy **`cp-aico-echo-cost-guard`** — `CapEC2InstanceFamilies` **Deny** `ec2:RunInstances` unless type is in an allow-list (`t2/t3/t3a/t4g.*`, `m5/m5a/m6i.large | xlarge`, `c5/c5a.large | xlarge`, `r5.large | xlarge`) |
| Fallback       | Largest useful CPU on the allow-list: **`c5.xlarge` Spot** + stock **Ubuntu 24.04** AMI (no GPU; CPU ONNX/Torch path)                                                          |

#### Timing: AWS vs MacBook Pro (M5)

| Run                                  | Scope                                                                                                                                                                                                                                                              | Measured / estimated                                                                                                    |
| ------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------- |
| **EC2 Spot `c5.xlarge`**             | Pages **481–2542** (resume after local progress)                                                                                                                                                                                                                   | **15,426.47 s ≈ 4.29 hours** · ~**8 pages/min** · log: `OCR process finished in 15426.47 seconds` → **7,992,823** chars |
| **EC2 extrapolated full file**       | All **2,542** pages at same rate                                                                                                                                                                                                                                   | **≈ 5.3 hours** wall-clock                                                                                              |
| **MacBook Pro M5** (local early run) | ~290 pages in ~15 minutes before we stopped for EC2                                                                                                                                                                                                                | **≈ 19–20 pages/min** → uninterrupted full file **≈ 2.1 hours** *if* the laptop could sustain it                        |
| **Why we still used EC2**            | M5 was faster *per page* early on, but the full `hi_res` job **thrashed the machine** (CPU/RAM, heat, couldn’t leave it overnight / shut down). Spot ran **unattended**, with page-batch **resume**, then we pulled a validated cache and terminated the instance. |

**Tradeoff we accepted:** slightly slower pages/min on CPU Spot vs M5, in exchange for reliable overnight completion and not melting the laptop. Output contract unchanged: one `full_text_ocr.txt` for Day 2 (now shared via Git LFS).

### Page-batch OCR chunking

The lab processes the full PDF in one pass. We added an optimization for the 72 MB ordinances file:

| Piece                         | Purpose                           |
| ----------------------------- | --------------------------------- |
| `PAGES_PER_CHUNK = 10`        | Process PDF in manageable batches |
| `full_text_ocr.partial.txt`   | Append OCR text after each batch  |
| `full_text_ocr.progress.json` | Track next page for resume        |

PyMuPDF slices each batch; `unstructured` runs `hi_res` OCR per slice. Final output is still a single `full_text_ocr.txt` — Day 2 semantic chunking in `load_to_db.py` is unchanged.

Monitor a run:

```bash
tail -f ingest_ocr.log
cat full_text_ocr.progress.json
ls -lh full_text_ocr.partial.txt
```

### If two-column reading order looks wrong

Switch `ingest.py` to `strategy="fast"`, delete `full_text_ocr.txt`, and rerun.

## Team enhancements (Day 2)

**Baseline lab:** [Day 2 Lab 1 — Building a Vector Database with LangChain](https://github.com/CodePlatoon/aico-echo/blob/main/Module03-CICD/Week14-CICDPipeline/Day02/labs/01-lab-vector_db_using_lagchain.md) (`load_to_db.py` → `chroma_db`).

### Workaround: Google free-tier rate limits → Bedrock embeddings

|                  |                                                                                                                                                                                                                                                                                                 |
| ---------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Problem**      | Lab defaults to `GoogleGenerativeAIEmbeddings` + `GOOGLE_API_KEY`. Our OCR cache parses into **~16,700+ documents**. Google Gemini **free tier** returned `429 RESOURCE_EXHAUSTED` almost immediately — even with batching and retries, we could not finish embedding the full ordinances file. |
| **Fix**          | Default embedding provider switched to **AWS Bedrock** (`amazon.titan-embed-text-v2:0`) via `langchain-aws`, using the Code Platoon AWS profile. Same LangChain + Chroma pipeline; only the embedder backend changed.                                                                           |
| **Config**       | `EMBEDDING_PROVIDER` env var: `ollama` (default), `bedrock`, or `google`. Shared logic in `embeddings.py`.                                                                                                                                                                                      |
| **Forward path** | Output is still `chroma_db/` with section metadata. **Use the same embedder** in Lab 2b (`check_db.py`) and Day 3 RAG — mismatched models break similarity search.                                                                                                                              |

### Troubleshooting we hit (Lab 1 for Day 2)

1. **LangChain 1.x import paths** — `langchain.schema.Document` → `langchain_core.documents.Document`; text splitter → `langchain_text_splitters`.
2. **Deprecated Google model** — lab’s `models/embedding-001` → `404 NOT_FOUND`; updated to `models/gemini-embedding-001`.
3. **`.env` variable name** — must be `GOOGLE_API_KEY` (all caps), not `Google_API_KEY`.
4. **Free-tier quota** — `429 RESOURCE_EXHAUSTED` on ~17k docs; Bedrock unblocked the run.

### Run Day 2 Lab 1 (`load_to_db.py`)

```bash
source venv/bin/activate
pip install -r requirements.txt

# Default: Bedrock (recommended for full ordinances file)
export AWS_PROFILE=codeplatoon
export AWS_REGION=us-east-1
python3 load_to_db.py

# Optional: force Google (small tests only on free tier)
EMBEDDING_PROVIDER=google python3 load_to_db.py
```

Batch embedding with progress bar and exponential backoff on rate limits are built into `load_to_db.py`.

### Local-first: Ollama (recommended for team laptops)

Week 14 Day 2+ labs use **`nomic-embed-text`** for embeddings and **`llama3`** for the Day 3 chat LLM — both run locally via [Ollama](https://ollama.com). No Google/AWS keys required for embeddings.

#### 1. Install Ollama

| OS              | Command                                                                 |
| --------------- | ----------------------------------------------------------------------- |
| **macOS**       | Download from [ollama.com](https://ollama.com) or `brew install ollama` |
| **WSL / Linux** | `curl -fsSL https://ollama.com/install.sh \| sh`                        |

Start the server (macOS app does this automatically):

```bash
ollama serve
```

#### 2. Pull models

```bash
# Embeddings — Day 2 load_to_db.py + check_db.py
ollama pull nomic-embed-text

# Chat LLM — Day 3 RAG (pull now so you're ready)
ollama pull llama3

ollama list
```

#### 3. Configure project (optional — Ollama is already the default)

```bash
cp .env.example .env
# EMBEDDING_PROVIDER=ollama  (default)
```

#### 4. Build and verify vector DB

```bash
source venv/bin/activate
pip install -r requirements.txt

# Rebuild chroma_db if you previously used Bedrock or Google (different vector space)
rm -rf chroma_db
python3 load_to_db.py
python3 check_db.py
```

**Note:** ~16,700 docs on CPU is slow but steady — no cloud rate limits. Expect a multi-hour local run on laptops; leave Ollama running.

#### Progress dashboard

Watch embedding progress while `load_to_db.py` runs:

```bash
# Browser dashboard (http://127.0.0.1:8765)
python3 watch_load_dashboard.py --web

# Terminal dashboard (refreshes every 2s)
python3 watch_load_dashboard.py
```

Writes `load_status.json` each batch (future runs). For runs already in flight, the dashboard parses `load_to_db_ollama.log` as a fallback.

#### Day 3 RAG (`main.py`)

```bash
# Lab baseline (similarity, k=3)
python3 main.py

# Retrieval-quality enhancement: MMR + tunable k
python3 main.py --search-type mmr --k 3

# Evidence helpers (no interactive loop)
python3 compare_retrieval_quality.py
python3 eval_retrieval_quality.py
```

Use the **same** `nomic-embed-text` embedder everywhere you touch `chroma_db`.

## What is not in git

| Path                          | Reason                                             |
| ----------------------------- | -------------------------------------------------- |
| `venv/`                       | Local virtualenv                                   |
| `full_text_ocr.partial.txt`   | In-progress OCR batch cache                        |
| `full_text_ocr.progress.json` | Resume checkpoint for chunked OCR                  |
| `ingest_ocr.log`              | Local run log                                      |
| Other files in `source_data/` | Local PDFs gitignored; see `source_data/README.md` |

`full_text_ocr.txt` and `chroma_db/` **are** in git via **LFS** so collaborators skip multi-hour OCR and vector DB rebuilds (must use the same `nomic-embed-text` embedder). Re-run `load_to_db.py` only if you change embedding provider.

---

## How we explain what Day 1 accomplished

First-person answers to the labs’ “you should be able to…” goals — what we actually built and how we’d talk about it in a demo or TA review.

### Lab 1a — Foundation & CI

**Initialize a new project and connect it to GitHub.**
I set up `municipal-ai` as a Git repo, pushed it to GitHub under `Bigessfour/municipal-ai`, and treat that shared remote as the single place for pair work, CI, and Day tickets. Day-to-day I clone, branch or commit on `main` for this week’s cadence, and push so my partner and Actions both see the same tree.

**Manage Python dependencies with a `requirements.txt` file.**
I keep installable deps in `requirements.txt` (`ruff`, LangChain packages, `unstructured[pdf,ocr]`, PyMuPDF). Anyone on the team can recreate the environment with `python3 -m venv venv`, activate it, and `pip install -r requirements.txt`. That beats “it works on my machine” and matches what CI installs before linting.

**Explain the purpose of a CI (Continuous Integration) workflow.**
CI is our automated quality gate. Every push to `main` runs GitHub Actions so we don’t rely on remembering to lint locally. If Ruff fails, the workflow fails — we find style and simple correctness issues before they pile up into Day 2–4 work. It’s continuous because the check runs on each integration into the shared branch, not once at the end of the week.

**Verify the status of a GitHub Actions run.**
I check the **Actions** tab on the repo (or `gh run list --repo Bigessfour/municipal-ai`) after a push. A green “Code Quality CI” run means checkout, Python setup, `pip install -r requirements.txt`, and `ruff check .` all succeeded. A red run means I open the log, fix the lint/error, and push again.

### Lab 1b — OCR ingest & caching

**Explain the difference between basic text extraction and OCR.**
Basic extraction pulls embedded text streams out of a PDF (fast, cheap, fails or gibberish when pages are scanned or layout-heavy). OCR treats pages more like images: it detects layout and characters so we still get usable text from messy municipal PDFs. For El Paso’s ordinances we used `unstructured` with `strategy="hi_res"` (plus YOLOX layout) so we weren’t stuck with a naive dump that ignored structure. That’s slower — which is exactly why we needed caching and eventually EC2.

**Implement a file-based caching system in Python.**
`ingest.py`’s `get_ocr_text()` checks for `full_text_ocr.txt` first. Cache hit → read the file and return immediately. Cache miss → run OCR, write the file, then return. We extended that idea with page batches: append to `full_text_ocr.partial.txt` and record `full_text_ocr.progress.json` so a crash or Spot reclaim doesn’t throw away hours of work. The contract for Day 2 stays one finished `full_text_ocr.txt`.

**Use the `unstructured` library to perform OCR on a PDF document.**
I call `partition_pdf` on each page batch (or the whole file in the lab baseline). Unstructured returns elements; we join them into one text blob and save it. System deps (`poppler`, `tesseract`) support the OCR path. In practice we proved cache-miss on EC2 (~2,542 pages → ~8M characters) and cache-hit locally in seconds — so the rest of the week can load text without re-running OCR.
