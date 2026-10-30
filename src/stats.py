"""Interval estimates and agreement statistics used in aggregates."""

from __future__ import annotations

import math
from collections import Counter
from typing import Sequence

import numpy as np

Z95 = 1.959963984540054


def wilson(successes: int, n: int, z: float = Z95) -> list[float]:
    """Wilson score interval for a binomial proportion, as [low, high]."""
    if n <= 0:
        return [0.0, 0.0]
    p = successes / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return [max(0.0, centre - half), min(1.0, centre + half)]


def bootstrap_mean(
    values: Sequence[float], resamples: int = 2000, seed: int = 0, level: float = 0.95
) -> dict:
    """Mean with a percentile bootstrap interval. Deterministic for a given seed."""
    vals = np.asarray(list(values), dtype=float)
    if vals.size == 0:
        return {"mean": 0.0, "ci95": [0.0, 0.0], "n": 0}
    mean = float(vals.mean())
    if vals.size == 1:
        return {"mean": mean, "ci95": [mean, mean], "n": 1}
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, vals.size, size=(resamples, vals.size))
    means = vals[idx].mean(axis=1)
    alpha = (1 - level) / 2
    lo, hi = np.quantile(means, [alpha, 1 - alpha])
    return {"mean": mean, "ci95": [float(lo), float(hi)], "n": int(vals.size)}


def cohen_kappa(a: Sequence[str], b: Sequence[str]) -> float | None:
    """Cohen's kappa for two label sequences; None when undefined (no items)."""
    if len(a) != len(b):
        raise ValueError("label sequences differ in length")
    n = len(a)
    if n == 0:
        return None
    observed = sum(x == y for x, y in zip(a, b)) / n
    ca, cb = Counter(a), Counter(b)
    expected = sum(ca[k] * cb[k] for k in set(ca) | set(cb)) / (n * n)
    if expected == 1.0:
        return 1.0 if observed == 1.0 else 0.0
    return (observed - expected) / (1 - expected)
