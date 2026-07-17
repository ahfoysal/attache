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

The Claude agent backend runs on the Claude Agent SDK, which drives the
installed `claude` CLI — so if you're already signed in to Claude Code, **no API
key is needed**:

```sh
uv sync --extra claude
# in .env:
ATTACHE_AGENT=claude
```

Now tasks run on a real Claude Agent SDK session: the agent reports through the
`taskboard` MCP tools and every tool call passes the policy tiers. Verified with
a live task — the agent researched, wrote a report, and completed with a spoken
summary (session + cost recorded in `agent_sessions`).

Smoke-test it directly:

```sh
uv run python scripts/smoke_agent.py    # runs one real, budget-capped task (~$0.20)
```

## Routers

- `heuristic` (default) — keyword-based, free, no key. Recognises task verbs
  (research/find/build/fix…); plain chat gets a canned reply.
- `claude` — smart routing on your **Claude subscription** via the CLI (no API
  key, no cash — uses a little subscription allowance per turn). Understands
  general chat and dispatches actionable requests to tasks. Set
  `ATTACHE_ROUTER=claude`. This is the recommended smart router.
- `openai` — an OpenAI model (`OPENAI_API_KEY` + `uv sync --extra openai`).
  Real money (OpenAI API is not covered by a ChatGPT subscription), but cheap.
  Verify with `uv run python scripts/smoke_router.py`.
- `llm` — the anthropic API (`ANTHROPIC_API_KEY`); like `claude` but metered
  per token instead of via the subscription.

If the smart router errors on a turn, the gateway falls back to the heuristic
router so the turn still succeeds. The agent stays Claude regardless — routing
and reasoning are separate choices.

Note on cost: each agent task is its own SDK session with meaningful fixed
overhead (~$0.20 even for a tiny task), so per-task budget caps matter.

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
