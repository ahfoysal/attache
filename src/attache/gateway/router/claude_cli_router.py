"""ClaudeCliRouter — smart routing on the Claude subscription (no API key, no cash).

Selected when ATTACHE_ROUTER=claude. Routes via the Agent SDK / claude CLI using
constrained structured output — same free subscription path as the agent.

Each route() is a fresh, self-contained query(): it connects, classifies, and
disconnects. We deliberately do NOT hold a persistent session — a long-lived
router session contends with the agent's own Claude sessions on the same
subscription and can stall them. Since obvious task/status/cancel turns are
handled instantly upstream (fast_route), the router is only hit for genuine
conversation, where a per-call cold start is acceptable.
"""

from __future__ import annotations

from ...config import settings
from .base import Decision, Router
from .llm import SYSTEM, _context_block

DECISION_SCHEMA = {
    "type": "object",
    "properties": {
        "action": {
            "type": "string",
            "enum": ["answer", "create_task", "continue_task", "task_status", "cancel_task"],
        },
        "speak": {"type": "string", "description": "One or two spoken sentences to say back."},
        "title": {"type": "string", "description": "Short, speakable task title (create_task)."},
        "goal": {"type": "string", "description": "What the agent should achieve (create_task)."},
        "task_ref": {"type": "string", "description": "Task id or title (continue/status/cancel)."},
        "instruction": {"type": "string", "description": "Follow-up instruction (continue_task)."},
    },
    "required": ["action", "speak"],
    "additionalProperties": False,
}

INSTRUCTION = (
    "You are a conversational assistant that can also dispatch background work. "
    "Use the RECENT CONVERSATION to stay in context and resolve references like "
    "'start', 'that one', 'yes', 'the first', 'do it' from what was just said.\n"
    "Pick exactly ONE action:\n"
    "- answer — normal conversation, chit-chat, or a question you can answer "
    "directly. This is the DEFAULT for talking; keep it natural and in-context.\n"
    "- create_task — ONLY when the user clearly wants you to go DO substantial work "
    "in the background (research, build, fix, investigate, set up). Capture their "
    "request as `goal` and a short `title`; don't ask clarifying questions first.\n"
    "- task_status — 'what are you working on / did it finish / what did you find'.\n"
    "- continue_task / cancel_task — about an existing task in ACTIVE TASKS "
    "(resolve which one from the conversation).\n"
    "Always write a natural spoken `speak` that fits the conversation."
)


class ClaudeCliRouter(Router):
    async def route(self, text: str, ctx) -> Decision:
        from claude_agent_sdk import ClaudeAgentOptions, ResultMessage, query

        system = f"{SYSTEM}\n\n{INSTRUCTION}"
        options = ClaudeAgentOptions(
            model=settings.claude_router_model,
            system_prompt=system,
            max_turns=4,          # headroom: model may reason before emitting JSON
            allowed_tools=[],     # pure classifier — no tools, still bounded
            setting_sources=[],   # skip loading project/user settings — faster
            output_format={"type": "json_schema", "schema": DECISION_SCHEMA},
        )
        prompt = f"{_context_block(ctx)}\n\nUser message: {text}"
        data = None
        async for msg in query(prompt=prompt, options=options):
            if isinstance(msg, ResultMessage):
                data = msg.structured_output
        if not isinstance(data, dict) or "action" not in data:
            return Decision("answer", "Okay.", {})
        args = {k: v for k, v in data.items() if k not in ("action", "speak") and v}
        return Decision(data["action"], data.get("speak", ""), args)
