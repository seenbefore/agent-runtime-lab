from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field


RunStatus = Literal["running", "completed", "failed"]
StepType = Literal["model_decision", "tool_call", "tool_result", "final", "error"]
ToolStatus = Literal["success", "failed"]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class TaskRequest(BaseModel):
    task: str


class TaskResponse(BaseModel):
    run_id: str
    status: RunStatus
    result: str | None = None
    trace_url: str


class Step(BaseModel):
    index: int
    type: StepType
    data: dict[str, Any]
    created_at: str = Field(default_factory=utc_now)


class Run(BaseModel):
    id: str
    task: str
    status: RunStatus = "running"
    steps: list[Step] = Field(default_factory=list)
    result: str | None = None
    error: str | None = None
    created_at: str = Field(default_factory=utc_now)
    updated_at: str = Field(default_factory=utc_now)


class ToolResult(BaseModel):
    tool: str
    status: ToolStatus
    data: dict[str, Any] | None = None
    error: str | None = None