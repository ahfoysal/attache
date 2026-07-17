"""Run one real task through the Claude Agent SDK backend, end to end.

Costs a small amount (~$0.20, budget-capped) and needs either an authenticated
`claude` CLI or ANTHROPIC_API_KEY, plus `uv sync --extra claude`. Uses the local
`attache` database. Not part of the pytest suite (it hits the paid model).

    uv run python scripts/smoke_agent.py
"""

from __future__ import annotations

import anyio

from attache.config import Settings
from attache.gateway.context import AppContext


async def main() -> None:
    settings = Settings(agent="claude", router="heuristic", agent_model="haiku")
    ctx = AppContext(settings)
    await ctx.startup(run_background=False)
    try:
        task = await ctx.engine.create_task(
            title="Recommend a Python web framework",
            spec={
                "goal": "Recommend ONE Python web framework for a solo dev building a "
                        "small JSON API in 2-3 sentences. Then call the complete tool "
                        "with a one-sentence spoken_summary ending in a question and a "
                        "short markdown report.",
                "model": "haiku",
            },
            budget={"max_usd": 0.60, "max_minutes": 5},
        )
        print("task:", task["id"])
        with anyio.fail_after(180):
            await ctx.dispatcher.dispatch_once()

        done = await ctx.engine.get(task["id"])
        print("state:", done["state"])
        print("spoken:", done["spoken_summary"])
        session = await ctx.db.fetchrow(
            "select external_session_id, cost_usd, status from agent_sessions "
            "where task_id = %s",
            task["id"],
        )
        print("session:", dict(session) if session else None)
        print("artifacts:", [a["name"] for a in await ctx.engine.artifacts(task["id"])])
    finally:
        await ctx.shutdown()


if __name__ == "__main__":
    anyio.run(main)
