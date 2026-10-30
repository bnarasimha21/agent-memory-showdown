"""LLM judge over saved probe responses.

The prompt lives in `judge_prompt.md` next to this file; its sha256 and the
judge model are recorded wherever judge labels are written. The judge never
sees the backend name.
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage

from src.backends.base import usage_from_message
from src.scoring import LABELS
from src.scoring.matcher import answers_of, expects_abstention

PROMPT_PATH = Path(__file__).with_name("judge_prompt.md")
INPUT_MARKER = "JUDGE_INPUT_JSON:"


def load_prompt() -> str:
    return PROMPT_PATH.read_text(encoding="utf-8")


def prompt_hash() -> str:
    return hashlib.sha256(load_prompt().encode("utf-8")).hexdigest()


def judge_input(record: dict) -> dict:
    abstain = expects_abstention(record)
    return {
        "question": record["question"],
        "expect_abstention": abstain,
        "expected": "(never stated)" if abstain else record["answer_key"],
        "required_parts": answers_of(record),
        "stale_values": list(record.get("stale") or []),
        "response": record["response"],
    }


def render(record: dict, template: str | None = None) -> str:
    template = template if template is not None else load_prompt()
    payload = json.dumps(judge_input(record), ensure_ascii=False, indent=2)
    return template.replace("{input_json}", payload)


def parse_verdict(text: str) -> tuple[str, str]:
    """(label, rationale). Unparseable output becomes label `error`."""
    for candidate in re.findall(r"\{[^{}]*\}", text, flags=re.DOTALL):
        try:
            data = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        label = str(data.get("label", "")).strip().lower()
        if label in LABELS:
            return label, str(data.get("rationale", "")).strip()
    return "error", f"unparseable judge output: {text.strip()[:200]}"


class Judge:
    def __init__(self, llm: BaseChatModel, provider: str, model: str) -> None:
        self.llm = llm
        self.provider = provider
        self.model = model
        self.template = load_prompt()

    def info(self) -> dict:
        return {
            "judge_provider": self.provider,
            "judge_model": self.model,
            "judge_prompt": str(PROMPT_PATH.relative_to(PROMPT_PATH.parents[2])),
            "judge_prompt_hash": prompt_hash(),
        }

    def judge(self, record: dict) -> dict:
        try:
            message = self.llm.invoke([HumanMessage(content=render(record, self.template))])
        except Exception as exc:  # one failed call should not lose the whole rescore
            return {"label": "error", "rationale": f"{type(exc).__name__}: {exc}",
                    "input_tokens": 0, "output_tokens": 0}
        text = message.content if isinstance(message.content, str) else str(message.content)
        label, rationale = parse_verdict(text)
        if label == "abstained" and expects_abstention(record):
            # The rubric asks for `correct` here; an `abstained` verdict means
            # the same thing, so it is mapped rather than counted as a miss.
            label, rationale = "correct", f"(abstained, which is correct here) {rationale}"
        in_tok, out_tok = usage_from_message(message)
        return {"label": label, "rationale": rationale,
                "input_tokens": in_tok, "output_tokens": out_tok}


def get_judge() -> Judge:
    from src.config import config
    from src.llm_factory import get_judge_llm, judge_model_id

    return Judge(get_judge_llm(), config.JUDGE_PROVIDER, judge_model_id())
