import json

from app.models import Run
from app.storage import append_step, create_run, fail_run, finish_run, get_run


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


def test_finish_run_marks_run_completed_and_saves_result(tmp_path):
    run = create_run("hello", storage_dir=str(tmp_path))

    finished_run = finish_run(
        run.id,
        "done",
        storage_dir=str(tmp_path),
    )

    assert finished_run.id == run.id
    assert finished_run.status == "completed"
    assert finished_run.result == "done"
    assert finished_run.error is None
    assert finished_run.updated_at != run.updated_at

    loaded_run = get_run(run.id, storage_dir=str(tmp_path))
    assert loaded_run.status == "completed"
    assert loaded_run.result == "done"
    assert loaded_run.error is None


def test_fail_run_marks_run_failed_and_saves_error(tmp_path):
    run = create_run("hello", storage_dir=str(tmp_path))

    failed_run = fail_run(
        run.id,
        "boom",
        storage_dir=str(tmp_path),
    )

    assert failed_run.id == run.id
    assert failed_run.status == "failed"
    assert failed_run.result is None
    assert failed_run.error == "boom"
    assert failed_run.updated_at != run.updated_at

    loaded_run = get_run(run.id, storage_dir=str(tmp_path))
    assert loaded_run.status == "failed"
    assert loaded_run.result is None
    assert loaded_run.error == "boom"
