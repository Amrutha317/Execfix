"""Pydantic schemas for backend API requests and responses."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class DebugRequest(BaseModel):
    code: str = Field(..., min_length=1, description="Buggy Python source code.")
    tests: str | None = Field(
        default=None,
        description="Optional test harness appended to code before each run.",
    )
    max_attempts: int = Field(default=3, ge=1, le=10)
    timeout: float = Field(default=10.0, gt=0, le=120)
    model: str | None = Field(default=None, description="OpenAI model override.")


class HistoryEntryOut(BaseModel):
    attempt: int | None = None
    code: str | None = None
    success: bool | None = None
    error: str | None = None
    exception_type: str | None = None
    duration_ms: int | None = None
    rejected: bool | None = None
    llm_output: str | None = None


class DebugResponse(BaseModel):
    success: bool
    attempts_used: int
    final_code: str
    original_code: str
    final_error: str
    final_exception_type: str | None = None
    history: list[HistoryEntryOut]


class EvalRunRequest(BaseModel):
    model: str | None = Field(default=None)
    max_attempts: int = Field(default=3, ge=1, le=10)
    timeout: float = Field(default=30.0, gt=0, le=180)
    limit: int | None = Field(default=None, ge=1, le=100)
    only: list[str] | None = Field(default=None)


class EvalProblemResult(BaseModel):
    name: str
    passed: bool
    attempts_used: int
    fixed_on_first_run: bool
    final_exception_type: str | None = None
    duration_ms: int
    final_code: str
    error_excerpt: str
    skipped_reason: str | None = None


class EvalRunResponse(BaseModel):
    model: str
    max_attempts: int
    summary: dict[str, Any]
    results: list[EvalProblemResult]

