# Attaché

Voice assistant that runs real work through coding agents.

Status: **beta planning**. No code yet. Docs change often.

## Problem

Siri-class assistants stop at timers and lookups. Target use case: say *"find an open source project worth contributing to"* from the phone, get a short voice briefing later, full report waiting in the app. Research, cloning, tests and server work run on owned machines through coding agents — not inside a chat window.

Three parts: a phone app for voice, a control plane on a home machine, agent sessions for execution.

## How it works

Speech goes to the app. A fast model classifies the request: question or job. Questions get answered in about a second. Jobs become tasks — durable records with state, logs, budgets and artifacts — executed by a coding-agent session in a sandboxed workspace. On completion or when a decision is needed, the app gets a push and can read the summary aloud. Risky actions (pushing code, sending messages, spending money) always wait for explicit approval.

Details: [docs/architecture.md](docs/architecture.md).

## Mobile first

The first draft had a desktop push-to-talk client. Dropped. The value of a voice assistant shows up away from the keyboard; at a desk, a terminal is faster. The phone also brings push notifications, mic access and background audio for free.

MVP = a React Native app and nothing else. No desktop client, no wake word, no smart speaker. IoT satellites come only after the app proves daily use.

## Roadmap

| Phase | Scope | Status |
|---|---|---|
| 0 | Text-only proof: request → task → agent → notification | planning |
| 1 | Mobile MVP: app, push-to-talk, one agent, approvals | planning |
| 2 | Remote machines over SSH | later |
| 3 | Durable memory | later |
| 4 | More agent runtimes, parallel tasks | later |
| 5 | IoT wake-word satellites | future |

Details: [docs/roadmap.md](docs/roadmap.md) · MVP scope: [docs/mvp.md](docs/mvp.md) · settled choices: [docs/decisions.md](docs/decisions.md)

## Full plan

Start with [architecture.md](docs/architecture.md), then:

- [prior-art.md](docs/prior-art.md) — existing projects, what they cover, gaps
- [system-design.md](docs/system-design.md) — components, boundaries, sequence diagrams
- [voice.md](docs/voice.md) — speech pipeline, latency budget, intent routing
- [sessions.md](docs/sessions.md) — session-per-task model, resume, reference resolution
- [memory.md](docs/memory.md) — memory layers, retrieval, correction, deletion
- [task-engine.md](docs/task-engine.md) — state machine, approvals, budgets
- [execution.md](docs/execution.md) — sandboxes, SSH remotes, isolation ladder
- [security.md](docs/security.md) — risk tiers, threat model, secrets
- [data-model.md](docs/data-model.md) — tables and DDL
- [stack.md](docs/stack.md) — technology picks, costs, build-vs-buy
- [code-sketches.md](docs/code-sketches.md) — pseudocode for the core paths
- [risks.md](docs/risks.md) — what's easy, what's hard, what models can't be trusted with

## Stack, short version

Python control plane (FastAPI, Postgres, Redis), Claude Agent SDK for workers, React Native + Expo for the app, Tailscale for networking. Nothing listens on a public interface.

## Feedback

Issues and discussions are open. Especially useful: experience with voice pipelines or agent fleets in daily use.
