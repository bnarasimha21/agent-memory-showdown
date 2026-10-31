"""Generate one run's conversation from the fact bank and the run seed.

The seed decides which templates are used (per category, in the counts given by
the composition), their slot values, the turns their statements land on, the
distractor turns and the filler. The same seed and composition give the same
dataset; different seeds give different values and positions.

Every turn is a real conversation turn. Checkpoints are separate: after
checkpoint turn N completes, every fact that is ready by turn N is probed
against a read-only snapshot of memory. A fact is ready once its last statement
has been made (an update fact once its correction has been made; an abstention
fact, which is never stated, from the start).
"""

from __future__ import annotations

import logging
import random
from dataclasses import asdict, dataclass, field
from typing import Optional

from src.dataset.bank import CATEGORIES, FactBank, fill, load_bank, realize_slots

logger = logging.getLogger(__name__)

DEFAULT_CHECKPOINTS = [15, 25, 35, 50]

DEFAULT_COMPOSITION = {
    "extraction": 3,
    "update": 2,
    "temporal": 1,
    "multi_hop": 1,
    "abstention": 2,
    "sensitive": 2,
}


def parse_composition(text: str) -> dict[str, int]:
    """'extraction=3,update=2' -> {'extraction': 3, 'update': 2, others: 0}."""
    out = {c: 0 for c in CATEGORIES}
    for item in filter(None, (s.strip() for s in text.split(","))):
        name, sep, count = item.partition("=")
        name = name.strip()
        if not sep or name not in CATEGORIES:
            raise ValueError(f"bad fact count {item!r}: use category=N with category in {CATEGORIES}")
        out[name] = int(count)
        if out[name] < 0:
            raise ValueError(f"bad fact count {item!r}: must be >= 0")
    return out


@dataclass
class Statement:
    turn: int
    text: str


@dataclass
class Turn:
    turn_number: int
    human_message: str
    fact_id: Optional[str] = None
    kind: str = "filler"  # fact | distractor | filler


@dataclass
class Fact:
    """A realized fact. `turn` is the turn after which it can be probed.

    `answers` lists the required parts of a correct answer, each a list of
    accepted aliases (matched after src/scoring/normalize.py); `stale` lists
    replaced values that make an answer wrong. Abstention facts have no
    `answer_key` and no `answers`: the correct response says it was not told.
    """

    id: str
    category: str
    turn: int
    probe: str
    answer_key: Optional[str]
    answers: list[list[str]] = field(default_factory=list)
    stale: list[str] = field(default_factory=list)
    statements: list[Statement] = field(default_factory=list)
    headline: bool = True
    values: dict[str, str] = field(default_factory=dict)

    @property
    def expect_abstention(self) -> bool:
        return self.category == "abstention"


@dataclass
class ConversationDataset:
    seed: int
    turns: list[Turn] = field(default_factory=list)
    facts: list[Fact] = field(default_factory=list)
    checkpoints: list[int] = field(default_factory=list)
    composition: dict[str, int] = field(default_factory=dict)
    bank_version: str = ""
    bank_sha256: str = ""

    def probes_at(self, checkpoint: int) -> list[Fact]:
        """Facts ready on or before this checkpoint turn."""
        return [f for f in self.facts if f.turn <= checkpoint]

    def expected_probe_counts(self) -> dict[str, int]:
        """Probes per category this dataset produces over all its checkpoints."""
        counts = {c: 0 for c in self.composition}
        for cp in self.checkpoints:
            for f in self.probes_at(cp):
                counts[f.category] = counts.get(f.category, 0) + 1
        return counts

    def to_dict(self) -> dict:
        return asdict(self)


MAX_VALUE_DRAWS = 200


def list_values(template, values: dict[str, str]) -> set[str]:
    """Case-folded values a fact drew for its list slots, and for their `other_` (distractor) values."""
    names = [n for n, spec in template.slots.items() if isinstance(spec, list)]
    return {values[key].casefold() for n in names for key in (n, f"other_{n}")}


def generate_dataset(
    num_turns: int = 50,
    checkpoints: list[int] | None = None,
    random_seed: int = 42,
    composition: dict[str, int] | None = None,
    distractors: bool = True,
    bank: FactBank | None = None,
) -> ConversationDataset:
    bank = bank or load_bank()
    composition = dict(DEFAULT_COMPOSITION if composition is None else composition)
    unknown = sorted(set(composition) - set(CATEGORIES))
    if unknown:
        raise ValueError(f"unknown fact categories {unknown}")
    if checkpoints is None:
        checkpoints = DEFAULT_CHECKPOINTS
    beyond = sorted(c for c in checkpoints if c > num_turns or c < 1)
    if beyond:
        logger.warning("Checkpoints %s are outside 1..%d; ignoring them", beyond, num_turns)

    rng = random.Random(random_seed)
    dataset = ConversationDataset(
        seed=random_seed, composition=composition,
        bank_version=bank.version, bank_sha256=bank.sha256,
    )
    dataset.checkpoints = sorted({c for c in checkpoints if 1 <= c <= num_turns})

    # 1. Which templates, with which values. Two facts may not draw the same
    # list value (flight_date and deadline_before_trip both pick a city: "my
    # flight to Tokyo" and "my trip to Tokyo" would have two right dates), and
    # that includes the values their distractors use.
    chosen = []
    used: set[str] = set()
    for category in CATEGORIES:
        count = composition.get(category, 0)
        pool = bank.by_category(category)
        if count > len(pool):
            raise ValueError(f"{count} {category} facts requested but the bank has {len(pool)}")
        for template in rng.sample(pool, count):
            for _ in range(MAX_VALUE_DRAWS):
                values = realize_slots(template.slots, rng)
                mine = list_values(template, values)
                if not mine & used:
                    break
            else:
                raise ValueError(
                    f"{template.id}: no draw of its values in {MAX_VALUE_DRAWS} tries avoids the values "
                    f"other facts in this dataset already use ({sorted(mine & used)}); give its slots "
                    "more values")
            used |= mine
            chosen.append((template, values))

    # 2. Statement turns: all before the last checkpoint, so every fact is probed.
    last = dataset.checkpoints[-1] if dataset.checkpoints else num_turns
    needed = sum(len(t.statements) for t, _ in chosen)
    if needed > last:
        raise ValueError(f"{needed} fact statements do not fit in turns 1..{last}")
    statement_turns = rng.sample(range(1, last + 1), needed)
    messages: dict[int, Turn] = {}
    cursor = 0
    for template, values in chosen:
        mine = sorted(statement_turns[cursor:cursor + len(template.statements)])
        cursor += len(template.statements)
        statements = []
        for index, (turn, text) in enumerate(zip(mine, template.statements)):
            sentence = fill(text, values)
            wrapper = rng.choice(bank.fact_wrappers) if index == 0 else "{text}"
            messages[turn] = Turn(turn, wrapper.format(text=sentence), template.id, "fact")
            statements.append(Statement(turn, sentence))
        dataset.facts.append(Fact(
            id=template.id, category=template.category,
            turn=mine[-1] if mine else 0,
            probe=fill(template.probe, values),
            answer_key=fill(template.answer, values) if template.answer else None,
            answers=[[fill(a, values) for a in part] for part in template.answers],
            stale=[fill(s, values) for s in template.stale],
            statements=statements, headline=template.headline, values=values,
        ))

    # 3. Distractors: same kind of thing, different value, anywhere in the conversation.
    if distractors:
        wanted = [(t, v) for t, v in chosen if t.distractors]
        free = [n for n in range(1, num_turns + 1) if n not in messages]
        if len(wanted) > len(free):
            raise ValueError(f"{len(wanted)} distractors do not fit in {len(free)} free turns")
        for (template, values), turn in zip(wanted, rng.sample(free, len(wanted))):
            text = fill(rng.choice(template.distractors), values)
            messages[turn] = Turn(turn, text, None, "distractor")

    # 4. Filler for every other turn.
    topics = bank.filler_topics.copy()
    rng.shuffle(topics)
    filler_index = 0
    for n in range(1, num_turns + 1):
        if n in messages:
            dataset.turns.append(messages[n])
            continue
        topic = topics[filler_index % len(topics)]
        filler_index += 1
        template = rng.choice(bank.filler_templates)
        dataset.turns.append(Turn(n, template.format(topic=topic)))

    dataset.facts.sort(key=lambda f: (f.turn, f.id))
    return dataset
