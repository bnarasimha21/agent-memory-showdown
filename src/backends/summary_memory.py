"""Running LLM summary: each exchange is folded into one summary by an extra LLM call."""

from __future__ import annotations

from langchain.memory import ConversationSummaryMemory
from langchain_core.messages import HumanMessage

from src.backends.base import (
    BaseMemoryBackend,
    Retrieval,
    WriteStats,
    format_exchange,
    fingerprint,
    usage_from_message,
)


class SummaryMemoryBackend(BaseMemoryBackend):
    name = "summary"

    def setup(self) -> None:
        # Used for its summarizer prompt and as the holder of the summary text.
        self._memory = ConversationSummaryMemory(llm=self.llm)
        self._memory.buffer = ""

    def teardown(self) -> None:
        self._memory.clear()

    def retrieve(self, query: str) -> Retrieval:
        summary = self._memory.buffer
        return Retrieval(text=summary, items=[summary] if summary else [])

    def write(self, human_message: str, ai_message: str) -> WriteStats:
        prompt = self._memory.prompt.format(
            summary=self._memory.buffer,
            new_lines=format_exchange(human_message, ai_message),
        )
        message = self.llm.invoke([HumanMessage(content=prompt)])
        self._memory.buffer = str(message.content).strip()
        in_tok, out_tok = usage_from_message(message)
        return WriteStats(llm_calls=1, input_tokens=in_tok, output_tokens=out_tok)

    def memory_fingerprint(self) -> dict:
        summary = self._memory.buffer
        return fingerprint(len(summary), "summary_chars", [summary])
