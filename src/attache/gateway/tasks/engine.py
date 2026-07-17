"""The task engine: the single writer of task state.

Every transition is a guarded, transactional DB write plus an append to
`task_events` plus a publish to the event bus — the three happen together or
not at all. All state changes (API buttons, voice commands, agent callbacks)
funnel through `transition()`, so an illegal edge surfaces as an error instead
of corrupting state.
"""

from __future__ import annotations

from typing import Any

from ... import OWNER_ID
from ...db import Database, J
from ...events import EventBus
from .states import IllegalTransition, State, is_legal


class TaskEngine:
    def __init__(self, db: Database, bus: EventBus) -> None:
        self.db = db
        self.bus = bus

    async def create_task(
        self,
        *,
        title: str,
        spec: dict,
        project_id: str | None = None,
        budget: dict | None = None,
        parent_task_id: str | None = None,
    ) -> dict:
        async with self.db.connection() as conn:
            cur = await conn.execute(
                """insert into tasks
                     (user_id, project_id, parent_task_id, title, spec, budget, state)
                   values (%s, %s, %s, %s, %s, %s, 'created')
                   returning *""",
                (OWNER_ID, project_id, parent_task_id, title, J(spec), J(budget or {})),
            )
            task = await cur.fetchone()
            await conn.execute(
                "insert into task_events (task_id, type, payload) values (%s, %s, %s)",
                (task["id"], "state_change", J({"to": "created"})),
            )
        await self.bus.publish(task["id"], "state_change", {"to": "created", "title": title})
        return task

    async def get(self, task_id: str) -> dict | None:
        return await self.db.fetchrow("select * from tasks where id = %s", task_id)

    async def append_event(self, task_id: str, type: str, payload: dict) -> None:
        async with self.db.connection() as conn:
            await conn.execute(
                "insert into task_events (task_id, type, payload) values (%s, %s, %s)",
                (task_id, type, J(payload)),
            )
            await conn.execute(
                "update tasks set last_activity_at = now() where id = %s", (task_id,)
            )
        await self.bus.publish(task_id, type, payload)

    async def transition(
        self,
        task_id: str,
        to: str | State,
        *,
        event: dict | None = None,
        expected_from: str | State | None = None,
        blocked_reason: str | None = None,
        spoken_summary: str | None = None,
    ) -> dict:
        to = State(to)
        async with self.db.connection() as conn:
            cur = await conn.execute(
                "select state from tasks where id = %s for update", (task_id,)
            )
            row = await cur.fetchone()
            if row is None:
                raise ValueError(f"no such task: {task_id}")
            frm = State(row["state"])
            if expected_from is not None and frm != State(expected_from):
                raise IllegalTransition(frm, to)
            if not is_legal(frm, to):
                raise IllegalTransition(frm, to)
            await conn.execute(
                """update tasks
                     set state = %s,
                         blocked_reason = %s,
                         spoken_summary = coalesce(%s, spoken_summary),
                         last_activity_at = now()
                   where id = %s""",
                (to.value, blocked_reason, spoken_summary, task_id),
            )
            payload: dict[str, Any] = {"from": frm.value, "to": to.value}
            if event:
                payload.update(event)
            await conn.execute(
                "insert into task_events (task_id, type, payload) values (%s, %s, %s)",
                (task_id, "state_change", J(payload)),
            )
        await self.bus.publish(task_id, "state_change", payload)
        return payload

    async def claim_next(self) -> dict | None:
        """Atomically grab one queued task and move it to running.

        Uses FOR UPDATE SKIP LOCKED so concurrent dispatchers never hand the
        same task to two runners.
        """
        async with self.db.connection() as conn:
            cur = await conn.execute(
                """select * from tasks
                     where state = 'created'
                     order by created_at
                     for update skip locked
                     limit 1"""
            )
            task = await cur.fetchone()
            if task is None:
                return None
            await conn.execute(
                "update tasks set state = 'running', last_activity_at = now() where id = %s",
                (task["id"],),
            )
            await conn.execute(
                "insert into task_events (task_id, type, payload) values (%s, %s, %s)",
                (task["id"], "state_change", J({"from": "created", "to": "running"})),
            )
        await self.bus.publish(task["id"], "state_change", {"from": "created", "to": "running"})
        task["state"] = "running"
        return task

    async def list_active(self, limit: int = 8) -> list[dict]:
        return await self.db.fetch(
            """select id, title, state, blocked_reason, spoken_summary,
                      (select payload from task_events e
                        where e.task_id = t.id order by e.id desc limit 1) as last_event
               from tasks t
               where state in ('created','planning','running','blocked',
                               'waiting_approval','paused')
               order by last_activity_at desc
               limit %s""",
            limit,
        )

    async def recent(self, limit: int = 20) -> list[dict]:
        return await self.db.fetch(
            "select id, title, state, spoken_summary, created_at, last_activity_at "
            "from tasks order by last_activity_at desc limit %s",
            limit,
        )

    async def events(self, task_id: str) -> list[dict]:
        return await self.db.fetch(
            "select id, type, payload, created_at from task_events "
            "where task_id = %s order by id",
            task_id,
        )

    async def artifacts(self, task_id: str) -> list[dict]:
        return await self.db.fetch(
            "select kind, name, uri, media_type, created_at from artifacts "
            "where task_id = %s order by id",
            task_id,
        )

    async def add_artifact(
        self, task_id: str, kind: str, name: str, uri: str,
        media_type: str | None = None, size_bytes: int | None = None,
        digest: str | None = None,
    ) -> dict:
        row = await self.db.fetchrow(
            """insert into artifacts (task_id, kind, name, uri, media_type, size_bytes, digest)
               values (%s, %s, %s, %s, %s, %s, %s) returning *""",
            task_id, kind, name, uri, media_type, size_bytes, digest,
        )
        await self.bus.publish(task_id, "artifact", {"name": name, "kind": kind})
        return row
