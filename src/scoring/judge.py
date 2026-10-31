"""LLM judge over saved probe responses.

The prompt lives in `judge_prompt.md` next to this file; its sha256 and the
judge model are recorded wherever judge labels are written. The judge never
sees the backend name.
"""

from __future__ import annotations

import hashlib
import logging
import json
from pathlib import Path

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage

from src.backends.base import usage_from_message
from src.scoring import LABELS
from src.retry import invoke_with_retry
from src.scoring.matcher import answers_of, expects_abstention

logger = logging.getLogger(__name__)
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
        "sensitive": record.get("category") == "sensitive",
        "candidate_values": list(record.get("candidates") or []) if abstain else [],
        "response": record["response"],
    }


def render(record: dict, template: str | None = None) -> str:
    template = template if template is not None else load_prompt()
    payload = json.dumps(judge_input(record), ensure_ascii=False, indent=2)
    return template.replace("{input_json}", payload)


def parse_verdict(text: str) -> tuple[str, str]:
    """(label, rationale). Unparseable output becomes label `error`.

    Each top-level JSON object in the text is decoded whole with the JSON
    parser, so braces inside the rationale string or a nested object do not
    split it; objects nested inside a decoded one are not considered on their
    own. The first top-level object with a known `label` wins.
    """
    decoder = json.JSONDecoder()
    pos = text.find("{")
    while pos != -1:
        try:
            data, end = decoder.raw_decode(text, pos)
        except json.JSONDecodeError:
            pos = text.find("{", pos + 1)
            continue
        if isinstance(data, dict):
            label = str(data.get("label", "")).strip().lower()
            if label in LABELS:
                return label, str(data.get("rationale", "")).strip()
        pos = text.find("{", end)
    return "error", f"unparseable judge output: {text.strip()[:200]}"


class Judge:
    def __init__(self, llm: BaseChatModel, provider: str, model: str,
                 answering_model: str | None = None) -> None:
        self.llm = llm
        self.provider = provider
        self.model = model
        self.template = load_prompt()
        # A model grading its own answers may favour them (self-preference).
        self.same_as_answerer = answering_model is not None and model == answering_model

    def info(self) -> dict:
        return {
            "judge_provider": self.provider,
            "judge_model": self.model,
            "judge_prompt": str(PROMPT_PATH.relative_to(PROMPT_PATH.parents[2])),
            "judge_prompt_hash": prompt_hash(),
            "judge_is_answering_model": self.same_as_answerer,
        }

    def judge(self, record: dict) -> dict:
        try:
            message, _retries, _ms = invoke_with_retry(
                self.llm, [HumanMessage(content=render(record, self.template))], "judge")
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


def get_judge(answering_model: str | None = None) -> Judge:
    """The configured judge. `answering_model` (default: the configured LLM) is
    the model whose answers it grades, recorded to flag self-grading."""
    from src.config import config
    from src.llm_factory import get_judge_llm, judge_model_id

    from src.llm_factory import llm_model_id

    judge = Judge(get_judge_llm(), config.JUDGE_PROVIDER, judge_model_id(),
                  answering_model or llm_model_id())
    if judge.same_as_answerer and config.JUDGE_PROVIDER != "fake":
        logger.warning(
            "The judge (%s) is the answering model: it may favour its own answers. Set JUDGE_MODEL "
            "to a different model to avoid that; agreement with the matcher is reported either way.",
            judge.model)
    return judge
