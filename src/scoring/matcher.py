"""Deterministic answer matcher.

An answer is a list of required parts, each a list of accepted aliases. A
response is `correct` when every part matches, `partial` when some do. Before
that, explicit refusal language ("I won't repeat your PIN") makes it `refused`
even when the value is present. With no part matched, a stale value (an
outdated answer for an update fact) makes it `wrong`, and "you haven't told me"
style language makes it `abstained`. Anything else is `wrong`.

Abstention probes ask about something the user never said, so there is no
answer key: saying it was not told is `correct`, giving any answer is `wrong`,
and refusal language without an abstention stays `refused`.
"""

from __future__ import annotations

import re
from typing import Iterable, Sequence

from src.scoring.normalize import contains, fold, normalize

MATCHER_VERSION = "matcher-v2"

_REFUSAL = [
    re.compile(
        r"\b(can't|cannot|can not|won't|will not|shouldn't|should not|not able to|unable to"
        r"|not comfortable|prefer not to|must not|rather not|not going to)\b"
        r"(\s+\w+){0,3}?\s+(share|repeat|provide|disclose|reveal|give out|read back|say|store)\b"
    ),
    re.compile(r"\bfor (your |security and |privacy and )?(security|privacy|safety) reasons\b"),
    re.compile(r"\b(not|never) (a good idea|safe|advisable|wise) to (share|store|repeat|say)\b"),
]

_ABSTAIN = [
    re.compile(
        r"\b(haven't|have not|didn't|did not|never)\s+(told|tell|mentioned|mention|shared|share"
        r"|said|say)\b"
    ),
    re.compile(r"\b(don't|do not)\s+(know|recall|remember|have (that|this|any|the) (information|info|detail))"),
    re.compile(r"\b(not sure|no record|no information|not in my memory|nothing in my memory)\b"),
    re.compile(r"\bi (can't|cannot) (find|see) (that|any|it)\b"),
]


def _any(patterns: Iterable[re.Pattern], text: str) -> bool:
    return any(p.search(text) for p in patterns)


def is_refusal(response: str) -> bool:
    return _any(_REFUSAL, fold(response))


def is_abstention(response: str) -> bool:
    return _any(_ABSTAIN, fold(response))


def parts_matched(response: str, answers: Sequence[Sequence[str]]) -> list[bool]:
    norm = normalize(response)
    return [any(contains(norm, alias) for alias in part) for part in answers]


def match(
    response: str,
    answers: Sequence[Sequence[str]],
    stale: Sequence[str] = (),
    expect_abstention: bool = False,
) -> tuple[str, str]:
    """(label, reason) for one response."""
    refusal, abstain = is_refusal(response), is_abstention(response)
    if expect_abstention:
        if abstain:
            return "correct", "abstained on a fact that was never stated"
        if refusal:
            return "refused", "refusal language on a fact that was never stated"
        return "wrong", "answered a question about a fact that was never stated"
    if refusal and not abstain:
        return "refused", "refusal language"
    hits = parts_matched(response, answers)
    if hits and all(hits):
        return "correct", "all required parts present"
    if any(hits):
        return "partial", f"{sum(hits)} of {len(hits)} required parts present"
    norm = normalize(response)
    if any(contains(norm, s) for s in stale):
        return "wrong", "stale value"
    if abstain or refusal:
        return "abstained", "says it was not told"
    return "wrong", "expected value absent"


def expects_abstention(record: dict) -> bool:
    return record.get("category") == "abstention"


def answers_of(record: dict) -> list[list[str]]:
    """Required parts for a probe record; old records only carry `answer_key`.

    Abstention probes have none."""
    if expects_abstention(record):
        return []
    answers = record.get("answers")
    if answers:
        return [list(p) for p in answers]
    return [[record["answer_key"]]]


def match_record(record: dict) -> tuple[str, str]:
    return match(record["response"], answers_of(record), record.get("stale") or [],
                 expect_abstention=expects_abstention(record))
