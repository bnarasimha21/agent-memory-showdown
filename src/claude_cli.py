"""Chat model that runs the `claude` CLI, so the benchmark uses a Claude subscription.

Selected with `LLM_PROVIDER=claude_cli` and/or `JUDGE_PROVIDER=claude_cli`.
Every call is one process:

    claude -p --model <alias> --system-prompt <system text> --tools ""
           --strict-mcp-config --setting-sources "" --no-session-persistence
           --output-format json          (prompt on stdin, cwd = an empty temp dir)

That combination sends only the system text and the prompt (about 540 input
tokens of overhead): no CLAUDE.md, no memory files, no tools, no MCP servers.
`--bare` is deliberately not used, because it ignores the subscription login.
ANTHROPIC_API_KEY and ANTHROPIC_AUTH_TOKEN are removed from the child's
environment so a stray key can never turn a subscription run into a billed one.

What the CLI cannot do, and the consequences:

- no temperature: the model samples at its default (recorded in the manifest as
  `temperature_controllable: false`);
- latency includes process start-up (about 2 s), so LLM latency from this
  provider is not comparable with an API provider (`llm_latency_comparable:
  false` in the manifest); memory read and write latencies are unaffected;
- no tool calling and no structured-output mode: `response_format` asks for
  JSON in the system text and the reply is checked to be valid JSON.

Errors map onto src/retry.py: a transient failure (timeout, overloaded, CLI
crash, malformed JSON when JSON was requested) raises `ClaudeCLITransientError`
(retried with backoff); a subscription usage limit raises `UsageLimitError`
(slept out until the reset time, no retry used, sleep not counted as latency);
anything else (not logged in, bad flag) raises `ClaudeCLIError` at once.
"""

from __future__ import annotations

import json
import logging
import os
import re
import shutil
import subprocess
import tempfile
import time
from datetime import datetime, timedelta
from typing import Any, List, Optional

from langchain_core.callbacks import CallbackManagerForLLMRun
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult

from src.retry import UsageLimitError

logger = logging.getLogger(__name__)

DEFAULT_SYSTEM = "You are a helpful assistant."
JSON_INSTRUCTION = ("Respond with a single valid JSON object and nothing else: no prose before or "
                    "after it and no code fences.")
# Variables that would make the CLI bill an API account instead of the subscription.
STRIPPED_ENV = ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN")


# Number of `claude` processes started by this Python process (all attempts).
CALLS = 0


class ClaudeCLIError(RuntimeError):
    """The CLI failed in a way that retrying will not fix."""


class ClaudeCLITransientError(ClaudeCLIError):
    """The CLI failed in a way that is worth retrying (src/retry.py checks `transient`)."""

    transient = True


# ----------------------------------------------------------------- flattening


def _text(message: BaseMessage) -> str:
    content = message.content
    if isinstance(content, str):
        return content
    parts = []
    for block in content:
        parts.append(block if isinstance(block, str) else str(block.get("text", "")) if isinstance(block, dict) else str(block))
    return "".join(parts)


def flatten_messages(messages: List[BaseMessage]) -> tuple[str, str]:
    """(system text, prompt) for the CLI.

    System messages are joined into the system prompt. A conversation that is
    a single human message is sent as it is, which is what every benchmark
    call is. Anything longer is sent as a labelled transcript ending with a cue
    for the assistant's turn, so no turn is dropped or merged.
    """
    system = "\n\n".join(_text(m) for m in messages if m.type == "system").strip()
    rest = [m for m in messages if m.type != "system"]
    if not rest:
        raise ValueError("No non-system message to send to the model")
    if len(rest) == 1 and rest[0].type == "human":
        return system, _text(rest[0])
    labels = {"human": "User", "ai": "Assistant"}
    lines = ["Below is the conversation so far. Write the next Assistant turn only.", ""]
    for m in rest:
        lines += [f"[{labels.get(m.type, m.type.capitalize())}]", _text(m), ""]
    lines.append("[Assistant]")
    return system, "\n".join(lines)


# ------------------------------------------------------------- error handling

_LIMIT_RE = re.compile(r"usage limit|limit reached|hit your (?:\w+ )?limit|reached your (?:\w+ )?limit"
                       r"|out of (?:extra )?usage|session limit|weekly limit", re.I)
_EPOCH_RE = re.compile(r"\|\s*(\d{10})\b")
_CLOCK_RE = re.compile(r"resets?\s*(?:at\s*)?(\d{1,2})(?::(\d{2}))?\s*([ap]m)(?:\s*\(([^)]+)\))?", re.I)
_IN_RE = re.compile(r"(?:resets?|try again|available)\s+in\s+(?:about\s+)?(\d+(?:\.\d+)?)\s*"
                    r"(hours?|hrs?|h|minutes?|mins?|m)\b", re.I)
_TRANSIENT_TEXT = re.compile(r"overloaded|timed? ?out|timeout|temporar|econn|socket|connection|"
                             r"\b(?:429|500|502|503|504|529)\b|internal server|unavailable|try again", re.I)
_AUTH_TEXT = re.compile(r"log ?in|logged|authenticat|invalid api key|credit balance|unauthori[sz]ed", re.I)


def is_usage_limit(text: str) -> bool:
    return bool(_LIMIT_RE.search(text or ""))


def parse_reset(text: str, now: float | None = None) -> float | None:
    """Reset time as epoch seconds, from a usage-limit message, or None."""
    now = time.time() if now is None else now
    m = _EPOCH_RE.search(text)
    if m:
        return float(m.group(1))
    m = _IN_RE.search(text)
    if m:
        amount = float(m.group(1))
        return now + amount * (3600 if m.group(2).lower().startswith("h") else 60)
    m = _CLOCK_RE.search(text)
    if m:
        hour, minute = int(m.group(1)) % 12, int(m.group(2) or 0)
        if m.group(3).lower() == "pm":
            hour += 12
        tz = None
        if m.group(4):
            try:
                from zoneinfo import ZoneInfo

                tz = ZoneInfo(m.group(4).strip())
            except Exception:  # unknown zone name: fall back to local time
                tz = None
        base = datetime.fromtimestamp(now, tz)
        target = base.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if target.timestamp() <= now:
            target += timedelta(days=1)
        return target.timestamp()
    return None


def usage_limit_error(text: str, now: float | None = None) -> UsageLimitError:
    from src.config import config

    now = time.time() if now is None else now
    reset = parse_reset(text, now)
    # A minute of margin after the stated reset; no stated reset = the configured wait.
    wait = (reset - now + 60) if reset is not None else config.USAGE_LIMIT_WAIT_S
    return UsageLimitError(text.strip()[:300], max(1.0, wait), reset)


# ------------------------------------------------------------------ the model


def claude_bin() -> str:
    from src.config import config

    path = config.CLAUDE_BIN or shutil.which("claude")
    if not path:
        raise ClaudeCLIError("The 'claude' CLI was not found on PATH. Install Claude Code or set CLAUDE_BIN.")
    return path


def extract_json(text: str) -> str:
    """The first JSON object in `text` (code fences and surrounding prose removed), re-serialised."""
    decoder = json.JSONDecoder()
    pos = text.find("{")
    while pos != -1:
        try:
            data, _ = decoder.raw_decode(text, pos)
        except json.JSONDecodeError:
            pos = text.find("{", pos + 1)
            continue
        if isinstance(data, dict):
            return json.dumps(data, ensure_ascii=False)
        pos = text.find("{", pos + 1)
    raise ValueError("no JSON object in the reply")


class ChatClaudeCLI(BaseChatModel):
    """LangChain chat model over `claude -p`. One process per call, no concurrency."""

    model: str = "sonnet"
    timeout_s: float = 300.0
    # Real model id seen in the CLI's `modelUsage` on the last call.
    last_model_id: Optional[str] = None

    @property
    def _llm_type(self) -> str:
        return "claude-cli"

    def bind_tools(self, *args: Any, **kwargs: Any):
        raise NotImplementedError("the claude_cli provider has no tool calling")

    def _command(self, system: str) -> list[str]:
        return [claude_bin(), "-p", "--model", self.model, "--system-prompt", system or DEFAULT_SYSTEM,
                "--tools", "", "--strict-mcp-config", "--setting-sources", "",
                "--no-session-persistence", "--output-format", "json"]

    def run_cli(self, system: str, prompt: str) -> dict:
        """One CLI call; returns the parsed JSON result or raises (see module docstring)."""
        global CALLS
        CALLS += 1
        env = {k: v for k, v in os.environ.items() if k not in STRIPPED_ENV}
        with tempfile.TemporaryDirectory(prefix="ams-claude-") as cwd:  # empty: nothing to read
            try:
                proc = subprocess.run(self._command(system), input=prompt, capture_output=True,
                                      text=True, timeout=self.timeout_s, cwd=cwd, env=env)
            except subprocess.TimeoutExpired as exc:
                raise ClaudeCLITransientError(f"claude CLI timed out after {self.timeout_s:.0f} s") from exc
            except OSError as exc:
                raise ClaudeCLIError(f"could not run the claude CLI: {exc}") from exc
        out, err = (proc.stdout or "").strip(), (proc.stderr or "").strip()
        data = None
        if out:
            try:
                data = json.loads(out)
            except json.JSONDecodeError:
                data = None
        if not isinstance(data, dict):
            detail = (err or out)[:300] or "no output"
            if is_usage_limit(detail):
                raise usage_limit_error(detail)
            if proc.returncode != 0 and _AUTH_TEXT.search(detail):
                raise ClaudeCLIError(f"claude CLI exited {proc.returncode}: {detail}")
            raise ClaudeCLITransientError(f"claude CLI exited {proc.returncode} without JSON: {detail}")
        result = data.get("result")
        text = result if isinstance(result, str) else ""
        if data.get("is_error") or proc.returncode != 0:
            detail = (text or err or json.dumps(data)[:300]).strip()
            if is_usage_limit(detail):
                raise usage_limit_error(detail)
            status = data.get("api_error_status")
            if (isinstance(status, int) and (status == 429 or status >= 500)) or (
                    _TRANSIENT_TEXT.search(detail) and not _AUTH_TEXT.search(detail)):
                raise ClaudeCLITransientError(f"claude CLI error: {detail[:300]}")
            raise ClaudeCLIError(f"claude CLI error: {detail[:300]}")
        return data

    def _generate(self, messages: List[BaseMessage], stop: Optional[List[str]] = None,
                  run_manager: Optional[CallbackManagerForLLMRun] = None, **kwargs: Any) -> ChatResult:
        system, prompt = flatten_messages(messages)
        want_json = (kwargs.get("response_format") or {}).get("type") in ("json_object", "json_schema")
        if want_json:
            system = f"{system}\n\n{JSON_INSTRUCTION}".strip()
        data = self.run_cli(system, prompt)
        text = data.get("result") if isinstance(data.get("result"), str) else ""
        if want_json:
            try:
                text = extract_json(text)
            except ValueError as exc:  # the model answered in prose: worth another attempt
                raise ClaudeCLITransientError(f"JSON was requested but the reply is not JSON: {text[:120]!r}") from exc
        usage = data.get("usage") or {}
        in_tok = (int(usage.get("input_tokens") or 0) + int(usage.get("cache_creation_input_tokens") or 0)
                  + int(usage.get("cache_read_input_tokens") or 0))
        out_tok = int(usage.get("output_tokens") or 0)
        model_usage = data.get("modelUsage") or {}
        model_id = next(iter(model_usage), None) or self.model
        if self.last_model_id not in (None, model_id):
            logger.warning("claude CLI answered with model %s, earlier calls used %s", model_id, self.last_model_id)
        self.last_model_id = model_id
        message = AIMessage(
            content=text,
            usage_metadata={"input_tokens": in_tok, "output_tokens": out_tok, "total_tokens": in_tok + out_tok},
            response_metadata={"model_name": model_id, "total_cost_usd": data.get("total_cost_usd")},
        )
        return ChatResult(generations=[ChatGeneration(message=message)],
                          llm_output={"model_name": model_id})


_RESOLVED: dict[tuple[str, str], str] = {}


def resolve_model_id(alias: str) -> str:
    """The real model id behind a CLI alias such as `sonnet`, from one tiny call (cached).

    Needed before a run starts, because the manifest and the price lookup use
    the id the API reports, not the alias."""
    from src.config import config
    from src.retry import invoke_with_retry

    key = (config.CLAUDE_BIN or "", alias)
    if key not in _RESOLVED:
        model = ChatClaudeCLI(model=alias, timeout_s=config.CLAUDE_CLI_TIMEOUT_S)
        from langchain_core.messages import HumanMessage

        invoke_with_retry(model, [HumanMessage(content="Reply with the single word OK.")],
                          "claude_cli model id probe")
        _RESOLVED[key] = model.last_model_id or alias
    return _RESOLVED[key]
