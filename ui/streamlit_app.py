"""Streamlit demo UI for the autonomous debugging agent.

Run with:
    streamlit run ui/streamlit_app.py

Layout:
- Left: code editor + controls (max attempts, model, optional test harness).
- Right: per-attempt timeline showing run status, captured stderr, and a diff
  of the LLM's proposed fix vs the previous attempt.
- Bottom: final status banner + final source code.
"""

from __future__ import annotations

import difflib
import os
import sys
from pathlib import Path

# Allow running ``streamlit run ui/streamlit_app.py`` from the project root by
# prepending the parent dir to ``sys.path``.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import streamlit as st  # noqa: E402

from agent.debugger import run_debug_session  # noqa: E402

# --------------------------------------------------------------------------- #
# Page setup                                                                  #
# --------------------------------------------------------------------------- #

st.set_page_config(
    page_title="Autonomous Code Debugging Agent",
    page_icon=":wrench:",
    layout="wide",
)

st.title("Autonomous Code Debugging Agent")
st.caption(
    "LangGraph + OpenAI agent that runs Python in a sandboxed subprocess, "
    "captures real errors, and iteratively repairs the code."
)


# --------------------------------------------------------------------------- #
# Sidebar controls                                                            #
# --------------------------------------------------------------------------- #


SAMPLE_BUGS = {
    "ZeroDivisionError": "x = 10\ny = 0\nprint(x / y)\n",
    "IndexError": "items = [1, 2, 3]\nprint(items[5])\n",
    "NameError": "print(undeclared_variable)\n",
    "SyntaxError (missing colon)": "def add(a, b)\n    return a + b\n\nprint(add(2, 3))\n",
    "Off-by-one": (
        "def sum_to(n):\n"
        "    total = 0\n"
        "    for i in range(1, n):  # bug: should be n+1\n"
        "        total += i\n"
        "    return total\n\n"
        "assert sum_to(5) == 15, f'got {sum_to(5)}'\n"
        "print('ok')\n"
    ),
    "Custom (paste your own)": "",
}


with st.sidebar:
    st.header("Settings")

    api_key_present = bool(os.environ.get("OPENAI_API_KEY"))
    if api_key_present:
        st.success("OPENAI_API_KEY detected")
    else:
        st.error("OPENAI_API_KEY not set. Add it to .env before running.")

    model = st.text_input(
        "Model",
        value=os.environ.get("DEBUGGER_MODEL", "gpt-5-mini"),
        help="Any OpenAI chat model (e.g. gpt-5-mini).",
    )
    max_attempts = st.slider("Max attempts", min_value=1, max_value=8, value=3)
    timeout = st.slider(
        "Per-execution timeout (s)", min_value=2, max_value=60, value=10
    )

    st.markdown("---")
    st.markdown("**Quick-load a sample bug:**")
    sample_choice = st.selectbox(
        "Sample", list(SAMPLE_BUGS.keys()), index=0, label_visibility="collapsed"
    )
    if st.button("Load sample"):
        st.session_state["editor_code"] = SAMPLE_BUGS[sample_choice]


# --------------------------------------------------------------------------- #
# Editor + run trigger                                                        #
# --------------------------------------------------------------------------- #


col_left, col_right = st.columns([1, 1])

with col_left:
    st.subheader("Buggy code")
    code = st.text_area(
        "Source",
        value=st.session_state.get("editor_code", SAMPLE_BUGS["ZeroDivisionError"]),
        key="editor_code",
        height=320,
        label_visibility="collapsed",
    )
    with st.expander("Optional test harness (appended to your code)"):
        tests = st.text_area(
            "Harness",
            value="",
            height=120,
            placeholder="e.g. assert add(2, 3) == 5\nprint('OK')",
            label_visibility="collapsed",
        )

    run_clicked = st.button(
        "Debug it",
        type="primary",
        disabled=not api_key_present,
        use_container_width=True,
    )


# --------------------------------------------------------------------------- #
# Run + timeline                                                              #
# --------------------------------------------------------------------------- #


def _diff(prev: str, curr: str) -> str:
    if not prev:
        return curr
    diff_lines = difflib.unified_diff(
        prev.splitlines(keepends=True),
        curr.splitlines(keepends=True),
        fromfile="previous",
        tofile="proposed",
        lineterm="",
    )
    return "".join(diff_lines) or "(no textual change)"


with col_right:
    st.subheader("Attempt timeline")
    timeline_slot = st.container()
    summary_slot = st.empty()

if run_clicked:
    with st.spinner("Running the agent..."):
        try:
            session = run_debug_session(
                code,
                tests=tests.strip() or None,
                max_attempts=max_attempts,
                timeout=float(timeout),
                model=model.strip() or None,
            )
        except Exception as exc:  # noqa: BLE001
            st.error(f"Agent crashed: {type(exc).__name__}: {exc}")
            st.stop()

    with timeline_slot:
        prev_code: str = ""
        for entry in session.history:
            attempt_idx = entry.get("attempt", 0)
            success = entry.get("success", False)
            duration_ms = entry.get("duration_ms", 0)
            exc_type = entry.get("exception_type") or "OK"
            badge = ":white_check_mark: PASS" if success else f":x: {exc_type}"
            with st.expander(
                f"Attempt {attempt_idx}: {badge} ({duration_ms} ms)",
                expanded=not success and attempt_idx == len(session.history) - 1,
            ):
                st.markdown("**Code under test**")
                st.code(entry.get("code", ""), language="python")
                stderr = entry.get("error", "") or ""
                if stderr.strip():
                    st.markdown("**Captured stderr**")
                    st.code(stderr, language="text")
                llm_out = entry.get("llm_output")
                if llm_out:
                    st.markdown("**LLM proposed fix (diff vs previous)**")
                    st.code(_diff(entry.get("code", ""), llm_out), language="diff")
            prev_code = entry.get("code", "") or prev_code

    with summary_slot.container():
        st.markdown("---")
        repairs_used = max(0, session.attempts_used - 1)
        if session.success:
            st.success(
                f"Fixed in {repairs_used} repair(s) "
                f"({len(session.history)} total runs)."
            )
        else:
            st.error(
                f"Gave up after {repairs_used} repair(s). "
                f"Final exception: {session.final_exception_type or 'unknown'}."
            )
        st.markdown("**Final source code**")
        st.code(session.final_code, language="python")
else:
    with timeline_slot:
        st.info("Click **Debug it** to run the agent.")
