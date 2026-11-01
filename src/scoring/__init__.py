"""Scoring of probe responses: a deterministic matcher and an LLM judge.

Labels (both scorers): correct | partial | wrong | refused | abstained.
"""

LABELS = ("correct", "partial", "wrong", "refused", "abstained")
