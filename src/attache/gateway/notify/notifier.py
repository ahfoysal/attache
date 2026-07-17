"""Notifier — reads the event stream and surfaces the moments that matter.

Fires on tasks reaching completed / failed / waiting_approval. In Phase 0 the
"channel" is a log line carrying the agent-written spoken_summary (the same
string a phone push or TTS will speak later); the app subscribes to the
`notification` event for the in-UI badge.
"""

from __future__ import annotations

import logging

from ... import OWNER_ID
from ...db import Database
from ...events import EventBus
from ..tasks import TaskEngine

log = logging.getLogger("attache.notify")

ANNOUNCE_STATES = {"completed", "failed", "waiting_approval"}


class Notifier:
    def __init__(self, db: Database, bus: EventBus, engine: TaskEngine) -> None:
        self.db = db
        self.bus = bus
        self.engine = engine

    def _default_spoken(self, to: str, task: dict) -> str:
        title = task["title"]
        if to == "failed":
            return f"The task “{title}” failed: {task.get('blocked_reason') or 'see the log'}."
        if to == "waiting_approval":
            return f"The task “{title}” needs your approval to continue."
        return f"The task “{title}” finished."

    async def _announce(self, task_id: str, to: str) -> None:
        task = await self.engine.get(task_id)
        if task is None:
            return
        spoken = task.get("spoken_summary") or self._default_spoken(to, task)
        await self.db.execute(
            """insert into notifications (user_id, task_id, kind, spoken, channel, status, delivered_at)
               values (%s, %s, %s, %s, 'log', 'delivered', now())""",
            OWNER_ID, task_id, to, spoken,
        )
        await self.bus.publish(task_id, "notification", {"kind": to, "spoken": spoken})
        log.info("🔔 [%s] %s", to, spoken)

    async def run(self) -> None:
        """Background loop. Cancelled at shutdown."""
        async for event in self.bus.subscribe():
            if (
                event.get("type") == "state_change"
                and event.get("payload", {}).get("to") in ANNOUNCE_STATES
            ):
                try:
                    await self._announce(event["task_id"], event["payload"]["to"])
                except Exception:
                    log.exception("notifier failed for %s", event.get("task_id"))
