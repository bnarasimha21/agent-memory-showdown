"""Issue 4: dataset v2 is sampled per seed, from the YAML fact bank."""

import datetime as dt

import pytest
import yaml

from src.dataset import (
    CATEGORIES,
    BankError,
    generate_dataset,
    load_bank,
    parse_composition,
    probe_category,
)
from src.dataset.bank import _load_bank
from src.scoring.normalize import normalize, tokens

ONE_EACH = {c: 1 for c in CATEGORIES}


def _signature(ds):
    return [(f.id, f.turn, tuple(s.turn for s in f.statements), tuple(sorted(f.values.items())))
            for f in ds.facts]


def test_same_seed_reproduces_the_dataset():
    a = generate_dataset(num_turns=50, random_seed=7)
    b = generate_dataset(num_turns=50, random_seed=7)
    assert a.to_dict() == b.to_dict()


def test_different_seeds_change_values_and_positions():
    a = generate_dataset(num_turns=50, random_seed=42)
    b = generate_dataset(num_turns=50, random_seed=43)
    assert _signature(a) != _signature(b)
    turns_a = {s.turn for f in a.facts for s in f.statements}
    turns_b = {s.turn for f in b.facts for s in f.statements}
    assert turns_a != turns_b
    values_a = {v for f in a.facts for k, v in f.values.items() if not k.startswith("other_")}
    values_b = {v for f in b.facts for k, v in f.values.items() if not k.startswith("other_")}
    assert values_a != values_b


def test_values_and_turns_vary_across_seeds_for_the_same_template():
    names, turns = set(), set()
    for seed in range(20):
        ds = generate_dataset(num_turns=30, checkpoints=[30], random_seed=seed,
                              composition={"extraction": 6})
        dog = next(f for f in ds.facts if f.id == "dog_name")
        names.add(dog.answer_key)
        turns.add(dog.turn)
    assert len(names) > 3 and len(turns) > 3


def test_every_turn_is_a_real_turn_and_composition_is_respected():
    ds = generate_dataset(num_turns=50, checkpoints=[15, 25, 35, 50], random_seed=1)
    assert [t.turn_number for t in ds.turns] == list(range(1, 51))
    assert all(t.human_message for t in ds.turns)
    counts = {c: sum(f.category == c for f in ds.facts) for c in CATEGORIES}
    assert counts == ds.composition
    for fact in ds.facts:
        for st in fact.statements:
            turn = ds.turns[st.turn - 1]
            assert turn.fact_id == fact.id and st.text in turn.human_message


def test_statements_land_before_the_last_checkpoint():
    for seed in range(10):
        ds = generate_dataset(num_turns=50, checkpoints=[10, 30], random_seed=seed)
        assert all(s.turn <= 30 for f in ds.facts for s in f.statements)
        assert all(f in ds.probes_at(30) for f in ds.facts)


def test_update_fact_is_probed_after_its_correction_with_the_old_value_stale():
    for seed in range(10):
        ds = generate_dataset(num_turns=30, checkpoints=[30], random_seed=seed,
                              composition={"update": 2}, distractors=False)
        for f in ds.facts:
            first, second = f.statements
            assert first.turn < second.turn == f.turn
            assert normalize(f.stale[0]) in normalize(first.text)
            assert normalize(f.answers[0][0]) in normalize(second.text)
            assert normalize(f.stale[0]) != normalize(f.answers[0][0])


def test_temporal_answer_is_the_real_day_difference():
    for seed in range(10):
        ds = generate_dataset(num_turns=20, checkpoints=[20], random_seed=seed,
                              composition={"temporal": 1}, distractors=False)
        (f,) = ds.facts
        dates = [t for st in f.statements for t in tokens(st.text) if t.startswith("date-")]
        d1, d2 = (dt.date(2027, int(d[5:7]), int(d[8:10])) for d in dates)
        assert f.answer_key == f"{abs((d2 - d1).days)} days"


def test_abstention_facts_are_never_stated_and_have_no_answer_key():
    ds = generate_dataset(num_turns=30, checkpoints=[10, 30], random_seed=3,
                          composition={"abstention": 2, "extraction": 1})
    abst = [f for f in ds.facts if f.category == "abstention"]
    assert len(abst) == 2
    for f in abst:
        assert f.answer_key is None and f.answers == [] and f.statements == []
        assert f.turn == 0 and f in ds.probes_at(10)


def test_distractors_mention_a_different_value():
    ds = generate_dataset(num_turns=50, random_seed=5)
    distractors = [t for t in ds.turns if t.kind == "distractor"]
    assert len(distractors) == sum(f.category != "sensitive" for f in ds.facts)
    for f in ds.facts:
        for t in distractors:
            # no distractor states every required part of a real answer
            assert not (f.answers and all(
                any(normalize(a) in normalize(t.human_message) for a in part) for part in f.answers
            )), (f.id, t.human_message)
    off = generate_dataset(num_turns=50, random_seed=5, distractors=False)
    assert not [t for t in off.turns if t.kind == "distractor"]


def test_filler_is_varied():
    ds = generate_dataset(num_turns=50, random_seed=2)
    openings = {t.human_message.split()[0] for t in ds.turns if t.kind == "filler"}
    assert len(openings) > 2


def test_expected_probe_counts_follow_readiness():
    ds = generate_dataset(num_turns=30, checkpoints=[15, 30], random_seed=11, composition=ONE_EACH)
    counts = ds.expected_probe_counts()
    assert counts["abstention"] == 2  # ready from the start, asked at both checkpoints
    assert all(1 <= counts[c] <= 2 for c in CATEGORIES)
    assert sum(counts.values()) == len(ds.probes_at(15)) + len(ds.probes_at(30))


def test_checkpoints_outside_the_conversation_are_dropped():
    ds = generate_dataset(num_turns=20, checkpoints=[0, 10, 20, 50], composition={"extraction": 2})
    assert ds.checkpoints == [10, 20]


def test_too_many_facts_for_the_conversation_is_an_error():
    with pytest.raises(ValueError, match="do not fit"):
        generate_dataset(num_turns=5, checkpoints=[5], composition={"update": 3, "extraction": 2})
    with pytest.raises(ValueError, match="bank has"):
        generate_dataset(num_turns=50, composition={"temporal": 50})
    with pytest.raises(ValueError, match="unknown"):
        generate_dataset(num_turns=50, composition={"vibes": 1})


def test_parse_composition():
    assert parse_composition("extraction=2, update=1")["update"] == 1
    assert parse_composition("extraction=2")["sensitive"] == 0
    with pytest.raises(ValueError):
        parse_composition("vibes=2")
    with pytest.raises(ValueError):
        parse_composition("extraction")


def test_every_template_realizes_cleanly():
    bank = load_bank()
    assert {f.category for f in bank.facts} == set(CATEGORIES)
    for category in CATEGORIES:
        n = len(bank.by_category(category))
        for seed in range(5):
            ds = generate_dataset(num_turns=60, checkpoints=[60], random_seed=seed,
                                  composition={category: n})
            assert len(ds.facts) == n
            for f in ds.facts:
                texts = [f.probe] + [a for p in f.answers for a in p] + [s.text for s in f.statements]
                assert not any("{" in t or "}" in t for t in texts), f


def test_malformed_bank_is_rejected(tmp_path):
    raw = yaml.safe_load(open(load_bank().path, encoding="utf-8").read())
    path = tmp_path / "bank.yaml"
    path.write_text(yaml.safe_dump(dict(raw, facts=[dict(raw["facts"][0], statements=["My dog is {nope}."])])))
    with pytest.raises(BankError, match="nope"):
        _load_bank(str(path))
    bad = {"id": "x", "category": "update", "probe": "?", "answer": "a",
           "answers": [["a"]], "statements": ["only one"], "stale": ["b"]}
    path.write_text(yaml.safe_dump(dict(raw, facts=[bad])))
    with pytest.raises(BankError, match="exactly 2"):
        _load_bank(str(path))
    bad = {"id": "x", "category": "abstention", "probe": "?", "answer": "a", "answers": [["a"]]}
    path.write_text(yaml.safe_dump(dict(raw, facts=[bad])))
    with pytest.raises(BankError, match="no answer"):
        _load_bank(str(path))


def test_probe_category_for_old_records():
    assert probe_category({"fact_id": "bank_pin"}) == "sensitive"
    assert probe_category({"fact_id": "dog_name"}) == "extraction"
    assert probe_category({"fact_id": "x", "category": "update"}) == "update"


def test_no_two_facts_share_a_list_value_over_1000_seeds():
    # flight_date and deadline_before_trip both draw a city; on about 3% of seeds
    # they used to draw the same one, so "my flight to Tokyo" and "my trip to
    # Tokyo" had two different right dates.
    from src.dataset.generate import list_values

    bank = load_bank()
    everything = {c: len(bank.by_category(c)) for c in CATEGORIES}
    templates = {t.id: t for c in CATEGORIES for t in bank.by_category(c)}
    both = 0
    for seed in range(1000):
        d = generate_dataset(num_turns=120, checkpoints=[120], random_seed=seed,
                             composition=everything, bank=bank)
        seen: set[str] = set()
        for fact in d.facts:
            mine = list_values(templates[fact.id], fact.values)
            assert not mine & seen, (seed, fact.id, mine & seen)
            seen |= mine
        by_id = {f.id: f for f in d.facts}
        if "flight_date" in by_id and "deadline_before_trip" in by_id:
            both += 1
            assert by_id["flight_date"].values["city"] != by_id["deadline_before_trip"].values["city"]
            assert by_id["flight_date"].values["other_city"] != by_id["deadline_before_trip"].values["city"]
    assert both == 1000


def test_default_composition_still_varies_cities_over_seeds():
    cities = {f.values["city"] for seed in range(200)
              for f in generate_dataset(random_seed=seed).facts if f.id in ("flight_date", "deadline_before_trip")}
    assert len(cities) == 6
