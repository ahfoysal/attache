"""Approvals — rows, not callbacks (docs/task-engine.md).

The permission callback requests an approval and waits a short window on a
Redis key for a fast voice/app "yes". Past the window it returns `timeout`; the
runner then parks the task in `waiting_approval` and the decision can arrive
later via the API, which resolves the same row.
"""

from __future__ import annotations

import asyncio

from ..db import Database, J
from ..events import EventBus

_KEY = "attache:approval:{id}"


class Approvals:
    def __init__(self, db: Database, bus: EventBus) -> None:
        self.db = db
        self.bus = bus

    async def request(
        self, task_id: str, action: str, detail: dict, tier: str
    ) -> dict:
        row = await self.db.fetchrow(
            """insert into approvals (task_id, action, detail, risk_tier)
               values (%s, %s, %s, %s) returning *""",
            task_id, action, J(detail), tier,
        )
        await self.bus.publish(
            task_id, "approval_requested",
            {"approval_id": str(row["id"]), "action": action, "tier": tier, "detail": detail},
        )
        return row

    async def wait(self, approval_id: str, timeout: float = 120.0) -> str:
        """Block up to `timeout` seconds for a decision. Returns
        'approved' | 'denied' | 'timeout'."""
        assert self.bus.redis is not None
        key = _KEY.format(id=approval_id)
        deadline = timeout
        # Poll the key; resolve() sets it. Short interval keeps voice snappy.
        step = 0.5
        waited = 0.0
        while waited < deadline:
            value = await self.bus.redis.get(key)
            if value in ("approved", "denied"):
                await self.bus.redis.delete(key)
                return value
            await asyncio.sleep(step)
            waited += step
        return "timeout"

    async def resolve(self, approval_id: str, decision: str, via: str) -> dict | None:
        row = await self.db.fetchrow(
            """update approvals
                 set status = %s, decided_via = %s, decided_at = now()
               where id = %s and status = 'pending'
               returning *""",
            decision, via, approval_id,
        )
        if row is not None:
            assert self.bus.redis is not None
            await self.bus.redis.set(_KEY.format(id=approval_id), decision, ex=180)
            await self.bus.publish(
                row["task_id"], "approval_resolved",
                {"approval_id": str(approval_id), "decision": decision, "via": via},
            )
        return row
