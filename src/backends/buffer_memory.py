"""Full conversation buffer (baseline): every exchange goes into the prompt."""

from __future__ import annotations

from langchain.memory import ConversationBufferMemory

from src.backends.base import BaseMemoryBackend, Retrieval, WriteStats, fingerprint


class BufferMemoryBackend(BaseMemoryBackend):
    name = "buffer"

    def setup(self) -> None:
        self._memory = ConversationBufferMemory(human_prefix="Human", ai_prefix="AI")

    def teardown(self) -> None:
        self._memory.clear()

    def retrieve(self, query: str) -> Retrieval:
        history = self._memory.load_memory_variables({})["history"]
        return Retrieval(text=history, items=[])

    def write(self, human_message: str, ai_message: str) -> WriteStats:
        self._memory.save_context({"input": human_message}, {"output": ai_message})
        return WriteStats()

    def memory_fingerprint(self) -> dict:
        messages = self._memory.chat_memory.messages
        return fingerprint(
            len(messages), "messages", [(m.type, m.content) for m in messages]
        )
