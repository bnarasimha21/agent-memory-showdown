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


def render_chat_prompt(history: str, user_input: str) -> str:
    return CHAT_TEMPLATE.format(history=history.strip() or EMPTY_HISTORY, input=user_input)


def template_hash(template: str = CHAT_TEMPLATE) -> str:
    return hashlib.sha256(template.encode("utf-8")).hexdigest()
