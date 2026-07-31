# source_data

The large `EP_Ordinances.pdf` (~72 MB) was removed from the repo to save clone/LFS space for collaborators.

**Day 2+ work does not need the PDF.** Use the shared OCR cache instead:

- `full_text_ocr.txt` (Git LFS) — already extracted text for embeddings / RAG

To re-run OCR (`ingest.py`), place a local copy at:

```text
source_data/EP_Ordinances.pdf
```

That path is gitignored; do not commit the PDF again.
