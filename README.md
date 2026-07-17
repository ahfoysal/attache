# Attaché

A voice assistant that does real work.

**Status: beta planning.** There's no code here yet. This repo is me thinking in public before committing to an architecture, so expect the docs to change often and without ceremony.

## The itch

Siri can set a timer. What I actually want is to say *"find me an open source project worth contributing to"* from my phone while I'm out, and an hour later get a short voice briefing with the full report waiting in the app. The heavy lifting (research, cloning, running tests, poking at servers) should happen on my own machines through coding agents, not inside a chat window.

So: a phone app for talking, a small control plane on my home machine for thinking, and agent sessions for doing. Basically a chief of staff for AI labor.

## How it works, in one breath

You talk to the app. A fast model decides whether you asked a question or handed over a job. Questions get answered in about a second. Jobs become tasks: durable things with state, logs, budgets and artifacts, executed by a coding-agent session inside a sandboxed workspace. When a task finishes or needs a yes/no, the app pings you and can read the summary out loud. Anything risky, like pushing code or sending messages, waits for explicit approval every single time.

Longer version in [docs/architecture.md](docs/architecture.md).

## Why mobile first

An earlier draft of this plan started with a desktop push-to-talk client. Wrong order. The whole point is being away from the keyboard; if I'm at my desk I'll just type in the terminal. The phone is where a voice assistant earns its keep, and it brings push notifications, mic access and background audio for free.

So the MVP is a React Native app and nothing else. No desktop client, no wake word, no smart speaker. If the app proves that I actually reach for this every day, IoT satellites around the house come later. That part is dessert.

## Roadmap at a glance

| Phase | What | Status |
|---|---|---|
| 0 | Text-only proof: request → task → agent → notification | planning |
| 1 | Mobile MVP: app, push-to-talk, one agent, approvals | planning |
| 2 | Remote machines over SSH | later |
| 3 | Memory that survives weeks | later |
| 4 | More agent runtimes, parallel tasks | later |
| 5 | IoT: wake-word satellites in rooms | someday |

Details in [docs/roadmap.md](docs/roadmap.md), MVP scope in [docs/mvp.md](docs/mvp.md), choices I've already made (and why) in [docs/decisions.md](docs/decisions.md).

## The full plan

Start with [architecture.md](docs/architecture.md) for the shape, then go as deep as you like:

- [prior-art.md](docs/prior-art.md) — what already exists, what it solves, why I'm still building this
- [system-design.md](docs/system-design.md) — components, boundaries, sequence diagrams
- [voice.md](docs/voice.md) — the speech pipeline, latency budget, intent routing
- [sessions.md](docs/sessions.md) — one agent session per task, and how "continue yesterday's thing" resolves
- [memory.md](docs/memory.md) — layered memory, retrieval, correction, forgetting
- [task-engine.md](docs/task-engine.md) — the state machine, approvals, budgets, why not Temporal
- [execution.md](docs/execution.md) — local sandboxes, SSH remotes, the isolation ladder
- [security.md](docs/security.md) — risk tiers, the attacks I'm designing for, secrets
- [data-model.md](docs/data-model.md) — the fifteen tables, with DDL
- [stack.md](docs/stack.md) — every pick with its trade-off, cost estimates, build-vs-buy
- [code-sketches.md](docs/code-sketches.md) — pseudocode for the spine, planned repo layout
- [risks.md](docs/risks.md) — what's easy, what's hard, what current models can't be trusted with

## The stack I'm betting on

Python for the control plane (FastAPI, Postgres, Redis), the Claude Agent SDK for the workers, React Native with Expo for the app, Tailscale so nothing ever listens on a public port. Short version of the reasoning: the voice tooling lives in Python, my UI muscle memory lives in React, and I refuse to expose a public server for something that can push code to my repos.

## Following along

It's early. Issues and discussions are open if you have opinions, especially if you've built voice pipelines or run agent fleets and have scars to share.
