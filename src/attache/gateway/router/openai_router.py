"""OpenAIRouter — routing on an OpenAI model via function calling.

Selected when ATTACHE_ROUTER=openai. Needs OPENAI_API_KEY (loaded from .env)
and the [openai] extra. Only routing runs on OpenAI — the agent stays Claude,
so reasoning remains free on the subscription. Routing cost is a fraction of a
cent per turn.

Reuses the same tool set and context/system prompt as the Anthropic router,
translated to OpenAI's function-calling shape.
"""

from __future__ import annotations

import json

from ...config import settings
from .base import Decision, Router
from .llm import SYSTEM, _context_block
from .tools import ROUTER_TOOLS, decision_from_tool_use


def _openai_tools() -> list[dict]:
    return [
        {
            "type": "function",
            "function": {
                "name": t["name"],
                "description": t["description"],
                "parameters": t["input_schema"],
            },
        }
        for t in ROUTER_TOOLS
    ]


class OpenAIRouter(Router):
    def __init__(self) -> None:
        from openai import AsyncOpenAI

        self.client = AsyncOpenAI()  # reads OPENAI_API_KEY from the environment
        self.tools = _openai_tools()

    async def route(self, text: str, ctx) -> Decision:
        system = f"{SYSTEM}\n\n{_context_block(ctx)}"
        resp = await self.client.chat.completions.create(
            model=settings.openai_router_model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": text},
            ],
            tools=self.tools,
            tool_choice="required",
        )
        msg = resp.choices[0].message
        if msg.tool_calls:
            call = msg.tool_calls[0]
            args = json.loads(call.function.arguments or "{}")
            return decision_from_tool_use(call.function.name, args)
        return Decision("answer", msg.content or "Okay.", {})
