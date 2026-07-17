"""Agent runner interface.

One method: run a task to a terminal state, reporting through the taskboard.
Two implementations select at config time — ScriptedRunner (offline, for tests
and app development) and ClaudeAgentRunner (the real Agent SDK backend).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class RunResult:
    ok: bool
    session_id: str | None = None
    cost_usd: float = 0.0
    error: str | None = None


class AgentRunner(ABC):
    name: str = "base"

    @abstractmethod
    async def run(self, task: dict) -> RunResult:
        """Drive `task` to completion/failure, reporting via the taskboard."""
        raise NotImplementedError
