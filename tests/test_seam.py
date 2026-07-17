"""The seam, end to end: a typed request becomes a task, an agent runs it in the
background, and it finishes with a spoken summary and a report — all through the
real HTTP endpoint, offline (scripted agent + heuristic router)."""

from httpx import ASGITransport, AsyncClient

from attache.gateway.app import app_from_context


async def _client(ctx):
    app = app_from_context(ctx)
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://t")


async def test_request_becomes_completed_task(ctx):
    async with await _client(ctx) as client:
        r = await client.post("/v1/turns", json={
            "text": "find a good open-source TypeScript project I could contribute to"
        })
        assert r.status_code == 200
        data = r.json()
        assert data["action"] == "create_task"
        task_id = data["task_ref"]

        # Task is queued; drive one dispatch cycle (scripted runner completes it).
        assert await ctx.dispatcher.dispatch_once() is True

        task = await ctx.engine.get(task_id)
        assert task["state"] == "completed"
        assert task["spoken_summary"]

        arts = await ctx.engine.artifacts(task_id)
        assert any(a["name"] == "report.md" for a in arts)


async def test_status_query_after_completion(ctx):
    async with await _client(ctx) as client:
        first = await client.post("/v1/turns", json={"text": "research the best CLI parsers"})
        convo = first.json()["conversation_id"]
        await ctx.dispatcher.dispatch_once()

        r = await client.post("/v1/turns", json={
            "text": "what's the status?", "conversation_id": convo
        })
        speak = r.json()["speak"].lower()
        assert "finished" in speak or "nothing running" in speak


async def test_status_with_no_tasks(ctx):
    async with await _client(ctx) as client:
        r = await client.post("/v1/turns", json={"text": "what are you working on?"})
        assert r.json()["action"] == "task_status"
        assert "nothing running" in r.json()["speak"].lower()


async def test_tasks_api_lists_the_task(ctx):
    async with await _client(ctx) as client:
        created = await client.post("/v1/turns", json={"text": "investigate flaky tests"})
        task_id = created.json()["task_ref"]
        await ctx.dispatcher.dispatch_once()

        listing = await client.get("/v1/tasks")
        ids = [t["id"] for t in listing.json()["tasks"]]
        assert task_id in ids

        detail = await client.get(f"/v1/tasks/{task_id}")
        body = detail.json()
        assert body["task"]["state"] == "completed"
        assert any(e["type"] == "progress" for e in body["events"])


async def test_cancel_flow(ctx):
    async with await _client(ctx) as client:
        created = await client.post("/v1/turns", json={"text": "research something big"})
        task_id = created.json()["task_ref"]
        # Cancel while still queued (created), before dispatch.
        r = await client.post(f"/v1/tasks/{task_id}/cancel")
        assert r.status_code == 200
        task = await ctx.engine.get(task_id)
        assert task["state"] == "cancelled"
