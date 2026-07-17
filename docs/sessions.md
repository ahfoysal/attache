# Agent sessions

The heart of the design. Options first, then the pick.

## Options

| Approach | Verdict | Why |
|---|---|---|
| One permanent assistant session | No | Context pollution is fatal: yesterday's SSH debugging bleeds into today's research, the window fills with unrelated tool output, one confused compaction damages everything |
| **One session per task** | **Yes** | Isolation matches the mental model. A task's session holds exactly its own working state. Resume the task = resume the session. Kill it and nothing else notices |
| One session per project | As a memory scope, yes; as a session, no | A project session accumulates the same pollution as a god-session, just slower. Project knowledge flows through notes files, not shared context |
| Parent assistant delegating to child agents | The shape yes, as LLM sessions no | The "parent" is the orchestrator *service* plus the stateless router — deterministic code, not a long-lived model session that can drift. Within a task, SDK subagents are fair game |
| Stateless calls + reconstructed context | Not as primary | Reconstruction loses implicit working state; an agent mid-refactor knows things nobody wrote down. Kept as disaster recovery: any task can cold-restart from its record and artifacts |
| Persistent sessions in tmux | No | Scraping a TUI yields strings where the SDK gives structured messages, tool hooks and a real permission callback. tmux keeps one narrow job: supervising interactive processes an agent needs to watch |

## The mechanism

The Claude Agent SDK persists every session as a resumable transcript with a stable id; passing `resume` restores full working context, and forking branches a what-if without contaminating the original. The session manager is therefore mostly a registry table mapping `task → (session_id, runner, workspace, machine, status, summary)` plus lifecycle code. The hard state problem is already solved by the SDK; not worth rebuilding.

Rules:

- One *active* session per task; follow-ups route into it. If a task's direction changes fundamentally, it gets a fresh session seeded from the stored summary instead of dragging a confused transcript forward.
- Sessions are pinned to the machine and workspace where they started. A session resumed against a different filesystem is dangerously wrong. "Continue it on my server" is an explicit *migration*: summarize state, sync the repo, fresh session on the target seeded with the summary. (The SDK's session-store adapter can do true cross-host resume; the summary-and-restart version is simpler and usually enough.)
- Every session ends by writing a structured close-out — summary, decisions, artifacts, next steps — through the taskboard tools. That's what makes cheap cold restarts and cross-session references possible.

## How "continue the task from yesterday" resolves

The router's system prompt is rebuilt every turn with a cheap context block: an active-task shortlist (id, title, state, one-line last event — a few hundred tokens) plus top memory hits for the utterance. Resolution then falls out of ordinary tool use:

- *"What happened with that GitHub search?"* → shortlist match → `task_status` → narrate the stored last event and spoken summary.
- *"Continue the task from yesterday."* → if ambiguous, one disambiguating question ("the GitHub research or the SSL fix?"). Cheaper than resuming the wrong session, every time.
- *"Ask the coding agent to fix the tests."* → `continue_task` against the task whose session already sits in that repo; the instruction lands as a new message in the resumed session.
- *"Use the same repository we discussed."* → repos are first-class rows; retrieval surfaces the earlier reference and the new task spec points at it.

The anti-pollution guarantee: tasks share **no** LLM context. All continuity flows through three explicit, inspectable channels — task records, memory rows, session close-outs. If a reference can't be resolved from those, the assistant asks, which is the correct behavior anyway.
