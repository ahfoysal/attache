"""The event bus: every task state change and progress update fans out here.

One Redis channel (`attache:events`) carries the whole stream. The dashboard
websocket, the notifier, and any future subscriber all read the same channel —
one source of truth for "what happened", per docs/system-design.md.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import AsyncIterator

from redis.asyncio import Redis

CHANNEL = "attache:events"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class EventBus:
    def __init__(self, url: str) -> None:
        self._url = url
        self.redis: Redis | None = None

    async def open(self) -> None:
        self.redis = Redis.from_url(self._url, decode_responses=True)
        await self.redis.ping()

    async def close(self) -> None:
        if self.redis is not None:
            await self.redis.aclose()

    async def publish(self, task_id: str, type: str, payload: dict) -> dict:
        event = {"task_id": str(task_id), "type": type, "payload": payload, "ts": _now()}
        assert self.redis is not None, "event bus not opened"
        await self.redis.publish(CHANNEL, json.dumps(event))
        return event

    async def subscribe(self) -> AsyncIterator[dict]:
        """Yield every event published to the channel. Used by the WS endpoint."""
        assert self.redis is not None, "event bus not opened"
        pubsub = self.redis.pubsub()
        await pubsub.subscribe(CHANNEL)
        try:
            async for message in pubsub.listen():
                if message.get("type") != "message":
                    continue
                yield json.loads(message["data"])
        finally:
            await pubsub.unsubscribe(CHANNEL)
            await pubsub.aclose()
