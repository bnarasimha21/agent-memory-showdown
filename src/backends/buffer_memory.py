"""Full conversation buffer (baseline): every exchange goes into the prompt."""

from __future__ import annotations

from src.backends.base import BaseMemoryBackend, Retrieval, WriteStats, format_exchange, fingerprint


class BufferMemoryBackend(BaseMemoryBackend):
    name = "buffer"
    stores = "raw turns, all of them; a write is an append (no LLM call, no embedding)"

    def setup(self) -> None:
        self._exchanges: list[tuple[str, str]] = []

    def teardown(self) -> None:
        self._exchanges = []

    def retrieve(self, query: str) -> Retrieval:
        history = "\n".join(format_exchange(h, a) for h, a in self._exchanges)
        return Retrieval(text=history, items=[])

    def write(self, human_message: str, ai_message: str) -> WriteStats:
        self._exchanges.append((human_message, ai_message))
        return WriteStats()

    def memory_fingerprint(self) -> dict:
        messages = [m for h, a in self._exchanges for m in (("human", h), ("ai", a))]
        return fingerprint(len(messages), "messages", messages)
