"""Memory store.

Phase 0 covers the always-on block from docs/memory.md — the active-task
shortlist, a preference digest, and recent facts via a manual "remember this".
Semantic retrieval (embeddings + pgvector) is Phase 3; the retrieval interface
here (`recall_for_turn`) stays the same when that lands.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ... import OWNER_ID
from ...db import Database
from ..tasks import TaskEngine


@dataclass
class TurnContext:
    task_shortlist: list[dict]
    memory_block: list[dict]
    preferences: dict
    recent_turns: list[dict] = field(default_factory=list)


class MemoryStore:
    def __init__(self, db: Database) -> None:
        self.db = db

    async def preferences(self) -> dict:
        row = await self.db.fetchrow("select preferences from users where id = %s", OWNER_ID)
        return (row or {}).get("preferences") or {}

    async def remember(
        self,
        content: str,
        *,
        scope: str = "user",
        type: str = "fact",
        project_id: str | None = None,
        source_kind: str | None = None,
        source_id: str | None = None,
    ) -> dict:
        return await self.db.fetchrow(
            """insert into memories
                 (user_id, scope, project_id, type, content, source_kind, source_id)
               values (%s, %s, %s, %s, %s, %s, %s)
               returning *""",
            OWNER_ID, scope, project_id, type, content, source_kind, source_id,
        )

    async def recent_facts(self, limit: int = 5) -> list[dict]:
        return await self.db.fetch(
            """select content, type from memories
               where superseded_by is null and scope in ('user','project')
               order by created_at desc limit %s""",
            limit,
        )

    async def recent_turns(self, convo_id: str, limit: int = 10) -> list[dict]:
        rows = await self.db.fetch(
            "select role, text from turns where conversation_id = %s "
            "order by created_at desc limit %s",
            convo_id, limit,
        )
        return list(reversed(rows))

    async def recall_for_turn(
        self, text: str, engine: TaskEngine, convo_id: str | None = None
    ) -> TurnContext:
        return TurnContext(
            task_shortlist=await engine.list_active(),
            memory_block=await self.recent_facts(),
            preferences=await self.preferences(),
            recent_turns=await self.recent_turns(convo_id) if convo_id else [],
        )
