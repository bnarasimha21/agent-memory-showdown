"""Deterministic offline stand-ins for the paid LLM and the embedding model.

Selected with `LLM_PROVIDER=fake` and `EMBEDDING_PROVIDER=fake`. They exist so
the whole harness (real backends, real Qdrant and Postgres, real bundles) can be
exercised for free and reproducibly. Numbers produced with them are NOT
benchmark results.

FakeMemoryChatModel answers only from what is in its prompt: for a chat prompt
rendered from `src/prompts.py` it picks, from the human-authored sentences in
the Memory section, the one sharing the most content words with the user's
question (later sentences win ties), and says the user has not told it when
nothing overlaps enough. Recall therefore depends entirely on what the memory
backend put in front of it. It also handles the summarizer prompt (keeps the
most recent first-person sentences, so the summary is lossy), mem0's memory
extraction prompt (each first-person statement in the user's new messages
becomes one memory, unless it is already an existing memory) and the judge
prompt (applies the deterministic matcher, so fake judge and matcher agree).
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import time
from typing import Any, Iterable, List, Optional

from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.embeddings import Embeddings
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult

FAKE_ABSTAIN_REPLY = "You haven't told me that, so I don't know."

STOPWORDS = frozenset(
    """a an the and or but if then so of to in on at by for with from about as into
    is are was were be been being am do does did done have has had having
    i me my mine myself you your yours we our us it its this that these those
    what which who whom whose when where why how there here
    can could would should will shall may might must
    not no yes just also very really too again
    let lets let's s t okay ok anyway wanted share something keep chatting
    i'm i've i'd i'll it's that's don't didn't
    think talk tell said say""".split()
)

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?:])\s+")
_WORD = re.compile(r"[a-z0-9]+(?:'[a-z]+)?")


def content_words(text: str) -> set[str]:
    words = set()
    for w in _WORD.findall(text.lower()):
        if w.endswith("'s"):
            w = w[:-2]
        if w in STOPWORDS or not w:
            continue
        if len(w) > 3 and w.endswith("s") and not w.endswith("ss"):
            w = w[:-1]
        words.add(w)
    return words


def split_sentences(text: str) -> list[str]:
    return [s.strip() for s in _SENTENCE_SPLIT.split(text) if s.strip()]


def _strip_speaker(line: str) -> tuple[str | None, str]:
    m = re.match(r"^\s*(Human|AI|User|Assistant)\s*:\s*(.*)$", line)
    if m:
        return m.group(1), m.group(2)
    return None, line.strip()


def human_sentences(memory_text: str) -> list[str]:
    """Sentences in a memory block that were not written by the assistant."""
    out: list[str] = []
    for line in memory_text.splitlines():
        speaker, body = _strip_speaker(line)
        if speaker in ("AI", "Assistant") or not body:
            continue
        body = re.sub(r"^[-*]\s+", "", body)
        out.extend(split_sentences(body))
    return out


_FIRST_PERSON = re.compile(r"\b(i|i'm|my|me|mine)\b", re.IGNORECASE)


def _is_statement(sentence: str) -> bool:
    return not sentence.rstrip().endswith("?") and bool(_FIRST_PERSON.search(sentence))


def fake_answer(memory_text: str, question: str) -> str:
    q_words = content_words(question)
    if not q_words:
        return FAKE_ABSTAIN_REPLY
    best_score, best = 0, None
    for sentence in human_sentences(memory_text):
        if sentence.rstrip().endswith("?"):
            continue
        score = len(q_words & content_words(sentence))
        if score >= best_score and score > 0:
            best_score, best = score, sentence
    if best is None:
        return FAKE_ABSTAIN_REPLY
    return best


def fake_summary(current_summary: str, new_lines: str, max_sentences: int) -> str:
    kept: list[str] = []
    for s in split_sentences(current_summary) + human_sentences(new_lines):
        if _is_statement(s) and s not in kept:
            kept.append(s)
    return " ".join(kept[-max_sentences:])


def fake_mem0_extraction(new_messages: str, existing: list[str]) -> str:
    """mem0's ADD-only extraction: {"memory": [{"id", "text", "attributed_to"}]}."""
    seen = {e.strip() for e in existing}
    memories: list[str] = []
    for line in new_messages.splitlines():
        role, _, content = line.partition(": ")
        if role != "user":
            continue
        for sentence in split_sentences(content):
            if _is_statement(sentence) and sentence not in seen and sentence not in memories:
                memories.append(sentence)
    return json.dumps({"memory": [
        {"id": str(i), "text": text, "attributed_to": "user"} for i, text in enumerate(memories)
    ]})


def _section(text: str, start: str, end: str | None) -> str:
    """Text between the LAST `start` marker and the next `end` marker."""
    i = text.rfind(start)
    if i < 0:
        return ""
    i += len(start)
    j = text.find(end, i) if end else -1
    return text[i:j] if j >= 0 else text[i:]


class FakeMemoryChatModel(BaseChatModel):
    """Deterministic chat model that can only answer from its prompt."""

    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    sleep_ms: float = 0.0
    summary_max_sentences: int = 8
    model_name: str = "fake-memory-v1"

    @property
    def _llm_type(self) -> str:
        return "fake-memory"

    def respond(self, text: str) -> str:
        if "JUDGE_INPUT_JSON:" in text:
            return self._judge(text)
        if "Memory Extractor" in text and "## New Messages\n" in text:
            new_messages = _section(text, "## New Messages\n", "\n\n## Observation Date")
            raw_existing = _section(text, "## Existing Memories\n", "\n\n## New Messages").strip()
            existing = [m.get("text", "") for m in json.loads(raw_existing or "[]")]
            return fake_mem0_extraction(new_messages, existing)
        if text.rstrip().endswith("New summary:"):
            current = _section(text, "Current summary:", "New lines of conversation:")
            new_lines = _section(text, "New lines of conversation:", "New summary:")
            return fake_summary(current, new_lines, self.summary_max_sentences)
        if "\nUser: " in text and "Memory:" in text:
            head, _, tail = text.rpartition("\nUser: ")
            question = tail.split("\nAssistant:")[0]
            memory = _section(head, "Memory:", None)
            return fake_answer(memory, question)
        return fake_answer("", text)

    @staticmethod
    def _judge(text: str) -> str:
        """Fake judge: applies the deterministic matcher to the judge input."""
        from src.scoring.matcher import match

        raw = text.split("JUDGE_INPUT_JSON:", 1)[1]
        data = json.loads(raw[raw.index("{"): raw.rindex("}") + 1])
        label, reason = match(data["response"], data["required_parts"], data.get("stale_values", []),
                              expect_abstention=bool(data.get("expect_abstention")),
                              sensitive=bool(data.get("sensitive")),
                              candidates=data.get("candidate_values") or [],
                              question=data.get("question") or "")
        return json.dumps({"label": label, "rationale": f"fake judge (matcher rule): {reason}"})

    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs: Any,
    ) -> ChatResult:
        text = "\n".join(
            m.content if isinstance(m.content, str) else json.dumps(m.content) for m in messages
        )
        if self.sleep_ms:
            time.sleep(self.sleep_ms / 1000.0)
        reply = self.respond(text)
        in_tok = self.input_tokens if self.input_tokens is not None else len(text.split())
        out_tok = self.output_tokens if self.output_tokens is not None else len(reply.split())
        usage = {"input_tokens": in_tok, "output_tokens": out_tok, "total_tokens": in_tok + out_tok}
        message = AIMessage(content=reply, usage_metadata=usage)
        return ChatResult(
            generations=[ChatGeneration(message=message)],
            llm_output={
                "token_usage": {
                    "prompt_tokens": in_tok,
                    "completion_tokens": out_tok,
                    "total_tokens": in_tok + out_tok,
                },
                "model_name": self.model_name,
            },
        )


class HashingEmbeddings(Embeddings):
    """Bag-of-content-words feature hashing, L2-normalised. Deterministic.

    Lexical overlap stands in for semantic similarity, which is enough for the
    vector backends to retrieve sensibly in tests without downloading a model.
    """

    def __init__(self, dimension: int = 384) -> None:
        self.dimension = dimension

    def _embed(self, text: str) -> list[float]:
        vec = [0.0] * self.dimension
        for word in content_words(text):
            digest = hashlib.md5(word.encode("utf-8")).digest()
            idx = int.from_bytes(digest[:4], "big") % self.dimension
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vec[idx] += sign
        norm = math.sqrt(sum(v * v for v in vec))
        if norm == 0:
            vec[0] = 1.0
            return vec
        return [v / norm for v in vec]

    def embed_documents(self, texts: Iterable[str]) -> list[list[float]]:
        return [self._embed(t) for t in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._embed(text)
