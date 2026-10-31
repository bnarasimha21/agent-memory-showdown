"""Vector-backed memory using Qdrant: each exchange is one point, top-k retrieved."""

from __future__ import annotations

from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams

from src.backends.base import (
    BaseMemoryBackend,
    Retrieval,
    WriteStats,
    format_exchange,
    fingerprint,
)
from src.config import config

COLLECTION_PREFIX = "mem_bench_qdrant_"


class QdrantMemoryBackend(BaseMemoryBackend):
    name = "qdrant"
    stores = "raw turns, one point per exchange; a write embeds the exchange (no LLM call)"
    uses_k = True

    def setup(self) -> None:
        self._collection = f"{COLLECTION_PREFIX}{self.session_id[:8]}"
        self._client = QdrantClient(url=config.QDRANT_URL)
        if self._client.collection_exists(self._collection):
            self._client.delete_collection(self._collection)
        self._client.create_collection(
            collection_name=self._collection,
            vectors_config=VectorParams(size=config.EMBEDDING_DIMENSION, distance=Distance.COSINE),
        )
        self._store = QdrantVectorStore(
            client=self._client,
            collection_name=self._collection,
            embedding=self.embeddings,
        )

    def teardown(self) -> None:
        client = getattr(self, "_client", None)
        if client is None:
            return
        try:
            if client.collection_exists(self._collection):
                client.delete_collection(self._collection)
        finally:
            client.close()

    def retrieve(self, query: str) -> Retrieval:
        if self._point_count() == 0:
            return Retrieval(text="", items=[])
        docs = self._store.similarity_search(query, k=self.k)
        items = [d.page_content for d in docs]
        return Retrieval(text="\n\n".join(items), items=items)

    def write(self, human_message: str, ai_message: str) -> WriteStats:
        self._store.add_texts([format_exchange(human_message, ai_message)])
        return WriteStats()

    def _point_count(self) -> int:
        return self._client.count(self._collection, exact=True).count

    def memory_fingerprint(self) -> dict:
        points, offset = [], None
        while True:
            batch, offset = self._client.scroll(
                self._collection, limit=256, offset=offset, with_payload=True, with_vectors=False
            )
            points.extend(batch)
            if offset is None:
                break
        payloads = sorted((str(p.id), p.payload.get("page_content", "")) for p in points)
        return fingerprint(self._point_count(), "points", payloads)
