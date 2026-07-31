# source_data

The large `EP_Ordinances.pdf` (~72 MB) was removed from the repo to save clone/LFS space for collaborators.

**Day 2+ work does not need the PDF.** Shared team artifacts (Git LFS):

| Asset | Purpose |
| ----- | ------- |
| `full_text_ocr.txt` | Day 1 OCR cache — source text for embeddings |
| `chroma_db/` | Day 2 vector DB — skip local `load_to_db.py` rebuild |

After clone: `git lfs pull`, then confirm `du -sh chroma_db` is ~107 MB (not pointer stubs).

To re-run OCR (`ingest.py`), place a local copy at:

```text
source_data/EP_Ordinances.pdf
```

That path is gitignored; do not commit the PDF again.
