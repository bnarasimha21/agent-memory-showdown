"""Vector-backed memory using Qdrant."""

from __future__ import annotations

import uuid
from langchain.memory import VectorStoreRetrieverMemory
from langchain.chains import ConversationChain
from langchain_community.vectorstores import Qdrant
from langchain_core.prompts import PromptTemplate
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams
from src.backends.base import BaseMemoryBackend
from src.llm_factory import get_llm, get_embeddings
from src.config import config

COLLECTION_PREFIX = "mem_bench_qdrant_"

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


class QdrantMemoryBackend(BaseMemoryBackend):
    name = "qdrant"

    def setup(self) -> None:
        self._collection = f"{COLLECTION_PREFIX}{self.session_id[:8]}"
        self._client = QdrantClient(url=config.QDRANT_URL)
        self._embeddings = get_embeddings()

        # Create a fresh collection for this session
        self._client.recreate_collection(
            collection_name=self._collection,
            vectors_config=VectorParams(size=384, distance=Distance.COSINE),
        )

        vectorstore = Qdrant(
            client=self._client,
            collection_name=self._collection,
            embeddings=self._embeddings,
        )
        retriever = vectorstore.as_retriever(search_kwargs={"k": 4})
        self._memory = VectorStoreRetrieverMemory(retriever=retriever)
        self._chain = ConversationChain(
            llm=get_llm(),
            memory=self._memory,
            prompt=MEMORY_PROMPT,
            verbose=False,
        )

    def teardown(self) -> None:
        try:
            self._client.delete_collection(self._collection)
        except Exception:
            pass

    def chat(self, human_message: str) -> tuple[str, int]:
        response = self._chain.predict(input=human_message)
        tokens = len(human_message.split()) + len(response.split())
        return response, tokens
