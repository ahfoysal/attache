"""Pure transition-table tests — no DB, no I/O."""

from attache.gateway.tasks.states import (
    RESTING,
    TERMINAL,
    TRANSITIONS,
    State,
    is_legal,
)


def test_every_state_has_an_entry():
    for state in State:
        assert state in TRANSITIONS


def test_happy_path_is_legal():
    assert is_legal(State.CREATED, State.RUNNING)
    assert is_legal(State.RUNNING, State.COMPLETED)
    assert is_legal(State.RUNNING, State.WAITING_APPROVAL)
    assert is_legal(State.WAITING_APPROVAL, State.RUNNING)
    assert is_legal(State.COMPLETED, State.RUNNING)  # reopen for follow-up


def test_illegal_edges():
    assert not is_legal(State.COMPLETED, State.BLOCKED)
    assert not is_legal(State.CANCELLED, State.RUNNING)  # terminal
    assert not is_legal(State.CREATED, State.COMPLETED)  # must run first


def test_cancelled_is_terminal():
    assert State.CANCELLED in TERMINAL
    assert TRANSITIONS[State.CANCELLED] == set()


def test_resting_states():
    assert State.COMPLETED in RESTING
    assert State.RUNNING not in RESTING


def test_no_transition_targets_unknown_states():
    valid = set(State)
    for froms, tos in TRANSITIONS.items():
        assert tos <= valid, f"{froms} has an unknown target"
