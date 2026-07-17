"""AppContext — assembles the whole control plane and owns its lifecycle.

Built once by the FastAPI lifespan, and independently by tests (against a test
database, with the background loops off so dispatch can be driven step by step).
"""

from __future__ import annotations

import asyncio
import logging

from ..config import Settings
from ..db import Database
from ..events import EventBus
from ..runner import ArtifactStore, Taskboard, build_runner
from .approvals import Approvals
from .dispatcher import Dispatcher
from .memory import MemoryStore
from .notify import Notifier
from .policy import PolicyEngine
from .tasks import TaskEngine

log = logging.getLogger("attache")


def build_router(name: str):
    if name == "heuristic":
        from .router.heuristic import HeuristicRouter

        return HeuristicRouter()
    if name == "llm":
        from .router.llm import LLMRouter

        return LLMRouter()
    if name == "openai":
        from .router.openai_router import OpenAIRouter

        return OpenAIRouter()
    if name == "claude":
        from .router.claude_cli_router import ClaudeCliRouter

        return ClaudeCliRouter()
    raise ValueError(
        f"unknown router backend: {name!r} "
        "(use 'heuristic', 'claude', 'openai', or 'llm')"
    )


class AppContext:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.db = Database(settings.database_url)
        self.bus = EventBus(settings.redis_url)
        self._bg: list[asyncio.Task] = []

    async def startup(self, run_background: bool = True) -> None:
        await self.db.open()
        await self.bus.open()

        self.engine = TaskEngine(self.db, self.bus)
        self.policy = PolicyEngine()
        self.memory = MemoryStore(self.db)
        self.approvals = Approvals(self.db, self.bus)
        self.artifacts = ArtifactStore(self.settings.artifacts)
        self.taskboard = Taskboard(self.engine, self.memory, self.artifacts)
        self.runner = build_runner(
            self.settings.agent,
            taskboard=self.taskboard,
            engine=self.engine,
            policy=self.policy,
            approvals=self.approvals,
            db=self.db,
        )
        self.router = build_router(self.settings.router)
        self.dispatcher = Dispatcher(self.engine, self.runner)
        self.notifier = Notifier(self.db, self.bus, self.engine)

        # Reconcile: a fresh process means any task still 'running'/'planning'
        # was orphaned by the previous process — no runner is working it now.
        await self.db.execute(
            "update tasks set state = 'failed', "
            "blocked_reason = 'interrupted (gateway restarted)', last_activity_at = now() "
            "where state in ('running', 'planning')"
        )

        log.info(
            "Attaché up — agent=%s router=%s", self.settings.agent, self.settings.router
        )
        if run_background:
            self._bg.append(asyncio.create_task(self.dispatcher.run_loop()))
            self._bg.append(asyncio.create_task(self.notifier.run()))
            # Warm a reusable router client so the first turn isn't a cold start.
            if hasattr(self.router, "warmup"):
                self._bg.append(asyncio.create_task(self._warmup_router()))

    async def _warmup_router(self) -> None:
        try:
            await self.router.warmup()
            log.info("router warmed")
        except Exception:
            log.warning("router warmup failed (will warm on first turn)", exc_info=True)

    async def shutdown(self) -> None:
        if hasattr(self.router, "aclose"):
            try:
                await self.router.aclose()
            except Exception:
                pass
        for task in self._bg:
            task.cancel()
        for task in self._bg:
            try:
                await task
            except (asyncio.CancelledError, Exception):
                pass
        self._bg.clear()
        await self.bus.close()
        await self.db.close()
