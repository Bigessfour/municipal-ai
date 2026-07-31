"""Compare baseline similarity vs MMR retrieval for Day 3 retrieval-quality evidence.

Does not call the LLM — focuses on retrieval sections, scores, and overlap.
Run from municipal-ai/:

    python3 compare_retrieval_quality.py
"""

from __future__ import annotations

from pathlib import Path

from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings

DB_PATH = "chroma_db"
K = 3
FETCH_K = 20
LAMBDA_MULT = 0.5

# Mandatory challenge question set (retrieval side).
QUESTIONS = [
    {
        "label": "answerable",
        "text": "What is the rule for fence height?",
    },
    {
        "label": "source_context",
        "text": "Which ordinance section discusses fence height limits?",
    },
    {
        "label": "not_enough_context",
        "text": "What is the parking fine for hoverboards on Mars?",
    },
]


def prefix(text: str, n: int = 80) -> str:
    return text[:n]


def near_duplicate_pairs(docs, n: int = 60) -> int:
    """Count pairs that share the same leading characters (near-duplicates)."""
    heads = [prefix(d.page_content, n) for d in docs]
    count = 0
    for i in range(len(heads)):
        for j in range(i + 1, len(heads)):
            if heads[i] == heads[j]:
                count += 1
    return count


def main() -> None:
    if not Path(DB_PATH).is_dir() or not any(Path(DB_PATH).iterdir()):
        raise SystemExit(f"Missing or empty {DB_PATH}/ — run Day 2 load first.")

    embeddings = OllamaEmbeddings(model="nomic-embed-text")
    db = Chroma(persist_directory=DB_PATH, embedding_function=embeddings)

    print("=== Retrieval quality comparison: similarity (baseline) vs MMR ===")
    print(f"k={K}, mmr fetch_k={FETCH_K}, lambda_mult={LAMBDA_MULT}")
    print(f"collection size: {db._collection.count()}")
    print()

    for item in QUESTIONS:
        question = item["text"]
        print("=" * 72)
        print(f"[{item['label']}] {question}")
        print("-" * 72)

        scored = db.similarity_search_with_score(question, k=K)
        mmr_docs = db.max_marginal_relevance_search(
            question,
            k=K,
            fetch_k=FETCH_K,
            lambda_mult=LAMBDA_MULT,
        )

        print("BASELINE similarity:")
        for i, (doc, score) in enumerate(scored, start=1):
            section = doc.metadata.get("section", "N/A")
            print(f"  {i}. section={section}  distance={score:.4f}")
            print(f"     preview={doc.page_content[:120]!r}...")

        print("ENHANCED mmr:")
        for i, doc in enumerate(mmr_docs, start=1):
            section = doc.metadata.get("section", "N/A")
            print(f"  {i}. section={section}")
            print(f"     preview={doc.page_content[:120]!r}...")

        baseline_prefixes = {prefix(doc.page_content) for doc, _ in scored}
        mmr_prefixes = {prefix(doc.page_content) for doc in mmr_docs}
        shared = baseline_prefixes & mmr_prefixes
        print(
            f"overlap (shared content prefixes): {len(shared)}/{K} "
            f"({sorted(shared)!r})"
        )
        print(
            f"near-duplicate pairs within baseline: "
            f"{near_duplicate_pairs([d for d, _ in scored])}"
        )
        print(f"near-duplicate pairs within mmr: {near_duplicate_pairs(mmr_docs)}")
        print()


if __name__ == "__main__":
    main()
