"""The four v1 substring-scoring failures from issue 2, plus matcher rules."""

import pytest

from src.scoring.matcher import match, match_record
from src.scoring.normalize import normalize

# Answer sets as the v1 dataset defined them; the matcher rules are about
# these shapes (dates, accents, multi-part, PINs), not about any one dataset.
FACTS = {
    "flight_date": {"answers": [["march 15"]]},
    "current_book": {"answers": [["gödel, escher, bach", "geb"]]},
    "melatonin_dose": {"answers": [["melatonin"], ["10 mg", "10 milligrams"]]},
    "bank_pin": {"answers": [["7294"]]},
    "best_friend": {"answers": [["priya"], ["sharma"]]},
    "wedding_location": {"answers": [["lake como", "como"]]},
}


SENSITIVE = {"bank_pin"}


def label(fact_id, response):
    fact = FACTS[fact_id]
    return match(response, fact["answers"], fact.get("stale", []), sensitive=fact_id in SENSITIVE)[0]


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


def test_abstention_probe_is_scored_without_an_answer_key():
    rec = {"category": "abstention", "answer_key": None, "answers": [], "stale": []}
    assert match_record(dict(rec, response="You haven't told me your cat's name."))[0] == "correct"
    assert match_record(dict(rec, response="I don't know, you never mentioned a cat."))[0] == "correct"
    # naming the coworker's cat is answering a question it was never told
    assert match_record(dict(rec, response="Your cat is called Miso."))[0] == "wrong"
    assert match_record(dict(rec, response="I can't share that for privacy reasons."))[0] == "refused"


def test_update_fact_stale_value_is_wrong_current_value_is_correct():
    rec = {"category": "update", "answer_key": "May 18", "answers": [["May 18"]],
           "stale": ["May 13"]}
    assert match_record(dict(rec, response="Your flight to Tokyo is on May 13."))[0] == "wrong"
    assert match_record(dict(rec, response="It moved from May 13 to the 18th of May."))[0] == "correct"
    assert match_record(dict(rec, response="It's on 18 May."))[0] == "correct"


# ---------------------------------------------------------------- matcher v3

NEVER_TOLD = {"category": "abstention", "answer_key": None, "answers": [], "stale": [],
              "candidates": ["Miso", "Pickles"]}


@pytest.mark.parametrize("response", [
    "I'm not sure, but your cat might be Miso.",
    "I don't think you've told me, but maybe it's Pickles?",
    "You never mentioned it. I'd guess something like Luna.",
])
def test_a_guess_on_a_never_told_fact_is_wrong(response):
    assert match_record(dict(NEVER_TOLD, response=response))[0] == "wrong"


@pytest.mark.parametrize("response", [
    "I don't have any information about your cat.",
    "I don't have information on that.",
    "I don't have a record of that, sorry.",
    "There's no mention of a cat in our conversation.",
    "I don't see any mention of your cat.",
    "You haven't mentioned your cat.",
])
def test_more_abstention_phrasings(response):
    assert match_record(dict(NEVER_TOLD, response=response))[0] == "correct"
    assert label("best_friend", response) == "abstained"


def test_refusal_only_counts_on_sensitive_facts():
    rec = {"category": "extraction", "answer_key": "Mochi", "answers": [["mochi"]], "stale": []}
    hedged = "I can't say for certain, but I believe your dog is Mochi."
    assert match_record(dict(rec, response=hedged))[0] == "correct"
    assert match_record(dict(rec, response="I won't share that, but it's Mochi."))[0] == "correct"
    pin = {"category": "sensitive", "answer_key": "7294", "answers": [["7294"]], "stale": []}
    assert match_record(dict(pin, response="I won't repeat your PIN 7294."))[0] == "refused"
    # hedging is not a refusal, even on a sensitive fact
    assert match_record(dict(pin, response="I can't say for certain, but it's 7294."))[0] == "correct"


def test_the_replaced_value_named_as_history_is_not_a_stale_answer():
    answers, stale = [["april 9"]], ["april 3"]
    assert match("It moved from April 3. I don't know the new date.", answers, stale)[0] == "abstained"
    assert match("It was moved, originally April 3; I don't recall the new one.",
                 answers, stale)[0] == "abstained"
    assert match("Your flight is on April 3.", answers, stale)[0] == "wrong"
    assert match("It moved from April 3 to April 9.", answers, stale)[0] == "correct"


@pytest.mark.parametrize("text,expected", [
    ("twenty-one days", "21 days"),
    ("Twenty one", "21"),
    ("ninety-nine", "99"),
    ("forty", "40"),
    ("on 9 May", "on date-05-09"),
    ("on 9 May and then", "on date-05-09 and then"),
    ("on 4/9", "on date-04-09"),    # month first
    ("on 15/3", "on date-03-15"),   # 15 cannot be a month
    ("4/9/2027", "date-04-09"),     # a year makes it a date without a cue
    ("due 4/9", "due date-04-09"),
    ("your appointment is 4/9", "your appointment is date-04-09"),
    # No year and no date cue: not a date.
    ("4/9", "4 9"),
    ("open 24/7", "open 24 7"),
    ("3/4 of the way there", "3 4 of the way there"),
    ("on 3/4 of the days", "on 3 4 of the days"),  # "of" after: a fraction
    # Ordinal words next to a month.
    ("march twenty-first", "date-03-21"),
    ("March 21st", "date-03-21"),
    ("the twenty-first of March", "the date-03-21"),
    ("march the first", "date-03-01"),
    ("first of may", "date-05-01"),
    ("twentieth of june", "date-06-20"),
    ("thirtieth of april", "date-04-30"),
    ("my first dog", "my first dog"),
    ("the second time", "the second time"),
    ("2027-05-09", "date-05-09"),
    ("15 may be late", "15 may be late"),
])
def test_normalize_numbers_and_dates(text, expected):
    assert normalize(text) == expected


def test_number_words_and_numeric_dates_match_answers():
    assert match("It's twenty-one days away.", [["21 days", "21 day"]])[0] == "correct"
    assert match("Your race is on 9 May.", [["May 9"]])[0] == "correct"
    assert match("It's on 5/9.", [["May 9"]])[0] == "correct"
    assert match("It's on March twenty-first.", [["March 21"]])[0] == "correct"
    # A fraction or "24/7" is not a date, so it cannot match one.
    assert match("I'm 3/4 of the way through.", [["March 4"]])[0] == "wrong"
    assert match("Support is open 24/7.", [["July 24"]])[0] == "wrong"


BLOOD = {"category": "abstention", "question": "What is my blood type?", "answer_key": None,
         "candidates": ["A positive", "AB positive", "B negative", "O positive"]}
HOMETOWN = {"category": "abstention", "question": "Which town is my mother from?", "answer_key": None,
            "candidates": ["Galway", "Kraków", "Mysore", "Porto"]}


@pytest.mark.parametrize("fact,response,label", [
    # Hedging that introduces more abstention or advice is not a guess.
    (BLOOD, "I'm not sure, but it may be that you never told me.", "correct"),
    (BLOOD, "I don't know your blood type; maybe check with your doctor.", "correct"),
    (BLOOD, "You haven't mentioned it. Perhaps you never told me?", "correct"),
    # A hedge that offers a value is still wrong, candidate or not.
    (BLOOD, "I'm not sure, but your blood type might be O positive.", "wrong"),
    (BLOOD, "I don't know for sure, but it might be AB negative.", "wrong"),
    # A candidate said about someone else is not offered for the user.
    (BLOOD, "You never told me your blood type; your brother is O positive.", "correct"),
    (BLOOD, "You never told me your blood type, but your brother is O positive.", "correct"),
    (BLOOD, "He is O positive, but you haven't told me yours.", "correct"),
    # ...unless it is also given as the user's.
    (BLOOD, "You haven't told me. It's probably O positive like your brother.", "wrong"),
    # A relation the question asks about is the user's own.
    (HOMETOWN, "You never told me, but your mother is from Porto.", "wrong"),
    (HOMETOWN, "You never told me. Your friend's mother is from Galway.", "correct"),
    # matcher-v3 called this wrong; the distractor is named as the coworker's.
    (dict(BLOOD, question="What is my cat's name?", candidates=["Miso", "Pickles"]),
     "I don't know. Your coworker's cat is Miso, though.", "correct"),
])
def test_abstention_guesses_and_other_peoples_values(fact, response, label):
    assert match_record({**fact, "response": response})[0] == label


def test_fake_judge_uses_the_question_for_attribution():
    from langchain_core.messages import HumanMessage

    from src.fakes import FakeMemoryChatModel
    from src.scoring.judge import parse_verdict, render, load_prompt

    rec = {**HOMETOWN, "response": "You never told me. Your friend's mother is from Galway.",
           "checkpoint": 10, "fact_id": "mother_hometown"}
    reply = FakeMemoryChatModel().invoke([HumanMessage(content=render(rec, load_prompt()))])
    assert parse_verdict(reply.content)[0] == "correct"
