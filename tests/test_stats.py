import pytest

from src.stats import bootstrap_mean, cohen_kappa, wilson


def test_wilson_known_values():
    lo, hi = wilson(9, 14)
    # hand-computed from the Wilson formula with z = 1.96
    assert lo == pytest.approx(0.3876, abs=1e-4)
    assert hi == pytest.approx(0.8366, abs=1e-4)
    assert wilson(0, 0) == [0.0, 0.0]
    assert wilson(10, 10)[1] == pytest.approx(1.0)
    assert wilson(0, 10)[0] == pytest.approx(0.0)


def test_bootstrap_is_deterministic_and_brackets_the_mean():
    a = bootstrap_mean([0.8, 0.9, 0.7, 1.0, 0.6])
    b = bootstrap_mean([0.8, 0.9, 0.7, 1.0, 0.6])
    assert a == b
    assert a["ci95"][0] <= a["mean"] <= a["ci95"][1]
    assert bootstrap_mean([0.5]) == {"mean": 0.5, "ci95": [0.5, 0.5], "n": 1}


def test_cohen_kappa():
    assert cohen_kappa(["a", "b", "a"], ["a", "b", "a"]) == 1.0
    # textbook example: 20 items, observed 0.7, expected 0.5 -> 0.4
    m = ["y"] * 10 + ["n"] * 10
    j = ["y"] * 7 + ["n"] * 3 + ["y"] * 3 + ["n"] * 7
    assert cohen_kappa(m, j) == pytest.approx(0.4)
    assert cohen_kappa([], []) is None
    assert cohen_kappa(["a", "a"], ["a", "a"]) == 1.0
