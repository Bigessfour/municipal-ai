# Import argparse so retrieval quality knobs can be set from the CLI.
import argparse

# Import Path so Python can check whether the local Chroma folder exists.
from pathlib import Path

# Import Chroma so the app can connect to the persisted vector database.
from langchain_chroma import Chroma

# Import StrOutputParser so the LLM response is returned as a plain string.
from langchain_core.output_parsers import StrOutputParser

# Import PromptTemplate so the prompt can use {context} and {question} placeholders.
from langchain_core.prompts import PromptTemplate

# Import LCEL helpers used to assemble the RAG chain.
from langchain_core.runnables import (
    RunnableLambda,
    RunnableParallel,
    RunnablePassthrough,
)

# Import OllamaEmbeddings for vectors and OllamaLLM for local text generation.
from langchain_ollama import OllamaEmbeddings, OllamaLLM

# Store the local Chroma database folder path in one reusable variable.
# This expects a chroma_db/ folder in the current project directory.
DB_PATH = "chroma_db"


def parse_args():
    """Parse Day 3 retrieval-quality CLI options (defaults match the lab baseline)."""
    parser = argparse.ArgumentParser(
        description="El Paso municipal RAG assistant (Day 3 lab + retrieval quality enhancement)."
    )
    parser.add_argument(
        "--k",
        type=int,
        default=3,
        help="Number of chunks to retrieve into the prompt (lab default: 3).",
    )
    parser.add_argument(
        "--search-type",
        choices=("similarity", "mmr"),
        default="similarity",
        help="similarity = lab baseline; mmr = diversify context to reduce near-duplicates.",
    )
    parser.add_argument(
        "--fetch-k",
        type=int,
        default=None,
        help="MMR candidate pool size (default: max(20, k*4)). Ignored for similarity.",
    )
    parser.add_argument(
        "--lambda-mult",
        type=float,
        default=0.5,
        help="MMR relevance vs diversity (0=max diversity, 1=max relevance).",
    )
    return parser.parse_args()


def build_retriever(
    db, search_type: str, k: int, fetch_k: int | None, lambda_mult: float
):
    """Build a Chroma retriever for baseline similarity or MMR."""
    if search_type == "similarity":
        return db.as_retriever(search_type="similarity", search_kwargs={"k": k})

    candidate_k = fetch_k if fetch_k is not None else max(20, k * 4)
    return db.as_retriever(
        search_type="mmr",
        search_kwargs={
            "k": k,
            "fetch_k": candidate_k,
            "lambda_mult": lambda_mult,
        },
    )


def score_map_for_docs(db, question: str, docs):
    """Map content prefixes to similarity distances when using similarity search."""
    if not docs:
        return {}
    scored = db.similarity_search_with_score(question, k=len(docs))
    return {doc.page_content[:80]: score for doc, score in scored}


def print_sources(question: str, docs, db, search_type: str):
    """Print retrieved sources with section metadata and optional scores."""
    print("\n--- Sources ---")
    scores = (
        score_map_for_docs(db, question, docs) if search_type == "similarity" else {}
    )

    for i, doc in enumerate(docs):
        section = doc.metadata.get("section", "N/A")
        prefix = doc.page_content[:80]
        if search_type == "similarity":
            score = scores.get(prefix, "n/a")
            score_text = f"{score:.4f}" if isinstance(score, (int, float)) else score
        else:
            score_text = "n/a (mmr)"

        print(f"{i + 1}. Section: {section} | score/distance: {score_text}")
        print(f"   Content: {doc.page_content[:400]}...")


def main():
    args = parse_args()

    # Print a startup message so the terminal shows that the script began.
    print("🚀 Initializing AI Assistant...")
    print(
        f"Retrieval mode: search_type={args.search_type}, k={args.k}"
        + (
            f", fetch_k={args.fetch_k or max(20, args.k * 4)}, lambda_mult={args.lambda_mult}"
            if args.search_type == "mmr"
            else ""
        )
    )

    # Convert the database folder string into a Path object.
    db_path = Path(DB_PATH)

    # Stop early if the Chroma database folder does not exist.
    if not db_path.exists():
        # Raise a clear error that explains which prerequisite step is missing.
        raise FileNotFoundError(
            f"Could not find {DB_PATH}/. Run the Day 02 Chroma/vector database labs first, "
            f"then run this script from the project root where {DB_PATH}/ exists."
        )

    # Stop early if the path exists but is not a folder.
    if not db_path.is_dir():
        # Raise a clear error if something named chroma_db exists but is not a database folder.
        raise NotADirectoryError(
            f"{DB_PATH} exists, but it is not a folder. Expected a persisted Chroma database directory."
        )

    # Stop early if the folder exists but does not contain database files.
    if not any(db_path.iterdir()):
        # Raise a clear error that explains the database has not been populated yet.
        raise ValueError(
            f"{DB_PATH}/ exists, but it appears to be empty. Re-run the Day 02 Chroma/vector database labs "
            "so documents are embedded and saved locally."
        )

    # Create the embedding model used to turn questions into vectors.
    embeddings = OllamaEmbeddings(model="nomic-embed-text")

    # Connect to the existing Chroma database on disk using the same embeddings.
    db = Chroma(persist_directory=DB_PATH, embedding_function=embeddings)

    # Convert the database into a retriever (lab baseline or MMR enhancement).
    retriever = build_retriever(
        db,
        search_type=args.search_type,
        k=args.k,
        fetch_k=args.fetch_k,
        lambda_mult=args.lambda_mult,
    )

    # Print a section label for the retriever test output.
    print("\n--- Testing the retriever ---")

    # Store a test question that should match content in the knowledge base.
    question = "What is the rule for fence height?"

    # Ask the retriever to find documents related to the test question.
    retrieved_docs = retriever.invoke(question)

    # Print how many documents the retriever returned.
    print(f"✅ Retriever found {len(retrieved_docs)} documents.")

    # Stop early if the retriever did not find any matching documents.
    if not retrieved_docs:
        # Raise a clear error instead of crashing later with retrieved_docs[0].
        raise ValueError(
            "The retriever returned no documents. Check that chroma_db/ contains embedded documents "
            "and that your query matches the source content."
        )

    # Print a label before showing the first retrieved result.
    print("Top result preview:")

    # Print the first 400 characters of the top result for quick inspection.
    print(retrieved_docs[0].page_content[:400])

    # Print a divider so the terminal output is easier to scan.
    print("-" * 25)

    # Store the full prompt text in a multiline string.
    prompt_template = """
You are an expert assistant on El Paso municipal codes. Your task is to answer questions based ONLY on the following context.
If the context does not contain the answer, state that the information is not available in the provided documents.
Do not use any outside knowledge.

CONTEXT:
{context}

QUESTION:
{question}

ANSWER:
"""

    # Convert the prompt text into a LangChain PromptTemplate object.
    prompt = PromptTemplate.from_template(prompt_template)

    # Create the local Ollama LLM that will generate the final answer.
    llm = OllamaLLM(model="llama3")

    # Build the answer chain: prompt -> model -> plain string output.
    answer_chain = prompt | llm | StrOutputParser()

    # Define a helper function that turns retrieved Document objects into prompt text.
    def format_docs(docs):
        # Join each document's page_content with blank lines between chunks.
        return "\n\n".join(doc.page_content for doc in docs)

    # Define a helper function that reads source documents from the chain input.
    def get_context(inputs):
        # Pull the raw retrieved Document objects from the chain dictionary.
        source_documents = inputs["source_documents"]

        # Return only the formatted document text for the prompt's {context} field.
        return format_docs(source_documents)

    # Define a helper function that keeps only the fields the prompt expects.
    def get_answer_inputs(inputs):
        # Return a small dictionary with clean context text and the original question.
        return {
            # Send the formatted document text into the prompt.
            "context": inputs["context"],
            # Send the original user question into the prompt.
            "question": inputs["question"],
        }

    # Build the complete RAG chain in three stages.
    rag_chain = (
        # Stage 1 prepares both raw source documents and the original question.
        RunnableParallel(
            # Use the retriever to turn the question into raw Document objects.
            source_documents=retriever,
            # Pass the original question through without changing it.
            question=RunnablePassthrough(),
            # Stage 2 adds formatted context text for the prompt.
        )
        .assign(
            # Convert raw Document objects into a clean string for {context}.
            context=RunnableLambda(get_context)
            # Stage 3 adds an answer key by running the answer chain.
        )
        .assign(
            # Run the prompt, model, and parser using only context and question.
            answer=RunnableLambda(get_answer_inputs) | answer_chain
        )
    )

    # Print a message showing the app is ready for interactive questions.
    print("\n✅ AI Assistant is ready. Ask a question or type 'exit' to quit.")
    print("Tip: python3 main.py --search-type mmr --k 3   # diversified retrieval")

    # Start an infinite loop so the user can ask multiple questions.
    while True:
        # Read one question from the terminal.
        user_question = input("\nYour question: ")

        # Stop the loop if the user types exit.
        if user_question.lower() == "exit":
            # Leave the while loop.
            break

        # Run the complete RAG chain with the user's question.
        response = rag_chain.invoke(user_question)

        # Print sources with optional similarity scores (retrieval quality enhancement).
        print_sources(user_question, response["source_documents"], db, args.search_type)

        # Print a label before showing the generated answer.
        print("\nAssistant's Answer:")

        # Print the final answer generated from the retrieved context.
        print(response["answer"])


if __name__ == "__main__":
    # Run the main function when the script is executed directly.
    main()
