"""Text normalization shared by the matcher and the dataset's answer aliases.

`tokens(text)` folds case and accents (NFKD), removes possessive 's, splits
digits from units ("10mg" -> "10 mg"), drops ordinal suffixes ("15th" -> "15"),
turns number words from zero to ninety-nine into digits ("twenty-one" -> "21"),
strips punctuation, and replaces dates written as "March 15", "15 March",
"15th of March", "3/15" or "2027-03-15" with one canonical token
("date-03-15"), so "march 15" can only match a date and never "turn 15".

Numeric dates without a month name are read month first ("4/9" is April 9,
the US order the answering models default to), unless the first number cannot
be a month ("15/3" is March 15). The dataset writes every date with a month
name, so this only matters for how a model chooses to answer.
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
    "nineteen": "19",
}
TENS = {"twenty": 20, "thirty": 30, "forty": 40, "fifty": 50, "sixty": 60, "seventy": 70,
        "eighty": 80, "ninety": 90}
NUMBER_WORDS.update({w: str(n) for w, n in TENS.items()})
_UNITS = {w: int(d) for w, d in NUMBER_WORDS.items() if len(d) == 1 and d != "0"}

# After "<day> may", these words mean "may" is the verb ("15 may be late").
_MAY_VERB_NEXT = {"be", "have", "not", "need", "want", "get", "take", "come", "go", "arrive",
                  "change", "also", "still", "well", "just", "move", "work", "help"}
_MONTH_NAMES = ["january", "february", "march", "april", "may", "june", "july", "august",
                "september", "october", "november", "december"]

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
            # "may" is also a verb ("15 may be late"), so after a number it is
            # only read as a month unless a verb-like word follows.
            ambiguous = nxt == "may" and after in _MAY_VERB_NEXT
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


def _numeric_date(m: re.Match) -> str:
    if m["iso_month"]:
        month, day = int(m["iso_month"]), int(m["iso_day"])
    else:
        a, b = int(m["a"]), int(m["b"])
        month, day = (a, b) if a <= 12 else (b, a)
    if not (1 <= month <= 12 and 1 <= day <= 31):
        return m[0]
    return f" {_MONTH_NAMES[month - 1]} {day} "


_NUMERIC_DATE = re.compile(
    r"\b(?:\d{4}-(?P<iso_month>\d{1,2})-(?P<iso_day>\d{1,2})"
    r"|(?P<a>\d{1,2})/(?P<b>\d{1,2})(?:/\d{2,4})?)\b"
)


def _join_number_words(words: list[str]) -> list[str]:
    """"twenty one" (the hyphen is already gone) -> "21"."""
    out: list[str] = []
    i = 0
    while i < len(words):
        w = words[i]
        nxt = words[i + 1] if i + 1 < len(words) else None
        if w in TENS and nxt in _UNITS:
            out.append(str(TENS[w] + _UNITS[nxt]))
            i += 2
            continue
        out.append(NUMBER_WORDS.get(w, w))
        i += 1
    return out


def tokens(text: str) -> list[str]:
    t = fold(text)
    t = _NUMERIC_DATE.sub(_numeric_date, t)
    t = re.sub(r"'s\b", "", t)
    t = re.sub(r"\b(\d+)(st|nd|rd|th)\b", r"\1", t)
    t = re.sub(r"(\d)([a-z])", r"\1 \2", t)
    t = re.sub(r"[^a-z0-9]+", " ", t)
    return _dates(_join_number_words(t.split()))


def normalize(text: str) -> str:
    return " ".join(tokens(text))


def contains(haystack_norm: str, needle: str) -> bool:
    """True if the normalized `needle` occurs in `haystack_norm` on token boundaries."""
    n = normalize(needle)
    return bool(n) and f" {n} " in f" {haystack_norm} "
