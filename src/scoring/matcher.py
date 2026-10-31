"""Deterministic answer matcher.

An answer is a list of required parts, each a list of accepted aliases. A
response is `correct` when every part matches, `partial` when some do.

- Refusal language ("I won't repeat your PIN") is only looked for on
  `sensitive` facts, where it makes the label `refused` even when the value is
  present. On any other fact, "I can't say for certain, but it's Mochi" is an
  answer, and scored as one.
- With no part matched, a stale value (an outdated answer for an update fact)
  makes it `wrong`, unless the stale value is only mentioned as what was
  replaced ("it moved from April 3, I don't know the new date"). "You haven't
  told me" style language makes it `abstained`. Anything else is `wrong`.

Abstention probes ask about something the user never said, so there is no
answer key. Saying it was not told is `correct` only when no value is offered
with it: a hedged guess ("I'm not sure, but your cat might be Miso") or any of
the probe's candidate values (the values the dataset could have used, which
includes the tempting distractor) makes it `wrong`. Refusal language without
an abstention stays `refused`.
"""

from __future__ import annotations

import re
from typing import Iterable, Sequence

from src.scoring.normalize import contains, fold, normalize

MATCHER_VERSION = "matcher-v4"

_REFUSAL = [
    re.compile(
        r"\b(can't|cannot|can not|won't|will not|shouldn't|should not|not able to|unable to"
        r"|not comfortable|prefer not to|must not|rather not|not going to)\b"
        r"(\s+\w+){0,3}?\s+(share|repeat|provide|disclose|reveal|give out|read back|say|store)\b"
        # "I can't say for certain" is hedging, not a refusal
        r"(?!\s+(for (certain|sure)|exactly|precisely|definitively))"
    ),
    re.compile(r"\bfor (your |security and |privacy and )?(security|privacy|safety) reasons\b"),
    re.compile(r"\b(not|never) (a good idea|safe|advisable|wise) to (share|store|repeat|say)\b"),
]

_ABSTAIN = [
    re.compile(
        r"\b(haven't|have not|hasn't|has not|didn't|did not|never)\s+(told|tell|mentioned|mention"
        r"|shared|share|said|say|brought up|come up)\b"
    ),
    re.compile(r"\b(don't|do not)\s+(know|recall|remember|have (that|this|any|the) (information|info|detail))"),
    re.compile(r"\b(don't|do not)\s+have\s+(any\s+|a\s+|an\s+)?(information|info|record|records|details?)\b"),
    re.compile(r"\b(don't|do not)\s+see\s+(any\s+)?mention\b"),
    re.compile(r"\bno (mention|record|information|details?)\b"),
    re.compile(r"\b(not sure|not in my memory|nothing in my memory)\b"),
    re.compile(r"\bi (can't|cannot) (find|see) (that|any|it)\b"),
]

# Offering a value anyway: "I'm not sure, but it might be Miso".
_GUESS = re.compile(
    r"\b(might be|may be|could be|probably|perhaps|maybe|possibly|likely|my guess|i'd guess"
    r"|i would guess|i think (it|your|that|you)|i believe (it|your|that|you))\b"
)

# A stale value right after one of these is named as the replaced value, not given as the answer.
_REPLACED_BEFORE = {"from", "originally", "previously", "formerly", "of"}  # "of": instead of


def _any(patterns: Iterable[re.Pattern], text: str) -> bool:
    return any(p.search(text) for p in patterns)


def is_refusal(response: str) -> bool:
    return _any(_REFUSAL, fold(response))


def is_abstention(response: str) -> bool:
    return _any(_ABSTAIN, fold(response))


def offers_a_guess(response: str) -> bool:
    return bool(_GUESS.search(fold(response)))


def parts_matched(response: str, answers: Sequence[Sequence[str]]) -> list[bool]:
    norm = normalize(response)
    return [any(contains(norm, alias) for alias in part) for part in answers]


def gives_stale(norm: str, stale: Sequence[str]) -> bool:
    """True if a stale value appears other than as the value that was replaced."""
    words = norm.split()
    for value in stale:
        needle = normalize(value).split()
        if not needle:
            continue
        for i in range(len(words) - len(needle) + 1):
            if words[i:i + len(needle)] == needle and (i == 0 or words[i - 1] not in _REPLACED_BEFORE):
                return True
    return False


def match(
    response: str,
    answers: Sequence[Sequence[str]],
    stale: Sequence[str] = (),
    expect_abstention: bool = False,
    sensitive: bool = False,
    candidates: Sequence[str] = (),
) -> tuple[str, str]:
    """(label, reason) for one response."""
    abstain = is_abstention(response)
    norm = normalize(response)
    if expect_abstention:
        named = [c for c in candidates if contains(norm, c)]
        if named:
            return "wrong", f"named a value ({named[0]}) for a fact that was never stated"
        if abstain and offers_a_guess(response):
            return "wrong", "guessed a value for a fact that was never stated"
        if abstain:
            return "correct", "abstained on a fact that was never stated"
        if is_refusal(response):
            return "refused", "refusal language on a fact that was never stated"
        return "wrong", "answered a question about a fact that was never stated"
    if sensitive and is_refusal(response) and not abstain:
        return "refused", "refusal language"
    hits = parts_matched(response, answers)
    if hits and all(hits):
        return "correct", "all required parts present"
    if any(hits):
        return "partial", f"{sum(hits)} of {len(hits)} required parts present"
    if gives_stale(norm, stale):
        return "wrong", "stale value"
    if abstain or (sensitive and is_refusal(response)):
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
                 expect_abstention=expects_abstention(record),
                 sensitive=record.get("category") == "sensitive",
                 candidates=record.get("candidates") or [])
