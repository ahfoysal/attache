"""POST /v1/turns — the one entry point for voice and text alike.

Transcript in, structured reply out ({speak, action, task_ref}). The voice
plane and the app are two clients of this endpoint; neither knows about tasks.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Request
from pydantic import BaseModel

from ... import OWNER_ID
from ...config import settings
from ..router import Decision, fastpath
from ..router.heuristic import HeuristicRouter

log = logging.getLogger("attache.turns")
router = APIRouter()

# Keyword fallback: if the smart router errors mid-turn, the assistant stays
# usable instead of failing the turn.
_fallback_router = HeuristicRouter()


class TurnIn(BaseModel):
    text: str
    conversation_id: str | None = None
    source: str = "text"


async def _get_or_create_conversation(ctx, cid: str | None) -> dict:
    if cid:
        row = await ctx.db.fetchrow("select * from conversations where id = %s", cid)
        if row:
            return row
    return await ctx.db.fetchrow(
        "insert into conversations (user_id) values (%s) returning *", OWNER_ID
    )


async def _append_turn(ctx, convo_id, role, text, task_id=None) -> None:
    await ctx.db.execute(
        "insert into turns (conversation_id, role, text, task_id) values (%s, %s, %s, %s)",
        convo_id, role, text, task_id,
    )


async def _status_speak(ctx, task_ref: str | None) -> str:
    active = await ctx.engine.list_active()
    if not active:
        recent = await ctx.engine.recent(1)
        if recent and recent[0]["state"] == "completed" and recent[0]["spoken_summary"]:
            return f"Nothing running now. The last one finished: {recent[0]['spoken_summary']}"
        return "Nothing running right now."
    if len(active) == 1:
        t = active[0]
        note = (t.get("last_event") or {}).get("msg") or ""
        return f"One task {t['state']}: {t['title']}. {note}".strip()
    joined = "; ".join(f"{t['title']} ({t['state']})" for t in active)
    return f"{len(active)} tasks active: {joined}."


async def _resolve_task(ctx, task_ref: str | None) -> dict | None:
    if task_ref:
        task = await ctx.engine.get(task_ref)
        if task:
            return task
    active = await ctx.engine.list_active(limit=1)
    if active:
        return await ctx.engine.get(active[0]["id"])
    return None


async def _dispatch(ctx, decision: Decision, convo: dict, text: str) -> dict:
    action = decision.action

    if action == "create_task":
        spec = {
            "goal": decision.args.get("goal", text),
            "constraints": decision.args.get("constraints", []),
            "model": settings.agent_model,
        }
        task = await ctx.engine.create_task(
            title=decision.args.get("title", "Task"),
            spec=spec,
            budget={"max_usd": 3.0, "max_minutes": 60},
        )
        return {"speak": decision.speak, "action": action, "task_ref": str(task["id"])}

    if action == "task_status":
        return {"speak": await _status_speak(ctx, decision.args.get("task_ref")),
                "action": action}

    if action == "cancel_task":
        task = await _resolve_task(ctx, decision.args.get("task_ref"))
        if task is None:
            return {"speak": "There's nothing active to cancel.", "action": action}
        try:
            await ctx.engine.transition(task["id"], "cancelled", event={"by": "user"})
            return {"speak": f"Cancelled “{task['title']}”.", "action": action,
                    "task_ref": str(task["id"])}
        except Exception:
            return {"speak": f"Couldn't cancel “{task['title']}” from its current state.",
                    "action": action}

    if action == "continue_task":
        parent = await _resolve_task(ctx, decision.args.get("task_ref"))
        if parent is None:
            return {"speak": "I don't have a task to continue.", "action": action}
        child = await ctx.engine.create_task(
            title=f"Follow-up: {parent['title']}"[:80],
            spec={"goal": decision.args.get("instruction", text),
                  "model": settings.agent_model},
            parent_task_id=parent["id"],
        )
        return {"speak": decision.speak or "Okay, continuing.", "action": action,
                "task_ref": str(child["id"])}

    # answer / ask_confirmation
    return {"speak": decision.speak, "action": action}


@router.post("/v1/turns")
async def handle_turn(body: TurnIn, request: Request) -> dict:
    ctx = request.app.state.ctx
    convo = await _get_or_create_conversation(ctx, body.conversation_id)
    await _append_turn(ctx, convo["id"], "user", body.text)

    decision = fastpath(body.text)
    if decision is None:
        turn_ctx = await ctx.memory.recall_for_turn(body.text, ctx.engine)
        # Instant lane: obvious task/continue requests skip the LLM round-trip
        # (the agent enriches the goal itself, so nothing is lost).
        quick = await _fallback_router.route(body.text, turn_ctx)
        if settings.fast_route and quick.action in ("create_task", "continue_task"):
            decision = quick
        else:
            try:
                decision = await ctx.router.route(body.text, turn_ctx)
            except Exception:
                log.exception("router failed; using heuristic result")
                decision = quick

    result = await _dispatch(ctx, decision, convo, body.text)
    await _append_turn(ctx, convo["id"], "assistant", result["speak"],
                       task_id=result.get("task_ref"))
    return {"conversation_id": str(convo["id"]), **result}
