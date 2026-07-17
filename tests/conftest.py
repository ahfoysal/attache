"""Test fixtures.

Spins up a throwaway `attache_test` database from db/schema.sql for the session,
and hands each test a started AppContext (scripted agent, heuristic router,
background loops off so dispatch is driven step by step) on Redis db 15.
"""

from __future__ import annotations

from pathlib import Path

import psycopg
import pytest
import pytest_asyncio

from attache.config import Settings
from attache.gateway.context import AppContext

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "db" / "schema.sql"
ADMIN_URL = "postgresql://apple@localhost:5432/postgres"
TEST_URL = "postgresql://apple@localhost:5432/attache_test"
CHURN_TABLES = (
    "conversations, turns, tasks, task_events, agent_sessions, approvals, "
    "memories, artifacts, tool_calls, notifications"
)


@pytest.fixture(scope="session", autouse=True)
def _test_database():
    with psycopg.connect(ADMIN_URL, autocommit=True) as conn:
        conn.execute("drop database if exists attache_test with (force)")
        conn.execute("create database attache_test")
    with psycopg.connect(TEST_URL) as conn:
        conn.execute(SCHEMA.read_text())
    yield
    with psycopg.connect(ADMIN_URL, autocommit=True) as conn:
        conn.execute("drop database if exists attache_test with (force)")


@pytest_asyncio.fixture
async def ctx(tmp_path):
    settings = Settings(
        database_url=TEST_URL,
        redis_url="redis://localhost:6379/15",
        agent="scripted",
        router="heuristic",
        workspace_root=str(tmp_path / "ws"),
        artifact_root=str(tmp_path / "art"),
    )
    context = AppContext(settings)
    await context.startup(run_background=False)
    # Clean slate each test; keep the seeded users/machines rows.
    await context.db.execute(f"truncate {CHURN_TABLES} restart identity cascade")
    await context.bus.redis.flushdb()
    try:
        yield context
    finally:
        await context.shutdown()
