"""Model calls retry with backoff on rate limits and server errors, and nowhere else."""

from __future__ import annotations

import json

import httpx
import openai
import pytest

from src import retry
from src.backends.registry import AVAILABLE_BACKENDS
from src.fakes import FakeMemoryChatModel

_REQUEST = httpx.Request("POST", "https://inference.example/v1/chat/completions")


def _status_error(cls, code):
    return cls(f"HTTP {code}", response=httpx.Response(code, request=_REQUEST), body=None)


# Errors raised by the flaky model, in order, before it answers normally.
PENDING: list[Exception] = []


class FlakyModel(FakeMemoryChatModel):
    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        if PENDING:
            raise PENDING.pop(0)
        return super()._generate(messages, stop, run_manager, **kwargs)


@pytest.fixture
def sleeps(monkeypatch):
    waited: list[float] = []
    monkeypatch.setattr(retry.time, "sleep", waited.append)
    PENDING.clear()
    yield waited
    PENDING.clear()


def test_rate_limit_and_server_errors_are_retried_with_growing_waits(sleeps):
    PENDING.extend([
        _status_error(openai.RateLimitError, 429),
        _status_error(openai.InternalServerError, 503),
        openai.APIConnectionError(request=_REQUEST),
    ])
    message, retries, ms, waited_ms = retry.invoke_with_retry(FlakyModel(), "hello", "test")
    assert message.content and retries == 3 and ms >= 0 and waited_ms >= 0
    assert len(sleeps) == 3
    for n, wait in enumerate(sleeps):
        base = 2.0 * 2 ** n  # LLM_RETRY_BASE_S defaults to 2
        assert base <= wait <= base * 1.25


def test_client_errors_are_not_retried(sleeps):
    PENDING.append(_status_error(openai.BadRequestError, 400))
    with pytest.raises(openai.BadRequestError):
        retry.invoke_with_retry(FlakyModel(), "hello")
    assert sleeps == []
    PENDING.append(ValueError("a bug, not a network problem"))
    with pytest.raises(ValueError):
        retry.invoke_with_retry(FlakyModel(), "hello")
    assert sleeps == []


def test_retries_stop_at_the_limit(sleeps, monkeypatch, fresh_config):
    monkeypatch.setenv("LLM_MAX_RETRIES", "2")
    fresh_config()
    PENDING.extend([_status_error(openai.RateLimitError, 429) for _ in range(5)])
    with pytest.raises(openai.RateLimitError):
        retry.invoke_with_retry(FlakyModel(), "hello")
    assert len(sleeps) == 2 and len(PENDING) == 2  # three attempts made


def test_status_on_the_response_counts():
    class Wrapped(Exception):
        response = type("R", (), {"status_code": 502})()

    assert retry.is_transient(Wrapped()) and not retry.is_transient(RuntimeError("x"))


def test_answering_call_and_summary_write_survive_a_rate_limit(sleeps):
    backend = AVAILABLE_BACKENDS["summary"](llm=FlakyModel())
    backend.setup()
    PENDING.append(_status_error(openai.RateLimitError, 429))  # the answering call
    exchange = backend.chat("My dog's name is Baxter.")
    assert exchange.response
    PENDING.append(_status_error(openai.InternalServerError, 500))  # the answer
    PENDING.append(_status_error(openai.RateLimitError, 429))  # the summary rewrite
    backend.chat("I live in Lisbon.")
    assert len(sleeps) == 3
    assert "Lisbon" in backend.retrieve("x").text


def test_mem0_adapter_retries_and_forwards_response_format(sleeps):
    from mem0.configs.llms.base import BaseLlmConfig

    from src.backends.mem0_memory import _llm_adapter_class

    seen: list[dict] = []

    class Recording(FlakyModel):
        def _generate(self, messages, stop=None, run_manager=None, **kwargs):
            seen.append(kwargs)
            return super()._generate(messages, stop, run_manager, **kwargs)

    adapter = _llm_adapter_class()(BaseLlmConfig(model=Recording()))
    PENDING.append(_status_error(openai.RateLimitError, 429))
    reply = adapter.generate_response([{"role": "user", "content": "hi"}],
                                      response_format={"type": "json_object"})
    assert reply and len(sleeps) == 1
    assert seen[-1].get("response_format") == {"type": "json_object"}
    assert adapter.usage.calls == 1  # the failed attempt is not counted as a call


def test_judge_retries_before_giving_up(sleeps):
    from src.scoring.judge import Judge
    from tests.test_judge import PROBE

    PENDING.append(_status_error(openai.RateLimitError, 429))
    verdict = Judge(FlakyModel(), "fake", "fake-judge-v1").judge(PROBE)
    assert verdict["label"] == "partial" and len(sleeps) == 1


def test_openai_client_retries_are_off(monkeypatch, fresh_config):
    monkeypatch.setenv("DO_API_KEY", "not-a-real-key")
    fresh_config()
    from src.llm_factory import _do_chat_model

    model = _do_chat_model("anthropic-claude-4.5-sonnet")  # built only, never called
    assert model.max_retries == 0


@pytest.fixture
def real_short_sleeps(monkeypatch):
    """Every backoff really sleeps 0.15 s, so it shows up in a wall-clock timer."""
    import time as _time

    real = _time.sleep
    monkeypatch.setattr(retry.time, "sleep", lambda _delay: real(0.15))
    PENDING.clear()
    yield
    PENDING.clear()


def test_backoff_sleep_is_not_write_latency_and_retries_are_recorded(real_short_sleeps):
    class FailOnceInWrite(AVAILABLE_BACKENDS["summary"]):
        def write(self, human_message, ai_message):
            PENDING.append(_status_error(openai.RateLimitError, 429))  # the summary rewrite
            return super().write(human_message, ai_message)

    backend = FailOnceInWrite(llm=FlakyModel())
    backend.setup()
    PENDING.append(_status_error(openai.RateLimitError, 429))  # the answering call
    exchange = backend.chat("My dog's name is Baxter.")
    assert exchange.llm_retries == 1 and exchange.write_retries == 1
    assert exchange.llm_retry_wait_ms >= 140 and exchange.write_retry_wait_ms >= 140
    # The fake model answers in well under the 150 ms slept.
    assert exchange.write_ms < 100 and exchange.llm_ms < 100
    d = exchange.to_dict()
    assert d["write_retries"] == 1 and d["llm_retries"] == 1


def test_retries_reach_the_transcript_and_the_aggregate(tmp_path, sleeps):
    from src.bundle import read_transcript
    from src.harness import run_benchmark

    class FlakySummary(AVAILABLE_BACKENDS["summary"]):
        name = "summary"

        def write(self, human_message, ai_message):
            if not getattr(self, "_failed", False):
                self._failed = True
                PENDING.append(_status_error(openai.InternalServerError, 503))
            return super().write(human_message, ai_message)

    bundle = run_benchmark([FlakySummary], num_runs=1, num_turns=10, checkpoints=[10],
                           composition={"extraction": 1}, results_dir=tmp_path, judge=False,
                           backend_kwargs={"llm": FlakyModel()})
    turns = [r for r in read_transcript(bundle) if r["type"] == "turn"]
    assert sum(t["write_retries"] for t in turns) == 1
    assert all("llm_retries" in t and "write_retry_wait_ms" in t for t in turns)
    agg = json.loads((bundle / "aggregate.json").read_text())
    assert agg["backends"]["summary"]["retries"]["write"] == 1
    assert agg["backends"]["summary"]["retries"]["answer"] == 0


def test_old_transcripts_without_retry_fields_aggregate_as_zero():
    from src.aggregate import aggregate_records
    from tests.test_harness import _end, _run_probe

    # Rows written before retries were recorded carry none of the fields.
    agg = aggregate_records([_end("buffer", 0), _run_probe("buffer", 0, "f", "Baxter")])
    assert agg["backends"]["buffer"]["retries"] == {
        "answer": 0, "write": 0, "probe": 0, "judge": 0, "wait_s": 0.0}


def _mem0_adapter(model):
    from mem0.configs.llms.base import BaseLlmConfig

    from src.backends.mem0_memory import _llm_adapter_class

    return _llm_adapter_class()(BaseLlmConfig(model=model))


class FormatRejecting(FlakyModel):
    """Answers 400 whenever response_format is bound, like an endpoint without JSON mode."""

    calls: list = []

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        type(self).calls.append(dict(kwargs))
        if "response_format" in kwargs:
            raise _status_error(openai.BadRequestError, 400)
        return super()._generate(messages, stop, run_manager, **kwargs)


def test_mem0_falls_back_without_response_format_when_the_provider_rejects_it(sleeps):
    FormatRejecting.calls = []
    adapter = _mem0_adapter(FormatRejecting())
    msgs = [{"role": "user", "content": "hi"}]
    assert adapter.generate_response(msgs, response_format={"type": "json_object"})
    assert [("response_format" in c) for c in FormatRejecting.calls] == [True, False]
    assert adapter.usage.calls == 1 and adapter.usage.retries == 1 and sleeps == []
    # Later calls skip the format instead of paying for the rejected attempt again.
    adapter.generate_response(msgs, response_format={"type": "json_object"})
    assert [("response_format" in c) for c in FormatRejecting.calls] == [True, False, False]


def test_mem0_raises_a_400_that_is_not_about_the_format():
    class AlwaysBad(FlakyModel):
        def _generate(self, messages, stop=None, run_manager=None, **kwargs):
            raise _status_error(openai.BadRequestError, 400)

    adapter = _mem0_adapter(AlwaysBad())
    with pytest.raises(openai.BadRequestError):
        adapter.generate_response([{"role": "user", "content": "hi"}],
                                  response_format={"type": "json_object"})
    assert adapter.usage.response_format_rejected is False


def test_mem0_write_reports_its_retries(sleeps):
    from src.backends.base import WriteStats

    adapter = _mem0_adapter(FlakyModel())
    PENDING.append(_status_error(openai.RateLimitError, 429))
    adapter.generate_response([{"role": "user", "content": "hi"}])
    assert adapter.usage.retries == 1
    assert WriteStats().retries == 0
