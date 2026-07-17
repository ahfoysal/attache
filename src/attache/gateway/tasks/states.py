"""The task lifecycle as a pure transition table.

This module has no I/O so the legality of every edge is unit-testable in
isolation. docs/task-engine.md's state diagram is the source of truth; a few
pragmatic edges (cancel-from-queued, cancel-from-blocked, fail-from-planning)
are added here and noted.
"""

from __future__ import annotations

from enum import StrEnum


class State(StrEnum):
    CREATED = "created"
    PLANNING = "planning"
    WAITING_APPROVAL = "waiting_approval"
    RUNNING = "running"
    BLOCKED = "blocked"
    PAUSED = "paused"
    FAILED = "failed"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


# from-state -> set of allowed to-states
TRANSITIONS: dict[State, set[State]] = {
    State.CREATED: {State.PLANNING, State.RUNNING, State.CANCELLED},
    State.PLANNING: {State.WAITING_APPROVAL, State.RUNNING, State.FAILED, State.CANCELLED},
    State.WAITING_APPROVAL: {State.RUNNING, State.PAUSED, State.CANCELLED},
    State.RUNNING: {
        State.WAITING_APPROVAL,
        State.BLOCKED,
        State.PAUSED,
        State.FAILED,
        State.COMPLETED,
        State.CANCELLED,
    },
    State.BLOCKED: {State.RUNNING, State.FAILED, State.CANCELLED},
    State.PAUSED: {State.RUNNING, State.CANCELLED},
    State.FAILED: {State.RUNNING, State.CANCELLED},
    State.COMPLETED: {State.RUNNING},  # reopen for a follow-up
    State.CANCELLED: set(),            # terminal
}

# States a task can never leave (cancelled is final; completed can reopen).
TERMINAL: frozenset[State] = frozenset({State.CANCELLED})

# States the dispatcher/notifier treat as "the task has stopped for now".
RESTING: frozenset[State] = frozenset(
    {State.WAITING_APPROVAL, State.BLOCKED, State.PAUSED, State.FAILED,
     State.COMPLETED, State.CANCELLED}
)


def is_legal(frm: State, to: State) -> bool:
    return to in TRANSITIONS.get(frm, set())


class IllegalTransition(Exception):
    def __init__(self, frm: State, to: State) -> None:
        super().__init__(f"illegal task transition: {frm} -> {to}")
        self.frm = frm
        self.to = to
