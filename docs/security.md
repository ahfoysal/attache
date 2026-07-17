# Security and permissions

Three things I assume are always true: the model can be manipulated by text it reads; I will over-trust the system once it works; and any credential reachable by a process can eventually be exfiltrated by that process. Design goal: **no single deception can cause irreversible harm.** Prompt injection may waste a task's budget; it must never be able to push code, spend money, or read my mail.

## Risk tiers

| Tier | Policy | Actions |
|---|---|---|
| **T0 — auto** | No prompt, logged | Read files in workspace; allowlisted read-only commands; web reads from allowlisted domains; writing scratch/artifacts |
| **T1 — workspace-scoped** | Auto only inside an approved workspace | Edit files; branches; local commits; package installs *inside containers*; project build/test commands |
| **T2 — one-time consent** | First use per (action, scope) asks; remembered, revocable | Cloning a new external repo; a new network domain; installs outside containers; reads outside the workspace; long-lived processes |
| **T3 — every time** | Explicit approval per action, read back to me | Push to any remote; open a PR; send any message; delete beyond workspace; anything touching credentials; sudo; purchase-adjacent steps |
| **T4 — never** | Hard-blocked in the executor, not voice-overridable | Force-push shared branches; delete repos/infra; modify the policy engine, its config, or audit logs; read the secret store; disable the sandbox; financial transactions |

Mapping the obvious actions: read files T0 (T2 outside workspace), edit T1, delete T1 inside / T3 beyond, shell T0–T3 by pattern, installs T1/T2, SSH access T2 per machine, GitHub credentials T3 per use, messages T3, purchases T4 for now, system settings T4, push/PR T3.

## Enforcement: three layers, no single point of failure

1. **Policy engine decides.** Deterministic, data-driven rules, no LLM in the loop, invoked from the SDK's `can_use_tool` callback and from the executors. LLM auto-approval classifiers may reduce friction inside T0–T1; they never decide T3.
2. **OS/container layer contains.** SDK sandbox locally, Docker/microVM for untrusted work, Unix users + cgroups + tailnet ACLs on remotes. If the policy layer is somehow talked around, the walls hold.
3. **Credential layer limits blast radius.** Tools reference secrets by name; the executor resolves via the broker at spawn time into that one process env, and scrubs output. The agent never sees values in context. Fine-grained GitHub PATs scoped per purpose (read-only research vs push-capable), short expiries.

## The attacks I'm designing for

| Attack | Defense |
|---|---|
| Prompt injection (pages, issues, READMEs instructing the agent) | Structural, not textual: research tasks run in containers holding zero credentials, egress allowlisted; outward actions stay T3 regardless of what the agent believes; instructions found in content get surfaced to me, quoted, never followed. Injected text can waste a budget — the design's job is making that *all* it can do |
| Malicious repo (install scripts, hooks, build files) | Untrusted repo code never runs on the host: clone, install, build, test in the container tier only. `npm install` of a stranger's lockfile is code execution; treated as such |
| Secret leakage | Absent from prompts and env by construction; output redaction before storage; distiller redaction before memory writes; periodic artifact scans for token patterns |
| Destructive shell | Executor denylist evaluated on the parsed command (`rm -rf` outside workspace, `mkfs`, `dd` to devices, force-push, history rewrites), plus filesystem confinement so novel phrasings can't reach outside anyway |
| Dependency attacks | Container-only installs for untrusted work; lockfile-only where lockfiles exist; new top-level deps surfaced in the close-out |
| Unauthorized network | Default-deny egress in sandboxes with per-task domain allowlists; expansion is a T2 approval naming the domain |
| The agent editing its own rules | Policy config, gateway code and audit logs live outside every workspace, owned by a different Unix user, hash-pinned at gateway start; executor hard-blocks those paths. An agent asked to improve Attaché works on a *copy* in a normal workspace |
| A compromised remote | Assume it happens: per-machine keys and tunnel ACLs so a lost box can't reach the others; remotes hold no long-lived provider keys — model calls route through the gateway's LLM proxy on revocable per-machine virtual keys; artifacts coming back are data, never executed on the home base |

OpenClaw's 2026 security history (internet-exposed gateways, injection-driven RCE, a poisoned skill marketplace) is the cautionary syllabus here. Every one of those maps to a line above.
