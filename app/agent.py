from collections.abc import Callable
from typing import Any

from app.models import Run, ToolResult
from app.storage import append_step, fail_run, finish_run, get_run


ModelFn = Callable[[str, list[dict[str, Any]], dict[str, Callable[..., ToolResult]]], dict[str, Any]]


def _step_history(run_id: str, storage_dir: str) -> list[dict[str, Any]]:
    run = get_run(run_id, storage_dir=storage_dir)
    return [step.model_dump() for step in run.steps]


def run_agent(
    run_id: str,
    task: str,
    model: ModelFn,
    allowed_tools: dict[str, Callable[..., ToolResult]],
    storage_dir: str = "runs",
    workspace_dir: str = ".",
    max_steps: int = 8,
) -> Run:
    for _ in range(max_steps):
        decision = model(task, _step_history(run_id, storage_dir), allowed_tools)
        append_step(run_id, "model_decision", decision, storage_dir=storage_dir)

        if "final" in decision:
            final = decision["final"]
            append_step(run_id, "final", {"content": final}, storage_dir=storage_dir)
            return finish_run(run_id, final, storage_dir=storage_dir)

        if "action" not in decision:
            message = "Invalid decision: expected final or action"
            append_step(run_id, "error", {"message": message}, storage_dir=storage_dir)
            return fail_run(run_id, message, storage_dir=storage_dir)

        if "args" not in decision:
            message = "Invalid decision: action requires args"
            append_step(run_id, "error", {"message": message}, storage_dir=storage_dir)
            return fail_run(run_id, message, storage_dir=storage_dir)

        tool_name = decision.get("action")
        tool_args = decision.get("args")
        if tool_name not in allowed_tools:
            message = f"Tool not allowed: {tool_name}"
            append_step(run_id, "error", {"message": message}, storage_dir=storage_dir)
            return fail_run(run_id, message, storage_dir=storage_dir)

        append_step(
            run_id,
            "tool_call",
            {"tool": tool_name, "args": tool_args},
            storage_dir=storage_dir,
        )
        tool_result = allowed_tools[tool_name](**tool_args, workspace_dir=workspace_dir)
        append_step(
            run_id,
            "tool_result",
            tool_result.model_dump(),
            storage_dir=storage_dir,
        )

    message = "max steps exceeded"
    append_step(run_id, "error", {"message": message}, storage_dir=storage_dir)
    return fail_run(run_id, message, storage_dir=storage_dir)
