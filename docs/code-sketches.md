# Code sketches

Pseudocode-with-real-shapes for the spine of the system. Types trimmed. None of this is final; all of it is close enough to start from.

## Planned repo layout

```
attache/
├── docker-compose.yml            # postgres+pgvector, redis
├── gateway/                      # Python · FastAPI — control plane
│   ├── api/        # turns, tasks, approvals, websocket
│   ├── router/     # fastpath rules, brain, tool defs
│   ├── tasks/      # engine (state machine), dispatcher, models
│   ├── memory/     # retrieve, distill, redact
│   ├── policy/     # engine, rules.yaml (hash-pinned), approvals
│   ├── notify/     # speak-or-push decision, expo push
│   └── llmproxy/   # virtual keys for remotes (phase 2)
├── voice/                        # Python · Pipecat process
├── runner/                       # Python — installable on any machine
│   ├── server.py                 # start/send/interrupt/status
│   ├── claude_runner.py          # Agent SDK wrapper
│   ├── executor.py               # restricted exec + audit
│   ├── ssh_executor.py           # thin-remote via AsyncSSH
│   └── taskboard/                # MCP server the agents see
├── app/                          # TypeScript · React Native + Expo
└── dashboard/                    # TypeScript · Vite + React
```

The runner is its own package from day one even though phase 1 always runs it locally — that boundary is what makes phase 2 an installation task instead of a refactor.

## Receiving a turn

```python
@app.post("/v1/turns")
async def handle_turn(req: TurnIn):                    # {conversation_id?, text, source}
    convo = await conversations.get_or_create(req.conversation_id)
    await turns.append(convo.id, role="user", text=req.text)

    if reply := fastpath.match(req.text):              # reflex: stop/cancel/status
        return await finalize(convo, reply)

    ctx = await memory.recall_for_turn(req.text, convo)
    decision = await brain.route(req.text, convo, ctx)
    reply = await dispatch(decision, convo)
    return await finalize(convo, reply)                # {speak, action_taken, task_ref}
```

## Routing = tool choice

```python
TOOLS = [answer, create_task, continue_task, task_status,
         cancel_task, run_quick_command, ask_confirmation]

async def route(text, convo, ctx):
    system = f"""You are Attaché, a voice assistant that dispatches work to agents.
    Be concise; one or two spoken sentences. Never do long work yourself.
    ACTIVE TASKS:\n{ctx.task_shortlist}\nRELEVANT MEMORY:\n{ctx.memory_block}
    PREFERENCES:\n{ctx.preferences}"""
    resp = await haiku.create(system=system, tools=TOOLS, tool_choice="auto",
                              messages=await turns.recent(convo.id, 20) + [user(text)])
    return Decision.from_tool_call(resp)
```

## Finding or creating the right session

```python
async def continue_task(task_ref, instruction):
    task = await resolve_task_ref(task_ref)            # shortlist id, title match, or ask
    sess = await db.agent_sessions.active_for(task.id)
    if sess is None:                                   # cold restart from close-out
        return await create_followup(task, instruction)
    await transition(task.id, to="running", event={"instruction": instruction})
    await runner_client(sess.machine_id).send(sess.external_session_id, instruction)
    return task
```

## Memory recall per turn

```python
async def recall_for_turn(text, convo):
    shortlist = await db.fetch("""
        select id, title, state, blocked_reason, last_event(t.id)
        from tasks t
        where state in ('running','blocked','waiting_approval','paused')
        order by last_activity_at desc limit 8""")
    emb = await embed(text)
    memories = await db.fetch("""
        select content, type from memories
        where superseded_by is null and scope in ('user','project')
        order by (embedding <=> $1) + recency_penalty(created_at)
        limit 5""", emb)
    return TurnContext(fmt(shortlist), fmt(memories), await prefs.digest())
```

## Dispatching to the agent

```python
from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions

async def run_task(task, workspace, resume_id=None):
    opts = ClaudeAgentOptions(
        cwd=workspace.path,
        resume=resume_id,
        model=task.spec["model"],
        permission_mode="default",
        can_use_tool=policy_callback(task),            # the choke point
        mcp_servers={"taskboard": taskboard_server(task.id)},
        setting_sources=["project"],                   # reads workspace NOTES.md
        max_budget_usd=task.budget["max_usd"])
    async with ClaudeSDKClient(opts) as client:
        await client.query(compose_prompt(task))       # spec + memory pack + report contract
        async for msg in client.receive_response():
            await mirror_to_events(task.id, msg)
        result = client.last_result
    await sessions.record(task.id, result.session_id, cost=result.total_cost_usd)
```

## The policy callback

```python
def policy_callback(task):
    async def can_use_tool(tool, input, ctx):
        verdict = policy.evaluate(tool, input, task)    # pure rules, tier table
        await audit.log(task.id, tool, input, verdict)
        match verdict.tier:
            case "T0" | "T1": return allow()
            case "T4":        return deny(f"Prohibited: {verdict.rule}")
            case "T2" | "T3":
                appr = await approvals.request(task.id, tool, input, verdict.tier)
                decision = await approvals.wait(appr.id, timeout=120)
                if decision == "approved": return allow()
                if decision == "timeout":                # park, don't block forever
                    await engine.transition(task.id, to="waiting_approval",
                                            event={"approval_id": appr.id})
                    return deny("Approval pending; task parked.")
                return deny("Declined.")
    return can_use_tool
```

## Restricted SSH execution

```python
async def ssh_exec(machine, cmd, task, timeout=120):
    verdict = policy.evaluate("ssh_exec", {"cmd": cmd, "machine": machine.name}, task)
    if not verdict.allowed: raise PolicyDenied(verdict)
    async with pool.connection(machine) as conn:       # AsyncSSH, per-machine key
        r = await asyncio.wait_for(conn.run(cmd, env=workspace_env(task)), timeout)
    await audit.log(task.id, "ssh_exec", {"cmd": cmd}, verdict,
                    exit=r.exit_status, out_ref=await artifacts.store_log(r.stdout))
    return redact(r.stdout), r.exit_status
```

## What agents call (taskboard MCP)

```python
@tool
def report_progress(msg, step=None):
    events.emit(task_id, "progress", {"msg": msg, "step": step})

@tool
def save_artifact(path, kind, name):
    uri = artifact_store.ingest(path)                  # content-addressed copy
    db.artifacts.insert(task_id, kind, name, uri)

@tool
def complete(spoken_summary, report_path):
    save_artifact(report_path, "report", "report.md")
    db.tasks.update(task_id, spoken_summary=spoken_summary)
    engine.transition(task_id, to="completed", event={})   # triggers the notifier
```

## Completion → briefing

```python
async def on_task_event(evt):
    if evt.type != "state_change": return
    task = await db.tasks.get(evt.task_id)
    spoken = task.spoken_summary or await haiku.summarize_events(task.id, "2 sentences")
    if await presence.voice_active(within_min=5):
        await voice_ws.announce(spoken)                # spoken now
    else:
        await push.send(title=task.title, body=spoken) # expo push to the app
```

## The flagship task, as data

```json
{
  "title": "GitHub contribution search",
  "state": "completed",
  "spec": {
    "goal": "Find open-source projects where I can contribute",
    "constraints": ["TypeScript or Python", "active maintainers",
                    "good first issues", "clear dev setup"],
    "context_pack": ["memory: strong TS/React; builds frameworks and dev tools",
                     "memory: prefers projects with real users over toys"],
    "model": "sonnet", "workspace_profile": "research-sandbox",
    "deliverables": ["report.md ranking 3+ candidates with rationale",
                     "spoken_summary ending in a next-step question"]
  },
  "budget": {"max_usd": 3.0, "max_minutes": 60},
  "events": ["created", "state→running",
             "progress: querying GitHub for candidates",
             "progress: shortlisted 12, checking CONTRIBUTING + issue hygiene",
             "artifact: report.md", "state→completed"],
  "spoken_summary": "I found three good matches; the strongest is X — beginner-friendly issues, active maintainers, one-command dev setup. Want me to clone it and prepare the environment?"
}
```
