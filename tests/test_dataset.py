from src.dataset import SEEDED_FACTS, generate_dataset


def test_every_turn_is_a_real_conversation_turn():
    ds = generate_dataset(num_turns=50, checkpoints=[15, 25, 35, 50])
    assert [t.turn_number for t in ds.turns] == list(range(1, 51))
    assert all(t.human_message for t in ds.turns)


def test_checkpoint_colliding_with_seed_turn_is_probed():
    # 25 and 35 are both seed turns and checkpoints. In v1 the seed won and
    # these recall turns were silently dropped.
    ds = generate_dataset(num_turns=50, checkpoints=[15, 25, 35, 50])
    assert ds.checkpoints == [15, 25, 35, 50]
    seeded_25 = SEEDED_FACTS[25]["id"]
    assert seeded_25 in [f.id for f in ds.probes_at(25)]
    assert ds.turns[24].fact_id == seeded_25  # turn 25 still plants its fact
    assert len(ds.probes_at(25)) == 6  # facts at 1, 3, 7, 12, 18, 25
    assert len(ds.probes_at(35)) == 8
    assert len(ds.probes_at(50)) == 10


def test_checkpoints_outside_the_conversation_are_dropped():
    ds = generate_dataset(num_turns=20, checkpoints=[0, 10, 20, 50])
    assert ds.checkpoints == [10, 20]
    assert [f.turn for f in ds.facts] == [1, 3, 7, 12, 18]
