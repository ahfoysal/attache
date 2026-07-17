"""LLMRouter — the real router, on a fast model with tool calling.

Selected when ATTACHE_ROUTER=llm (needs ANTHROPIC_API_KEY and the [claude]
extra). One call does classification, parameter extraction, and the spoken
reply. The anthropic SDK is imported lazily so the offline path never needs it.
"""

from __future__ import annotations

from ...config import settings
from .base import Decision, Router
from .tools import ROUTER_TOOLS, decision_from_tool_use

SYSTEM = """You are Attaché, a voice assistant that dispatches work to coding \
agents. Be concise — one or two spoken sentences. Never do long work yourself; \
for anything that takes a while, call create_task. Use the active-task list and \
memory below to resolve references like "that task" or "the same repo"."""


def _context_block(ctx) -> str:
    lines = []
    recent = getattr(ctx, "recent_turns", []) or []
    if recent:
        lines.append("RECENT CONVERSATION (oldest to newest):")
        for t in recent[-10:]:
            who = "User" if t.get("role") == "user" else "You (Attaché)"
            lines.append(f"{who}: {t.get('text', '')}")
        lines.append("")
    shortlist = getattr(ctx, "task_shortlist", []) or []
    if shortlist:
        lines.append("ACTIVE TASKS:")
        for t in shortlist:
            last = (t.get("last_event") or {})
            note = last.get("msg") or last.get("to") or ""
            lines.append(f"- [{t['state']}] {t['title']} ({t['id']}) {note}")
    facts = getattr(ctx, "memory_block", []) or []
    if facts:
        lines.append("MEMORY:")
        lines += [f"- {f['content']}" for f in facts]
    return "\n".join(lines) or "(no active tasks)"


class LLMRouter(Router):
    def __init__(self) -> None:
        from anthropic import AsyncAnthropic

        self.client = AsyncAnthropic()

    async def route(self, text: str, ctx) -> Decision:
        system = f"{SYSTEM}\n\n{_context_block(ctx)}"
        resp = await self.client.messages.create(
            model=settings.router_model,
            max_tokens=512,
            system=system,
            tools=ROUTER_TOOLS,
            tool_choice={"type": "any"},
            messages=[{"role": "user", "content": text}],
        )
        for block in resp.content:
            if getattr(block, "type", None) == "tool_use":
                return decision_from_tool_use(block.name, dict(block.input))
        # No tool call: treat the text as a direct answer.
        text_out = "".join(
            getattr(b, "text", "") for b in resp.content if getattr(b, "type", None) == "text"
        )
        return Decision("answer", text_out or "Okay.", {})
