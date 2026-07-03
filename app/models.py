"""
Agent Runtime 的共享数据模型。

本模块定义 API、Storage、Agent Loop 和 Tools 之间共同使用的数据契约：
TaskRequest/TaskResponse 描述 HTTP 输入输出，Run/Step 描述一次可观察执行，
ToolResult 描述工具调用结果。

边界：本模块只定义结构和基础默认值，不负责存储、工具执行或模型调用。
"""

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
