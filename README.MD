# Municipal AI — El Paso Code of Ordinances

Question-answering RAG app over the El Paso municipal code (Week 14 capstone).

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

- First run: OCR on the PDF (slow on the full file — 30+ minutes with `hi_res`).
- Second run: instant cache hit from `full_text_ocr.txt` (gitignored, generated locally).

Lab reference: `aico-echo/Module03-CICD/Week14-CICDPipeline/Day01/labs/02-lab-Ingest_using_OCR.md`

### 4. If two-column reading order looks wrong

Switch `ingest.py` to `strategy="fast"`, delete `full_text_ocr.txt`, and rerun.

## What is not in git

| Path | Reason |
|------|--------|
| `venv/` | Local virtualenv |
| `full_text_ocr.txt` | Generated OCR cache |
| `ingest_ocr.log` | Local run log |
| Other files in `source_data/` | Only `EP_Ordinances.pdf` is tracked via LFS |
