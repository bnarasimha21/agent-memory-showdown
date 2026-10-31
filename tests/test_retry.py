"""Model calls retry with backoff on rate limits and server errors, and nowhere else."""

from __future__ import annotations

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
    message, retries, ms = retry.invoke_with_retry(FlakyModel(), "hello", "test")
    assert message.content and retries == 3 and ms >= 0
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
