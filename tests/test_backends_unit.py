"""In-process backends (buffer, summary) with the fake LLM: probe isolation and shared prompt."""

import pytest
from langchain_core.messages import HumanMessage

from src.backends.base import BaseMemoryBackend
from src.backends.registry import AVAILABLE_BACKENDS
from src.fakes import FakeMemoryChatModel
from src.prompts import CHAT_TEMPLATE, render_chat_prompt


class RecordingFake(FakeMemoryChatModel):
    prompts: list = []

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        self.prompts.append(messages[-1].content)
        return super()._generate(messages, stop, run_manager, **kwargs)


@pytest.mark.parametrize("name", ["buffer", "summary"])
def test_probe_does_not_change_memory_but_chat_does(name):
    backend = AVAILABLE_BACKENDS[name](llm=FakeMemoryChatModel())
    backend.setup()
    backend.chat("I wanted to share something with you: My dog's name is Baxter.")
    before = backend.memory_fingerprint()
    exchange = backend.probe("What is my dog's name?")
    assert "Baxter" in exchange.response
    assert backend.memory_fingerprint() == before
    backend.chat("I went hiking in the hills last weekend.")
    assert backend.memory_fingerprint() != before
    backend.teardown()


def test_all_backends_share_the_chat_loop():
    for cls in AVAILABLE_BACKENDS.values():
        assert cls.chat is BaseMemoryBackend.chat
        assert cls.probe is BaseMemoryBackend.probe
        assert cls._answer is BaseMemoryBackend._answer


@pytest.mark.parametrize("name", ["buffer", "summary"])
def test_backend_prompts_use_the_shared_template(name):
    llm = RecordingFake()
    llm.prompts = []
    backend = AVAILABLE_BACKENDS[name](llm=llm)
    backend.setup()
    ex = backend.chat("My dog's name is Baxter.")
    ex2 = backend.probe("What is my dog's name?")
    chat_prompts = [p for p in llm.prompts if not p.rstrip().endswith("New summary:")]
    assert chat_prompts[0] == render_chat_prompt(ex.context, ex.input)
    assert chat_prompts[-1] == render_chat_prompt(ex2.context, ex2.input)
    prefix = CHAT_TEMPLATE.split("{history}")[0]
    assert all(p.startswith(prefix) for p in chat_prompts)


def test_summary_write_counts_the_summarizer_call():
    backend = AVAILABLE_BACKENDS["summary"](llm=FakeMemoryChatModel(input_tokens=5, output_tokens=2))
    backend.setup()
    ex = backend.chat("My dog's name is Baxter.")
    assert ex.write_llm_calls == 1
    assert (ex.write_input_tokens, ex.write_output_tokens) == (5, 2)
    assert (ex.input_tokens, ex.output_tokens) == (5, 2)
    assert "Baxter" in backend.retrieve("x").text


class _OneSearchStore:
    """Stands in for the vector store; counts similarity searches."""

    def __init__(self):
        self.searches = 0

    def similarity_search(self, query, k):
        from langchain_core.documents import Document

        self.searches += 1
        return [Document(page_content="Human: hi\nAI: hello")][:k]


class _NoCalls:
    def __getattr__(self, name):
        raise AssertionError(f"retrieve made an extra call: client.{name}")


@pytest.mark.parametrize("name", ["qdrant", "pgvector"])
def test_vector_retrieve_is_one_search_and_nothing_else(name, monkeypatch):
    """retrieve_ms is compared across backends: no row count or new connection inside it."""
    import psycopg

    def no_connect(*args, **kwargs):
        raise AssertionError("retrieve opened a database connection")

    monkeypatch.setattr(psycopg, "connect", no_connect)
    backend = AVAILABLE_BACKENDS[name](llm=FakeMemoryChatModel(), k=3)
    backend._store = _OneSearchStore()
    backend._client = _NoCalls()
    backend._collection = "unused"
    result = backend.retrieve("what did I say?")
    assert backend._store.searches == 1
    assert result.items == ["Human: hi\nAI: hello"]
