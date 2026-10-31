"""Abstract base class for memory backends.

Every backend implements three memory operations:

- `retrieve(query)`: return the memory context for a message, read-only.
- `write(human, ai)`: store a completed exchange.
- `memory_fingerprint()`: size plus a digest of everything stored, used to
  prove that probes do not change memory.

The chat loop itself (`chat` for real turns, `probe` for recall questions) lives
here and is shared, so every backend renders the same prompt from
`src/prompts.py` and is timed the same way. `probe` never calls `write`.
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from typing import Any, Iterable

from langchain_core.embeddings import Embeddings
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage, HumanMessage

from src.prompts import render_chat_prompt
from src.retry import invoke_with_retry

logger = logging.getLogger(__name__)


def usage_from_message(message: BaseMessage) -> tuple[int, int]:
    """(input_tokens, output_tokens) from the message's `usage_metadata`.

    LangChain chat models fill `usage_metadata` from the provider's reported
    usage. A message without it is counted as zero and logged, so a provider
    that stops reporting usage shows up in the log rather than as a silent
    cost of zero.
    """
    usage = getattr(message, "usage_metadata", None)
    if not usage:
        logger.warning("LLM response has no usage_metadata; counting 0 tokens")
        return 0, 0
    return int(usage.get("input_tokens", 0)), int(usage.get("output_tokens", 0))


@dataclass
class Retrieval:
    text: str
    items: list[str] = field(default_factory=list)


@dataclass
class WriteStats:
    llm_calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0


@dataclass
class Exchange:
    """One LLM-backed exchange: a conversation turn or a probe."""

    input: str
    context: str
    context_items: list[str]
    response: str
    input_tokens: int
    output_tokens: int
    retrieve_ms: float
    llm_ms: float
    write_ms: float = 0.0
    write_llm_calls: int = 0
    write_input_tokens: int = 0
    write_output_tokens: int = 0

    def to_dict(self) -> dict:
        return asdict(self)


def fingerprint(size: int, unit: str, payload: Iterable[Any]) -> dict:
    digest = hashlib.sha256()
    for item in payload:
        digest.update(json.dumps(item, sort_keys=True, default=str).encode("utf-8"))
        digest.update(b"\x00")
    return {"size": size, "unit": unit, "digest": digest.hexdigest()}


def backend_label(cls: type, k: int, sweep: bool) -> str:
    """`name@k<k>` for a k-dependent backend in a k sweep, otherwise `name`."""
    return f"{cls.name}@k{k}" if sweep and cls.uses_k else cls.name


class BaseMemoryBackend(ABC):
    name: str
    # What the backend keeps, and what a write costs; shown in the README table.
    stores: str = ""
    # True for backends whose retrieval depth is `k` (swept by `--k`).
    uses_k: bool = False

    def __init__(
        self,
        llm: BaseChatModel | None = None,
        embeddings: Embeddings | None = None,
        k: int | None = None,
    ):
        from src.config import config

        self.session_id = str(uuid.uuid4())
        self._llm = llm
        self._embeddings = embeddings
        self.k = k if k is not None else config.RETRIEVAL_K

    def label(self, sweep: bool = False) -> str:
        """Name used in the bundle: `qdrant`, or `qdrant@k8` in a k sweep."""
        return backend_label(type(self), self.k, sweep)

    @property
    def llm(self) -> BaseChatModel:
        if self._llm is None:
            from src.llm_factory import get_llm

            self._llm = get_llm()
        return self._llm

    @property
    def embeddings(self) -> Embeddings:
        if self._embeddings is None:
            from src.llm_factory import get_embeddings

            self._embeddings = get_embeddings()
        return self._embeddings

    @abstractmethod
    def setup(self) -> None:
        """Initialize resources (DB connections, collections, etc.)."""

    @abstractmethod
    def teardown(self) -> None:
        """Remove everything this session stored."""

    @abstractmethod
    def retrieve(self, query: str) -> Retrieval:
        """Memory context for `query`. Must not modify memory."""

    @abstractmethod
    def write(self, human_message: str, ai_message: str) -> WriteStats:
        """Store one completed exchange."""

    @abstractmethod
    def memory_fingerprint(self) -> dict:
        """{'size', 'unit', 'digest'} describing everything currently stored."""

    def memory_stats(self) -> dict:
        """Store size reported at the end of a run."""
        fp = self.memory_fingerprint()
        return {"size": fp["size"], "unit": fp["unit"]}

    def _call_llm(self, prompt: str) -> tuple[str, int, int, float]:
        message, _retries, llm_ms = invoke_with_retry(self.llm, [HumanMessage(content=prompt)],
                                                      f"{self.name} answer")
        input_tokens, output_tokens = usage_from_message(message)
        content = message.content if isinstance(message.content, str) else str(message.content)
        return content, input_tokens, output_tokens, llm_ms

    def _answer(self, message: str) -> Exchange:
        start = time.perf_counter()
        retrieval = self.retrieve(message)
        retrieve_ms = (time.perf_counter() - start) * 1000
        prompt = render_chat_prompt(retrieval.text, message)
        response, in_tok, out_tok, llm_ms = self._call_llm(prompt)
        return Exchange(
            input=message,
            context=retrieval.text,
            context_items=list(retrieval.items),
            response=response,
            input_tokens=in_tok,
            output_tokens=out_tok,
            retrieve_ms=retrieve_ms,
            llm_ms=llm_ms,
        )

    def chat(self, human_message: str) -> Exchange:
        """A real conversation turn: retrieve, answer, then write to memory."""
        exchange = self._answer(human_message)
        start = time.perf_counter()
        stats = self.write(human_message, exchange.response)
        exchange.write_ms = (time.perf_counter() - start) * 1000
        exchange.write_llm_calls = stats.llm_calls
        exchange.write_input_tokens = stats.input_tokens
        exchange.write_output_tokens = stats.output_tokens
        return exchange

    def probe(self, question: str) -> Exchange:
        """A recall question answered from memory without writing anything back."""
        return self._answer(question)


def format_exchange(human_message: str, ai_message: str) -> str:
    return f"Human: {human_message}\nAI: {ai_message}"

