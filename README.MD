# Municipal AI — El Paso Code of Ordinances

Question-answering RAG app over the El Paso municipal code (Week 14 capstone).

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

| Problem | The Week 14 `Resources/EP_Ordinances.pdf` was a bogus file — OCR failed or produced garbage |
| Fix | Sourced the real El Paso ordinances PDF externally |
| Delivery | Committed via **Git LFS** so the team shares one canonical ~72 MB file without blowing up git history |
| Path | `source_data/EP_Ordinances.pdf` |

### EC2 Spot OCR offload

Full `hi_res` OCR on 2,542 pages is too slow to keep on a laptop. We run the job on **EC2 Spot** in the Code Platoon AWS account so the Mac can sleep/shut down.

| Detail   | Value                                                                  |
| -------- | ---------------------------------------------------------------------- |
| Wanted   | `g4dn.xlarge` GPU Spot                                                 |
| Blocked  | Class IAM `cp-aico-echo-cost-guard` denies GPU families                |
| Used     | `c5.xlarge` Spot (largest allowed CPU) + Ubuntu 24.04                  |
| Transfer | SCP job tarball (code + PDF + resume progress + `.env`)                |
| Output   | `full_text_ocr.txt` → SCP back or `s3://municipal-ai-ocr-388691194728` |
| Resume   | Same page-batch checkpoint files as local                              |

Once `nohup python ingest.py` is running on the instance, **closing Cursor or shutting down the Mac does not stop OCR**. Terminate the Spot instance after you download the cache file.

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

### 4. If two-column reading order looks wrong

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
