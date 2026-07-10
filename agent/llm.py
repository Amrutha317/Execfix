"""OpenAI client wrapper for the debugging agent.

Lazy-instantiates a single ``OpenAI()`` client (so importing the module does
not require an API key) and exposes ``fix_code`` which the LangGraph
``fix_code_node`` ultimately calls.
"""

from __future__ import annotations

import os
import re
from functools import lru_cache
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI

from agent.prompts import SYSTEM_PROMPT, render_user_prompt

# Load environment at import time so any caller (CLI, Streamlit, evaluator)
# picks up ``OPENAI_API_KEY`` from a local ``.env`` automatically.
load_dotenv()

DEFAULT_MODEL = os.environ.get("DEBUGGER_MODEL", "gpt-5-mini")
DEFAULT_TEMPERATURE = 0.0


@lru_cache(maxsize=1)
def _client() -> OpenAI:
    return OpenAI()


_FENCE_RE = re.compile(r"^\s*```(?:python|py)?\s*\n?(.*?)\n?```\s*$", re.DOTALL)


def _strip_code_fences(text: str) -> str:
    """LLMs sometimes wrap output in ```python ... ``` despite instructions."""
    if not text:
        return text
    match = _FENCE_RE.match(text.strip())
    if match:
        return match.group(1).strip("\n")
    return text.strip()


def _supports_explicit_temperature(model_name: str) -> bool:
    """Return True if this model family typically accepts explicit temperature."""
    lowered = model_name.lower()
    # GPT-5 family on this endpoint may reject explicit temperature values and
    # require default sampling behavior.
    return not lowered.startswith("gpt-5")


def fix_code(
    code: str,
    error: str,
    *,
    exception_type: str | None = None,
    attempts: int = 0,
    history: list[dict] | None = None,
    model: str | None = None,
    temperature: float = DEFAULT_TEMPERATURE,
    extra_args: dict[str, Any] | None = None,
) -> str:
    """Ask the LLM to repair ``code`` given the captured ``error``.

    Returns the corrected source string (markdown fences stripped).
    """
    user_prompt = render_user_prompt(
        code=code,
        error=error,
        exception_type=exception_type,
        attempts=attempts,
        history=history,
    )

    selected_model = model or DEFAULT_MODEL
    request: dict[str, Any] = {
        "model": selected_model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
    }
    # Some models (notably GPT-5 variants via this endpoint) reject explicit
    # temperature values. Omit temperature there and use provider defaults.
    if _supports_explicit_temperature(selected_model):
        request["temperature"] = temperature
    if extra_args:
        request.update(extra_args)

    response = _client().chat.completions.create(**request)
    raw = response.choices[0].message.content or ""
    return _strip_code_fences(raw)
