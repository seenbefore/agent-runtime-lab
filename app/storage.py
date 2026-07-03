"""
Run/Step 的 JSON 文件存储层。

本模块负责创建、读取、更新 Run，并把每个 Run 持久化到
`runs/{run_id}.json` 这类 JSON 文件中。

边界：Agent Loop 只通过本模块访问 Run，不直接读写 JSON 文件；
本模块不决定 Agent 行为，也不执行工具。
"""

import json
from pathlib import Path
from typing import Any
from uuid import uuid4

from app.models import Run, Step, StepType, utc_now


def _write_run(run: Run, storage_dir: str = "runs") -> None:
    storage_path = Path(storage_dir)
    storage_path.mkdir(parents=True, exist_ok=True)

    run_file = storage_path / f"{run.id}.json"
    run_file.write_text(
        json.dumps(run.model_dump(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def create_run(task: str, storage_dir: str = "runs") -> Run:
    run = Run(id=f"run_{uuid4().hex}", task=task)
    _write_run(run, storage_dir)
    return run


def get_run(run_id: str, storage_dir: str = "runs") -> Run:
    storage_path = Path(storage_dir)
    run_file = storage_path / f"{run_id}.json"

    raw = run_file.read_text(encoding="utf-8")
    data = json.loads(raw)

    return Run(**data)


def append_step(
    run_id: str,
    step_type: StepType,
    data: dict[str, Any],
    storage_dir: str = "runs",
) -> Step:
    run = get_run(run_id, storage_dir=storage_dir)
    step = Step(index=len(run.steps) + 1, type=step_type, data=data)

    run.steps.append(step)
    run.updated_at = utc_now()
    _write_run(run, storage_dir)

    return step


def finish_run(
    run_id: str,
    result: str,
    storage_dir: str = "runs",
) -> Run:
    run = get_run(run_id, storage_dir=storage_dir)
    run.status = "completed"
    run.result = result
    run.error = None
    run.updated_at = utc_now()

    _write_run(run, storage_dir)
    return run


def fail_run(
    run_id: str,
    error: str,
    storage_dir: str = "runs",
) -> Run:
    run = get_run(run_id, storage_dir=storage_dir)
    run.status = "failed"
    run.result = None
    run.error = error
    run.updated_at = utc_now()

    _write_run(run, storage_dir)
    return run
