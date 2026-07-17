# Stack

## Language split

Python for the core, TypeScript for the UI surfaces. The voice ecosystem is Python-first — Pipecat, faster-whisper, Silero, the smart-turn model all live there, and the Node voice SDKs trail their Python versions. The Claude Agent SDK is first-class in both, so the agent layer doesn't vote. A full-TS build moves faster for two weeks, then pays for it every time a voice component only exists in Python. Two processes, one language each, over HTTP/WS.

## The picks

| Concern | Pick | Trade-off accepted |
|---|---|---|
| Backend | FastAPI | Async-native (SSH, SDK streams, websockets all concurrent); Pydantic doubles as the API contract. Django's batteries traded for lightness |
| Database | Postgres 16 + pgvector | None worth naming. One database for relational + vector + queue duty is the best simplification available |
| Queue/events | Redis pub/sub; Postgres `SKIP LOCKED` for dispatch | Redis is nearly optional at this scale; kept because pub/sub→WS fan-out is annoying to fake in Postgres |
| Voice pipeline | Pipecat (BSD-2) | Most active, vendor-neutral. LiveKit Agents if WebRTC room semantics become needed |
| STT | Deepgram streaming; faster-whisper/whisper.cpp local | Cloud for latency, local path stays wired for privacy-routed and offline turns |
| TTS | OpenAI mini-tts or ElevenLabs Flash; Kokoro local (Apache-2.0) | ElevenLabs is the premium voice at premium price; Kokoro is genuinely good and free |
| Wake word (phase 5) | Porcupine, or openWakeWord with self-trained models | openWakeWord's bundled models are CC-BY-NC — self-training required to avoid that |
| Agent runtime | Claude Agent SDK (Python) | Commercial ToS, not OSS; SDK usage now meters separately from the subscription. Codex SDK (Apache-2.0) is the hedge, added in phase 4 |
| Sandboxing | SDK's built-in sandbox for trusted work; Docker for untrusted; Apple `container` when on macOS 26 | Never hand-roll isolation |
| Mobile app | React Native + Expo | See [decisions.md](decisions.md) — RN over Flutter, bare workflow as the native-audio escape hatch |
| Dashboard | Vite + React SPA served by the gateway | For deep review on a laptop; no SSR, nothing to gain |
| Networking/auth | Tailscale everywhere; single bearer token + device list | A real IdP only if this ever leaves the tailnet. Nothing listens publicly, ever |
| Workflow engine | None — custom state machine; DBOS then Temporal are the graduation path | Recovery correctness becomes an owned problem, contained to ~500 lines |
| Observability | Structured JSON logs + the task event stream itself | The app/dashboard *is* the observability product for tasks; OTel only if latency tuning demands |
| Secrets | 1Password CLI, or sops+age | Infisical self-hosted is the middle option; it's another service to run |

## What it should cost (moderate daily use)

| Line | Monthly | Notes |
|---|---|---|
| Router turns (Haiku-class, ~200/day) | $3–8 | Small prompts, cached system block |
| Agent tasks (Sonnet-class, 2–5 real tasks/day) | $20–100 | The dominant line; per-task budget caps are the governor, and plan-included SDK credit absorbs some |
| STT (1–2h/day cloud) | $5–15 | ~$0 local |
| TTS | $2–20 | $0 with Kokoro |
| Summaries/embeddings | <$3 | |
| **Total** | **~$30–150** | Realtime speech-to-speech APIs would multiply the voice line; another reason for the cascade |

## Build vs buy, per subsystem

| Subsystem | Call | Why |
|---|---|---|
| Voice pipeline | Buy (Pipecat) | Years of edge cases not worth rediscovering |
| STT/TTS/wake word | Buy/rent | Commodity with healthy competition; swappable behind Pipecat |
| Agent runtime | Buy (Agent SDK) | Sessions, permissions, sandboxing, MCP — a year of work, maintained by the vendor with the model. Highest-leverage buy on the list |
| Sandbox infra | Buy (Docker, SDK sandbox, Apple container) | Anthropic's hosted Managed Agents ($0.08/session-hour) is the "buy even more" option; declined — it outsources exactly the control plane I'm building, and local-first is the point |
| Intent routing | Build (thin) | A prompt, a tool list, twenty regexes |
| Task engine + session registry | **Build** | The product. Nothing ships these semantics |
| Memory | Build (Postgres+pgvector) | Frameworks would own the most product-defining data shape; re-evaluate at phase 3 |
| Policy engine | Build | Security semantics that must fit in one head, auditable |
| Mobile app | Build (RN) | The daily surface; Happy (MIT) exists as reference and fallback |
| Networking/secrets/push | Buy (Tailscale, 1Password, ntfy/Expo push) | Solved problems, great free tiers |
