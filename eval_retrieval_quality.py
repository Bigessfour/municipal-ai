"""Run the three mandatory Day 3 RAG questions under similarity and MMR.

Writes a text report suitable for challenge evidence. Run from municipal-ai/:

    python3 eval_retrieval_quality.py
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

from langchain_chroma import Chroma
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_core.runnables import (
    RunnableLambda,
    RunnableParallel,
    RunnablePassthrough,
)
from langchain_ollama import OllamaEmbeddings, OllamaLLM

from main import build_retriever, print_sources

DB_PATH = "chroma_db"
K = 3

QUESTIONS = [
    ("answerable", "What is the rule for fence height?"),
    ("source_context", "Which ordinance section discusses fence height limits?"),
    ("not_enough_context", "What is the parking fine for hoverboards on Mars?"),
]

PROMPT = PromptTemplate.from_template(
    """
You are an expert assistant on El Paso municipal codes. Your task is to answer questions based ONLY on the following context.
If the context does not contain the answer, state that the information is not available in the provided documents.
Do not use any outside knowledge.

CONTEXT:
{context}

QUESTION:
{question}

ANSWER:
"""
)


def build_chain(retriever, llm):
    answer_chain = PROMPT | llm | StrOutputParser()

    def format_docs(docs):
        return "\n\n".join(doc.page_content for doc in docs)

    def get_context(inputs):
        return format_docs(inputs["source_documents"])

    def get_answer_inputs(inputs):
        return {"context": inputs["context"], "question": inputs["question"]}

    return (
        RunnableParallel(
            source_documents=retriever,
            question=RunnablePassthrough(),
        )
        .assign(context=RunnableLambda(get_context))
        .assign(answer=RunnableLambda(get_answer_inputs) | answer_chain)
    )


def main() -> None:
    if not Path(DB_PATH).is_dir() or not any(Path(DB_PATH).iterdir()):
        raise SystemExit(f"Missing or empty {DB_PATH}/ — run Day 2 load first.")

    out_path = (
        Path(sys.argv[1])
        if len(sys.argv) > 1
        else Path("eval_retrieval_quality_out.txt")
    )

    embeddings = OllamaEmbeddings(model="nomic-embed-text")
    db = Chroma(persist_directory=DB_PATH, embedding_function=embeddings)
    llm = OllamaLLM(model="llama3")

    lines: list[str] = []
    lines.append(f"Day 3 RAG eval — {datetime.now(timezone.utc).isoformat()}")
    lines.append(f"command: python3 eval_retrieval_quality.py {out_path}")
    lines.append(f"docs in chroma: {db._collection.count()}")
    lines.append("")

    def log(msg: str = "") -> None:
        print(msg)
        lines.append(msg)

    for mode in ("similarity", "mmr"):
        retriever = build_retriever(db, mode, K, fetch_k=20, lambda_mult=0.5)
        chain = build_chain(retriever, llm)
        log("=" * 72)
        log(f"MODE={mode} k={K}")
        log("=" * 72)

        for label, question in QUESTIONS:
            log("")
            log(f"[{label}] Q: {question}")
            response = chain.invoke(question)
            # Capture print_sources to stdout and mirror into file.
            print_sources(question, response["source_documents"], db, mode)
            for i, doc in enumerate(response["source_documents"], start=1):
                section = doc.metadata.get("section", "N/A")
                lines.append(f"  source {i}: section={section}")
                lines.append(f"    preview={doc.page_content[:200]!r}...")
            log("Assistant's Answer:")
            log(response["answer"])
            log("-" * 40)

    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\nWrote evidence report: {out_path.resolve()}")


if __name__ == "__main__":
    main()
