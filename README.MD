# Municipal AI — El Paso Code of Ordinances

Question-answering RAG app over the El Paso municipal code (Week 14 capstone).

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

The Week 14 curriculum `Resources/EP_Ordinances.pdf` was **not usable** for OCR (bogus/corrupt file in the repo resources folder). We sourced the real **El Paso Code of Ordinances** PDF externally and added it to this project as `source_data/EP_Ordinances.pdf`.

Because the file is ~72 MB, we **did not commit it as a normal git blob**. Instead:

1. Installed Git LFS (`brew install git-lfs && git lfs install`)
2. Tracked PDFs under `source_data/` via `.gitattributes`
3. Committed the LFS pointer; the binary lives in GitHub LFS storage

Collaborators must run `git lfs pull` after clone to get the real PDF (not the 133-byte stub pointer).

## Catch-up for collaborators

### 1. Clone and install Git LFS

The ordinances PDF (~72 MB) is stored with Git LFS. Install once per machine:

```bash
brew install git-lfs
git lfs install
git clone https://github.com/Bigessfour/municipal-ai.git
cd municipal-ai
git lfs pull
```

Confirm the PDF is real (not a 133-byte stub):

```bash
ls -lh source_data/EP_Ordinances.pdf
```

### 2. Python environment

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

**macOS OCR dependencies** (required by `unstructured[pdf,ocr]`):

```bash
brew install poppler tesseract
```

### 3. Run OCR ingest (Lab 1b)

```bash
python ingest.py
```

- First run: OCR on the PDF in **10-page batches** (progress logged per batch; 30+ minutes total with `hi_res`).
- If interrupted, rerun the same command — it **resumes** from `full_text_ocr.progress.json`.
- Second run (after cache exists): instant hit from `full_text_ocr.txt` (gitignored, generated locally).

Lab reference: `aico-echo/Module03-CICD/Week14-CICDPipeline/Day01/labs/02-lab-Ingest_using_OCR.md`

## Team enhancements (Day 1)

### El Paso PDF + Git LFS workaround

|          |                                                                                                       |
| -------- | ----------------------------------------------------------------------------------------------------- |
| Problem  | The Week 14 `Resources/EP_Ordinances.pdf` was a bogus file — OCR failed or produced garbage           |
| Fix      | Sourced the real El Paso ordinances PDF externally                                                    |
| Delivery | Committed via **Git LFS** so the team shares one canonical ~72 MB file without blowing up git history |
| Path     | `source_data/EP_Ordinances.pdf`                                                                       |

### EC2 Spot OCR offload (compute workaround)

Full `hi_res` OCR on **2,542 pages** saturated a MacBook Pro (M5): long wall-clock, high CPU/RAM, machine heat/fan load, and we could not leave the laptop running overnight. We offloaded the job to **EC2 Spot** so generation of `full_text_ocr.txt` could finish unattended.

#### What we launched

| Setting | Value |
| ------- | ----- |
| AWS account / profile | Code Platoon · `codeplatoon` · `us-east-1` |
| Purchase option | **Spot** (`one-time`, interrupt → terminate) |
| AMI | Ubuntu 24.04 (`ami-052355af2a014bd2c`) — Deep Learning GPU AMI blocked for our use case below |
| Instance type | **`c5.xlarge`** (4 vCPU, 8 GiB) |
| Key pair | `stephen-key` |
| VPC / subnet | Default VPC · public subnet `subnet-002827af9379deb64` (`us-east-1a`) |
| Security group | `municipal-ai-ocr` (`sg-0ee365f18ea667ecb`) — SSH/22 from Stephen’s public IP only |
| Storage | 80 GB **gp3** root volume |
| Name tag | `municipal-ai-ocr` · instance `i-0885869c1c8cb0e83` |
| Bootstrap | User-data + manual install: `poppler-utils`, `tesseract-ocr`, `libgl1`, Python venv, `pip install -r requirements.txt` |
| Job transfer | SCP tarball (chunked `ingest.py`, LFS PDF, `.env` / `HF_TOKEN`, resume progress) — private GH clone avoided |
| Run style | `nohup python ingest.py > ingest_ocr.log 2>&1 &` (laptop can shut down) |
| Output pull | SCP `full_text_ocr.txt` → local; backup `s3://municipal-ai-ocr-388691194728/` |
| Cleanup | Validated SHA locally, then **terminated** the Spot instance |

#### AMI / IAM configuration (what we wanted vs what class policy allows)

| Intent | Result |
| ------ | ------ |
| Preferred AMI | Deep Learning OSS Nvidia Driver AMI GPU PyTorch (Ubuntu 24.04) |
| Preferred type | `g4dn.xlarge` / `g5.xlarge` Spot for YOLOX/`hi_res` GPU accel |
| Blocker | IAM identity policy **`cp-aico-echo-cost-guard`** — `CapEC2InstanceFamilies` **Deny** `ec2:RunInstances` unless type is in an allow-list (`t2/t3/t3a/t4g.*`, `m5/m5a/m6i.large|xlarge`, `c5/c5a.large|xlarge`, `r5.large|xlarge`) |
| Fallback | Largest useful CPU on the allow-list: **`c5.xlarge` Spot** + stock **Ubuntu 24.04** AMI (no GPU; CPU ONNX/Torch path) |

#### Timing: AWS vs MacBook Pro (M5)

| Run | Scope | Measured / estimated |
| --- | ----- | -------------------- |
| **EC2 Spot `c5.xlarge`** | Pages **481–2542** (resume after local progress) | **15,426.47 s ≈ 4.29 hours** · ~**8 pages/min** · log: `OCR process finished in 15426.47 seconds` → **7,992,823** chars |
| **EC2 extrapolated full file** | All **2,542** pages at same rate | **≈ 5.3 hours** wall-clock |
| **MacBook Pro M5** (local early run) | ~290 pages in ~15 minutes before we stopped for EC2 | **≈ 19–20 pages/min** → uninterrupted full file **≈ 2.1 hours** *if* the laptop could sustain it |
| **Why we still used EC2** | M5 was faster *per page* early on, but the full `hi_res` job **thrashed the machine** (CPU/RAM, heat, couldn’t leave it overnight / shut down). Spot ran **unattended**, with page-batch **resume**, then we pulled a validated cache and terminated the instance. |

**Tradeoff we accepted:** slightly slower pages/min on CPU Spot vs M5, in exchange for reliable overnight completion and not melting the laptop. Output contract unchanged: one gitignored `full_text_ocr.txt` for Day 2.

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

## What is not in git

| Path                          | Reason                                      |
| ----------------------------- | ------------------------------------------- |
| `venv/`                       | Local virtualenv                            |
| `full_text_ocr.txt`           | Generated OCR cache                         |
| `full_text_ocr.partial.txt`   | In-progress OCR batch cache                 |
| `full_text_ocr.progress.json` | Resume checkpoint for chunked OCR           |
| `ingest_ocr.log`              | Local run log                               |
| Other files in `source_data/` | Only `EP_Ordinances.pdf` is tracked via LFS |

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
