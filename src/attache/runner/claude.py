"""ClaudeAgentRunner — the real backend, on the Claude Agent SDK.

Selected when ATTACHE_AGENT=claude (needs ANTHROPIC_API_KEY and the [claude]
extra). The SDK is imported lazily so the gateway and the scripted path run
without it installed.

The agent reports through an in-process `taskboard` MCP server rather than the
gateway parsing its prose. Every tool call passes the policy callback, which
maps to the risk tiers in docs/security.md: T0/T1 auto-run, T2/T3 request an
approval and wait, T4 hard-deny.
"""

from __future__ import annotations

import json
from pathlib import Path

from ..config import settings
from ..db import Database, J
from ..gateway.approvals import Approvals
from ..gateway.policy import PolicyEngine
from ..gateway.tasks import TaskEngine
from .base import AgentRunner, RunResult
from .taskboard import Taskboard

SYSTEM_PROMPT = """You are a task agent for Attaché. Do the work in the task \
spec, then finish.

Report as you go with the taskboard tools:
- report_progress(msg, step) — one short line per meaningful step.
- save_artifact(name, content, kind) — save reports/outputs to keep.
- remember(content) — durable facts worth recalling later.
- complete(spoken_summary, report) — call this LAST. `spoken_summary` is one or
  two sentences that will be read aloud, ending with the next decision to offer.

Do not push code, open PRs, send messages, or spend money without approval —
those actions are gated and will prompt the user."""


def _compose_prompt(task: dict) -> str:
    spec = task.get("spec") or {}
    parts = [f"Task: {task['title']}", "", f"Goal: {spec.get('goal', task['title'])}"]
    if spec.get("constraints"):
        parts += ["", "Constraints:"] + [f"- {c}" for c in spec["constraints"]]
    if spec.get("context_pack"):
        parts += ["", "Context:"] + [f"- {c}" for c in spec["context_pack"]]
    if spec.get("deliverables"):
        parts += ["", "Deliverables:"] + [f"- {d}" for d in spec["deliverables"]]
    return "\n".join(parts)


class ClaudeAgentRunner(AgentRunner):
    name = "claude"

    def __init__(
        self,
        taskboard: Taskboard,
        engine: TaskEngine,
        policy: PolicyEngine,
        approvals: Approvals,
        db: Database,
    ) -> None:
        self.tb = taskboard
        self.engine = engine
        self.policy = policy
        self.approvals = approvals
        self.db = db

    def _taskboard_server(self, task_id: str):
        from claude_agent_sdk import create_sdk_mcp_server, tool

        tb = self.tb

        @tool("report_progress", "Report a short progress update",
              {"msg": str, "step": str})
        async def report_progress(args):
            await tb.report_progress(task_id, args["msg"], args.get("step"))
            return {"content": [{"type": "text", "text": "ok"}]}

        @tool("save_artifact", "Save an output file to keep",
              {"name": str, "content": str, "kind": str})
        async def save_artifact(args):
            await tb.save_artifact(task_id, args["name"], args["content"],
                                   args.get("kind", "file"))
            return {"content": [{"type": "text", "text": "saved"}]}

        @tool("remember", "Store a durable fact", {"content": str})
        async def remember(args):
            await tb.remember(args["content"])
            return {"content": [{"type": "text", "text": "remembered"}]}

        @tool("complete", "Finish the task with a spoken summary",
              {"spoken_summary": str, "report": str})
        async def complete(args):
            await tb.complete(task_id, args["spoken_summary"], args.get("report"))
            return {"content": [{"type": "text", "text": "completed"}]}

        return create_sdk_mcp_server(
            name="taskboard", version="0.1.0",
            tools=[report_progress, save_artifact, remember, complete],
        )

    def _permission_callback(self, task: dict):
        task_id = task["id"]

        async def can_use_tool(tool_name: str, tool_input: dict, context):
            verdict = self.policy.evaluate(tool_name, tool_input, task)
            await self._audit(task_id, tool_name, tool_input, verdict)

            from claude_agent_sdk import PermissionResultAllow, PermissionResultDeny

            if verdict.allowed:
                return PermissionResultAllow()
            if verdict.prohibited:
                return PermissionResultDeny(
                    message=f"Prohibited by policy ({verdict.rule})."
                )
            # T2 / T3 — request an approval and wait a short window.
            action = f"{tool_name}: {json.dumps(tool_input)[:200]}"
            appr = await self.approvals.request(
                task_id, action=action, detail={"tool": tool_name, "input": tool_input},
                tier=verdict.tier,
            )
            decision = await self.approvals.wait(str(appr["id"]), timeout=120)
            if decision == "approved":
                return PermissionResultAllow()
            if decision == "timeout":
                await self.engine.transition(
                    task_id, "waiting_approval",
                    event={"approval_id": str(appr["id"])},
                )
                return PermissionResultDeny(message="Approval pending; task parked.")
            return PermissionResultDeny(message="Denied by user.")

        return can_use_tool

    async def _audit(self, task_id, tool_name, tool_input, verdict) -> None:
        await self.db.execute(
            """insert into tool_calls (task_id, tool, input_digest, policy_decision)
               values (%s, %s, %s, %s)""",
            task_id, tool_name,
            J({"input": str(tool_input)[:500]}),
            f"{verdict.tier}:{verdict.rule}:{'allow' if verdict.allowed else 'gate'}",
        )

    async def run(self, task: dict) -> RunResult:
        try:
            from claude_agent_sdk import ClaudeAgentOptions, ClaudeSDKClient
        except ImportError:
            return RunResult(
                ok=False,
                error="claude-agent-sdk not installed — `uv sync --extra claude` "
                      "and set ANTHROPIC_API_KEY, or use ATTACHE_AGENT=scripted.",
            )

        tid = task["id"]
        workspace = settings.workspaces / str(tid)
        workspace.mkdir(parents=True, exist_ok=True)

        session_row = await self.db.fetchrow(
            """insert into agent_sessions (task_id, runtime, model, status)
               values (%s, 'claude-agent-sdk', %s, 'active') returning id""",
            tid, settings.agent_model,
        )

        options = ClaudeAgentOptions(
            cwd=str(workspace),
            model=settings.agent_model,
            system_prompt=SYSTEM_PROMPT,
            permission_mode="default",
            can_use_tool=self._permission_callback(task),
            mcp_servers={"taskboard": self._taskboard_server(tid)},
        )

        final_text: list[str] = []
        external_session_id: str | None = None
        cost = 0.0
        try:
            async with ClaudeSDKClient(options=options) as client:
                await client.query(_compose_prompt(task))
                async for msg in client.receive_response():
                    external_session_id = getattr(msg, "session_id", external_session_id)
                    cost = getattr(msg, "total_cost_usd", None) or cost
                    for block in getattr(msg, "content", []) or []:
                        text = getattr(block, "text", None)
                        if text:
                            final_text.append(text)
        except Exception as exc:  # surface the failure honestly, don't fake success
            await self.tb.fail(tid, f"agent error: {exc}")
            await self._close_session(session_row["id"], external_session_id, cost, "abandoned")
            return RunResult(ok=False, error=str(exc), cost_usd=cost)

        # If the agent didn't call taskboard.complete, finish from its final text.
        current = await self.engine.get(tid)
        if current and current["state"] == "running":
            summary = " ".join(final_text)[-400:] or "Task finished."
            await self.tb.complete(tid, spoken_summary=summary,
                                   report="\n".join(final_text) or None)

        await self._close_session(session_row["id"], external_session_id, cost, "closed")
        return RunResult(ok=True, session_id=external_session_id, cost_usd=cost)

    async def _close_session(self, sid, external_id, cost, status) -> None:
        await self.db.execute(
            """update agent_sessions
                 set external_session_id = %s, cost_usd = %s, status = %s, closed_at = now()
               where id = %s""",
            external_id, cost, status, sid,
        )
