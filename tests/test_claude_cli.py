"""The claude_cli provider against a fake `claude` executable (tests/fake_claude.py).

The fake is a fresh file in pytest's tmp_path; CLAUDE_BIN points at it. No test
touches the real `claude` binary or anything on PATH, and none uses the
subscription.
"""

from __future__ import annotations

import json
import time

import pytest
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from src import claude_cli, retry
from src.claude_cli import (ChatClaudeCLI, ClaudeCLIError, ClaudeCLITransientError, flatten_messages,
                            parse_reset)
from src.retry import UsageLimitError, invoke_with_retry
from tests import fake_claude


@pytest.fixture
def fake(tmp_path, monkeypatch, fresh_config):
    f = fake_claude.install(tmp_path)
    monkeypatch.setenv("CLAUDE_BIN", str(f.bin))
    monkeypatch.setenv("LLM_PROVIDER", "claude_cli")
    monkeypatch.setenv("JUDGE_PROVIDER", "claude_cli")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-must-not-reach-the-cli")
    fresh_config()
    claude_cli.CALLS = 0
    retry.USAGE_LIMIT_PAUSES.clear()
    claude_cli._RESOLVED.clear()
    yield f
    retry.USAGE_LIMIT_PAUSES.clear()
    claude_cli._RESOLVED.clear()


@pytest.fixture
def sleeps(monkeypatch):
    waited: list[float] = []
    monkeypatch.setattr(retry.time, "sleep", waited.append)
    return waited


def model() -> ChatClaudeCLI:
    return ChatClaudeCLI(model="sonnet", timeout_s=30)


# ------------------------------------------------------------------ flattening


def test_single_human_message_is_sent_verbatim_with_the_exact_flags(fake):
    reply = model().invoke([SystemMessage(content="Be brief."), HumanMessage(content="My dog is Rex.")])
    (call,) = fake.calls()
    assert call["stdin"] == "My dog is Rex."
    assert call["system"] == "Be brief."
    argv = call["argv"]
    assert argv[:3] == ["-p", "--model", "sonnet"]
    for flag, value in (("--tools", ""), ("--setting-sources", "")):
        assert argv[argv.index(flag) + 1] == value
    assert {"--strict-mcp-config", "--no-session-persistence"} <= set(argv)
    assert argv[argv.index("--output-format") + 1] == "json"
    assert "--bare" not in argv
    assert isinstance(reply, AIMessage)


def test_runs_in_an_empty_directory_without_api_key_env(fake):
    model().invoke("hello")
    (call,) = fake.calls()
    assert call["cwd_entries"] == [] and "ams-claude-" in call["cwd"]
    assert call["api_key_visible"] is False


def test_multi_message_history_becomes_a_labelled_transcript_without_dropping_turns():
    system, prompt = flatten_messages([
        SystemMessage(content="S1"), SystemMessage(content="S2"),
        HumanMessage(content="first question"), AIMessage(content="first answer"),
        HumanMessage(content="second question"),
    ])
    assert system == "S1\n\nS2"
    order = [prompt.index(t) for t in ("[User]\nfirst question", "[Assistant]\nfirst answer",
                                       "[User]\nsecond question")]
    assert order == sorted(order) and prompt.rstrip().endswith("[Assistant]")


def test_no_system_message_gets_a_neutral_default(fake):
    model().invoke("hi")
    assert fake.calls()[0]["system"] == claude_cli.DEFAULT_SYSTEM


def test_nothing_but_a_system_message_is_refused():
    with pytest.raises(ValueError):
        flatten_messages([SystemMessage(content="only system")])


# ---------------------------------------------- tokens, model id, error mapping


def test_usage_is_input_plus_cache_tokens_and_the_real_model_id_is_recorded(fake):
    reply = model().invoke("one two three four")
    usage = reply.usage_metadata
    # the fake reports 2 fresh + len(words of system+prompt) cache-creation + 5 cache-read tokens
    words = len((claude_cli.DEFAULT_SYSTEM + " " + "one two three four").split())
    assert usage["input_tokens"] == 2 + words + 5
    assert usage["output_tokens"] == len(reply.content.split())
    assert usage["total_tokens"] == usage["input_tokens"] + usage["output_tokens"]
    assert reply.response_metadata["model_name"] == "claude-sonnet-5-5"


def test_model_id_is_resolved_from_modelUsage_not_the_alias(fake):
    from src.llm_factory import judge_model_id, llm_model_id

    fake.rules(model="claude-sonnet-9-9")
    assert llm_model_id() == "claude-sonnet-9-9"
    assert judge_model_id() == "claude-sonnet-9-9"
    assert len(fake.calls()) == 1  # resolved once, then cached


def test_a_permanent_error_is_raised_at_once_and_not_retried(fake, sleeps):
    fake.plan({"error": "Invalid API key. Please run /login"})
    with pytest.raises(ClaudeCLIError) as info:
        invoke_with_retry(model(), "hi")
    assert not isinstance(info.value, ClaudeCLITransientError)
    assert len(fake.calls()) == 1 and sleeps == []


def test_transient_errors_are_retried_with_backoff(fake, sleeps):
    fake.plan({"error": "API Error: Overloaded", "status": 529}, "crash", {"error": "boom", "status": 503})
    message, retries, ms, waited_ms = invoke_with_retry(model(), "hi")
    assert message.content and retries == 3 and len(sleeps) == 3
    assert sleeps[0] < sleeps[1] < sleeps[2]
    assert len(fake.calls()) == 4


def test_timeout_is_transient(fake, sleeps):
    fake.plan("hang")
    short = ChatClaudeCLI(model="sonnet", timeout_s=1)
    start = time.time()
    message, retries, *_ = invoke_with_retry(short, "hi")
    assert retries == 1 and time.time() - start < 20 and message.content


# ---------------------------------------------------------------- usage limits


def test_parse_reset_forms():
    now = 1_800_000_000.0
    assert parse_reset("Claude AI usage limit reached|1800003600", now) == 1_800_003_600
    assert parse_reset("limit reached, resets in 2 hours", now) == now + 7200
    assert parse_reset("try again in 45 minutes", now) == now + 2700
    assert parse_reset("You've hit your limit", now) is None
    when = parse_reset("You've hit your limit - resets 3pm (Asia/Kolkata)", now)
    assert when is not None and now < when <= now + 86400
    assert parse_reset("resets 11:30 pm (Not/AZone)", now) is not None  # unknown zone falls back to local


def test_usage_limit_sleeps_until_reset_without_using_a_retry_or_counting_as_latency(fake, sleeps):
    reset = int(time.time()) + 3000
    fake.plan({"limit": f"Claude AI usage limit reached|{reset}"})
    message, retries, ms, waited_ms = invoke_with_retry(model(), "hi")
    assert message.content and len(fake.calls()) == 2
    assert len(sleeps) == 1 and 3000 <= sleeps[0] <= 3100  # reset plus the one-minute margin
    assert retries == 1  # reported, but it did not spend the retry budget
    assert retry.USAGE_LIMIT_PAUSES[0]["seconds"] == sleeps[0]


def test_usage_limit_does_not_burn_the_retry_budget(fake, sleeps, monkeypatch):
    fake.plan(*[{"limit": "You've hit your limit"}] * 4, {"error": "overloaded", "status": 529})
    message, retries, *_ = retry.call_with_retry(lambda: model().invoke("hi"), max_retries=1)
    assert message.content and retries == 5
    assert sleeps[:4] == [1800.0] * 4  # no reset time: the configured wait


def test_usage_limit_wait_is_capped_and_configurable(fake, sleeps, monkeypatch, fresh_config):
    monkeypatch.setenv("USAGE_LIMIT_MAX_WAIT_S", "600")
    fresh_config()
    fake.plan({"limit": f"usage limit reached|{int(time.time()) + 10 * 3600}"})
    invoke_with_retry(model(), "hi")
    assert sleeps == [600.0]


def test_usage_limit_gives_up_after_the_configured_number_of_pauses(fake, sleeps, monkeypatch, fresh_config):
    monkeypatch.setenv("USAGE_LIMIT_MAX_PAUSES", "2")
    fresh_config()
    fake.plan(*[{"limit": "usage limit reached"}] * 5)
    with pytest.raises(UsageLimitError):
        invoke_with_retry(model(), "hi")
    assert len(sleeps) == 2


def test_a_model_answer_that_mentions_a_limit_is_not_a_usage_limit(fake, sleeps):
    fake.plan({"prose": "My usage limit reached the ceiling, as you said."})
    message, retries, *_ = invoke_with_retry(model(), "hi")
    assert "ceiling" in message.content and retries == 0 and sleeps == []


# ------------------------------------------------------------------ JSON (mem0)


def test_response_format_json_gets_valid_json_even_from_a_fenced_reply(fake):
    fake.plan({"prose": 'Sure!\n```json\n{"memory": [{"id": "0", "text": "I like tea"}]}\n```'})
    reply = model().bind(response_format={"type": "json_object"}).invoke("extract")
    assert json.loads(reply.content) == {"memory": [{"id": "0", "text": "I like tea"}]}
    assert "JSON" in fake.calls()[0]["system"]


def test_a_prose_reply_to_a_json_request_is_retried(fake, sleeps):
    fake.plan({"prose": "I could not do that."}, {"prose": '{"label": "correct"}'})
    bound = model().bind(response_format={"type": "json_object"})
    message, retries, *_ = invoke_with_retry(bound, "extract")
    assert retries == 1 and json.loads(message.content) == {"label": "correct"}


def test_mem0_adapter_returns_valid_json_and_counts_tokens(fake):
    pytest.importorskip("mem0")
    from mem0.configs.llms.base import BaseLlmConfig

    from src.backends.mem0_memory import _llm_adapter_class

    llm = _llm_adapter_class()(BaseLlmConfig(model=model()))
    system = "You are a Memory Extractor."
    user = ("## Existing Memories\n[]\n\n## New Messages\nuser: I live in Pune.\nassistant: Nice.\n\n"
            "## Observation Date\n2026-01-01")
    out = llm.generate_response([{"role": "system", "content": system}, {"role": "user", "content": user}],
                                response_format={"type": "json_object"})
    assert json.loads(out)["memory"][0]["text"] == "I live in Pune."
    assert llm.usage.calls == 1 and llm.usage.input_tokens > 0 and llm.usage.output_tokens > 0


def test_tools_are_not_supported():
    with pytest.raises(NotImplementedError):
        model().bind_tools([])


# ----------------------------------------------------- factory, manifest, pricing


def test_factory_builds_the_cli_model_for_both_roles_and_rejects_unknown_providers(fake, monkeypatch, fresh_config):
    from src.llm_factory import get_judge_llm, get_llm

    assert isinstance(get_llm(), ChatClaudeCLI) and isinstance(get_judge_llm(), ChatClaudeCLI)
    monkeypatch.setenv("LLM_PROVIDER", "nope")
    fresh_config()
    with pytest.raises(ValueError, match="claude_cli"):
        get_llm()


def test_price_entry_for_the_real_model_id_exists():
    from src.pricing import price_for

    price = price_for("claude-sonnet-5-5")
    assert price and (price.input_per_mtok, price.output_per_mtok) == (2.0, 10.0)
    assert price.source.startswith("https://") and price.checked_on


def test_manifest_caveats_and_report_note(fake):
    from src.harness import build_manifest
    from src.report import provider_note

    m = build_manifest(["buffer"], 1, 5, {}, [5], None, judge=True)
    assert m["llm_provider"] == "claude_cli" and m["llm_model"] == "claude-sonnet-5-5"
    caveats = m["provider_caveats"]
    assert caveats["cost_basis"] == "api_equivalent"
    assert caveats["temperature_controllable"] is False and caveats["llm_latency_comparable"] is False
    note = provider_note(caveats)
    assert "API-equivalent" in note and "not comparable" in note and "Temperature" in note
    assert provider_note({}) == ""


# ------------------------------------------------------------------ review fixes


def test_every_anthropic_and_cloud_variable_is_stripped_from_the_child(fake, monkeypatch):
    for name in ("ANTHROPIC_BASE_URL", "CLAUDE_CODE_USE_BEDROCK", "AWS_SECRET_ACCESS_KEY"):
        monkeypatch.setenv(name, "x")
    model().invoke("hello")
    env = claude_cli._child_env() if hasattr(claude_cli, "_child_env") else None
    if env is not None:
        assert not [k for k in env if k.startswith(claude_cli.STRIPPED_PREFIXES)]
    assert fake.calls()[-1]["api_key_visible"] is False


def test_limit_detection_ignores_bare_limit_words_and_context_overflow():
    assert claude_cli.is_usage_limit("Claude AI usage limit reached|1700000000")
    assert claude_cli.is_usage_limit("You've hit your 5-hour limit. Resets at 3pm")
    assert not claude_cli.is_usage_limit("The rate limit reached for this endpoint")
    assert not claude_cli.is_usage_limit("Prompt is too long: context limit reached")


def test_a_limit_notice_returned_as_a_normal_result_still_pauses(fake, sleeps):
    fake.plan({"prose": "Claude AI usage limit reached|4102444800"}, "ok")
    message, *_ = invoke_with_retry(model(), "hi")
    assert sleeps and message.content


def test_torn_last_line_is_cut_off_and_complete_lines_are_kept(tmp_path):
    from src.bundle import repair_jsonl

    path = tmp_path / "t.jsonl"
    path.write_text('{"a": 1}\n{"a": 2}\n{"a": 3, "tor')
    assert repair_jsonl(path) is True
    assert path.read_text() == '{"a": 1}\n{"a": 2}\n'
    assert repair_jsonl(path) is False
    path.write_text('{"a": 1}')
    assert repair_jsonl(path) is True and path.read_text() == '{"a": 1}\n'


def test_judge_cache_does_not_reuse_a_verdict_for_a_different_response(tmp_path):
    from src.scoring.rescore import JudgeCache

    class J:
        def info(self):
            return {"judge_model": "m", "judge_prompt_hash": "h"}

    rec = {"backend": "b", "run_index": 0, "checkpoint": 1, "fact_id": "p", "question": "q",
           "answer_key": "k", "response": "one"}
    cache = JudgeCache(tmp_path / "c.jsonl", J())
    cache.put(rec, {"label": "correct"})
    assert cache.get(rec) == {"label": "correct"}
    assert cache.get({**rec, "response": "two"}) is None
    (tmp_path / "c.jsonl").write_text((tmp_path / "c.jsonl").read_text() + '{"torn')
    assert JudgeCache(tmp_path / "c.jsonl", J()).get(rec) == {"label": "correct"}


# ------------------------------------------------------------- second review round


@pytest.mark.parametrize("llm,judge_provider,judge_on,billing,judge_note", [
    ("do", "claude_cli", True, False, True),
    ("do", "claude_cli", False, False, False),
    ("claude_cli", "claude_cli", True, True, False),
    ("claude_cli", "do", True, True, False),
    ("do", "do", True, False, False),
])
def test_provider_caveats_follow_the_answering_provider(monkeypatch, fresh_config, llm, judge_provider,
                                                        judge_on, billing, judge_note):
    from src.harness import build_manifest
    from src.report import provider_note

    monkeypatch.setenv("LLM_PROVIDER", llm)
    monkeypatch.setenv("JUDGE_PROVIDER", judge_provider)
    fresh_config()
    monkeypatch.setattr("src.llm_factory.llm_model_id", lambda: "x")
    monkeypatch.setattr("src.harness.llm_model_id", lambda: "x")
    monkeypatch.setattr("src.harness.judge_model_id", lambda: "x", raising=False)
    m = build_manifest(["buffer"], 1, 5, {}, [5], None, judge=judge_on)
    caveats = m["provider_caveats"]
    assert ("cost_basis" in caveats) is billing
    assert ("llm_latency_comparable" in caveats) is billing
    assert ("temperature_controllable" in caveats) is billing
    assert ("judge_note" in caveats) is judge_note
    note = provider_note(caveats)
    assert ("costs are API-equivalent" in note) is billing
    assert ("The judge runs on a Claude subscription" in note) is judge_note
    assert ("540 tokens" in note) is billing
    if not billing and not judge_note:
        assert caveats == {} and note == ""
