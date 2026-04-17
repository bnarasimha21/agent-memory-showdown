"""Synthetic conversation dataset generator with seeded facts and inline recall probes."""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Optional


SEEDED_FACTS = {
    1: {
        "fact": "My dog's name is Baxter.",
        "probe": "What is my dog's name?",
        "answer_key": "baxter",
    },
    3: {
        "fact": "I'm allergic to shellfish.",
        "probe": "What food am I allergic to?",
        "answer_key": "shellfish",
    },
    7: {
        "fact": "My flight to Tokyo is on March 15th.",
        "probe": "When is my flight to Tokyo?",
        "answer_key": "march 15",
    },
    12: {
        "fact": "The project deadline is April 30th.",
        "probe": "When is the project deadline?",
        "answer_key": "april 30",
    },
    18: {
        "fact": "My sister's wedding is in Lake Como, Italy.",
        "probe": "Where is my sister's wedding?",
        "answer_key": "lake como",
    },
    25: {
        "fact": "I'm reading 'Gödel, Escher, Bach' by Douglas Hofstadter.",
        "probe": "What book am I currently reading?",
        "answer_key": "gödel, escher, bach",
    },
    30: {
        "fact": "My home Wi-Fi password is 'sunkist-mango-42'.",
        "probe": "What is my home Wi-Fi password?",
        "answer_key": "sunkist-mango-42",
    },
    35: {
        "fact": "I take 10 mg of melatonin every night before bed.",
        "probe": "What supplement do I take before bed and at what dose?",
        "answer_key": "melatonin",
    },
    40: {
        "fact": "My childhood best friend's name is Priya Sharma.",
        "probe": "What is my childhood best friend's name?",
        "answer_key": "priya sharma",
    },
    45: {
        "fact": "My bank PIN is 7294.",
        "probe": "What is my bank PIN?",
        "answer_key": "7294",
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

RECALL_TURNS_DEFAULT = [15, 25, 35, 50]


@dataclass
class Turn:
    turn_number: int
    human_message: str
    is_seed_turn: bool = False
    seed_fact: Optional[str] = None
    is_recall_turn: bool = False
    recall_probes: list[dict] = field(default_factory=list)


@dataclass
class ConversationDataset:
    turns: list[Turn] = field(default_factory=list)
    seed_turns: dict[int, dict] = field(default_factory=dict)
    recall_schedule: dict[int, list[dict]] = field(default_factory=dict)


def _probes_for_recall_turn(
    recall_turn: int, seed_facts: dict[int, dict]
) -> list[dict]:
    """All facts seeded *before* this recall turn become probes."""
    probes = []
    for seed_turn in sorted(seed_facts):
        if seed_turn < recall_turn:
            info = seed_facts[seed_turn]
            probes.append(
                {
                    "seeded_at_turn": seed_turn,
                    "probe": info["probe"],
                    "answer_key": info["answer_key"],
                    "full_fact": info["fact"],
                }
            )
    return probes


def generate_dataset(
    num_turns: int = 50,
    seed_turns: list[int] | None = None,
    recall_turns: list[int] | None = None,
    random_seed: int = 42,
) -> ConversationDataset:
    if seed_turns is None:
        seed_turns = sorted(SEEDED_FACTS.keys())
    if recall_turns is None:
        recall_turns = RECALL_TURNS_DEFAULT

    rng = random.Random(random_seed)
    dataset = ConversationDataset()
    dataset.seed_turns = {t: SEEDED_FACTS[t] for t in seed_turns if t in SEEDED_FACTS}

    for rt in recall_turns:
        probes = _probes_for_recall_turn(rt, dataset.seed_turns)
        if probes:
            dataset.recall_schedule[rt] = probes

    filler_pool = FILLER_TOPICS.copy()
    rng.shuffle(filler_pool)
    filler_index = 0

    for turn_num in range(1, num_turns + 1):
        if turn_num in dataset.seed_turns:
            fact_info = dataset.seed_turns[turn_num]
            human_msg = (
                f"I wanted to share something with you: {fact_info['fact']} "
                f"Anyway, let's keep chatting."
            )
            dataset.turns.append(
                Turn(
                    turn_number=turn_num,
                    human_message=human_msg,
                    is_seed_turn=True,
                    seed_fact=fact_info["fact"],
                )
            )
        elif turn_num in dataset.recall_schedule:
            dataset.turns.append(
                Turn(
                    turn_number=turn_num,
                    human_message="",
                    is_recall_turn=True,
                    recall_probes=dataset.recall_schedule[turn_num],
                )
            )
        else:
            topic = filler_pool[filler_index % len(filler_pool)]
            filler_index += 1
            human_msg = f"Let's talk about {topic}. What do you think about it?"
            dataset.turns.append(
                Turn(turn_number=turn_num, human_message=human_msg)
            )

    return dataset
