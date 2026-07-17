"""Reflex layer — a handful of deterministic patterns that skip the model.

Kept tiny on purpose (docs/voice.md): this is a fast path for the reflex
vocabulary, not an NLU system.
"""

from __future__ import annotations

import re

from .base import Decision

_STATUS = re.compile(
    r"\b(status|what('?s| is) (the status|going on)|what are you (working on|doing)|"
    r"did (the|that|it) .*(finish|done|complete)|any (update|progress))\b",
    re.IGNORECASE,
)
_CANCEL = re.compile(r"\b(cancel|stop it|abort|never mind|nevermind)\b", re.IGNORECASE)


def fastpath(text: str) -> Decision | None:
    if _STATUS.search(text):
        return Decision("task_status", "", {})
    if _CANCEL.search(text):
        return Decision("cancel_task", "", {})
    return None
