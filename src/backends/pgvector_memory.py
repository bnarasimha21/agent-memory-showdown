"""Vector-backed memory using pgvector on PostgreSQL: each exchange is one row, top-k retrieved."""

from __future__ import annotations

import psycopg2
from langchain_community.vectorstores import PGVector

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

    def setup(self) -> None:
        self._collection = f"{COLLECTION_PREFIX}{self.session_id[:8]}"
        self._store = PGVector(
            connection_string=config.postgres_sqlalchemy_url,
            embedding_function=self.embeddings,
            collection_name=self._collection,
            pre_delete_collection=True,
        )

    def teardown(self) -> None:
        store = getattr(self, "_store", None)
        if store is not None:
            store.delete_collection()

    def retrieve(self, query: str) -> Retrieval:
        if not self._rows():
            return Retrieval(text="", items=[])
        docs = self._store.similarity_search(query, k=self.k)
        items = [d.page_content for d in docs]
        return Retrieval(text="\n\n".join(items), items=items)

    def write(self, human_message: str, ai_message: str) -> WriteStats:
        self._store.add_texts([format_exchange(human_message, ai_message)])
        return WriteStats()

    def _rows(self) -> list[tuple[str, str]]:
        conn = psycopg2.connect(config.postgres_dsn)
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT e.custom_id, e.document FROM langchain_pg_embedding e "
                    "JOIN langchain_pg_collection c ON e.collection_id = c.uuid "
                    "WHERE c.name = %s ORDER BY e.custom_id",
                    (self._collection,),
                )
                return [(str(a), str(b)) for a, b in cur.fetchall()]
        finally:
            conn.close()

    def memory_fingerprint(self) -> dict:
        rows = self._rows()
        return fingerprint(len(rows), "rows", rows)
