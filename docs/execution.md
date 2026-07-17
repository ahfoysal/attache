# Execution: local and remote

## The isolation ladder

| Target | How | Isolation | When |
|---|---|---|---|
| Local, trusted workspace | Agent SDK on the home base, cwd-scoped | The SDK's built-in OS sandbox (Seatbelt on macOS, bubblewrap on Linux): writes confined to the workspace, network through a domain-allowlist proxy | Own projects |
| Local, untrusted work | Agent inside a container workspace | Docker (or Apple's `container` tool on Apple Silicon — per-container microVMs) | Cloning strangers' repos, running their code — i.e. the flagship GitHub flow |
| Remote, thin | Agent runs locally; an `ssh_exec` tool runs single commands remotely | Remote user account + command policy | Short ops: restart a service, check disk |
| Remote, thick | Runner daemon on the remote; the agent executes where the code lives | Dedicated Unix user + systemd limits, or Docker there | Long tasks on remote codebases — latency and file locality make thin-SSH agents miserable |
| Cloud sandbox | E2B or a throwaway VPS enrolled like any remote | MicroVM | Scale-out experiments, much later |

The thin/thick split is the important line. Thin keeps one brain locally and treats the remote as a tool — right for admin one-liners. Thick moves the brain to the machine with the files — right for real work. Same runner codebase either way; enrolling a remote means installing it, creating its user, registering the machine row.

## SSH, done carefully

- **AsyncSSH** (actively maintained, async-native, fits FastAPI). One connection manager, per-machine pooled connections, keepalives, backoff.
- **Identity**: a dedicated keypair *per enrolled machine*, generated at enrollment, held only by the gateway's secret broker. Never a personal key, never agent forwarding. The remote account is a purpose-made user with access only to declared project paths; no sudo by default.
- **Networking**: Tailscale between home base and remotes, so the runner port never exists publicly and SSH keys become the second layer, not the first. This one choice deletes a whole class of exposure.
- **Repos move via git**, not rsync of working trees — the repo is then the audit trail. Read-only deploy keys unless a task is explicitly approved to push.
- **Interactive processes** (a dev server the agent needs to watch) run under tmux as processes the executor starts and owns — tmux as supervisor, never as the agent's interface.
- **Every spawned process is registered** (task, machine, pid, started_at), so "what's running?" has a truthful answer and cancel means killing a known process group, not hoping.

## Guardrails on every executor

Same contract locally and remotely, one implementation, one audit format:

- **Policy first.** Every command passes the [policy engine](security.md) before execution: denylist (always-blocked destructive patterns), allowlist (auto-approved per workspace), everything else tier-evaluated. Enforcement lives in the executor, not the prompt.
- **Timeouts and limits.** Default 120s per command, task-level wall-clock cap, ulimit/cgroup ceilings on the runner user, disk quota on workspaces.
- **Environment hygiene.** Executors build env from an explicit per-workspace list — the agent process never inherits a login shell environment. Secrets are injected by reference at spawn time and pattern-redacted from all captured output.
- **Audit log.** Every execution is an append-only `tool_calls` row: command, cwd, machine, policy decision and which rule, exit code, duration, output digest, task and session ids. The black-box recorder, and also what makes "show me what changed" answerable.
