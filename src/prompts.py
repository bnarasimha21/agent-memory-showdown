"""The single chat prompt shared by every memory backend.

Each backend decides what goes into `{history}` (that is the thing being
measured); the wording around it is identical for all of them, so differences
in recall cannot come from prompt wording. The hash of this template is
recorded in every run manifest.
"""

from __future__ import annotations

import hashlib

CHAT_TEMPLATE = (
    "You are a helpful assistant in a long-running conversation with one user.\n"
    "Below is what you remember from earlier in the conversation. Use it to answer "
    "the user's latest message. If the answer is not in your memory, say that the "
    "user has not told you.\n\n"
    "Memory:\n{history}\n\n"
    "User: {input}\n"
    "Assistant:"
)

EMPTY_HISTORY = "(nothing yet)"

# The `summary` backend folds each exchange into a running summary with this
# prompt. It is LangChain 0.2's ConversationSummaryMemory prompt, copied
# verbatim so the summary backend behaves as it did before the LangChain 1.x
# port removed `langchain.memory`.
SUMMARY_TEMPLATE = 'Progressively summarize the lines of conversation provided, adding onto the previous summary returning a new summary.\n\nEXAMPLE\nCurrent summary:\nThe human asks what the AI thinks of artificial intelligence. The AI thinks artificial intelligence is a force for good.\n\nNew lines of conversation:\nHuman: Why do you think artificial intelligence is a force for good?\nAI: Because artificial intelligence will help humans reach their full potential.\n\nNew summary:\nThe human asks what the AI thinks of artificial intelligence. The AI thinks artificial intelligence is a force for good because it will help humans reach their full potential.\nEND OF EXAMPLE\n\nCurrent summary:\n{summary}\n\nNew lines of conversation:\n{new_lines}\n\nNew summary:'


def render_summary_prompt(summary: str, new_lines: str) -> str:
    return SUMMARY_TEMPLATE.format(summary=summary, new_lines=new_lines)


def render_chat_prompt(history: str, user_input: str) -> str:
    return CHAT_TEMPLATE.format(history=history.strip() or EMPTY_HISTORY, input=user_input)


def template_hash(template: str = CHAT_TEMPLATE) -> str:
    return hashlib.sha256(template.encode("utf-8")).hexdigest()
