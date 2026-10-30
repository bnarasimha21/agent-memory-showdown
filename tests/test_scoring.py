"""The four v1 substring-scoring failures from issue 2, plus matcher rules."""

import pytest

from src.dataset import SEEDED_FACTS
from src.scoring.matcher import match
from src.scoring.normalize import normalize

FACTS = {info["id"]: info for info in SEEDED_FACTS.values()}


def label(fact_id, response):
    fact = FACTS[fact_id]
    return match(response, fact["answers"], fact.get("stale", []))[0]


# 1. "march 15" used to match any reply containing "march" and "15".
def test_date_key_does_not_match_unrelated_numbers():
    assert label("flight_date", "I'm not sure about March, but at turn 15 you mentioned Tokyo.") != "correct"
    assert label("flight_date", "Your flight to Tokyo is on the 15th of March.") == "correct"
    assert label("flight_date", "It's on March 15th.") == "correct"
    assert label("flight_date", "It's on 15 Mar.") == "correct"


# 2. "gödel, escher, bach" split to "gödel," with the comma, so plain ASCII failed.
def test_accents_and_punctuation_are_normalized():
    assert label("current_book", "You're reading Godel Escher Bach.") == "correct"
    assert label("current_book", "Gödel, Escher, Bach by Hofstadter") == "correct"
    assert label("current_book", "GEB!") == "correct"


# 3. The melatonin key ignored the dose the probe asks for.
def test_multi_part_answer_needs_every_part():
    assert label("melatonin_dose", "You take melatonin before bed.") == "partial"
    assert label("melatonin_dose", "You take 10mg of melatonin.") == "correct"
    assert label("melatonin_dose", "Ten milligrams of melatonin.") == "correct"
    assert label("melatonin_dose", "You take 5 mg of magnesium.") == "wrong"


# 4. "I won't repeat your PIN 7294" scored correct.
def test_refusal_is_labelled_refused_even_with_the_value():
    assert label("bank_pin", "I won't repeat your PIN 7294, for security reasons.") == "refused"
    assert label("bank_pin", "I can't share sensitive details like your bank PIN.") == "refused"
    assert label("bank_pin", "Your bank PIN is 7294.") == "correct"


@pytest.mark.parametrize("response", [
    "You haven't told me that, so I don't know.",
    "I don't have that information.",
    "You didn't mention a best friend.",
])
def test_abstention(response):
    assert label("best_friend", response) == "abstained"


def test_partial_and_wrong():
    assert label("best_friend", "Her name is Priya.") == "partial"
    assert label("best_friend", "Your best friend is Anjali.") == "wrong"


def test_stale_value_is_wrong_not_abstained():
    answers = [["tuesday"]]
    assert match("It moved, I don't know, it was Monday", answers, ["monday"])[0] == "wrong"
    assert match("It's on Tuesday now.", answers, ["monday"])[0] == "correct"


def test_token_boundaries():
    # "como" must not match inside another word; "7294" not inside "172945"
    assert label("wedding_location", "It's in Comoros.") == "wrong"
    assert label("bank_pin", "Account 172945.") == "wrong"


def test_normalize_examples():
    assert normalize("My flight is on March 15th!") == "my flight is on date-03-15"
    assert normalize("sunkist-mango-42") == "sunkist mango 42"
    assert normalize("15 may be late") == "15 may be late"
