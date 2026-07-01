import json

from app.models import Run
from app.storage import create_run


def test_create_run_creates_running_run_file(tmp_path):
    task = "hello"

    run = create_run(task, storage_dir=str(tmp_path))

    assert isinstance(run, Run)
    assert run.task == "hello"
    assert run.status == "running"
    assert run.steps == []
    assert run.result is None
    assert run.error is None

    run_file = tmp_path / f"{run.id}.json"
    assert run_file.exists()

    data = json.loads(run_file.read_text(encoding="utf-8"))
    assert data["id"] == run.id
    assert data["task"] == task