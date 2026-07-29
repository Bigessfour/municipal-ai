import os
import re
import shutil
import time

from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from tqdm import tqdm

from embeddings import DB_PATH, EMBEDDING_PROVIDER, get_embeddings
from load_progress import write_status

# --- CONFIGURATION ---
OCR_TEXT_PATH = "full_text_ocr.txt"

# Google free tier is tight; Ollama/Bedrock can use larger batches.
BATCH_SIZE = int(
    os.getenv("EMBED_BATCH_SIZE", "100" if EMBEDDING_PROVIDER != "google" else "10")
)
MAX_RETRIES = 8


def add_batch_with_retry(db: Chroma, batch: list[Document]) -> None:
    for attempt in range(MAX_RETRIES):
        try:
            db.add_documents(batch)
            return
        except Exception as e:
            err = str(e)
            is_rate_limit = (
                "429" in err
                or "RESOURCE_EXHAUSTED" in err
                or "ThrottlingException" in err
            )
            if not is_rate_limit or attempt == MAX_RETRIES - 1:
                raise
            wait = min(60 * (2**attempt), 600)
            print(
                f"\n⏳ Rate limited (attempt {attempt + 1}/{MAX_RETRIES}) — waiting {wait}s..."
            )
            time.sleep(wait)


def main():
    load_dotenv()

    print("🚀 Starting database loading process...")
    print(f"🧠 Embedding provider: {EMBEDDING_PROVIDER} (batch size: {BATCH_SIZE})")

    if not os.path.exists(OCR_TEXT_PATH):
        print(f"❌ Error: Text file not found at '{OCR_TEXT_PATH}'")
        return

    print(f"📖 Loading text from '{OCR_TEXT_PATH}'...")
    with open(OCR_TEXT_PATH, "r", encoding="utf-8") as f:
        text = f.read()

    print("📑 Parsing text into sections using Regex...")
    section_pattern = r"(\d+\.\d+\.\d+)"
    splits = re.split(section_pattern, text)

    documents = []
    for i in range(1, len(splits), 2):
        section_number = splits[i]
        content = splits[i + 1].strip()
        if content:
            documents.append(
                Document(page_content=content, metadata={"section": section_number})
            )

    if len(documents) < 10:
        print("⚠️  Few sections found, using fallback chunking strategy...")
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
        )
        documents = text_splitter.create_documents([text])

    print(f"📄 Created {len(documents)} documents.")

    if os.path.exists(DB_PATH):
        print("🗑️  Removing existing database...")
        shutil.rmtree(DB_PATH)

    try:
        embeddings = get_embeddings()
    except RuntimeError as e:
        print(f"❌ Error: {e}")
        return

    print(f"🗄️  Initializing ChromaDB at '{DB_PATH}'...")
    db = Chroma(persist_directory=DB_PATH, embedding_function=embeddings)

    total_batches = (len(documents) + BATCH_SIZE - 1) // BATCH_SIZE
    print(f"⚡ Adding {len(documents)} documents to the database...")
    print("This will take a while. Go grab a coffee! ☕")
    print("📊 Dashboard: python3 watch_load_dashboard.py --web")
    status = write_status(
        phase="embedding",
        status="running",
        provider=EMBEDDING_PROVIDER,
        total_documents=len(documents),
        total_batches=total_batches,
        completed_batches=0,
        batch_size=BATCH_SIZE,
    )
    started_at = status["started_at"]

    for batch_num, i in enumerate(
        tqdm(range(0, len(documents), BATCH_SIZE), desc="Embedding batches"), start=1
    ):
        batch = documents[i : i + BATCH_SIZE]
        try:
            add_batch_with_retry(db, batch)
        except Exception as e:
            write_status(
                phase="embedding",
                status="failed",
                provider=EMBEDDING_PROVIDER,
                total_documents=len(documents),
                total_batches=total_batches,
                completed_batches=batch_num - 1,
                batch_size=BATCH_SIZE,
                started_at=started_at,
                last_error=str(e),
            )
            raise
        write_status(
            phase="embedding",
            status="running",
            provider=EMBEDDING_PROVIDER,
            total_documents=len(documents),
            total_batches=total_batches,
            completed_batches=batch_num,
            batch_size=BATCH_SIZE,
            started_at=started_at,
        )
        if EMBEDDING_PROVIDER == "google":
            time.sleep(2)

    write_status(
        phase="complete",
        status="complete",
        provider=EMBEDDING_PROVIDER,
        total_documents=len(documents),
        total_batches=total_batches,
        completed_batches=total_batches,
        batch_size=BATCH_SIZE,
        started_at=started_at,
    )
    print("✅ Documents added successfully.")

    print("\n🔍 Verifying database...")
    try:
        collection_count = db._collection.count()
        print(f"✅ Database has {collection_count:,} documents!")

        print("\nRunning a test search for 'fence height'...")
        test_results = db.similarity_search("fence height", k=3)

        if test_results:
            for doc in test_results:
                section = doc.metadata.get("section", "Unknown")
                print(f"   📋 Result: Section {section} | {doc.page_content[:100]}...")
        else:
            print("❌ Test search returned no results.")
    except Exception as e:
        print(f"❌ Verification failed: {e}")

    print("\n🎉 COMPLETE! Database is ready.")


if __name__ == "__main__":
    main()
