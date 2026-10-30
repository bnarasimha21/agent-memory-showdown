import pytest

from src.aggregate import aggregate_records
from src.pricing import load_pricing, price_for


def test_fixed_tokens_and_price_table_give_the_expected_cost(tmp_path):
    table = tmp_path / "pricing.yaml"
    table.write_text(
        "models:\n  m:\n    input_per_mtok: 2.5\n    output_per_mtok: 10\n"
        "    source: test\n    checked_on: '2026-01-01'\n"
    )
    price = load_pricing(table)["m"]
    # 400,000 in * 2.5/M = 1.00 ; 30,000 out * 10/M = 0.30
    assert price.cost(400_000, 30_000) == pytest.approx(1.30)


def test_missing_fields_are_rejected(tmp_path):
    table = tmp_path / "pricing.yaml"
    table.write_text("models:\n  m:\n    input_per_mtok: 1\n")
    with pytest.raises(ValueError):
        load_pricing(table)


def test_repo_pricing_has_source_and_date_for_the_default_model():
    price = price_for("anthropic-claude-4.5-sonnet")
    assert price.input_per_mtok == 3.0 and price.output_per_mtok == 15.0
    assert price.source.startswith("https://") and price.checked_on


def _turn(run, n, i, o, wi=0, wo=0, calls=0):
    return {"backend": "b", "run_index": run, "type": "turn", "turn": n, "input_tokens": i,
            "output_tokens": o, "write_input_tokens": wi, "write_output_tokens": wo,
            "write_llm_calls": calls, "retrieve_ms": 1.0, "llm_ms": 10.0 * n, "write_ms": 2.0}


def test_aggregate_cost_uses_input_and_output_separately():
    recs = [{"backend": "b", "run_index": 0, "type": "run_end", "error": None,
             "memory_stats": {"size": 4, "unit": "messages"}}]
    # buffer-like: mostly input. 2 turns of 1000 in / 10 out, one summarizer call.
    recs += [_turn(0, 1, 1000, 10), _turn(0, 2, 1000, 10, wi=500, wo=50, calls=1)]
    recs += [{"backend": "b", "run_index": 0, "type": "probe", "checkpoint": 2, "fact_id": "f",
              "question": "q", "answer_key": "baxter", "response": "Baxter", "input_tokens": 100,
              "output_tokens": 0, "retrieve_ms": 1.0, "llm_ms": 1.0, "write_ms": 0.0}]
    agg = aggregate_records(recs, {"llm_model": "anthropic-claude-4.5-sonnet"})
    b = agg["backends"]["b"]
    conv = (2500 * 3 + 70 * 15) / 1e6
    assert b["cost"]["per_conversation_usd"] == pytest.approx(conv)
    assert b["cost"]["per_1k_conversations_usd"] == pytest.approx(conv * 1000)
    assert b["cost"]["memory_maintenance_per_conversation_usd"] == pytest.approx((500 * 3 + 50 * 15) / 1e6)
    assert b["cost"]["per_correct_recall_usd"] == pytest.approx(conv + 100 * 3 / 1e6)
    assert b["tokens"]["memory"]["calls"] == 1
    assert b["latency"]["llm_ms"]["p50"] == pytest.approx(15.0)
    assert b["latency"]["llm_ms"]["p95"] == pytest.approx(19.5)
    assert b["memory_size_end"] == {"mean": 4, "max": 4, "unit": "messages"}
    assert agg["pricing"]["source"].startswith("https://")


def test_unpriced_model_reports_no_cost():
    recs = [{"backend": "b", "run_index": 0, "type": "run_end", "error": None}, _turn(0, 1, 10, 1)]
    agg = aggregate_records(recs, {"llm_model": "unknown-model"})
    assert agg["backends"]["b"]["cost"] is None and agg["pricing"]["unpriced"]
