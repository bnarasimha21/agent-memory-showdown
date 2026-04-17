"""Factory for LLM and embedding instances via DigitalOcean Serverless Inference."""

from __future__ import annotations

from langchain_core.language_models import BaseChatModel
from langchain_core.embeddings import Embeddings
from src.config import config


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
    """Embedding model via DigitalOcean Serverless Inference."""
    from langchain_openai import OpenAIEmbeddings

    return OpenAIEmbeddings(
        model=config.EMBEDDING_MODEL,
        openai_api_key=config.DO_API_KEY,
        openai_api_base=config.DO_INFERENCE_URL,
    )
