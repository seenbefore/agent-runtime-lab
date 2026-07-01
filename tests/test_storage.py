import json

from app.models import Run
from app.storage import create_run, get_run, append_step


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

def test_get_run_reads_existing_run_file(tmp_path):
    run = create_run("hello", storage_dir=str(tmp_path))

    loaded_run = get_run(run.id, storage_dir=str(tmp_path))

    assert isinstance(loaded_run, Run)
    assert loaded_run.id == run.id
    assert loaded_run.task == run.task
    assert loaded_run.status == run.status
    assert loaded_run.steps == run.steps
    assert loaded_run.result == run.result
    assert loaded_run.error == run.error

def test_append_step_adds_step_to_run_file(tmp_path):
    run = create_run("hello", storage_dir=str(tmp_path))
    data = {"action": "read_file", "args": {"path": "README.md"}}

    step = append_step(
        run.id,
        "model_decision",
        data,
        storage_dir=str(tmp_path),
    )

    assert step.index == 1
    assert step.type == "model_decision"
    assert step.data == data

    loaded_run = get_run(run.id, storage_dir=str(tmp_path))
    assert len(loaded_run.steps) == 1
    assert loaded_run.steps[0].index == 1
    assert loaded_run.steps[0].type == "model_decision"
    assert loaded_run.steps[0].data == data