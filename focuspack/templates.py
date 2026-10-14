"""
Task / mission prompt templates for focuspack.
Prepends or appends structured, battle-tested system instructions tailored for
Claude 3.5/3.7, ChatGPT (GPT-4o), and Gemini 1.5/2.0.
"""

from __future__ import annotations

TASK_TEMPLATES: dict[str, str] = {
    "bugfix": (
        "You are a principal debugging engineer. Analyze the enclosed focus targets and "
        "their dependency contracts. Identify potential root causes, edge case failures, "
        "or race conditions, and provide a clean, minimal unified diff patch to fix the bug."
    ),
    "review": (
        "You are a senior staff code reviewer. Review the enclosed focus targets for: "
        "(1) Security vulnerabilities & input validation, "
        "(2) Concurrency, async, and state hazards, "
        "(3) API design and contract compliance with imported dependencies. "
        "Provide prioritized, constructive feedback with concrete code suggestions."
    ),
    "refactor": (
        "You are an expert software architect. Propose an idiomatic refactoring of the focus targets "
        "to improve readability, testability, and separation of concerns. Do not change external "
        "interfaces or break existing caller contracts."
    ),
    "explain": (
        "You are a technical lead explaining a codebase to a new team member. Explain the core "
        "responsibilities, control flow, key algorithms, and contract interactions in the focus targets."
    ),
    "test": (
        "You are a senior QA & automation engineer. Write a comprehensive pytest test suite "
        "for the focus targets. Cover edge cases, error scenarios, and mock dependency contracts."
    ),
}


def get_task_instruction(task_key_or_prompt: str | None) -> str | None:
    """Resolve a task name (e.g. 'bugfix') or return custom prompt string."""
    if not task_key_or_prompt:
        return None
    key = task_key_or_prompt.strip().lower()
    return TASK_TEMPLATES.get(key, task_key_or_prompt)
