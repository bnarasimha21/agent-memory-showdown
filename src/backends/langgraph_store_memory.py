"""LangGraph long-term store: `PostgresStore` with a pgvector semantic index.

Each exchange is one item in a namespace that belongs to this session
(`("ams", <session id>)`), indexed on its text with the benchmark's embedding
model; retrieval is the store's semantic `search` with `limit=k`. It runs on
the same Postgres container as the `pgvector` backend. The store's tables
(`store`, `store_vectors`) are shared by every session and created on first
use. Setup deletes anything already in this session's namespace and teardown
deletes this session's items, so the namespace starts and ends empty.

This is what LangGraph's built-in memory does when an agent saves every turn;
it stores raw turns like `qdrant` and `pgvector` and differs in the storage
layer (LangGraph's store API, HNSW index) rather than in what it keeps.
"""

from __future__ import annotations

from psycopg import Connection
from psycopg.rows import dict_row

from src.backends.base import (
    BaseMemoryBackend,
    Retrieval,
    WriteStats,
    format_exchange,
    fingerprint,
)
from src.config import config

NAMESPACE_ROOT = "ams"
PAGE = 500


class LangGraphStoreMemoryBackend(BaseMemoryBackend):
    name = "langgraph_store"
    stores = ("raw turns, one item per exchange in a per-session namespace; "
              "a write embeds the exchange (no LLM call)")
    uses_k = True

    def setup(self) -> None:
        from langgraph.store.postgres import PostgresStore

        self.namespace = (NAMESPACE_ROOT, self.session_id)
        self._conn = Connection.connect(
            config.postgres_dsn, autocommit=True, prepare_threshold=0, row_factory=dict_row
        )
        self._store = PostgresStore(
            self._conn,
            index={
                "dims": config.EMBEDDING_DIMENSION,
                "embed": self.embeddings,
                "fields": ["text"],
                "distance_type": "cosine",
            },
        )
        self._store.setup()
        self._clear()
        self._next = 0

    def _clear(self) -> None:
        for key, _ in self._items():
            self._store.delete(self.namespace, key)

    def teardown(self) -> None:
        # Setup can fail after the connection opened (the store constructor or
        # its migrations raising); the connection is closed either way.
        conn = getattr(self, "_conn", None)
        try:
            if getattr(self, "_store", None) is not None:
                self._clear()
        finally:
            if conn is not None:
                conn.close()

    def retrieve(self, query: str) -> Retrieval:
        hits = self._store.search(self.namespace, query=query, limit=self.k)
        items = [h.value["text"] for h in hits]
        return Retrieval(text="\n\n".join(items), items=items)

    def write(self, human_message: str, ai_message: str) -> WriteStats:
        key = f"{self._next:06d}"
        self._next += 1
        self._store.put(self.namespace, key, {"text": format_exchange(human_message, ai_message)})
        return WriteStats()

    def _items(self) -> list[tuple[str, str]]:
        """Every (key, text) in this session's namespace, without a query."""
        out, offset = [], 0
        while True:
            page = self._store.search(self.namespace, limit=PAGE, offset=offset)
            out.extend((h.key, h.value.get("text", "")) for h in page)
            if len(page) < PAGE:
                break
            offset += PAGE
        return sorted(out)

    def memory_fingerprint(self) -> dict:
        items = self._items()
        return fingerprint(len(items), "items", items)
