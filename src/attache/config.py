"""Runtime configuration, read from environment / .env with the ATTACHE_ prefix."""

from __future__ import annotations

import os
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="ATTACHE_", env_file=".env", extra="ignore"
    )

    database_url: str = "postgresql://apple@localhost:5432/attache"
    redis_url: str = "redis://localhost:6379/0"

    # Backend selection. The "scripted"/"heuristic" pair runs with no API key;
    # "claude"/"llm" need ANTHROPIC_API_KEY and the [claude] extra.
    agent: str = "scripted"       # scripted | claude
    router: str = "heuristic"     # heuristic | llm

    # agent_model drives the Agent SDK via the claude CLI (aliases resolve to
    # the latest; verified with "haiku"). router_model is used only by the
    # anthropic API path, which needs an exact id.
    router_model: str = "claude-haiku-4-5"
    agent_model: str = "sonnet"

    workspace_root: str = "~/.attache/workspaces"
    artifact_root: str = "~/.attache/artifacts"

    @property
    def workspaces(self) -> Path:
        return Path(self.workspace_root).expanduser()

    @property
    def artifacts(self) -> Path:
        return Path(self.artifact_root).expanduser()

    @property
    def has_api_key(self) -> bool:
        return bool(os.environ.get("ANTHROPIC_API_KEY"))


settings = Settings()
