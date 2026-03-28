"""ConversationSummaryMemory backend."""

from __future__ import annotations

from langchain.memory import ConversationSummaryMemory
from langchain.chains import ConversationChain
from src.backends.base import BaseMemoryBackend
from src.llm_factory import get_llm


class SummaryMemoryBackend(BaseMemoryBackend):
    name = "summary"

    def setup(self) -> None:
        llm = get_llm()
        self._memory = ConversationSummaryMemory(
            llm=llm,
            return_messages=True,
        )
        self._chain = ConversationChain(
            llm=llm,
            memory=self._memory,
            verbose=False,
        )

    def teardown(self) -> None:
        self._memory.clear()

    def chat(self, human_message: str) -> tuple[str, int]:
        response = self._chain.predict(input=human_message)
        summary = self._memory.buffer or ""
        tokens = len(summary.split()) // 4 * 5  # rough approximation
        return response, tokens
