# Running Phase 0

The Phase 0 seam: a typed request becomes a durable task, an agent runs it in
the background, and it finishes with a spoken summary + report. Runs fully
offline (no API key) with the scripted agent and heuristic router.

## Prerequisites

- Python 3.12+ and [uv](https://docs.astral.sh/uv/)
- Postgres 16+ and Redis, running locally

On a Homebrew mac:

```sh
brew services start postgresql@16
brew services start redis
createdb attache
```

(There's also a `compose.yaml` for machines with Docker instead.)

## Setup

```sh
uv sync                       # install deps
cp .env.example .env          # adjust DB/Redis URLs if needed
psql -d attache -f db/schema.sql
```

## Run

```sh
uv run attache-gateway        # http://127.0.0.1:8787
```

Open the console at <http://127.0.0.1:8787> and type a request, e.g.
*"find a good open-source TypeScript project I could contribute to"*. Or drive
it over HTTP:

```sh
curl -s localhost:8787/v1/turns -H 'content-type: application/json' \
  -d '{"text":"research the best CLI parsers"}'
```

The task dispatches in the background; watch it via the console's live events,
`GET /v1/tasks`, or `GET /v1/tasks/{id}`. The report lands at
`GET /v1/artifacts/{id}/report.md`.

## Tests

```sh
uv run pytest -q
```

Spins up a throwaway `attache_test` database and drives the seam end to end.

## Switching on the real agent

Set `ANTHROPIC_API_KEY`, install the extra, and flip the backends:

```sh
uv sync --extra claude
export ANTHROPIC_API_KEY=sk-ant-...
# in .env:
ATTACHE_AGENT=claude
ATTACHE_ROUTER=llm
```

Now `create_task` routes through a fast model and tasks run on a real Claude
Agent SDK session, with the policy tiers enforced on every tool call. The
scripted/heuristic backends stay available for offline development and tests.

## API surface (Phase 0)

| Method | Path | Purpose |
|---|---|---|
| POST | `/v1/turns` | Submit a transcript; returns `{speak, action, task_ref}` |
| GET | `/v1/tasks` | Recent tasks |
| GET | `/v1/tasks/{id}` | Task detail + events + artifacts |
| POST | `/v1/tasks/{id}/cancel` | Cancel a task |
| POST | `/v1/approvals/{id}` | Resolve an approval (`approved`/`denied`) |
| GET | `/v1/artifacts/{id}/{name}` | Fetch an artifact |
| WS | `/v1/events` | Live task-event stream |
| GET | `/healthz` | Health + active backends |
