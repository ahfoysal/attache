# Risks

## Easy, hard, unreliable

| Genuinely easy | Hard but tractable | Unreliable with current models |
|---|---|---|
| Push-to-talk loop (days, with Pipecat); task CRUD; SDK agent spawning; push notifications; basic policy tiers | Endpointing and barge-in *polish*; reference resolution across days; approval UX that's safe but not annoying; remote hardening; retrieval quality | Multi-hour unattended tasks (drift, rabbit holes — contained by budgets and milestone check-ins); agents' self-assessment of "done" (verify with tests and artifacts, not claims); wake words in noise; voice-only complex disambiguation |

## Top risks

| Risk | Severity | Mitigation |
|---|---|---|
| Prompt injection → credentialed action | Critical | The security triad: credential-free sandboxes for untrusted content, egress allowlists, approval gates on everything outward. Assume injection *succeeds* at the text layer and make that not matter |
| Cost runaway | High | Per-task budget caps in the runner, a daily ceiling in the gateway, cost printed on every close-out, cached router prompt |
| "It feels slow" | High | The latency budget tracked per turn from day one; acknowledge before enqueueing; sentence-streamed TTS; never block speech on a DB write |
| State divergence (DB says running, process is dead) | High | Runner heartbeats, reconciliation sweep at gateway start, append-only events as ground truth for repair |
| Trust collapse after one bad autonomous action | Critical | Start over-gated, loosen with evidence. Every action explicable from the audit log. No "it seemed like you'd want that" surprises. Trust is the product and dies in one incident |
| Scope creep toward an everything-assistant | Medium | The category line: agent work, not messaging integrations and smart-home breadth. Written down so it can't be quietly crossed |

## Direct answers to the awkward questions

**What should never be autonomous:** pushing code, opening PRs, sending anything to another human, spending money, deleting outside workspaces, touching credentials, changing its own policy. Not because models can't, but because one error there costs more than all the saved confirmations combined.

**What starts gated but can graduate:** package installs on the host, new network domains, new repo clones, long-lived processes. The one-time-consent tier with per-scope memory is exactly the graduation mechanism.

**What gets expensive:** agent tokens (dominant — a real task runs $1–5), then cloud STT at heavy daily use, then premium TTS. Routing, embeddings, summaries and storage stay near free.

**What creates latency:** endpointing, router first-token, and nothing else if the architecture holds — every slow thing (agents, memory writes, artifacts) is async by design. Cellular adds variance the design can't remove, only tolerate.

**Persistent terminals vs API-driven agents:** API-driven wins decisively. Structured message streams instead of scraped TUI text, a real permission callback instead of expect-scripting "Allow?" prompts, durable session files instead of fragile live processes, per-session cost accounting. The instinct behind persistent terminals — warm context, no cold starts — is correct, and SDK resume satisfies it. tmux keeps one job: supervising interactive processes an agent needs to watch.

**Always-listening in v1?** No. Hold-to-talk skips the two worst problems (wake-word tuning, always-on trust) and teaches everything else the project needs to learn. An always-on *brain* — heartbeat checking tasks, queueing announcements — yes from day one; that's just a scheduler.
