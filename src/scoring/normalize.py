"""Text normalization shared by the matcher and the dataset's answer aliases.

`tokens(text)` folds case and accents (NFKD), removes possessive 's, splits
digits from units ("10mg" -> "10 mg"), drops ordinal suffixes ("15th" -> "15"),
turns small number words into digits, strips punctuation, and replaces dates
written as "March 15", "15 March" or "15th of March" with one canonical token
("date-03-15"), so "march 15" can only match a date and never "turn 15".
"""

from __future__ import annotations

import re
import unicodedata

MONTHS = {
    "january": 1, "jan": 1, "february": 2, "feb": 2, "march": 3, "mar": 3,
    "april": 4, "apr": 4, "may": 5, "june": 6, "jun": 6, "july": 7, "jul": 7,
    "august": 8, "aug": 8, "september": 9, "sept": 9, "sep": 9, "october": 10,
    "oct": 10, "november": 11, "nov": 11, "december": 12, "dec": 12,
}

NUMBER_WORDS = {
    "zero": "0", "one": "1", "two": "2", "three": "3", "four": "4", "five": "5",
    "six": "6", "seven": "7", "eight": "8", "nine": "9", "ten": "10",
    "eleven": "11", "twelve": "12", "thirteen": "13", "fourteen": "14",
    "fifteen": "15", "sixteen": "16", "seventeen": "17", "eighteen": "18",
    "nineteen": "19", "twenty": "20", "thirty": "30",
}

_APOSTROPHES = str.maketrans({"’": "'", "‘": "'", "ʼ": "'"})


def fold(text: str) -> str:
    """Lowercase, NFKD, accents removed, curly apostrophes made straight."""
    decomposed = unicodedata.normalize("NFKD", text.translate(_APOSTROPHES))
    return "".join(c for c in decomposed if not unicodedata.combining(c)).lower()


def _day(token: str) -> int | None:
    if token.isdigit() and 1 <= int(token) <= 31 and len(token) <= 2:
        return int(token)
    return None


def _dates(tokens: list[str]) -> list[str]:
    out: list[str] = []
    i = 0
    while i < len(tokens):
        tok = tokens[i]
        nxt = tokens[i + 1] if i + 1 < len(tokens) else None
        # month day: "march 15"
        if tok in MONTHS and nxt is not None and _day(nxt):
            out.append(f"date-{MONTHS[tok]:02d}-{_day(nxt):02d}")
            i += 2
            continue
        # day month / day of month: "15 march", "15 of march"
        if _day(tok) and nxt is not None:
            after = tokens[i + 2] if i + 2 < len(tokens) else None
            # "may" is also a verb ("15 may be"), so only read it as a month at
            # the end of the text or before a year.
            ambiguous = nxt == "may" and after is not None and not (after.isdigit() and len(after) == 4)
            if nxt in MONTHS and not ambiguous:
                out.append(f"date-{MONTHS[nxt]:02d}-{_day(tok):02d}")
                i += 2
                continue
            if nxt == "of" and i + 2 < len(tokens) and tokens[i + 2] in MONTHS:
                out.append(f"date-{MONTHS[tokens[i + 2]]:02d}-{_day(tok):02d}")
                i += 3
                continue
        out.append(tok)
        i += 1
    return out


def tokens(text: str) -> list[str]:
    t = fold(text)
    t = re.sub(r"'s\b", "", t)
    t = re.sub(r"\b(\d+)(st|nd|rd|th)\b", r"\1", t)
    t = re.sub(r"(\d)([a-z])", r"\1 \2", t)
    t = re.sub(r"[^a-z0-9]+", " ", t)
    words = [NUMBER_WORDS.get(w, w) for w in t.split()]
    return _dates(words)


def normalize(text: str) -> str:
    return " ".join(tokens(text))


def contains(haystack_norm: str, needle: str) -> bool:
    """True if the normalized `needle` occurs in `haystack_norm` on token boundaries."""
    n = normalize(needle)
    return bool(n) and f" {n} " in f" {haystack_norm} "
