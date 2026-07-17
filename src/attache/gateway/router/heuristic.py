"""HeuristicRouter — deterministic classification, no API key.

Enough to drive the seam and the tests: it recognises task requests, status
questions, and cancels. General question-answering needs the LLM router; in
offline mode `answer` returns an honest note pointing at ATTACHE_ROUTER=llm.
"""

from __future__ import annotations

import re

from .base import Decision, Router

# Verbs that signal "go do work" rather than "answer me".
_TASK_VERBS = re.compile(
    r"\b(find|research|investigate|look (for|into)|search for|build|create|"
    r"implement|fix|debug|clone|set ?up|prepare|check out|analyze|analyse|review|"
    r"scaffold|refactor|write|generate)\b",
    re.IGNORECASE,
)
_CONTINUE = re.compile(
    r"\b(continue|resume|keep going|carry on|go ahead|yes,? (set it up|do it|please))\b",
    re.IGNORECASE,
)


def _title_from(text: str) -> str:
    t = re.sub(r"^\s*(hey )?(attach[ée]|claude)[,: ]*", "", text, flags=re.IGNORECASE)
    t = t.strip().rstrip(".!?")
    return (t[:1].upper() + t[1:])[:80] if t else "Task"


class HeuristicRouter(Router):
    async def route(self, text: str, ctx) -> Decision:
        shortlist = getattr(ctx, "task_shortlist", []) or []

        if _CONTINUE.search(text) and shortlist:
            return Decision(
                "continue_task",
                "Okay, continuing that now.",
                {"task_ref": shortlist[0]["id"], "instruction": text},
            )

        if _TASK_VERBS.search(text):
            title = _title_from(text)
            return Decision(
                "create_task",
                "On it — I'll work on that and let you know when it's done.",
                {"title": title, "goal": text},
            )

        return Decision(
            "answer",
            "I'm in offline mode, so I can't free-form chat yet — set "
            "ATTACHE_ROUTER=llm for that. But I can run tasks: try asking me to "
            "find or research something.",
            {},
        )
