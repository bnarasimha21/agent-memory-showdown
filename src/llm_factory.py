"""Factory for LLM and embedding instances.

LLM: Claude via DigitalOcean Serverless Inference (OpenAI-compatible API).
Embeddings: local sentence-transformers (all-MiniLM-L6-v2) to avoid API
            dependency and cost; 384-dim vectors, runs on CPU.
"""

from __future__ import annotations

from langchain_core.language_models import BaseChatModel
from langchain_core.embeddings import Embeddings
from src.config import config

EMBEDDING_DIMENSION = 384


def get_llm() -> BaseChatModel:
    """Claude via DigitalOcean Serverless Inference (OpenAI-compatible API)."""
    from langchain_openai import ChatOpenAI

    return ChatOpenAI(
        model=config.LLM_MODEL,
        openai_api_key=config.DO_API_KEY,
        openai_api_base=config.DO_INFERENCE_URL,
        temperature=0.0,
    )


def get_embeddings() -> Embeddings:
    """Local sentence-transformers embeddings (no API key needed)."""
    from langchain_community.embeddings import HuggingFaceEmbeddings

    return HuggingFaceEmbeddings(
        model_name="all-MiniLM-L6-v2",
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )
