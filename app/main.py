from collections.abc import Callable

from fastapi import FastAPI

from app.agent import ModelFn, run_agent
from app.models import TaskRequest, TaskResponse, ToolResult
from app.storage import create_run, get_run
from app.tools import read_file, run_tests, search_code


def default_model(task, steps, allowed_tools):
    return {"final": "No model configured"}


DEFAULT_ALLOWED_TOOLS: dict[str, Callable[..., ToolResult]] = {
    "read_file": read_file,
    "search_code": search_code,
    "run_tests": run_tests,
}


def create_app(
    model: ModelFn = default_model,
    allowed_tools: dict[str, Callable[..., ToolResult]] | None = None,
    storage_dir: str = "runs",
    workspace_dir: str = ".",
) -> FastAPI:
    app = FastAPI()
    tools = allowed_tools or DEFAULT_ALLOWED_TOOLS

    @app.post("/tasks", response_model=TaskResponse)
    def create_task(request: TaskRequest) -> TaskResponse:
        run = create_run(request.task, storage_dir=storage_dir)
        finished_run = run_agent(
            run.id,
            run.task,
            model=model,
            allowed_tools=tools,
            storage_dir=storage_dir,
            workspace_dir=workspace_dir,
        )

        return TaskResponse(
            run_id=finished_run.id,
            status=finished_run.status,
            result=finished_run.result,
            trace_url=f"/runs/{finished_run.id}",
        )

    @app.get("/runs/{run_id}")
    def read_run(run_id: str):
        return get_run(run_id, storage_dir=storage_dir)

    return app


app = create_app()
