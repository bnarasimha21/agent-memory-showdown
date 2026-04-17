"""ConversationBufferMemory backend (baseline)."""

from __future__ import annotations

from langchain.memory import ConversationBufferMemory
from langchain.chains import ConversationChain
from langchain_community.callbacks import get_openai_callback
from src.backends.base import BaseMemoryBackend
from src.llm_factory import get_llm


class BufferMemoryBackend(BaseMemoryBackend):
    name = "buffer"

    def setup(self) -> None:
        self._memory = ConversationBufferMemory(return_messages=True)
        self._chain = ConversationChain(
            llm=get_llm(),
            memory=self._memory,
            verbose=False,
        )

    def teardown(self) -> None:
        self._memory.clear()

    def chat(self, human_message: str) -> tuple[str, int]:
        with get_openai_callback() as cb:
            response = self._chain.predict(input=human_message)
        return response, cb.total_tokens
