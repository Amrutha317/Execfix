"""The debugging agent.

Provides three call sites:

1. :func:`debug_loop` -- a plain Python while-loop. Useful for unit-testing the
   prompt + executor wiring without LangGraph in the path.
2. :func:`build_graph` / :data:`DebuggerAgent` -- the LangGraph
   :class:`StateGraph` that the rest of the project (CLI, Streamlit, evaluator)
   actually invokes.
3. :func:`run_debug_session` -- thin convenience wrapper around the compiled
   graph that returns a :class:`DebugSession` dataclass.

The two implementations are functionally identical; LangGraph just makes the
control flow explicit and gives us per-node observability for the demo UI.
"""

from __future__ import annotations

import dataclasses
from typing import Any, Iterator

from langgraph.graph import END, StateGraph

from agent.executor import run_sandboxed
from agent.llm import fix_code
from agent.state import DebugState, HistoryEntry, initial_state


# --------------------------------------------------------------------------- #
# Plain while-loop prototype (Phase 2)                                        #
# --------------------------------------------------------------------------- #


def debug_loop(
    code: str,
    *,
    tests: str | None = None,
    max_attempts: int = 3,
    timeout: float = 10.0,
    model: str | None = None,
    verbose: bool = False,
) -> DebugState:
    """Run the debug loop without LangGraph. Returns the final state."""
    state = initial_state(
        code=code,
        tests=tests,
        max_attempts=max_attempts,
        timeout=timeout,
        model=model,
    )

    while True:
        result = run_sandboxed(state["code"], tests=state["tests"], timeout=state["timeout"])
        history_entry: HistoryEntry = {
            "attempt": state["attempts"] + 1,
            "code": state["code"],
            "success": result.success,
            "error": result.stderr,
            "exception_type": result.exception_type,
            "duration_ms": result.duration_ms,
            "rejected": result.was_rejected,
            "llm_output": None,
        }
        state["history"].append(history_entry)
        state["error"] = result.stderr
        state["exception_type"] = result.exception_type
        state["success"] = result.success

        if verbose:
            tag = "PASS" if result.success else (result.exception_type or "FAIL")
            print(f"[attempt {state['attempts']}] {tag} ({result.duration_ms} ms)")

        if result.success:
            return state
        if state["attempts"] + 1 >= state["max_attempts"]:
            return state

        fixed = fix_code(
            state["code"],
            state["error"],
            exception_type=state["exception_type"],
            attempts=state["attempts"],
            history=list(state["history"]),
            model=state.get("model"),
        )
        history_entry["llm_output"] = fixed
        state["code"] = fixed
        state["attempts"] += 1


# --------------------------------------------------------------------------- #
# LangGraph version (Phase 3)                                                 #
# --------------------------------------------------------------------------- #


def _run_code_node(state: DebugState) -> dict[str, Any]:
    result = run_sandboxed(
        state["code"],
        tests=state.get("tests"),
        timeout=state.get("timeout", 10.0),
    )
    history: list[HistoryEntry] = list(state.get("history", []))
    history.append(
        {
            "attempt": state.get("attempts", 0) + 1,
            "code": state["code"],
            "success": result.success,
            "error": result.stderr,
            "exception_type": result.exception_type,
            "duration_ms": result.duration_ms,
            "rejected": result.was_rejected,
            "llm_output": None,
        }
    )
    return {
        "error": result.stderr,
        "exception_type": result.exception_type,
        "success": result.success,
        "history": history,
    }


def _fix_code_node(state: DebugState) -> dict[str, Any]:
    fixed = fix_code(
        state["code"],
        state.get("error", ""),
        exception_type=state.get("exception_type"),
        attempts=state.get("attempts", 0),
        history=list(state.get("history", [])),
        model=state.get("model"),
    )
    history = list(state.get("history", []))
    if history:
        # Attach the LLM output to the most recent run entry for traceability.
        last = dict(history[-1])
        last["llm_output"] = fixed
        history[-1] = last  # type: ignore[assignment]
    return {
        "code": fixed,
        "attempts": state.get("attempts", 0) + 1,
        "history": history,
    }


def _router(state: DebugState) -> str:
    if state.get("success"):
        return "done"
    if state.get("attempts", 0) + 1 >= state.get("max_attempts", 3):
        return "give_up"
    return "fix"


def build_graph() -> Any:
    """Build and compile the debugger StateGraph. Cached at module level."""
    graph = StateGraph(DebugState)
    graph.add_node("run", _run_code_node)
    graph.add_node("fix", _fix_code_node)
    graph.set_entry_point("run")
    graph.add_conditional_edges(
        "run",
        _router,
        {"done": END, "give_up": END, "fix": "fix"},
    )
    graph.add_edge("fix", "run")
    return graph.compile()


# Compile once at import; importers reuse the same instance.
DebuggerAgent = build_graph()


# --------------------------------------------------------------------------- #
# Convenience wrapper                                                         #
# --------------------------------------------------------------------------- #


@dataclasses.dataclass
class DebugSession:
    success: bool
    attempts_used: int
    final_code: str
    original_code: str
    final_error: str
    final_exception_type: str | None
    history: list[HistoryEntry]
    state: DebugState


def run_debug_session(
    code: str,
    *,
    tests: str | None = None,
    max_attempts: int = 3,
    timeout: float = 10.0,
    model: str | None = None,
) -> DebugSession:
    """Invoke the compiled LangGraph agent and return a typed summary."""
    seed = initial_state(
        code=code,
        tests=tests,
        max_attempts=max_attempts,
        timeout=timeout,
        model=model,
    )
    final: DebugState = DebuggerAgent.invoke(seed)
    history = list(final.get("history", []))
    return DebugSession(
        success=bool(final.get("success", False)),
        attempts_used=len(history),
        final_code=str(final.get("code", "")),
        original_code=str(final.get("original_code", code)),
        final_error=str(final.get("error", "")),
        final_exception_type=final.get("exception_type"),
        history=history,
        state=final,
    )


def stream_debug_session(
    code: str,
    *,
    tests: str | None = None,
    max_attempts: int = 3,
    timeout: float = 10.0,
    model: str | None = None,
) -> Iterator[dict[str, Any]]:
    """Invoke the compiled LangGraph agent, yielding progress as it happens.

    Yields ``{"type": "attempt", "entry": HistoryEntry}`` each time the most
    recent history entry changes (a run just finished, or an LLM patch was
    just attached to it), then a final ``{"type": "done", ...}`` matching
    :class:`DebugSession`'s fields once the graph terminates.
    """
    seed = initial_state(
        code=code,
        tests=tests,
        max_attempts=max_attempts,
        timeout=timeout,
        model=model,
    )
    final: DebugState = seed
    last_sent: HistoryEntry | None = None
    for step in DebuggerAgent.stream(seed, stream_mode="values"):
        final = step
        history = step.get("history", [])
        if not history:
            continue
        latest = history[-1]
        if latest != last_sent:
            yield {"type": "attempt", "entry": latest}
            last_sent = latest

    history = list(final.get("history", []))
    yield {
        "type": "done",
        "success": bool(final.get("success", False)),
        "attempts_used": len(history),
        "final_code": str(final.get("code", "")),
        "original_code": str(final.get("original_code", code)),
        "final_error": str(final.get("error", "")),
        "final_exception_type": final.get("exception_type"),
        "history": history,
    }
