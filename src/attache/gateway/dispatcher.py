"""Dispatcher — claims queued tasks and hands them to the runner.

Phase 0 runs one runner and awaits each task fully (deterministic, simple).
Concurrency (spawning runs as tasks, per-task budgets) comes with more workers.
"""

from __future__ import annotations

import asyncio
import logging

from ..runner.base import AgentRunner
from .tasks import TaskEngine

log = logging.getLogger("attache.dispatch")


class Dispatcher:
    def __init__(self, engine: TaskEngine, runner: AgentRunner) -> None:
        self.engine = engine
        self.runner = runner

    async def dispatch_once(self) -> bool:
        """Claim and run one queued task. Returns False if the queue was empty."""
        task = await self.engine.claim_next()
        if task is None:
            return False
        log.info("dispatching task %s (%s) via %s", task["id"], task["title"], self.runner.name)
        try:
            await self.runner.run(task)
        except Exception as exc:
            log.exception("runner crashed on %s", task["id"])
            try:
                await self.engine.transition(task["id"], "failed", event={"reason": str(exc)})
            except Exception:
                log.exception("could not mark %s failed", task["id"])
        return True

    async def run_loop(self) -> None:
        """Background poll loop. Cancelled at shutdown."""
        while True:
            try:
                did = await self.dispatch_once()
            except Exception:
                log.exception("dispatch loop error")
                did = False
            if not did:
                await asyncio.sleep(0.4)
