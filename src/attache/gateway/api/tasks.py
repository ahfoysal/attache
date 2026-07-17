"""REST for the dashboard/app: task list, detail, cancel, approvals, artifacts."""

from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel

router = APIRouter()


@router.get("/v1/tasks")
async def list_tasks(request: Request) -> dict:
    ctx = request.app.state.ctx
    rows = await ctx.engine.recent(limit=50)
    return {"tasks": [_task_summary(r) for r in rows]}


@router.get("/v1/tasks/{task_id}")
async def get_task(task_id: str, request: Request) -> dict:
    ctx = request.app.state.ctx
    task = await ctx.engine.get(task_id)
    if task is None:
        raise HTTPException(404, "no such task")
    return {
        "task": _task_detail(task),
        "events": await ctx.engine.events(task_id),
        "artifacts": await ctx.engine.artifacts(task_id),
    }


@router.post("/v1/tasks/{task_id}/cancel")
async def cancel_task(task_id: str, request: Request) -> dict:
    ctx = request.app.state.ctx
    try:
        await ctx.engine.transition(task_id, "cancelled", event={"by": "dashboard"})
    except Exception as exc:
        raise HTTPException(409, str(exc))
    return {"ok": True}


class ApprovalDecision(BaseModel):
    decision: str  # approved | denied


@router.post("/v1/approvals/{approval_id}")
async def resolve_approval(approval_id: str, body: ApprovalDecision, request: Request) -> dict:
    ctx = request.app.state.ctx
    if body.decision not in ("approved", "denied"):
        raise HTTPException(400, "decision must be 'approved' or 'denied'")
    row = await ctx.approvals.resolve(approval_id, body.decision, via="dashboard")
    if row is None:
        raise HTTPException(404, "no pending approval with that id")
    return {"ok": True}


@router.get("/v1/artifacts/{task_id}/{name}", response_class=PlainTextResponse)
async def get_artifact(task_id: str, name: str, request: Request) -> str:
    ctx = request.app.state.ctx
    rows = await ctx.engine.artifacts(task_id)
    match = next((r for r in rows if r["name"] == name), None)
    if match is None:
        raise HTTPException(404, "no such artifact")
    path = Path(urlparse(match["uri"]).path)
    if not path.is_file():
        raise HTTPException(410, "artifact file missing")
    return path.read_text()


def _task_summary(r: dict) -> dict:
    return {
        "id": str(r["id"]),
        "title": r["title"],
        "state": r["state"],
        "spoken_summary": r.get("spoken_summary"),
        "last_activity_at": r["last_activity_at"].isoformat() if r.get("last_activity_at") else None,
    }


def _task_detail(r: dict) -> dict:
    return {
        "id": str(r["id"]),
        "title": r["title"],
        "state": r["state"],
        "spec": r["spec"],
        "blocked_reason": r.get("blocked_reason"),
        "spoken_summary": r.get("spoken_summary"),
        "budget": r.get("budget"),
        "created_at": r["created_at"].isoformat() if r.get("created_at") else None,
    }
