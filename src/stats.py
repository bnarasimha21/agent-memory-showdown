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
    # The bounds are exactly 0 and 1 at the extremes; without this, rounding
    # leaves 5e-17 above the point estimate and error bars go negative.
    low = 0.0 if successes <= 0 else max(0.0, min(p, centre - half))
    high = 1.0 if successes >= n else min(1.0, max(p, centre + half))
    return [low, high]


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


# Two-sided 95% quantiles of Student's t, df 1 to 30 (standard tables).
_T95 = [12.706, 4.303, 3.182, 2.776, 2.571, 2.447, 2.365, 2.306, 2.262, 2.228,
        2.201, 2.179, 2.160, 2.145, 2.131, 2.120, 2.110, 2.101, 2.093, 2.086,
        2.080, 2.074, 2.069, 2.064, 2.060, 2.056, 2.052, 2.048, 2.045, 2.042]


def t95(df: int) -> float:
    """Two-sided 95% Student t quantile. Table up to df 30, Cornish-Fisher expansion above."""
    if df < 1:
        raise ValueError("t95 needs df >= 1")
    if df <= len(_T95):
        return _T95[df - 1]
    z = Z95
    return (z + (z ** 3 + z) / (4 * df) + (5 * z ** 5 + 16 * z ** 3 + 3 * z) / (96 * df ** 2)
            + (3 * z ** 7 + 19 * z ** 5 + 17 * z ** 3 - 15 * z) / (384 * df ** 3))


def t_mean_interval(values: Sequence[float], bounds: tuple[float, float] | None = None) -> dict:
    """Mean of independent values with a 95% Student t interval.

    This is the interval for few runs: a percentile bootstrap over 3 to 5 values
    is too narrow (it can only resample the values seen). A single value has no
    interval (`ci95` None). `bounds` clips the interval, e.g. (0, 1) for rates.
    """
    vals = np.asarray(list(values), dtype=float)
    n = int(vals.size)
    if n == 0:
        return {"mean": None, "ci95": None, "n": 0, "method": "t"}
    mean = float(vals.mean())
    if n == 1:
        return {"mean": mean, "ci95": None, "n": 1, "method": "t"}
    half = t95(n - 1) * float(vals.std(ddof=1)) / math.sqrt(n)
    low, high = mean - half, mean + half
    if bounds is not None:
        low, high = max(bounds[0], low), min(bounds[1], high)
    return {"mean": mean, "ci95": [low, high], "n": n, "method": "t"}


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
