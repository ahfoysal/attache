"""Async Postgres access via a psycopg3 connection pool.

Thin helpers, no ORM. Each `pool.connection()` block is one transaction:
psycopg commits on clean exit and rolls back on exception, which is exactly
the guarantee the task engine relies on for state-change atomicity.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb
from psycopg_pool import AsyncConnectionPool

# Re-exported so call sites wrap dict/list values bound to jsonb columns.
J = Jsonb


class Database:
    def __init__(self, url: str) -> None:
        self._url = url
        self.pool: AsyncConnectionPool | None = None

    async def open(self) -> None:
        self.pool = AsyncConnectionPool(
            self._url, open=False, kwargs={"row_factory": dict_row}
        )
        await self.pool.open()

    async def close(self) -> None:
        if self.pool is not None:
            await self.pool.close()

    @asynccontextmanager
    async def connection(self):
        assert self.pool is not None, "database not opened"
        async with self.pool.connection() as conn:
            yield conn

    async def fetchrow(self, sql: str, *params: Any) -> dict | None:
        async with self.connection() as conn:
            cur = await conn.execute(sql, params)
            return await cur.fetchone()

    async def fetch(self, sql: str, *params: Any) -> list[dict]:
        async with self.connection() as conn:
            cur = await conn.execute(sql, params)
            return await cur.fetchall()

    async def execute(self, sql: str, *params: Any) -> None:
        async with self.connection() as conn:
            await conn.execute(sql, params)

    async def apply_schema(self, schema_path: Path) -> None:
        sql = schema_path.read_text()
        async with self.connection() as conn:
            await conn.execute(sql)


async def ping(url: str) -> bool:
    """Cheap connectivity check used at startup."""
    async with await psycopg.AsyncConnection.connect(url) as conn:
        await conn.execute("select 1")
    return True
