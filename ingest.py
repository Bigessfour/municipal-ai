import json
import os
import tempfile
import time

import fitz
from unstructured.partition.pdf import partition_pdf

# --- CONFIGURATION ---
PDF_PATH = "source_data/EP_Ordinances.pdf"
OCR_TEXT_CACHE = "full_text_ocr.txt"
OCR_PARTIAL_CACHE = "full_text_ocr.partial.txt"
OCR_PROGRESS_FILE = "full_text_ocr.progress.json"
PAGES_PER_CHUNK = 10

PARTITION_KWARGS = {
    "strategy": "hi_res",
    "infer_table_structure": True,
    "model_name": "yolox",
}


def _load_progress() -> int:
    if not os.path.exists(OCR_PROGRESS_FILE):
        return 0
    with open(OCR_PROGRESS_FILE, encoding="utf-8") as f:
        return int(json.load(f).get("next_page", 0))


def _save_progress(next_page: int) -> None:
    with open(OCR_PROGRESS_FILE, "w", encoding="utf-8") as f:
        json.dump({"next_page": next_page}, f)


def _ocr_page_range(doc: fitz.Document, start: int, end: int) -> str:
    chunk_doc = fitz.open()
    chunk_path = None
    try:
        chunk_doc.insert_pdf(doc, from_page=start, to_page=end - 1)
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            chunk_path = tmp.name
        chunk_doc.save(chunk_path)
    finally:
        chunk_doc.close()

    try:
        elements = partition_pdf(filename=chunk_path, **PARTITION_KWARGS)
        return "\n\n".join(str(el) for el in elements)
    finally:
        if chunk_path and os.path.exists(chunk_path):
            os.remove(chunk_path)


def _finalize_cache() -> str:
    with open(OCR_PARTIAL_CACHE, encoding="utf-8") as f:
        text = f.read()
    with open(OCR_TEXT_CACHE, "w", encoding="utf-8") as f:
        f.write(text)
    os.remove(OCR_PARTIAL_CACHE)
    if os.path.exists(OCR_PROGRESS_FILE):
        os.remove(OCR_PROGRESS_FILE)
    return text


def get_ocr_text():
    """
    Performs OCR in page batches and saves the result to a cache file.
    If the cache file already exists, it loads from there instead.
    """
    if not os.path.exists(PDF_PATH):
        print(f"❌ Error: The file '{PDF_PATH}' was not found.")
        print("Please make sure the PDF is in the 'source_data' directory.")
        return None

    if os.path.exists(OCR_TEXT_CACHE):
        print(f"✅ Found cached OCR text. Loading from '{OCR_TEXT_CACHE}'...")
        with open(OCR_TEXT_CACHE, encoding="utf-8") as f:
            return f.read()

    start_page = _load_progress()
    if start_page == 0 and os.path.exists(OCR_PARTIAL_CACHE):
        os.remove(OCR_PARTIAL_CACHE)

    doc = fitz.open(PDF_PATH)
    total_pages = doc.page_count

    if start_page >= total_pages:
        doc.close()
        if os.path.exists(OCR_PARTIAL_CACHE):
            return _finalize_cache()
        print("❌ Progress file indicates completion but final cache is missing.")
        return None

    if start_page == 0:
        print(f"📜 No cache found. Starting chunked OCR on '{PDF_PATH}'...")
    else:
        print(f"↩️ Resuming chunked OCR from page {start_page + 1} of {total_pages}...")
    print(f"Processing {PAGES_PER_CHUNK} pages per batch. This may take a while...")

    start_time = time.time()

    with open(OCR_PARTIAL_CACHE, "a", encoding="utf-8") as out:
        for batch_start in range(start_page, total_pages, PAGES_PER_CHUNK):
            batch_end = min(batch_start + PAGES_PER_CHUNK, total_pages)
            print(f"📄 OCR pages {batch_start + 1}–{batch_end} of {total_pages}...")

            text = _ocr_page_range(doc, batch_start, batch_end)
            if batch_start > 0 and out.tell() > 0:
                out.write("\n\n")
            out.write(text)
            out.flush()

            _save_progress(batch_end)

    doc.close()

    elapsed = time.time() - start_time
    print(f"⏱️ OCR process finished in {elapsed:.2f} seconds.")
    print(f"💾 Saving OCR text to cache file: '{OCR_TEXT_CACHE}'")
    return _finalize_cache()


if __name__ == "__main__":
    extracted_text = get_ocr_text()
    if extracted_text is None:
        raise SystemExit(1)
    print("\n--- Verification ---")
    print(f"Successfully retrieved {len(extracted_text)} characters.")
    print(f"Sample: {extracted_text[:400]}...")
