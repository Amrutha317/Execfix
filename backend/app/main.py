"""FastAPI entrypoint for the debugger backend."""

from __future__ import annotations

import sys
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

# Ensure project root imports work when running uvicorn from backend/.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.schemas import DebugRequest, DebugResponse, EvalRunRequest, EvalRunResponse
from app.service import run_debug, run_eval


app = FastAPI(
    title="Autonomous Code Debugger Backend",
    version="0.1.0",
    description="API wrapper around the LangGraph Python debugging agent.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/debug", response_model=DebugResponse)
def debug_code(payload: DebugRequest) -> DebugResponse:
    try:
        result = run_debug(
            code=payload.code,
            tests=payload.tests,
            max_attempts=payload.max_attempts,
            timeout=payload.timeout,
            model=payload.model,
        )
        return DebugResponse(**result)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=500, detail=f"{type(exc).__name__}: {exc}"
        ) from exc


@app.post("/eval/run", response_model=EvalRunResponse)
def eval_run(payload: EvalRunRequest) -> EvalRunResponse:
    try:
        result = run_eval(
            model=payload.model,
            max_attempts=payload.max_attempts,
            timeout=payload.timeout,
            limit=payload.limit,
            only=payload.only,
        )
        return EvalRunResponse(**result)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=500, detail=f"{type(exc).__name__}: {exc}"
        ) from exc

