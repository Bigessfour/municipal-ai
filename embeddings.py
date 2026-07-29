"""Shared embedding configuration for load_to_db.py, check_db.py, and Day 3 RAG."""

import os

import boto3
from dotenv import load_dotenv
from langchain_aws import BedrockEmbeddings
from langchain_core.embeddings import Embeddings
from langchain_google_genai import GoogleGenerativeAIEmbeddings

load_dotenv()

DB_PATH = "chroma_db"
EMBEDDING_PROVIDER = os.getenv("EMBEDDING_PROVIDER", "ollama").lower()
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
AWS_PROFILE = os.getenv("AWS_PROFILE", "codeplatoon")
GOOGLE_EMBEDDING_MODEL = "models/gemini-embedding-001"
BEDROCK_EMBEDDING_MODEL = "amazon.titan-embed-text-v2:0"
OLLAMA_EMBEDDING_MODEL = os.getenv("OLLAMA_EMBEDDING_MODEL", "nomic-embed-text")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")


def get_embeddings() -> Embeddings:
    if EMBEDDING_PROVIDER == "google":
        if not os.getenv("GOOGLE_API_KEY"):
            raise RuntimeError(
                "GOOGLE_API_KEY not found in .env (required for EMBEDDING_PROVIDER=google)"
            )
        return GoogleGenerativeAIEmbeddings(model=GOOGLE_EMBEDDING_MODEL)

    if EMBEDDING_PROVIDER == "bedrock":
        session = boto3.Session(profile_name=AWS_PROFILE, region_name=AWS_REGION)
        client = session.client("bedrock-runtime")
        return BedrockEmbeddings(client=client, model_id=BEDROCK_EMBEDDING_MODEL)

    if EMBEDDING_PROVIDER == "ollama":
        from langchain_ollama import OllamaEmbeddings

        return OllamaEmbeddings(
            model=OLLAMA_EMBEDDING_MODEL,
            base_url=OLLAMA_BASE_URL,
        )

    raise RuntimeError(
        f"Unknown EMBEDDING_PROVIDER={EMBEDDING_PROVIDER!r}. Use: ollama, bedrock, or google"
    )
