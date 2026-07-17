from .artifacts import ArtifactStore
from .base import AgentRunner, RunResult
from .taskboard import Taskboard


def build_runner(name: str, *, taskboard, engine, policy, approvals, db) -> AgentRunner:
    if name == "scripted":
        from .scripted import ScriptedRunner

        return ScriptedRunner(taskboard)
    if name == "claude":
        from .claude import ClaudeAgentRunner

        return ClaudeAgentRunner(taskboard, engine, policy, approvals, db)
    raise ValueError(f"unknown agent backend: {name!r} (use 'scripted' or 'claude')")


__all__ = ["AgentRunner", "RunResult", "Taskboard", "ArtifactStore", "build_runner"]
