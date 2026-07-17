"""ClaudeCliRouter — smart routing on the Claude subscription (no API key, no cash).

Selected when ATTACHE_ROUTER=claude. Runs the same free path as the agent: the
Agent SDK's query() authenticates via the logged-in `claude` CLI, so routing
costs no money — it draws a little subscription allowance per turn. Uses
constrained structured output, so the routing decision is always schema-valid.
No tools are allowed (allowed_tools=[]) — it's a pure classifier, one turn.
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
    "Pick exactly ONE action:\n"
    "- create_task — the user wants you to DO work that takes more than a sentence "
    "to answer: find, research, investigate, build, fix, set up, review, analyze, "
    "look for something. START it; do NOT ask clarifying questions first — capture "
    "their request as `goal` and a short `title`, and let the agent handle "
    "specifics. `speak` is a brief acknowledgement (e.g. 'On it — I'll research "
    "that and let you know.').\n"
    "- task_status — 'what are you working on / did it finish / what did you find'.\n"
    "- continue_task / cancel_task — about an existing task in ACTIVE TASKS.\n"
    "- answer — ONLY genuine conversation or a question you can fully answer in one "
    "or two sentences. When in doubt between answer and create_task for an action "
    "request, choose create_task.\n"
    "Always write a natural spoken `speak`."
)


class ClaudeCliRouter(Router):
    async def route(self, text: str, ctx) -> Decision:
        from claude_agent_sdk import ClaudeAgentOptions, ResultMessage, query

        system = f"{SYSTEM}\n\n{_context_block(ctx)}\n\n{INSTRUCTION}"
        options = ClaudeAgentOptions(
            model=settings.claude_router_model,
            system_prompt=system,
            max_turns=4,  # headroom: the model may reason before emitting the JSON
            allowed_tools=[],  # pure classifier — no tool use, so still bounded
            output_format={"type": "json_schema", "schema": DECISION_SCHEMA},
        )
        data = None
        async for msg in query(prompt=text, options=options):
            if isinstance(msg, ResultMessage):
                data = msg.structured_output
        if not isinstance(data, dict) or "action" not in data:
            return Decision("answer", "Okay.", {})
        args = {k: v for k, v in data.items() if k not in ("action", "speak") and v}
        return Decision(data["action"], data.get("speak", ""), args)
