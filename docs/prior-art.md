# Prior art

Before committing to build anything I spent time checking whether someone already built this. Short answer: every layer exists somewhere, the whole exists nowhere I can adopt. The voice edge is solved, the agent runtime is solved, remote control of coding agents is a crowded category, but no maintained open project combines voice, durable task orchestration, layered memory and local+remote agent execution behind one assistant.

One data point that convinced me the gap is real: someone filed a detailed "JARVIS-style hands-free mode for Claude Code" feature request in April 2026 and Anthropic closed it as *not planned*. Claude Code's own voice mode is push-to-talk dictation only. The whitespace is deliberate.

## The projects that matter

| Project | What it solves for me | What it doesn't | Status / license | My verdict |
|---|---|---|---|---|
| **Omnara** (post-2026 pivot) | Nearly this exact vision: voice-first control of Claude-SDK agents, phone/watch approvals, local↔cloud session migration. "No prompts. No syntax. Just talk." | It's a company mid-pivot; the claimed open-sourcing of the new platform doesn't check out against any real source tree; original repo archived | Active · Apache-2.0 claim unverified | Validation and design reference, not a foundation |
| **Happy** (slopus/happy) | Mobile/web client for Claude Code and Codex with realtime voice, E2E-encrypted sync, push notifications, desktop↔phone handoff. 22k+ stars | It follows live sessions; no task engine, no memory, no policy layer, no wake word | Active · MIT | Strongest reuse candidate for the client slice; study its cli/agent/server split |
| **OpenClaw** (ex-Clawdbot) | Proof of demand at absurd scale (~375k stars); gateway daemon + markdown memory + heartbeat patterns worth borrowing | Messaging-first not voice-first; no task state machine; brutal security record (prompt-injection CVE, ~40k exposed instances, poisoned skill marketplace) | Active, foundation-backed · MIT | Borrow patterns; treat its security history as my list of what not to do |
| **Pipecat** | The whole voice loop: VAD, barge-in, turn-taking (open smart-turn model), pluggable STT/LLM/TTS | Nothing about agents, tasks or memory, by design | Very active · BSD-2 | Adopt for the voice plane |
| **LiveKit Agents** | Same category plus a self-hostable WebRTC SFU and its own turn-detector model | Heavier if I don't need the SFU | Very active · Apache-2.0 | Credible alternative; decide on transport needs |
| **Claude Agent SDK** | The whole agent runtime: headless resumable sessions, fork, cross-host session store, permission callback, hooks, MCP, subagents, OS sandbox, cost metering | Everything above a single session: task identity across days, my policy semantics | Very active · commercial ToS (SDK free, usage paid) | Adopt for the workers |
| **Codex CLI/SDK** | A second runtime: Apache-2.0 Rust CLI, programmatic SDK, cloud sandboxes, JSONL rollouts | Same gaps | Very active · Apache-2.0 | Second worker type, later |
| **OpenHands** | MIT agent-server with Docker/K8s sandboxed workspaces, headless REST driving | Its own agent loop; no product layer | Active, funded · MIT | Sandbox-runtime reference, optional third worker |
| **Wyoming stack** (openWakeWord, faster-whisper, Piper) | License-clean voice-edge services as plain Docker containers; $59 satellite hardware exists | Edge only; Piper went GPL-3; satellite protocol shifting toward ESPHome | Active (Open Home Foundation) | The phase-5 IoT shortcut |
| **Letta / Mem0 / Zep-Graphiti** | Packaged memory: fact extraction, stateful agent server, temporal knowledge graph | Each wants to own a layer Postgres+pgvector covers fine at my scale | Active · Apache-2.0 mostly | Skip for now; Mem0's extraction prompts are worth reading |
| **Open Interpreter / 01** | Historical proof of the voice→computer-agent idea | Pivoted away entirely; hardware refunded | Pivoted | Inspiration only |
| **OVOS / Leon / Khoj / Willow** | Mature assistant plumbing, agentic-rewrite ambitions, RAG second-brain, ESP32 edge | All pre-agent or adjacent architectures | Active but niche | Inspiration only |
| **Vibe Kanban / Conductor / Terragon** | Multi-agent dashboards, isolated worktrees, cloud background agents | No voice; also the category is a graveyard, Bloop and Terragon both died in early 2026 | Mixed | Dashboard UX reference |

## What the landscape tells me

The demand signal is unambiguous: OpenClaw's growth, Happy's stars, Omnara's pivot, plus a cottage industry of tiny voice-plus-Claude-Code repos all point at the same unmet want.

Build on protocols, not products. The first half of 2026 killed Terragon and Bloop and forced Omnara to restart. The safe dependencies are the infrastructure layer: Pipecat, the Agent SDK, MCP, Postgres, Wyoming. Not any early-stage product's continuity.

OpenClaw is my security syllabus. Every headline failure it suffered maps to a decision in [security.md](security.md): tailnet-only exposure, credential-free sandboxes for untrusted content, no third-party skill execution.

And nobody has solved voice-grade task memory. The clients follow live sessions; the assistants keep flat memory files. The durable task registry + layered memory + resumable sessions triad is the genuinely novel part of this build.
