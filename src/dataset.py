"""Synthetic conversation dataset: seeded facts plus filler, probed at checkpoints.

Every turn is a real conversation turn. Checkpoints are a separate list: after
checkpoint turn N completes, every fact planted at a turn <= N is probed
against a read-only snapshot of memory (see `BaseMemoryBackend.probe`).
A checkpoint may coincide with a seed turn; the fact planted on that turn is
then probed too.
"""

from __future__ import annotations

import logging
import random
from dataclasses import asdict, dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)

SEEDED_FACTS = {
    1: {
        "id": "dog_name",
        "fact": "My dog's name is Baxter.",
        "probe": "What is my dog's name?",
        "answer_key": "baxter",
        "answers": [["baxter"]],
    },
    3: {
        "id": "allergy",
        "fact": "I'm allergic to shellfish.",
        "probe": "What food am I allergic to?",
        "answer_key": "shellfish",
        "answers": [["shellfish"]],
    },
    7: {
        "id": "flight_date",
        "fact": "My flight to Tokyo is on March 15th.",
        "probe": "When is my flight to Tokyo?",
        "answer_key": "march 15",
        "answers": [["march 15"]],
    },
    12: {
        "id": "project_deadline",
        "fact": "The project deadline is April 30th.",
        "probe": "When is the project deadline?",
        "answer_key": "april 30",
        "answers": [["april 30"]],
    },
    18: {
        "id": "wedding_location",
        "fact": "My sister's wedding is in Lake Como, Italy.",
        "probe": "Where is my sister's wedding?",
        "answer_key": "lake como",
        "answers": [["lake como", "como"]],
    },
    25: {
        "id": "current_book",
        "fact": "I'm reading 'Gödel, Escher, Bach' by Douglas Hofstadter.",
        "probe": "What book am I currently reading?",
        "answer_key": "gödel, escher, bach",
        "answers": [["gödel, escher, bach", "geb"]],
    },
    30: {
        "id": "wifi_password",
        "fact": "My home Wi-Fi password is 'sunkist-mango-42'.",
        "probe": "What is my home Wi-Fi password?",
        "answer_key": "sunkist-mango-42",
        "answers": [["sunkist-mango-42"]],
    },
    35: {
        "id": "melatonin_dose",
        "fact": "I take 10 mg of melatonin every night before bed.",
        "probe": "What supplement do I take before bed and at what dose?",
        "answer_key": "melatonin, 10 mg",
        "answers": [["melatonin"], ["10 mg", "10 milligrams"]],
    },
    40: {
        "id": "best_friend",
        "fact": "My childhood best friend's name is Priya Sharma.",
        "probe": "What is my childhood best friend's name?",
        "answer_key": "priya sharma",
        "answers": [["priya"], ["sharma"]],
    },
    45: {
        "id": "bank_pin",
        "fact": "My bank PIN is 7294.",
        "probe": "What is my bank PIN?",
        "answer_key": "7294",
        "answers": [["7294"]],
    },
}

FILLER_TOPICS = [
    "the weather in different cities",
    "a recent movie they watched",
    "their weekend plans",
    "a book recommendation",
    "cooking tips for pasta",
    "differences between Python and JavaScript",
    "tips for better sleep",
    "hiking trail recommendations",
    "the best podcasts to listen to",
    "strategies for learning a new language",
    "home office ergonomics",
    "the latest smartphone features",
    "vegetarian recipes",
    "time management strategies",
    "popular board games",
    "meditation techniques",
    "travel bucket list destinations",
    "gardening advice",
    "financial budgeting tips",
    "sports highlights",
    "the future of AI assistants",
    "favorite childhood memories",
    "electric vehicle pros and cons",
    "best coffee brewing methods",
    "work-life balance tips",
    "streaming service recommendations",
    "space exploration milestones",
    "local restaurant recommendations",
    "DIY home improvement ideas",
    "music playlists for focus",
]

DEFAULT_CHECKPOINTS = [15, 25, 35, 50]


@dataclass
class Turn:
    turn_number: int
    human_message: str
    fact_id: Optional[str] = None


@dataclass
class Fact:
    """A planted fact. `answers` lists the required parts of a correct answer,
    each as a list of accepted aliases (matched after src/scoring/normalize.py);
    `stale` lists outdated values that make an answer wrong."""

    id: str
    turn: int
    fact: str
    probe: str
    answer_key: str
    answers: list[list[str]] = field(default_factory=list)
    stale: list[str] = field(default_factory=list)


@dataclass
class ConversationDataset:
    seed: int
    turns: list[Turn] = field(default_factory=list)
    facts: list[Fact] = field(default_factory=list)
    checkpoints: list[int] = field(default_factory=list)

    def probes_at(self, checkpoint: int) -> list[Fact]:
        """Facts planted on or before this checkpoint turn."""
        return [f for f in self.facts if f.turn <= checkpoint]

    def to_dict(self) -> dict:
        return asdict(self)


def generate_dataset(
    num_turns: int = 50,
    seed_turns: list[int] | None = None,
    checkpoints: list[int] | None = None,
    random_seed: int = 42,
) -> ConversationDataset:
    if seed_turns is None:
        seed_turns = sorted(SEEDED_FACTS)
    if checkpoints is None:
        checkpoints = DEFAULT_CHECKPOINTS

    unknown = [t for t in seed_turns if t not in SEEDED_FACTS]
    if unknown:
        logger.warning("No seeded fact defined for turns %s; ignoring them", unknown)
    beyond = sorted(c for c in checkpoints if c > num_turns or c < 1)
    if beyond:
        logger.warning("Checkpoints %s are outside 1..%d; ignoring them", beyond, num_turns)

    rng = random.Random(random_seed)
    dataset = ConversationDataset(seed=random_seed)
    dataset.checkpoints = sorted({c for c in checkpoints if 1 <= c <= num_turns})

    planted = {t: SEEDED_FACTS[t] for t in sorted(seed_turns) if t in SEEDED_FACTS and t <= num_turns}
    for turn, info in planted.items():
        dataset.facts.append(
            Fact(
                id=info["id"],
                turn=turn,
                fact=info["fact"],
                probe=info["probe"],
                answer_key=info["answer_key"],
                answers=[list(p) for p in info["answers"]],
                stale=list(info.get("stale", [])),
            )
        )

    filler_pool = FILLER_TOPICS.copy()
    rng.shuffle(filler_pool)
    filler_index = 0

    for turn_num in range(1, num_turns + 1):
        if turn_num in planted:
            info = planted[turn_num]
            dataset.turns.append(
                Turn(
                    turn_number=turn_num,
                    human_message=(
                        f"I wanted to share something with you: {info['fact']} "
                        f"Anyway, let's keep chatting."
                    ),
                    fact_id=info["id"],
                )
            )
        else:
            topic = filler_pool[filler_index % len(filler_pool)]
            filler_index += 1
            dataset.turns.append(
                Turn(
                    turn_number=turn_num,
                    human_message=f"Let's talk about {topic}. What do you think about it?",
                )
            )

    return dataset
