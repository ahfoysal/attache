"""Taskboard — how an agent's work becomes user-visible state.

Both runners (scripted and Claude) call these methods to report progress, save
artifacts, record facts, and finish. For the Claude runner these are also
exposed as an in-process MCP server (see claude.py), so the agent reports
structured events instead of the gateway parsing prose from a transcript.
"""

from __future__ import annotations

from ..gateway.memory import MemoryStore
from ..gateway.tasks import TaskEngine
from .artifacts import ArtifactStore


class Taskboard:
    def __init__(self, engine: TaskEngine, memory: MemoryStore, artifacts: ArtifactStore) -> None:
        self.engine = engine
        self.memory = memory
        self.artifacts = artifacts

    async def report_progress(self, task_id: str, msg: str, step: str | None = None) -> None:
        await self.engine.append_event(task_id, "progress", {"msg": msg, "step": step})

    async def plan(self, task_id: str, steps: list[str]) -> None:
        await self.engine.append_event(task_id, "plan", {"steps": steps})

    async def save_artifact(
        self, task_id: str, name: str, content: str, kind: str = "report"
    ) -> dict:
        uri, size, digest = self.artifacts.ingest_text(task_id, name, content)
        return await self.engine.add_artifact(
            task_id, kind=kind, name=name, uri=uri,
            media_type="text/markdown", size_bytes=size, digest=digest,
        )

    async def remember(self, content: str, *, scope: str = "user", type: str = "fact") -> None:
        await self.memory.remember(content, scope=scope, type=type, source_kind="agent")

    async def complete(
        self, task_id: str, spoken_summary: str, report: str | None = None,
        report_name: str = "report.md",
    ) -> None:
        if report is not None:
            await self.save_artifact(task_id, report_name, report, kind="report")
        await self.engine.transition(task_id, "completed", spoken_summary=spoken_summary)

    async def fail(self, task_id: str, reason: str) -> None:
        await self.engine.transition(task_id, "failed", event={"reason": reason})

    async def block(self, task_id: str, reason: str) -> None:
        await self.engine.transition(task_id, "blocked", blocked_reason=reason)
