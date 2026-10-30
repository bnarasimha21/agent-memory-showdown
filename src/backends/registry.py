"""Name -> backend class registry used by the CLI and the tests."""

from __future__ import annotations

from src.backends.buffer_memory import BufferMemoryBackend
from src.backends.pgvector_memory import PGVectorMemoryBackend
from src.backends.qdrant_memory import QdrantMemoryBackend
from src.backends.summary_memory import SummaryMemoryBackend

AVAILABLE_BACKENDS = {
    "buffer": BufferMemoryBackend,
    "summary": SummaryMemoryBackend,
    "qdrant": QdrantMemoryBackend,
    "pgvector": PGVectorMemoryBackend,
}
