import os
import time

from unstructured.partition.pdf import partition_pdf

# --- CONFIGURATION ---
PDF_PATH = "source_data/EP_Ordinances.pdf"
OCR_TEXT_CACHE = "full_text_ocr.txt"  # File to save/load OCR results


def get_ocr_text():
    """
    Performs OCR and saves the result to a cache file.
    If the cache file already exists, it loads from there instead.
    """
    # 1. VALIDATE PDF PATH: Check if the source PDF file exists.
    if not os.path.exists(PDF_PATH):
        print(f"❌ Error: The file '{PDF_PATH}' was not found.")
        print("Please make sure the PDF is in the 'source_data' directory.")
        return None

    # 2. CACHE CHECK: Check if the processed text file already exists.
    if os.path.exists(OCR_TEXT_CACHE):
        print(f"✅ Found cached OCR text. Loading from '{OCR_TEXT_CACHE}'...")
        with open(OCR_TEXT_CACHE, "r", encoding="utf-8") as f:
            return f.read()

    print(f"📜 No cache found. Starting OCR process on '{PDF_PATH}'...")
    print("This may take a few minutes...")

    # 3. OCR
    start_time = time.time()

    # Use unstructured's partition_pdf with an OCR strategy.
    # This will automatically use OCR when text extraction is difficult.
    elements = partition_pdf(
        filename=PDF_PATH,
        strategy="hi_res",  # "hi_res" is a powerful strategy
        infer_table_structure=True,
        model_name="yolox",
    )

    full_text = "\n\n".join([str(el) for el in elements])

    end_time = time.time()
    print(f"⏱️ OCR process finished in {end_time - start_time:.2f} seconds.")

    print(f"💾 Saving OCR text to cache file: '{OCR_TEXT_CACHE}'")
    with open(OCR_TEXT_CACHE, "w", encoding="utf-8") as f:
        f.write(full_text)

    return full_text


if __name__ == "__main__":
    extracted_text = get_ocr_text()
    print("\n--- Verification ---")
    print(f"Successfully retrieved {len(extracted_text)} characters.")
    print(f"Sample: {extracted_text[:400]}...")
