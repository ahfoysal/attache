"""Tool schemas for the LLM router. Routing == tool selection (docs/voice.md)."""

from __future__ import annotations

ROUTER_TOOLS = [
    {
        "name": "answer",
        "description": "Answer a conversational question or chat directly. Use for "
                       "anything that does not require running a background task.",
        "input_schema": {
            "type": "object",
            "properties": {"speak": {"type": "string", "description": "The spoken reply."}},
            "required": ["speak"],
        },
    },
    {
        "name": "create_task",
        "description": "Start a new background task for work that takes a while "
                       "(research, coding, investigation).",
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Short, speakable title."},
                "goal": {"type": "string", "description": "What the agent should achieve."},
                "constraints": {"type": "array", "items": {"type": "string"}},
                "speak": {"type": "string", "description": "One-sentence acknowledgement."},
            },
            "required": ["title", "goal", "speak"],
        },
    },
    {
        "name": "continue_task",
        "description": "Send a follow-up instruction to an existing task.",
        "input_schema": {
            "type": "object",
            "properties": {
                "task_ref": {"type": "string", "description": "Task id or title reference."},
                "instruction": {"type": "string"},
                "speak": {"type": "string"},
            },
            "required": ["task_ref", "instruction", "speak"],
        },
    },
    {
        "name": "task_status",
        "description": "Report the status of a task or of current work.",
        "input_schema": {
            "type": "object",
            "properties": {"task_ref": {"type": "string"}},
        },
    },
    {
        "name": "cancel_task",
        "description": "Cancel a running task.",
        "input_schema": {
            "type": "object",
            "properties": {"task_ref": {"type": "string"}, "speak": {"type": "string"}},
        },
    },
]


def decision_from_tool_use(name: str, args: dict):
    from .base import Decision

    speak = args.get("speak", "")
    task_args = {k: v for k, v in args.items() if k != "speak"}
    return Decision(action=name, speak=speak, args=task_args)
