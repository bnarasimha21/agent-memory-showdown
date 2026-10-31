"""Mem0 (open source): an LLM extracts facts from each exchange; facts are retrieved by search.

Configured on the benchmark's own infrastructure so the comparison is fair:

- vector store: the compose Qdrant, one collection per session;
- LLM: the same chat model every backend answers with (`get_llm()`, Claude
  via DO Serverless Inference, or the fake model in tests);
- embeddings: the same embedding model as the vector backends;
- history: mem0's SQLite history and message log kept in memory (`:memory:`),
  so nothing is written outside the containers.

mem0 2.x adds memories only (its extraction prompt has no update or delete
step), so a corrected fact leaves both the old and the new memory in the
store. Each `add` is one extraction LLM call; its tokens and time are counted
as the write cost. Search makes no LLM call. mem0's optional hybrid scoring
(BM25 through fastembed, entity boosts through spaCy) is not installed, so
retrieval is semantic search over the extracted memories with `top_k=k`.
The score threshold is set to 0 (mem0 defaults to 0.1) so mem0, like the
other vector backends, always returns its k best matches.

The LLM and the embedder are passed to mem0 through small adapters registered
with mem0's factories, because mem0's own LangChain adapters import the
`langchain` 0.x package, which this project no longer depends on.
"""

from __future__ import annotations

import os
import threading
import time
from pathlib import Path
from typing import Any, Literal, Optional
from urllib.parse import urlparse

from langchain_core.embeddings import Embeddings
from langchain_core.language_models import BaseChatModel
from qdrant_client import QdrantClient

from src.backends.base import BaseMemoryBackend, Retrieval, WriteStats, fingerprint, usage_from_message
from src.config import config
from src.retry import invoke_with_retry

# mem0 reads these when it is first imported: keep its telemetry off unless the
# user opts in, and keep its state directory inside the repo (gitignored).
os.environ.setdefault("MEM0_TELEMETRY", "False")
os.environ.setdefault("MEM0_DIR", str(Path(__file__).resolve().parents[2] / ".cache" / "mem0"))

COLLECTION_PREFIX = "mem_bench_mem0_"
PROVIDER = "ams"
_registered = threading.Lock()
_done = False


class UsageCounter:
    """Calls and tokens of every LLM call mem0 makes through the adapter."""

    def __init__(self) -> None:
        self.calls = 0
        self.input_tokens = 0
        self.output_tokens = 0

    def snapshot(self) -> tuple[int, int, int]:
        return self.calls, self.input_tokens, self.output_tokens


def _llm_adapter_class():
    from mem0.llms.base import LLMBase

    class ChatModelLLM(LLMBase):
        """mem0 LLM backed by a LangChain chat model, counting usage."""

        def __init__(self, config=None):
            super().__init__(config)
            model = getattr(self.config, "model", None)
            if not isinstance(model, BaseChatModel):
                raise ValueError("ChatModelLLM needs a LangChain BaseChatModel as `model`")
            self.chat_model = model
            self.usage: UsageCounter = getattr(model, "_ams_usage", None) or UsageCounter()

        def generate_response(self, messages, response_format=None, tools=None,
                              tool_choice="auto", **kwargs):
            role_map = {"system": "system", "user": "human", "assistant": "ai"}
            lc_messages = [(role_map[m["role"]], m["content"]) for m in messages
                           if m.get("role") in role_map]
            if not lc_messages:
                raise ValueError("No valid messages for the LLM")
            model = self.chat_model
            if tools:
                model = model.bind_tools(tools=tools, tool_choice=tool_choice)
            elif response_format:
                # mem0 asks for {"type": "json_object"} on its extraction and
                # update calls; dropping it lets the model answer in prose.
                model = model.bind(response_format=response_format)
            response, _retries, _ms = invoke_with_retry(model, lc_messages, "mem0 write")
            in_tok, out_tok = usage_from_message(response)
            self.usage.calls += 1
            self.usage.input_tokens += in_tok
            self.usage.output_tokens += out_tok
            if not tools:
                return response.content
            return {
                "content": response.content,
                "tool_calls": [{"name": c["name"], "arguments": c["args"]}
                               for c in response.tool_calls],
            }

    return ChatModelLLM


def _embedder_adapter_class():
    from mem0.embeddings.base import EmbeddingBase

    class LangChainEmbedder(EmbeddingBase):
        """mem0 embedder backed by a LangChain `Embeddings`."""

        def __init__(self, config=None):
            super().__init__(config)
            if not isinstance(self.config.model, Embeddings):
                raise ValueError("LangChainEmbedder needs a LangChain Embeddings as `model`")
            self.model = self.config.model

        def embed(self, text, memory_action: Optional[Literal["add", "search", "update"]] = None):
            return self.model.embed_query(text)

        def embed_batch(self, texts, memory_action=None):
            return self.model.embed_documents(list(texts))

    return LangChainEmbedder


# The adapters are module-level names so mem0's factories can load them by path.
ChatModelLLM: Any = None
LangChainEmbedder: Any = None


def _register() -> None:
    """Point mem0's 'langchain' providers at our adapters (once per process)."""
    global _done, ChatModelLLM, LangChainEmbedder
    with _registered:
        if _done:
            return
        from mem0.utils.factory import EmbedderFactory, LlmFactory

        ChatModelLLM = _llm_adapter_class()
        LangChainEmbedder = _embedder_adapter_class()
        LlmFactory.register_provider("langchain", f"{__name__}.ChatModelLLM")
        EmbedderFactory.provider_to_class["langchain"] = f"{__name__}.LangChainEmbedder"
        _done = True


class Mem0MemoryBackend(BaseMemoryBackend):
    name = "mem0"
    stores = ("LLM-extracted facts, add-only, in Qdrant; every write is an extraction "
              "LLM call plus an embedding per extracted fact")
    uses_k = True

    def setup(self) -> None:
        _register()
        from mem0 import Memory
        from mem0.configs.base import MemoryConfig

        self._collection = f"{COLLECTION_PREFIX}{self.session_id[:8]}"
        self._usage = UsageCounter()
        llm = self.llm
        # The adapter finds the counter on the model object it is given.
        object.__setattr__(llm, "_ams_usage", self._usage)
        url = urlparse(config.QDRANT_URL)
        qdrant = {
            "collection_name": self._collection,
            "embedding_model_dims": config.EMBEDDING_DIMENSION,
            "host": url.hostname,
            "port": url.port or (443 if url.scheme == "https" else 6333),
            "https": url.scheme == "https",
        }
        self._memory = Memory(MemoryConfig(
            vector_store={"provider": "qdrant", "config": qdrant},
            llm={"provider": "langchain", "config": {"model": llm}},
            embedder={"provider": "langchain", "config": {"model": self.embeddings}},
            history_db_path=":memory:",
        ))
        self._client = self._memory.vector_store.client

    def teardown(self) -> None:
        collection = getattr(self, "_collection", None)
        if collection is None:
            return
        memory = getattr(self, "_memory", None)
        # mem0 creates the collection while it initialises, so a setup that
        # failed part way can leave it behind with no Memory to clean it up.
        client = self._client if memory is not None else QdrantClient(url=config.QDRANT_URL)
        try:
            for name in (collection, f"{collection}_entities"):
                if client.collection_exists(name):
                    client.delete_collection(name)
        finally:
            if memory is not None:
                memory.close()
            client.close()

    def retrieve(self, query: str) -> Retrieval:
        before = self._usage.snapshot()
        found = self._memory.search(
            query, top_k=self.k, filters={"user_id": self.session_id}, threshold=0.0
        )
        if self._usage.snapshot() != before:
            raise RuntimeError("mem0 search made an LLM call; its cost would be unaccounted")
        items = [r["memory"] for r in found.get("results", [])]
        return Retrieval(text="\n".join(f"- {m}" for m in items), items=items)

    def write(self, human_message: str, ai_message: str) -> WriteStats:
        calls, in_tok, out_tok = self._usage.snapshot()
        self._memory.add(
            [{"role": "user", "content": human_message},
             {"role": "assistant", "content": ai_message}],
            user_id=self.session_id,
        )
        c2, i2, o2 = self._usage.snapshot()
        return WriteStats(llm_calls=c2 - calls, input_tokens=i2 - in_tok, output_tokens=o2 - out_tok)

    def _points(self) -> list[tuple[str, str]]:
        points, offset = [], None
        while True:
            batch, offset = self._client.scroll(
                self._collection, limit=256, offset=offset, with_payload=True, with_vectors=False
            )
            points.extend(batch)
            if offset is None:
                break
        return sorted((str(p.id), (p.payload or {}).get("data", "")) for p in points)

    def _log_rows(self) -> list:
        """mem0's own message log and history table (in-memory SQLite)."""
        db = self._memory.db
        with db._lock:
            cur = db.connection.cursor()
            rows = []
            for table in ("history", "messages"):
                cur.execute(f"SELECT * FROM {table} ORDER BY rowid")
                rows.append((table, [tuple(r) for r in cur.fetchall()]))
            return rows

    def memory_fingerprint(self) -> dict:
        points = self._points()
        return fingerprint(len(points), "memories", [points, self._log_rows()])
