"""Load the fact bank (data/facts_v2.yaml) and realize templates with a seed.

See the header of the YAML file for the template format. Loading validates
every template, so a malformed bank fails before a run starts rather than in
the middle of one.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import random
import string
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

CATEGORIES = ("extraction", "update", "temporal", "multi_hop", "abstention", "sensitive")
# Reported on their own, never in the headline recall number. Abstention facts are
# never told, so they are probed at every checkpoint; in the headline they made up
# about a third of the probes and a backend that remembered nothing and always
# said "you never told me" scored about 35%. Sensitive facts measure a safety
# behaviour, not memory.
NON_HEADLINE = frozenset({"abstention", "sensitive"})
# How many statements each category needs. None means "one or more".
STATEMENT_COUNT = {"update": 2, "temporal": 2, "multi_hop": 2, "abstention": 0}

DEFAULT_BANK = Path(__file__).resolve().parents[2] / "data" / "facts_v2.yaml"

# Dates without a year in the text; computed in this (non-leap) year.
BASE_YEAR = 2027
_DATE_FIRST = dt.date(BASE_YEAR, 3, 15)
_DATE_LAST = dt.date(BASE_YEAR, 10, 15)


class BankError(ValueError):
    """The fact bank is malformed."""


@dataclass
class FactTemplate:
    id: str
    category: str
    slots: dict[str, Any]
    statements: list[str]
    probe: str
    answer: str | None
    answers: list[list[str]]
    stale: list[str] = field(default_factory=list)
    distractors: list[str] = field(default_factory=list)

    @property
    def headline(self) -> bool:
        return self.category not in NON_HEADLINE


@dataclass
class FactBank:
    version: str
    path: str
    sha256: str
    fact_wrappers: list[str]
    filler_templates: list[str]
    filler_topics: list[str]
    facts: list[FactTemplate]

    def by_category(self, category: str) -> list[FactTemplate]:
        return [f for f in self.facts if f.category == category]


def format_date(value: dt.date) -> str:
    return f"{value.strftime('%B')} {value.day}"


def _fields(template: str) -> set[str]:
    return {name for _, name, _, _ in string.Formatter().parse(template) if name}


def _validate(raw: dict, path: Path) -> FactTemplate:
    where = f"{path.name}: fact {raw.get('id', '?')!r}"
    for key in ("id", "category", "probe"):
        if not raw.get(key):
            raise BankError(f"{where}: missing {key!r}")
    category = raw["category"]
    if category not in CATEGORIES:
        raise BankError(f"{where}: unknown category {category!r} (use one of {CATEGORIES})")
    statements = list(raw.get("statements") or [])
    want = STATEMENT_COUNT.get(category)
    if want is not None and len(statements) != want:
        raise BankError(f"{where}: a {category} fact needs exactly {want} statement(s)")
    if want is None and not statements:
        raise BankError(f"{where}: a {category} fact needs at least one statement")
    answers = [list(p) for p in (raw.get("answers") or [])]
    if category == "abstention":
        if answers or raw.get("answer"):
            raise BankError(f"{where}: an abstention fact has no answer")
    elif not answers or not all(answers) or not raw.get("answer"):
        raise BankError(f"{where}: needs `answer` and non-empty `answers`")
    stale = list(raw.get("stale") or [])
    if stale and category != "update":
        raise BankError(f"{where}: only update facts have stale values")
    if category == "update" and not stale:
        raise BankError(f"{where}: an update fact needs the replaced value in `stale`")
    slots = dict(raw.get("slots") or {})
    known = set(slots) | {f"other_{s}" for s in slots}
    texts = statements + [raw["probe"], raw.get("answer") or ""] + stale
    texts += [a for part in answers for a in part] + list(raw.get("distractors") or [])
    missing = sorted({f for t in texts for f in _fields(t)} - known)
    if missing:
        raise BankError(f"{where}: placeholders without a slot: {missing}")
    return FactTemplate(
        id=raw["id"], category=category, slots=slots, statements=statements,
        probe=raw["probe"], answer=raw.get("answer"), answers=answers, stale=stale,
        distractors=list(raw.get("distractors") or []),
    )


def load_bank(path: str | Path | None = None) -> FactBank:
    path = Path(path) if path else DEFAULT_BANK
    return _load_bank(str(path.resolve()))


@lru_cache(maxsize=8)
def _load_bank(path_str: str) -> FactBank:
    path = Path(path_str)
    data = path.read_bytes()
    raw = yaml.safe_load(data)
    facts = [_validate(f, path) for f in raw.get("facts") or []]
    ids = [f.id for f in facts]
    dupes = sorted({i for i in ids if ids.count(i) > 1})
    if dupes:
        raise BankError(f"{path.name}: duplicate fact ids {dupes}")
    for key in ("fact_wrappers", "filler_templates", "filler_topics"):
        if not raw.get(key):
            raise BankError(f"{path.name}: missing {key!r}")
    return FactBank(
        version=str(raw.get("version", path.stem)), path=str(path),
        sha256=hashlib.sha256(data).hexdigest(),
        fact_wrappers=list(raw["fact_wrappers"]), filler_templates=list(raw["filler_templates"]),
        filler_topics=list(raw["filler_topics"]), facts=facts,
    )


# ---------------------------------------------------------------- realization

def _random_date(rng: random.Random) -> dt.date:
    span = (_DATE_LAST - _DATE_FIRST).days
    return _DATE_FIRST + dt.timedelta(days=rng.randint(0, span))


def _digits(rng: random.Random, n: int) -> str:
    return str(rng.randint(1, 9)) + "".join(str(rng.randint(0, 9)) for _ in range(n - 1))


def _date_value(spec: dict, raw: dict, rng: random.Random, slot: str) -> dt.date:
    if "after" in spec or "before" in spec:
        anchor_name = spec.get("after", spec.get("before"))
        anchor = raw.get(anchor_name)
        if not isinstance(anchor, dt.date):
            raise BankError(f"date slot {slot!r} is relative to {anchor_name!r}, which is not an earlier date slot")
        days = rng.randint(int(spec.get("min_days", 1)), int(spec.get("max_days", 30)))
        return anchor + dt.timedelta(days=days if "after" in spec else -days)
    return _random_date(rng)


def realize_slots(slots: dict[str, Any], rng: random.Random) -> dict[str, str]:
    """Pick a value (and a different `other_` value) for every slot, in order."""
    raw: dict[str, Any] = {}
    other: dict[str, Any] = {}
    for name, spec in slots.items():
        if isinstance(spec, list):
            if not spec:
                raise BankError(f"slot {name!r} has no values")
            raw[name] = rng.choice(spec)
            rest = [v for v in spec if v != raw[name]]
            other[name] = rng.choice(rest) if rest else raw[name]
        elif isinstance(spec, dict) and "digits" in spec:
            n = int(spec["digits"])
            raw[name] = _digits(rng, n)
            other[name] = raw[name]
            while other[name] == raw[name]:
                other[name] = _digits(rng, n)
        elif isinstance(spec, dict) and "date" in spec:
            raw[name] = _date_value(spec["date"] or {}, raw, rng, name)
            shift = rng.randint(5, 60) * rng.choice((-1, 1))
            other[name] = raw[name] + dt.timedelta(days=shift)
        elif isinstance(spec, dict) and "days_between" in spec:
            a, b = spec["days_between"]
            if not (isinstance(raw.get(a), dt.date) and isinstance(raw.get(b), dt.date)):
                raise BankError(f"slot {name!r}: days_between needs two earlier date slots")
            raw[name] = (raw[b] - raw[a]).days
            other[name] = raw[name] + rng.randint(2, 9)
        else:
            raise BankError(f"slot {name!r}: unsupported spec {spec!r}")

    def text(value: Any) -> str:
        return format_date(value) if isinstance(value, dt.date) else str(value)

    values = {k: text(v) for k, v in raw.items()}
    values.update({f"other_{k}": text(v) for k, v in other.items()})
    return values


def fill(template: str, values: dict[str, str]) -> str:
    return template.format_map(values)
