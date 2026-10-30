"""Factory for LLM and embedding instances.

LLM:        `LLM_PROVIDER=do` (default) is Claude via DigitalOcean Serverless
            Inference (OpenAI-compatible API, paid). `LLM_PROVIDER=fake` is the
            deterministic offline model in src/fakes.py (free, for tests).
Embeddings: `EMBEDDING_PROVIDER=local` (default) is sentence-transformers on CPU
            (all-MiniLM-L6-v2, 384-dim). `EMBEDDING_PROVIDER=fake` is a
            deterministic hashing embedding of the same dimension.
"""

from __future__ import annotations

from langchain_core.embeddings import Embeddings
from langchain_core.language_models import BaseChatModel

from src.config import config


def llm_model_id() -> str:
    """The model id recorded in manifests and used for pricing lookups."""
    if config.LLM_PROVIDER == "fake":
        return "fake-memory-v1"
    return config.LLM_MODEL


def embedding_model_id() -> str:
    if config.EMBEDDING_PROVIDER == "fake":
        return f"fake-hashing-{config.EMBEDDING_DIMENSION}"
    return config.EMBEDDING_MODEL


def get_llm() -> BaseChatModel:
    if config.LLM_PROVIDER == "fake":
        from src.fakes import FakeMemoryChatModel

        return FakeMemoryChatModel(
            input_tokens=config.FAKE_LLM_INPUT_TOKENS,
            output_tokens=config.FAKE_LLM_OUTPUT_TOKENS,
            sleep_ms=config.FAKE_LLM_SLEEP_MS,
            summary_max_sentences=config.FAKE_SUMMARY_MAX_SENTENCES,
        )
    if config.LLM_PROVIDER != "do":
        raise ValueError(f"Unknown LLM_PROVIDER {config.LLM_PROVIDER!r} (use 'do' or 'fake')")
    if not config.DO_API_KEY:
        raise RuntimeError(
            "LLM_PROVIDER=do needs DO_API_KEY in the environment or .env. "
            "Set LLM_PROVIDER=fake for an offline run."
        )
    from langchain_openai import ChatOpenAI

    return ChatOpenAI(
        model=config.LLM_MODEL,
        openai_api_key=config.DO_API_KEY,
        openai_api_base=config.DO_INFERENCE_URL,
        temperature=0.0,
    )


def get_embeddings() -> Embeddings:
    if config.EMBEDDING_PROVIDER == "fake":
        from src.fakes import HashingEmbeddings

        return HashingEmbeddings(dimension=config.EMBEDDING_DIMENSION)
    if config.EMBEDDING_PROVIDER != "local":
        raise ValueError(
            f"Unknown EMBEDDING_PROVIDER {config.EMBEDDING_PROVIDER!r} (use 'local' or 'fake')"
        )
    from langchain_community.embeddings import HuggingFaceEmbeddings

    return HuggingFaceEmbeddings(
        model_name=config.EMBEDDING_MODEL,
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )
