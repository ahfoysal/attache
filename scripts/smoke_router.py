"""Check the OpenAI router: authenticate and route a few sample utterances.

Needs OPENAI_API_KEY (loaded from .env) with API quota, and `uv sync --extra
openai`. Costs a fraction of a cent. Not part of the pytest suite.

    uv run python scripts/smoke_router.py
"""

from __future__ import annotations

import types

import anyio

from attache.gateway.router.openai_router import OpenAIRouter

SAMPLES = [
    "find me a good open-source rust project to contribute to",
    "what's the weather like — just chatting",
    "what are you working on right now?",
]


async def main() -> None:
    router = OpenAIRouter()
    ctx = types.SimpleNamespace(task_shortlist=[], memory_block=[], preferences={})
    for text in SAMPLES:
        try:
            d = await router.route(text, ctx)
            print(f"{text!r}\n  -> {d.action}  speak={d.speak!r}  args={d.args}")
        except Exception as exc:  # surface auth/quota problems clearly
            print(f"{text!r}\n  -> {type(exc).__name__}: {exc}")
            break


if __name__ == "__main__":
    anyio.run(main)
