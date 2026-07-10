"""Prompt templates for the debugging agent."""

from __future__ import annotations

SYSTEM_PROMPT = """\
You are a senior Python debugging engineer. You are given a snippet of Python \
source code and the captured stderr from running it. Your job is to return the \
SMALLEST possible corrected version of the source that will run without raising \
an unhandled exception and that satisfies any test harness appended to it.

Strict output rules:
- Return ONLY the corrected source code.
- Do NOT wrap the output in markdown code fences (no ``` ```).
- Do NOT include any commentary, prefixes, or trailing prose.
- Preserve the original function signatures and overall structure where possible.
- Keep variable and function names identical to the original unless the bug \
  requires renaming. Tests may import by name.
- If the original program reads from stdin, keep it reading from stdin.
- Do not introduce imports of network, subprocess, ctypes, or filesystem-mutating \
  modules; those are blocked by the sandbox and will cause the run to be rejected.
"""


USER_PROMPT_TEMPLATE = """\
The following Python program failed.

--- Source ---
{code}

--- Captured stderr ---
{error}

--- Detected exception type ---
{exception_type}

--- Previous fix attempts ({attempts}) ---
{history}

Return the full corrected source for the program. Output code only.
"""


def render_user_prompt(
    *,
    code: str,
    error: str,
    exception_type: str | None,
    attempts: int,
    history: list[dict] | None = None,
) -> str:
    """Render the user-side prompt for ``llm.fix_code``."""
    if not history:
        history_blob = "(none)"
    else:
        lines: list[str] = []
        for i, entry in enumerate(history, start=1):
            lines.append(
                f"Attempt {i}: exception={entry.get('exception_type') or 'OK'} "
                f"success={entry.get('success', False)}"
            )
        history_blob = "\n".join(lines)

    return USER_PROMPT_TEMPLATE.format(
        code=code,
        error=error or "(no stderr captured)",
        exception_type=exception_type or "(unknown)",
        attempts=attempts,
        history=history_blob,
    )
