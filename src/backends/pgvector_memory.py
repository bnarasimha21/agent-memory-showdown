"""Vector-backed memory using pgvector on PostgreSQL: each exchange is one row, top-k retrieved.

Uses `langchain_postgres.PGVector` (psycopg 3). Its tables are
`langchain_pg_collection` and `langchain_pg_embedding`, the same names the
old `langchain_community` store used but with a different schema, so a
Postgres volume left over from a pre-upgrade run must be recreated
(`docker compose down -v`).
"""

from __future__ import annotations

import psycopg
from langchain_postgres import PGVector

from src.backends.base import (
    BaseMemoryBackend,
    Retrieval,
    WriteStats,
    format_exchange,
    fingerprint,
)
from src.config import config

COLLECTION_PREFIX = "mem_bench_pg_"


class PGVectorMemoryBackend(BaseMemoryBackend):
    name = "pgvector"
    stores = "raw turns, one row per exchange; a write embeds the exchange (no LLM call)"
    uses_k = True

    def setup(self) -> None:
        self._collection = f"{COLLECTION_PREFIX}{self.session_id[:8]}"
        self._store = PGVector(
            embeddings=self.embeddings,
            connection=config.postgres_sqlalchemy_url,
            collection_name=self._collection,
            embedding_length=config.EMBEDDING_DIMENSION,
            pre_delete_collection=True,
            use_jsonb=True,
        )

    def teardown(self) -> None:
        store = getattr(self, "_store", None)
        if store is None:
            return
        try:
            store.delete_collection()
        finally:
            if store._engine is not None:
                store._engine.dispose()

    def retrieve(self, query: str) -> Retrieval:
        # One similarity search and nothing else: retrieve_ms is compared across
        # backends, so no extra round trip (a row count, a connection) belongs here.
        # An empty store simply returns no documents.
        docs = self._store.similarity_search(query, k=self.k)
        items = [d.page_content for d in docs]
        return Retrieval(text="\n\n".join(items), items=items)

    def write(self, human_message: str, ai_message: str) -> WriteStats:
        self._store.add_texts([format_exchange(human_message, ai_message)])
        return WriteStats()

    def _rows(self) -> list[tuple[str, str]]:
        with psycopg.connect(config.postgres_dsn) as conn, conn.cursor() as cur:
            cur.execute(
                "SELECT e.id, e.document FROM langchain_pg_embedding e "
                "JOIN langchain_pg_collection c ON e.collection_id = c.uuid "
                "WHERE c.name = %s ORDER BY e.id",
                (self._collection,),
            )
            return [(str(a), str(b)) for a, b in cur.fetchall()]

    def memory_fingerprint(self) -> dict:
        rows = self._rows()
        return fingerprint(len(rows), "rows", rows)
