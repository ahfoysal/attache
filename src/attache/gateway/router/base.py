"""Router interface. Routing is classification + parameter extraction + reply,
produced together. Two backends: HeuristicRouter (offline) and LLMRouter."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

# The router's action vocabulary == the turn handler's dispatch table.
ACTIONS = {
    "answer", "create_task", "continue_task",
    "task_status", "cancel_task", "ask_confirmation",
}


@dataclass
class Decision:
    action: str
    speak: str
    args: dict = field(default_factory=dict)


class Router(ABC):
    @abstractmethod
    async def route(self, text: str, ctx) -> Decision:
        raise NotImplementedError
