"""Backends start from an empty store and clean up after a setup that failed part way."""

import pytest
from qdrant_client import QdrantClient

from src.backends.registry import AVAILABLE_BACKENDS
from src.fakes import FakeMemoryChatModel

pytestmark = pytest.mark.integration

LangGraph = AVAILABLE_BACKENDS["langgraph_store"]
Mem0 = AVAILABLE_BACKENDS["mem0"]


def _collections(config) -> set[str]:
    client = QdrantClient(url=config.QDRANT_URL)
    try:
        return {c.name for c in client.get_collections().collections}
    finally:
        client.close()


def test_langgraph_store_setup_empties_a_namespace_left_by_a_crashed_run(services):
    crashed = LangGraph(llm=FakeMemoryChatModel())
    crashed.setup()
    crashed.write("My dog's name is Baxter.", "Nice!")
    crashed.write("I live in Lisbon.", "Lovely.")
    crashed._conn.close()  # the process died: no teardown ran
    again = LangGraph(llm=FakeMemoryChatModel())
    again.session_id = crashed.session_id
    try:
        again.setup()
        assert again._items() == []
        assert again.memory_fingerprint()["size"] == 0
    finally:
        again.teardown()


def test_langgraph_store_closes_its_connection_when_the_store_cannot_be_built(services, monkeypatch):
    import langgraph.store.postgres as lg

    def broken(*args, **kwargs):
        raise RuntimeError("store constructor failed")

    monkeypatch.setattr(lg, "PostgresStore", broken)
    backend = LangGraph(llm=FakeMemoryChatModel())
    with pytest.raises(RuntimeError, match="constructor failed"):
        backend.setup()
    backend.teardown()
    assert backend._conn.closed


def test_mem0_teardown_removes_the_collection_when_setup_failed_after_creating_it(services, monkeypatch):
    import mem0

    real_init = mem0.Memory.__init__

    def init_then_fail(self, *args, **kwargs):
        real_init(self, *args, **kwargs)
        raise RuntimeError("mem0 init failed after creating its collection")

    monkeypatch.setattr(mem0.Memory, "__init__", init_then_fail)
    backend = Mem0(llm=FakeMemoryChatModel())
    with pytest.raises(RuntimeError, match="after creating"):
        backend.setup()
    assert backend._collection in _collections(services)
    backend.teardown()
    assert backend._collection not in _collections(services)
