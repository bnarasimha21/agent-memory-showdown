"""Spend so far, from recorded tokens and pricing.yaml, and a budget that stops a run.

    python run_benchmark.py --budget 150        # or BUDGET_USD=150

Spend is what the recorded tokens cost at the listed prices: the answering
model's tokens for every turn, memory write and probe in the transcript
(including runs that failed and runs dropped on a resume, since they were paid
for), plus the judge model's tokens. It is a list-price figure computed here,
not the provider's invoice; calls that failed without reporting tokens are not
in it.

The budget covers the whole bundle, across resumes. It is checked before each
(backend, run) starts and before each judge call, so a run can go over it by at
most one conversation. When it is reached the run stops with `BudgetExceeded`
and the bundle stays unfinished (no `aggregate.json`, so it cannot be
published) and resumable.
"""

from __future__ import annotations

from src.pricing import Price, price_for


class BudgetExceeded(RuntimeError):
    """The budget was reached; the bundle is unfinished and can be resumed."""

    def __init__(self, message: str, bundle=None) -> None:
        super().__init__(message)
        self.bundle = bundle


def require_prices(answering_model: str, judge_model: str | None) -> tuple[Price, Price | None]:
    """The prices a budget needs, or a ValueError naming the model pricing.yaml lacks."""
    missing = [m for m in (answering_model, judge_model) if m and price_for(m) is None]
    if missing:
        raise ValueError(
            f"a budget is set but pricing.yaml has no price for {', '.join(dict.fromkeys(missing))}, "
            "so spend cannot be computed. Add the model to pricing.yaml (with its source and the "
            "date checked) or run without --budget / BUDGET_USD.")
    return price_for(answering_model), price_for(judge_model) if judge_model else None


def record_cost(price: Price, record: dict) -> float:
    """What one transcript record cost: answering tokens plus memory-write tokens."""
    if record.get("type") not in ("turn", "probe"):
        return 0.0
    return price.cost(
        (record.get("input_tokens") or 0) + (record.get("write_input_tokens") or 0),
        (record.get("output_tokens") or 0) + (record.get("write_output_tokens") or 0))


class SpendMeter:
    """Running spend for one bundle. `limit` None means track only, never stop."""

    def __init__(self, answering: Price, judge: Price | None, limit: float | None = None,
                 prior: dict | None = None) -> None:
        prior = prior or {}
        self.answering_price, self.judge_price, self.limit = answering, judge, limit
        self.answering_usd = 0.0  # records now in the transcript
        self.dropped_usd = float(prior.get("dropped_usd") or 0.0)  # records dropped on a resume
        self.judge_usd = float(prior.get("judge_usd") or 0.0)
        self.stopped: str | None = None

    @property
    def total_usd(self) -> float:
        return self.answering_usd + self.dropped_usd + self.judge_usd

    def add_record(self, record: dict) -> None:
        self.answering_usd += record_cost(self.answering_price, record)

    def add_dropped(self, records) -> None:
        self.dropped_usd += sum(record_cost(self.answering_price, r) for r in records)

    def add_judge(self, input_tokens: float, output_tokens: float) -> None:
        if self.judge_price is not None:
            self.judge_usd += self.judge_price.cost(input_tokens or 0, output_tokens or 0)

    def exceeded(self) -> bool:
        return self.limit is not None and self.total_usd >= self.limit

    def to_dict(self) -> dict:
        return {
            "answering_model": self.answering_price.model,
            "judge_model": self.judge_price.model if self.judge_price else None,
            "answering_usd": self.answering_usd,
            "dropped_usd": self.dropped_usd,
            "judge_usd": self.judge_usd,
            "total_usd": self.total_usd,
            "budget_usd": self.limit,
            "stopped": self.stopped,
            "basis": "recorded tokens at pricing.yaml list prices; not the provider's invoice",
        }


class MeteredJudge:
    """A judge whose calls are added to the spend and refused once the budget is reached."""

    def __init__(self, judge, meter: SpendMeter, on_stop=None, on_progress=None) -> None:
        self._judge, self._meter = judge, meter
        self._on_stop, self._on_progress = on_stop, on_progress
        self._calls = 0

    def __getattr__(self, name):
        return getattr(self._judge, name)

    def judge(self, record: dict) -> dict:
        if self._meter.exceeded() and self._on_stop is not None:
            self._on_stop("while judging")
        verdict = self._judge.judge(record)
        self._meter.add_judge(verdict.get("input_tokens", 0), verdict.get("output_tokens", 0))
        self._calls += 1
        if self._on_progress is not None and self._calls % 25 == 0:
            self._on_progress()
        return verdict
