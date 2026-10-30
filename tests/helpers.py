"""Shared helpers for reading bundles in tests."""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path

from src.bundle import read_transcript


def records(bundle: Path, kind: str | None = None, backend: str | None = None) -> list[dict]:
    out = []
    for rec in read_transcript(bundle):
        if kind and rec["type"] != kind:
            continue
        if backend and rec["backend"] != backend:
            continue
        out.append(rec)
    return out


def group(items: list[dict], *keys: str) -> dict:
    grouped = defaultdict(list)
    for item in items:
        grouped[tuple(item[k] for k in keys) if len(keys) > 1 else item[keys[0]]].append(item)
    return grouped
