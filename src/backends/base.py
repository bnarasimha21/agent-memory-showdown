"""Abstract base class for memory backends."""

from __future__ import annotations

import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class TurnMetrics:
    turn_number: int
    retrieval_latency_ms: float
    tokens_used: int = 0


@dataclass
class RecallResult:
    probe: str
    seeded_at_turn: int
    probed_at_turn: int
    response: str
    score: str  # "correct" | "partial" | "failed"
    answer_key: str


@dataclass
class RunResult:
    backend_name: str
    run_index: int
    session_id: str
    turn_metrics: list[TurnMetrics] = field(default_factory=list)
    recall_results: list[RecallResult] = field(default_factory=list)
    total_tokens: int = 0
    error: Optional[str] = None


class BaseMemoryBackend(ABC):
    name: str

    def __init__(self):
        self.session_id = str(uuid.uuid4())

    @abstractmethod
    def setup(self) -> None:
        """Initialize resources (DB connections, collections, etc.)."""

    @abstractmethod
    def teardown(self) -> None:
        """Clean up session data."""

    @abstractmethod
    def chat(self, human_message: str) -> tuple[str, int]:
        """
        Send a human message, get back (ai_response, tokens_used).
        Latency is measured externally by the harness.
        """

    def timed_chat(self, human_message: str) -> tuple[str, int, float]:
        """Returns (response, tokens, latency_ms)."""
        start = time.perf_counter()
        response, tokens = self.chat(human_message)
        latency_ms = (time.perf_counter() - start) * 1000
        return response, tokens, latency_ms


def score_recall(response: str, answer_key: str) -> str:
    response_lower = response.lower()
    answer_lower = answer_key.lower()

    words = answer_lower.split()
    matches = sum(1 for w in words if w in response_lower)

    if matches == len(words):
        return "correct"
    elif matches > 0:
        return "partial"
    else:
        return "failed"
