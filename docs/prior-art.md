# Prior art

Survey done before committing to build. Short answer: every layer exists somewhere, the whole exists nowhere. The voice edge is solved, the agent runtime is solved, remote control of coding agents is a crowded category — but no maintained open project combines voice, durable task orchestration, layered memory and local+remote agent execution behind one assistant.

One confirming data point: a detailed "JARVIS-style hands-free mode for Claude Code" feature request was closed *not planned* by Anthropic in April 2026. Claude Code's own voice mode is push-to-talk dictation only. The gap is deliberate, not an oversight.

## Projects that matter

| Project | Covers | Doesn't cover | Status / license | Verdict |
|---|---|---|---|---|
| **Omnara** (post-2026 pivot) | Nearly this exact vision: voice-first control of Claude-SDK agents, phone/watch approvals, local↔cloud session migration. "No prompts. No syntax. Just talk." | A company mid-pivot; claimed open-sourcing of the new platform doesn't match any locatable source tree; original repo archived | Active · Apache-2.0 claim unverified | Validation and design reference, not a foundation |
| **Happy** (slopus/happy) | Mobile/web client for Claude Code and Codex: realtime voice, E2E-encrypted sync, push notifications, desktop↔phone handoff. 22k+ stars | Follows live sessions only — no task engine, no memory, no policy layer, no wake word | Active · MIT | Strongest reuse candidate for the client slice; the cli/agent/server split is worth studying |
| **OpenClaw** (ex-Clawdbot) | Proof of demand at ~375k stars; gateway daemon, markdown memory, heartbeat/cron patterns | Messaging-first, not voice-first; no task state machine; severe security record (prompt-injection CVE, ~40k exposed instances, poisoned skill marketplace) | Active, foundation-backed · MIT | Borrow patterns; treat the security history as a list of what not to do |
| **Pipecat** | The whole voice loop: VAD, barge-in, turn-taking (open smart-turn model), pluggable STT/LLM/TTS | Agents, tasks, memory — out of scope by design | Very active · BSD-2 | Adopt for the voice plane |
| **LiveKit Agents** | Same category plus self-hostable WebRTC SFU and its own turn-detector model | Heavier without a need for the SFU | Very active · Apache-2.0 | Credible alternative; decide on transport needs |
| **Claude Agent SDK** | The agent runtime: headless resumable sessions, fork, cross-host session store, permission callback, hooks, MCP, subagents, OS sandbox, cost metering | Everything above a single session: task identity across days, custom policy semantics | Very active · commercial ToS (SDK free, usage paid) | Adopt for the workers |
| **Codex CLI/SDK** | Second runtime: Apache-2.0 Rust CLI, programmatic SDK, cloud sandboxes, JSONL rollouts | Same gaps | Very active · Apache-2.0 | Second worker type, phase 4 |
| **OpenHands** | MIT agent-server with Docker/K8s sandboxed workspaces, headless REST driving | Its own agent loop; no product layer | Active, funded · MIT | Sandbox-runtime reference; optional third worker |
| **Wyoming stack** (openWakeWord, faster-whisper, Piper) | License-clean voice-edge services as plain Docker containers; $59 satellite hardware exists | Edge only; Piper went GPL-3; satellite protocol shifting toward ESPHome | Active (Open Home Foundation) | The phase-5 IoT shortcut |
| **Letta / Mem0 / Zep-Graphiti** | Packaged memory: fact extraction, stateful agent server, temporal knowledge graph | Each owns a layer Postgres+pgvector covers at single-user scale | Active · Apache-2.0 mostly | Skip for now; Mem0's extraction prompts are worth reading |
| **Open Interpreter / 01** | Historical proof of the voice→computer-agent idea | Pivoted away entirely; hardware refunded | Pivoted | Inspiration only |
| **OVOS / Leon / Khoj / Willow** | Mature assistant plumbing, agentic-rewrite ambitions, RAG second-brain, ESP32 edge | Pre-agent or adjacent architectures | Active but niche | Inspiration only |
| **Vibe Kanban / Conductor / Terragon** | Multi-agent dashboards, isolated worktrees, cloud background agents | No voice; the category is a graveyard — Bloop and Terragon both died in early 2026 | Mixed | Dashboard UX reference |

## Takeaways

- Demand is proven: OpenClaw's growth, Happy's stars, Omnara's pivot, plus a cottage industry of small voice-plus-Claude-Code repos, all pointing at the same unmet want.
- Build on protocols, not products. H1 2026 killed Terragon and Bloop and forced Omnara to restart. Safe dependencies are the infrastructure layer: Pipecat, the Agent SDK, MCP, Postgres, Wyoming.
- OpenClaw's failures map one-to-one onto decisions in [security.md](security.md): tailnet-only exposure, credential-free sandboxes for untrusted content, no third-party skill execution.
- Nobody has solved voice-grade task memory. Clients follow live sessions; assistants keep flat memory files. The durable task registry + layered memory + resumable sessions triad is the genuinely novel part of this build.
