"""Deterministic policy evaluation — no LLM in the loop.

Invoked from the agent runner's `can_use_tool` callback and (later) the SSH
executor. Given a tool name and its input, returns a Verdict: which tier, the
matched rule, and whether it may run without an approval.
"""

from __future__ import annotations

from dataclasses import dataclass

from . import rules


@dataclass(frozen=True)
class Verdict:
    tier: str            # T0..T4
    rule: str            # which rule matched
    allowed: bool        # may auto-run (T0/T1) without an approval
    prohibited: bool     # T4 — hard blocked, never overridable

    @property
    def needs_approval(self) -> bool:
        return not self.allowed and not self.prohibited


def _mk(tier: str, rule: str) -> Verdict:
    return Verdict(
        tier=tier,
        rule=rule,
        allowed=tier in rules.ALLOWED_TIERS,
        prohibited=tier == "T4",
    )


class PolicyEngine:
    def classify_command(self, command: str) -> Verdict:
        for pattern, tier, rule in rules.COMMAND_RULES:
            if pattern.search(command):
                return _mk(tier, rule)
        return _mk(rules.DEFAULT_COMMAND_TIER, rules.DEFAULT_COMMAND_RULE)

    def evaluate(self, tool: str, tool_input: dict, task: dict | None = None) -> Verdict:
        if tool in rules.READONLY_TOOLS:
            return _mk("T0", f"readonly-tool:{tool}")
        if tool in rules.EDIT_TOOLS:
            return _mk("T1", f"edit-tool:{tool}")
        if tool == "Bash":
            command = (tool_input or {}).get("command", "")
            return self.classify_command(command)
        # Unknown tool: default to one-time consent rather than silent allow.
        return _mk("T2", f"unknown-tool:{tool}")
