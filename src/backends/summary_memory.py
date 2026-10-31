"""Running LLM summary: each exchange is folded into one summary by an extra LLM call."""

from __future__ import annotations

from langchain_core.messages import HumanMessage

from src.backends.base import (
    BaseMemoryBackend,
    Retrieval,
    WriteStats,
    format_exchange,
    fingerprint,
    usage_from_message,
)
from src.prompts import render_summary_prompt


class SummaryMemoryBackend(BaseMemoryBackend):
    name = "summary"
    stores = "one running summary; every write is an LLM call that rewrites it"

    def setup(self) -> None:
        self._summary = ""

    def teardown(self) -> None:
        self._summary = ""

    def retrieve(self, query: str) -> Retrieval:
        return Retrieval(text=self._summary, items=[self._summary] if self._summary else [])

    def write(self, human_message: str, ai_message: str) -> WriteStats:
        prompt = render_summary_prompt(self._summary, format_exchange(human_message, ai_message))
        message = self.llm.invoke([HumanMessage(content=prompt)])
        self._summary = str(message.content).strip()
        in_tok, out_tok = usage_from_message(message)
        return WriteStats(llm_calls=1, input_tokens=in_tok, output_tokens=out_tok)

    def memory_fingerprint(self) -> dict:
        return fingerprint(len(self._summary), "summary_chars", [self._summary])
