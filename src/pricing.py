"""Token prices from pricing.yaml and the cost formula used in aggregates."""

from __future__ import annotations

import os
from dataclasses import asdict, dataclass
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PRICING_FILE = REPO_ROOT / "pricing.yaml"


@dataclass(frozen=True)
class Price:
    model: str
    input_per_mtok: float
    output_per_mtok: float
    source: str
    checked_on: str
    currency: str = "USD"

    def cost(self, input_tokens: float, output_tokens: float) -> float:
        return (input_tokens * self.input_per_mtok + output_tokens * self.output_per_mtok) / 1e6

    def to_dict(self) -> dict:
        return asdict(self)


def load_pricing(path: str | Path | None = None) -> dict[str, Price]:
    path = Path(path or os.getenv("PRICING_FILE") or DEFAULT_PRICING_FILE)
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    currency = data.get("currency", "USD")
    prices = {}
    for model, entry in (data.get("models") or {}).items():
        for field in ("input_per_mtok", "output_per_mtok", "source", "checked_on"):
            if field not in entry:
                raise ValueError(f"{path}: model {model!r} is missing {field!r}")
        prices[model] = Price(
            model=model,
            input_per_mtok=float(entry["input_per_mtok"]),
            output_per_mtok=float(entry["output_per_mtok"]),
            source=str(entry["source"]),
            checked_on=str(entry["checked_on"]),
            currency=currency,
        )
    return prices


def price_for(model: str | None, pricing: dict[str, Price] | None = None) -> Price | None:
    if not model:
        return None
    pricing = pricing if pricing is not None else load_pricing()
    return pricing.get(model)
