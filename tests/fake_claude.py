"""A fake `claude` executable for the claude_cli tests.

`install(tmp_path)` writes a fresh Python script into the test's temp
directory (a plain file, never a link, and never anywhere on PATH) and returns
its path; tests point CLAUDE_BIN at it. The script answers like the offline
fake model (src/fakes.py) in the CLI's JSON output format, logs every
invocation (argv, stdin, cwd, whether ANTHROPIC_API_KEY was visible) to
`calls.jsonl`, and follows `plan.json`: a list of behaviours consumed one per
call, then the default answer. Behaviours:

    "ok"                    answer normally
    {"limit": text}         is_error result carrying a usage-limit message
    {"error": text}         is_error result (api_error_status optional)
    {"prose": text}         answer with this text instead of the fake model's
    "crash"                 exit 1 with no output
    "hang"                  sleep 60 s (to hit a timeout)

`fail_from` / `fail_until` in `rules.json` make every call whose 1-based index
is in [fail_from, fail_until) a permanent error, to interrupt a benchmark.
"""

from __future__ import annotations

import json
import os
import stat
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

SCRIPT = '''#!{python}
import json, os, sys, time
sys.path.insert(0, {root!r})
state = {state!r}
argv = sys.argv[1:]
prompt = sys.stdin.read()
def opt(name):
    return argv[argv.index(name) + 1] if name in argv else None
system = opt("--system-prompt") or ""
log = {{"argv": argv, "stdin": prompt, "system": system, "cwd": os.getcwd(),
        "cwd_entries": sorted(os.listdir(".")), "api_key_visible": "ANTHROPIC_API_KEY" in os.environ,
        "env_names": sorted(os.environ)}}
with open(os.path.join(state, "calls.jsonl"), "a") as fh:
    fh.write(json.dumps(log) + "\\n")
n = sum(1 for _ in open(os.path.join(state, "calls.jsonl")))
plan_path = os.path.join(state, "plan.json")
plan = json.load(open(plan_path)) if os.path.exists(plan_path) else []
step = plan.pop(0) if plan else "ok"
json.dump(plan, open(plan_path, "w"))
rules_path = os.path.join(state, "rules.json")
rules = json.load(open(rules_path)) if os.path.exists(rules_path) else {{}}
if rules.get("fail_from") and rules["fail_from"] <= n < rules.get("fail_until", 10**9):
    step = {{"error": "invalid credentials: please log in"}}
MODEL = rules.get("model", "claude-sonnet-5-5")

def emit(result, is_error=False, status=None, words_in=None):
    in_tok = words_in if words_in is not None else len((system + " " + prompt).split())
    out_tok = len(result.split())
    print(json.dumps({{
        "type": "result", "subtype": "error" if is_error else "success", "is_error": is_error,
        "api_error_status": status, "result": result, "total_cost_usd": 0.001,
        "usage": {{"input_tokens": 2, "cache_creation_input_tokens": in_tok, "cache_read_input_tokens": 5,
                  "output_tokens": out_tok}},
        "modelUsage": {{MODEL: {{"inputTokens": 2, "outputTokens": out_tok}}}},
    }}))
    sys.exit(1 if is_error else 0)

if step == "crash":
    sys.exit(1)
if step == "hang":
    time.sleep(60)
if isinstance(step, dict) and "limit" in step:
    emit(step["limit"], is_error=True)
if isinstance(step, dict) and "error" in step:
    emit(step["error"], is_error=True, status=step.get("status"))
if isinstance(step, dict) and "prose" in step:
    emit(step["prose"])
# Importing langchain costs about a second per call; src.fakes only needs its names to exist.
import types
class _Any(types.ModuleType):
    def __getattr__(self, name):
        return type(name, (), {{}})
for mod in ("langchain_core", "langchain_core.callbacks", "langchain_core.embeddings",
            "langchain_core.language_models", "langchain_core.messages", "langchain_core.outputs"):
    sys.modules[mod] = _Any(mod)
from src.fakes import FakeMemoryChatModel
emit(FakeMemoryChatModel().respond(system + "\\n" + prompt))
'''


class FakeClaude:
    def __init__(self, directory: Path) -> None:
        self.dir = directory
        self.bin = directory / "claude"

    def plan(self, *steps) -> None:
        (self.dir / "plan.json").write_text(json.dumps(list(steps)))

    def rules(self, **rules) -> None:
        (self.dir / "rules.json").write_text(json.dumps(rules))

    def calls(self) -> list[dict]:
        path = self.dir / "calls.jsonl"
        return [json.loads(line) for line in path.read_text().splitlines()] if path.exists() else []


def install(tmp_path: Path) -> FakeClaude:
    directory = tmp_path / "fake-claude"
    directory.mkdir()
    fake = FakeClaude(directory)
    assert not fake.bin.exists() and not fake.bin.is_symlink()
    fake.bin.write_text(SCRIPT.format(python=sys.executable, root=str(ROOT), state=str(directory)))
    fake.bin.chmod(fake.bin.stat().st_mode | stat.S_IXUSR)
    assert os.path.realpath(fake.bin) == str(fake.bin.resolve())
    return fake
