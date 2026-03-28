"""ConversationBufferMemory backend (baseline)."""

from __future__ import annotations

import os
from langchain.memory import ConversationBufferMemory
from langchain.chains import ConversationChain
from langchain_core.messages import get_buffer_string
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
        response = self._chain.predict(input=human_message)
        # Estimate tokens from memory buffer length
        buffer_text = get_buffer_string(self._memory.chat_memory.messages)
        tokens = len(buffer_text.split()) // 4 * 5  # rough approximation
        return response, tokens
