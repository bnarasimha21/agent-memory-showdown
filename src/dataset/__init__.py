"""Synthetic conversations for the benchmark (dataset v2).

Facts live as data in `data/facts_v2.yaml`; `generate_dataset` samples one
conversation per run seed. See `src/dataset/generate.py` for the rules.
"""

from src.dataset.bank import (
    CATEGORIES,
    NON_HEADLINE,
    BankError,
    FactBank,
    FactTemplate,
    load_bank,
)
from src.dataset.generate import (
    DEFAULT_CHECKPOINTS,
    DEFAULT_COMPOSITION,
    ConversationDataset,
    Fact,
    Statement,
    Turn,
    generate_dataset,
    parse_composition,
)

# Fact ids of the v1 dataset that were sensitive; used to categorise probes in
# bundles written before probe records carried a category.
LEGACY_SENSITIVE_IDS = frozenset({"wifi_password", "bank_pin"})


def probe_category(record: dict) -> str:
    """Category of a probe record, including records from pre-v2 bundles."""
    category = record.get("category")
    if category:
        return category
    return "sensitive" if record.get("fact_id") in LEGACY_SENSITIVE_IDS else "extraction"


__all__ = [
    "CATEGORIES", "NON_HEADLINE", "BankError", "FactBank", "FactTemplate", "load_bank",
    "DEFAULT_CHECKPOINTS", "DEFAULT_COMPOSITION", "ConversationDataset", "Fact", "Statement",
    "Turn", "generate_dataset", "parse_composition", "LEGACY_SENSITIVE_IDS", "probe_category",
]
