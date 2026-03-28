"""Vector-backed memory using pgvector on PostgreSQL."""

from __future__ import annotations

import psycopg2
import numpy as np
from langchain.memory import VectorStoreRetrieverMemory
from langchain.chains import ConversationChain
from langchain_community.vectorstores import PGVector
from langchain_core.prompts import PromptTemplate
from src.backends.base import BaseMemoryBackend
from src.llm_factory import get_llm, get_embeddings
from src.config import config

MEMORY_PROMPT = PromptTemplate(
    input_variables=["history", "input"],
    template=(
        "The following is a friendly conversation between a human and an AI. "
        "The AI uses the relevant memory snippets below to answer accurately.\n\n"
        "Relevant memory:\n{history}\n\n"
        "Human: {input}\n"
        "AI:"
    ),
)


class PGVectorMemoryBackend(BaseMemoryBackend):
    name = "pgvector"

    def setup(self) -> None:
        self._collection = f"mem_bench_pg_{self.session_id[:8]}"
        self._embeddings = get_embeddings()

        self._vectorstore = PGVector(
            connection_string=config.postgres_dsn,
            embedding_function=self._embeddings,
            collection_name=self._collection,
            pre_delete_collection=True,
        )
        retriever = self._vectorstore.as_retriever(search_kwargs={"k": 4})
        self._memory = VectorStoreRetrieverMemory(retriever=retriever)
        self._chain = ConversationChain(
            llm=get_llm(),
            memory=self._memory,
            prompt=MEMORY_PROMPT,
            verbose=False,
        )

    def teardown(self) -> None:
        try:
            self._vectorstore.delete_collection()
        except Exception:
            pass

    def chat(self, human_message: str) -> tuple[str, int]:
        response = self._chain.predict(input=human_message)
        tokens = len(human_message.split()) + len(response.split())
        return response, tokens
