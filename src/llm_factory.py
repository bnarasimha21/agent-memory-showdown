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


def judge_model_id() -> str:
    if config.JUDGE_PROVIDER == "fake":
        return "fake-judge-v1"
    return config.JUDGE_MODEL


def _do_chat_model(model: str) -> BaseChatModel:
    if not config.DO_API_KEY:
        raise RuntimeError(
            "The 'do' provider needs DO_API_KEY in the environment or .env. "
            "Set LLM_PROVIDER=fake (and JUDGE_PROVIDER=fake) for an offline run."
        )
    from langchain_openai import ChatOpenAI

    return ChatOpenAI(
        model=model,
        openai_api_key=config.DO_API_KEY,
        openai_api_base=config.DO_INFERENCE_URL,
        temperature=0.0,
        # src/retry.py does the retrying, so every attempt is counted once
        max_retries=0,
    )


def get_judge_llm() -> BaseChatModel:
    if config.JUDGE_PROVIDER == "fake":
        from src.fakes import FakeMemoryChatModel

        return FakeMemoryChatModel(model_name="fake-judge-v1")
    if config.JUDGE_PROVIDER != "do":
        raise ValueError(f"Unknown JUDGE_PROVIDER {config.JUDGE_PROVIDER!r} (use 'do' or 'fake')")
    return _do_chat_model(config.JUDGE_MODEL)


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
    return _do_chat_model(config.LLM_MODEL)


def get_embeddings() -> Embeddings:
    if config.EMBEDDING_PROVIDER == "fake":
        from src.fakes import HashingEmbeddings

        return HashingEmbeddings(dimension=config.EMBEDDING_DIMENSION)
    if config.EMBEDDING_PROVIDER != "local":
        raise ValueError(
            f"Unknown EMBEDDING_PROVIDER {config.EMBEDDING_PROVIDER!r} (use 'local' or 'fake')"
        )
    from langchain_huggingface import HuggingFaceEmbeddings

    return HuggingFaceEmbeddings(
        model_name=config.EMBEDDING_MODEL,
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )
