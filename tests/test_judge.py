import json

from src.aggregate import aggregate_records
from src.fakes import FakeMemoryChatModel
from src.scoring.judge import Judge, judge_input, parse_verdict, prompt_hash, render
from src.scoring.rescore import score_probes

PROBE = {
    "type": "probe", "backend": "b", "run_index": 0, "checkpoint": 10, "fact_id": "melatonin_dose",
    "question": "What supplement do I take before bed and at what dose?",
    "answer_key": "melatonin, 10 mg", "answers": [["melatonin"], ["10 mg"]], "stale": [],
    "response": "You take melatonin.", "input_tokens": 0, "output_tokens": 0,
}


def test_prompt_renders_the_probe_and_has_a_stable_hash():
    text = render(PROBE)
    assert "JUDGE_INPUT_JSON:" in text and "You take melatonin." in text
    assert "{input_json}" not in text
    assert len(prompt_hash()) == 64
    assert judge_input(PROBE)["required_parts"] == [["melatonin"], ["10 mg"]]


def test_parse_verdict():
    assert parse_verdict('{"label": "Correct", "rationale": "ok"}') == ("correct", "ok")
    assert parse_verdict('Sure.\n{"label": "refused", "rationale": "declined"}')[0] == "refused"
    assert parse_verdict("no json here")[0] == "error"
    assert parse_verdict('{"label": "maybe"}')[0] == "error"


def test_fake_judge_follows_the_matcher():
    judge = Judge(FakeMemoryChatModel(), "fake", "fake-judge-v1")
    verdict = judge.judge(PROBE)
    assert verdict["label"] == "partial"
    assert verdict["input_tokens"] > 0


class StubLLM(FakeMemoryChatModel):
    reply: str = '{"label": "correct", "rationale": "close enough"}'

    def respond(self, text):
        return self.reply


def test_disagreements_and_kappa_are_reported():
    recs = [{"backend": "b", "run_index": 0, "type": "run_end", "error": None}]
    recs += [dict(PROBE, fact_id=f"f{i}", response="You take 10 mg of melatonin.") for i in range(3)]
    recs += [dict(PROBE, fact_id="x")]  # matcher says partial
    scores = score_probes(recs, Judge(StubLLM(), "stub", "stub-1"))
    agg = aggregate_records(recs, scores=scores, scoring={"judge_model": "stub-1"})
    b = agg["backends"]["b"]
    assert b["scorer"] == "judge"
    assert b["recall_overall"]["counts"]["correct"] == 4  # judge labels are primary
    assert b["matcher"]["recall_overall"]["counts"]["partial"] == 1
    assert agg["agreement"]["disagreements"] == 1
    assert agg["agreement"]["disagreement_list"][0]["fact_id"] == "x"
    assert agg["agreement"]["kappa"] == 0.0  # judge is constant, so chance agreement only
    for row in agg["probes"]:
        assert {"matcher_label", "judge_label", "judge_rationale"} <= set(row)
    json.dumps(agg)


def test_judge_errors_fall_back_to_the_matcher():
    recs = [{"backend": "b", "run_index": 0, "type": "run_end", "error": None}, dict(PROBE)]
    stub = StubLLM(reply="not json")
    scores = score_probes(recs, Judge(stub, "stub", "stub-1"))
    assert scores[0]["judge_label"] == "error"
    b = aggregate_records(recs, scores=scores)["backends"]["b"]
    assert b["recall_overall"]["counts"]["partial"] == 1
    assert b["judge"]["errors"] == 1
