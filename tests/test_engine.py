"""Task engine tests — transitions persist atomically and guard illegal edges."""

import pytest

from attache.gateway.tasks import IllegalTransition


async def test_create_task_starts_created(ctx):
    task = await ctx.engine.create_task(title="X", spec={"goal": "do a thing"})
    assert task["state"] == "created"
    assert task["title"] == "X"
    events = await ctx.engine.events(task["id"])
    assert events[0]["type"] == "state_change"


async def test_claim_next_moves_to_running(ctx):
    task = await ctx.engine.create_task(title="X", spec={"goal": "g"})
    claimed = await ctx.engine.claim_next()
    assert claimed["id"] == task["id"]
    assert claimed["state"] == "running"
    # Queue now empty.
    assert await ctx.engine.claim_next() is None


async def test_transition_records_summary(ctx):
    task = await ctx.engine.create_task(title="X", spec={"goal": "g"})
    await ctx.engine.claim_next()
    await ctx.engine.transition(task["id"], "completed", spoken_summary="all done")
    got = await ctx.engine.get(task["id"])
    assert got["state"] == "completed"
    assert got["spoken_summary"] == "all done"


async def test_illegal_transition_raises(ctx):
    task = await ctx.engine.create_task(title="X", spec={"goal": "g"})
    # created -> completed is illegal (must run first)
    with pytest.raises(IllegalTransition):
        await ctx.engine.transition(task["id"], "completed")


async def test_expected_from_guards_concurrent_change(ctx):
    task = await ctx.engine.create_task(title="X", spec={"goal": "g"})
    await ctx.engine.claim_next()  # now running
    with pytest.raises(IllegalTransition):
        await ctx.engine.transition(task["id"], "completed", expected_from="created")


async def test_add_artifact(ctx):
    task = await ctx.engine.create_task(title="X", spec={"goal": "g"})
    await ctx.engine.add_artifact(task["id"], "report", "report.md", "file:///tmp/r.md")
    arts = await ctx.engine.artifacts(task["id"])
    assert arts[0]["name"] == "report.md"
