"""Synthetic conversation dataset generator with seeded facts."""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Optional


SEEDED_FACTS = {
    3: {
        "fact": "Alice's favorite color is cerulean blue.",
        "probe": "What is Alice's favorite color?",
        "answer_key": "cerulean blue",
    },
    10: {
        "fact": "Bob works as a marine biologist studying bioluminescent jellyfish.",
        "probe": "What does Bob do for work?",
        "answer_key": "marine biologist",
    },
    25: {
        "fact": "The team's secret project codename is 'Project Nightingale'.",
        "probe": "What is the team's secret project codename?",
        "answer_key": "nightingale",
    },
    40: {
        "fact": "Carol's grandmother taught her to bake sourdough bread every Sunday.",
        "probe": "Who taught Carol to bake sourdough?",
        "answer_key": "grandmother",
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
]


@dataclass
class Turn:
    turn_number: int
    human_message: str
    is_seed_turn: bool = False
    seed_fact: Optional[str] = None


@dataclass
class ConversationDataset:
    turns: list[Turn] = field(default_factory=list)
    seed_turns: dict[int, dict] = field(default_factory=dict)
    recall_probes: list[dict] = field(default_factory=list)


def generate_dataset(
    num_turns: int = 50, seed_turns: list[int] = None, random_seed: int = 42
) -> ConversationDataset:
    if seed_turns is None:
        seed_turns = [3, 10, 25, 40]

    rng = random.Random(random_seed)
    dataset = ConversationDataset()
    dataset.seed_turns = {t: SEEDED_FACTS[t] for t in seed_turns if t in SEEDED_FACTS}

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
        else:
            topic = filler_pool[filler_index % len(filler_pool)]
            filler_index += 1
            human_msg = f"Let's talk about {topic}. What do you think about it?"
            dataset.turns.append(
                Turn(turn_number=turn_num, human_message=human_msg)
            )

    for turn_num, fact_info in dataset.seed_turns.items():
        dataset.recall_probes.append(
            {
                "seeded_at_turn": turn_num,
                "probe": fact_info["probe"],
                "answer_key": fact_info["answer_key"],
                "full_fact": fact_info["fact"],
            }
        )

    return dataset
