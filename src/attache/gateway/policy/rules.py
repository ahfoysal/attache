"""Data-driven policy rules. Pattern → tier, evaluated on the parsed command.

Tiers (docs/security.md):
  T0 auto · T1 workspace-scoped · T2 one-time consent · T3 confirm every time
  · T4 prohibited (hard block).
"""

from __future__ import annotations

import re

# Read-only tools the agent may always use.
READONLY_TOOLS = {"Read", "Glob", "Grep", "WebFetch", "WebSearch", "NotebookRead", "TodoWrite"}
# Tools that edit within the workspace.
EDIT_TOOLS = {"Write", "Edit", "MultiEdit", "NotebookEdit"}

# Bash command classification. First match wins, top to bottom.
# Each entry: (compiled regex, tier, rule-name).
COMMAND_RULES: list[tuple[re.Pattern, str, str]] = [
    # T4 — prohibited, hard block regardless of workspace.
    (re.compile(r"\brm\s+-rf?\s+(/|~|\$HOME|\*)\s*$"), "T4", "rm-rf-root"),
    (re.compile(r"\bmkfs\b"), "T4", "mkfs"),
    (re.compile(r"\bdd\b.*\bof=/dev/"), "T4", "dd-to-device"),
    (re.compile(r":\(\)\s*\{.*\};:"), "T4", "fork-bomb"),
    (re.compile(r"\b(shutdown|reboot|halt|poweroff)\b"), "T4", "power-control"),
    (re.compile(r"git\s+push\s+.*--force.*\b(main|master|prod)\b"), "T4", "force-push-shared"),
    (re.compile(r"\bgit\s+push\s+.*\+"), "T4", "force-push-refspec"),
    # T3 — confirm every time (outward / irreversible).
    (re.compile(r"\bgit\s+push\b"), "T3", "git-push"),
    (re.compile(r"\bgh\s+pr\s+create\b"), "T3", "open-pr"),
    (re.compile(r"\bgh\s+release\b"), "T3", "gh-release"),
    (re.compile(r"\b(mail|sendmail|msmtp)\b"), "T3", "send-mail"),
    (re.compile(r"\bsudo\b"), "T3", "sudo"),
    # T2 — one-time consent (installs / reach outside workspace).
    (re.compile(r"\b(npm|pnpm|yarn)\s+(install|add|i)\b"), "T2", "node-install"),
    (re.compile(r"\b(pip|pip3|uv)\s+(install|add)\b"), "T2", "python-install"),
    (re.compile(r"\bbrew\s+install\b"), "T2", "brew-install"),
    (re.compile(r"\bgit\s+clone\b"), "T2", "git-clone"),
    # T0 — read-only allowlist.
    (re.compile(r"^\s*(ls|pwd|echo|cat|head|tail|wc|which|env|date|whoami)\b"), "T0", "read-only-shell"),
    (re.compile(r"^\s*git\s+(status|log|diff|show|branch|remote|rev-parse)\b"), "T0", "git-read"),
    (re.compile(r"^\s*gh\s+(repo\s+view|search|issue\s+list|pr\s+list)\b"), "T0", "gh-read"),
    (re.compile(r"^\s*(grep|rg|find|fd|tree|jq)\b"), "T0", "search-shell"),
    (re.compile(r"^\s*(pytest|jest|vitest|go\s+test|cargo\s+test)\b"), "T0", "run-tests"),
    (re.compile(r"^\s*(npm|pnpm|yarn)\s+(test|run\s+test|run\s+build|run\s+lint)\b"), "T0", "npm-scripts"),
]

# Default tier for a shell command that matches nothing above: workspace-scoped.
DEFAULT_COMMAND_TIER = "T1"
DEFAULT_COMMAND_RULE = "shell-default"

ALLOWED_TIERS = {"T0", "T1"}  # auto-run without an approval
