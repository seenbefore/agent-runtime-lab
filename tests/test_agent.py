from app.agent import run_agent
from app.models import ToolResult
from app.storage import create_run, get_run


def test_run_agent_executes_tool_and_finishes(tmp_path):
    run = create_run("read the file", storage_dir=str(tmp_path / "runs"))
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "README.md").write_text("hello agent", encoding="utf-8")
    decisions = [
        {"action": "read_file", "args": {"path": "README.md"}},
        {"final": "done"},
    ]

    def fake_model(task, steps, allowed_tools):
        return decisions.pop(0)

    def fake_read_file(path: str, workspace_dir: str = ".") -> ToolResult:
        return ToolResult(
            tool="read_file",
            status="success",
            data={"path": path, "exists": True, "content": "hello agent"},
            error=None,
        )

    result = run_agent(
        run.id,
        run.task,
        model=fake_model,
        allowed_tools={"read_file": fake_read_file},
        storage_dir=str(tmp_path / "runs"),
        workspace_dir=str(workspace),
    )

    assert result.status == "completed"
    assert result.result == "done"

    loaded_run = get_run(run.id, storage_dir=str(tmp_path / "runs"))
    assert loaded_run.status == "completed"
    assert loaded_run.result == "done"
    assert [step.type for step in loaded_run.steps] == [
        "model_decision",
        "tool_call",
        "tool_result",
        "model_decision",
        "final",
    ]
    assert loaded_run.steps[0].data == {
        "action": "read_file",
        "args": {"path": "README.md"},
    }
    assert loaded_run.steps[1].data == {
        "tool": "read_file",
        "args": {"path": "README.md"},
    }
    assert loaded_run.steps[2].data["tool"] == "read_file"
    assert loaded_run.steps[2].data["status"] == "success"


def test_run_agent_fails_when_tool_is_not_allowed(tmp_path):
    run = create_run("delete the file", storage_dir=str(tmp_path / "runs"))

    def fake_model(task, steps, allowed_tools):
        return {"action": "delete_file", "args": {"path": "README.md"}}

    result = run_agent(
        run.id,
        run.task,
        model=fake_model,
        allowed_tools={},
        storage_dir=str(tmp_path / "runs"),
        workspace_dir=str(tmp_path),
    )

    assert result.status == "failed"
    assert result.error == "Tool not allowed: delete_file"
    assert result.result is None

    loaded_run = get_run(run.id, storage_dir=str(tmp_path / "runs"))
    assert [step.type for step in loaded_run.steps] == [
        "model_decision",
        "error",
    ]
    assert loaded_run.steps[1].data == {
        "message": "Tool not allowed: delete_file"
    }


def test_run_agent_fails_when_max_steps_is_exceeded(tmp_path):
    run = create_run("keep reading", storage_dir=str(tmp_path / "runs"))

    def fake_model(task, steps, allowed_tools):
        return {"action": "read_file", "args": {"path": "README.md"}}

    def fake_read_file(path: str, workspace_dir: str = ".") -> ToolResult:
        return ToolResult(
            tool="read_file",
            status="success",
            data={"path": path, "exists": False, "content": None},
            error=None,
        )

    result = run_agent(
        run.id,
        run.task,
        model=fake_model,
        allowed_tools={"read_file": fake_read_file},
        storage_dir=str(tmp_path / "runs"),
        workspace_dir=str(tmp_path),
        max_steps=2,
    )

    assert result.status == "failed"
    assert result.error == "max steps exceeded"

    loaded_run = get_run(run.id, storage_dir=str(tmp_path / "runs"))
    assert [step.type for step in loaded_run.steps] == [
        "model_decision",
        "tool_call",
        "tool_result",
        "model_decision",
        "tool_call",
        "tool_result",
        "error",
    ]
    assert loaded_run.steps[-1].data == {"message": "max steps exceeded"}


def test_run_agent_fails_when_action_decision_missing_args(tmp_path):
    run = create_run("read the file", storage_dir=str(tmp_path / "runs"))

    def fake_model(task, steps, allowed_tools):
        return {"action": "read_file"}

    result = run_agent(
        run.id,
        run.task,
        model=fake_model,
        allowed_tools={"read_file": lambda **kwargs: None},
        storage_dir=str(tmp_path / "runs"),
        workspace_dir=str(tmp_path),
    )

    assert result.status == "failed"
    assert result.error == "Invalid decision: action requires args"

    loaded_run = get_run(run.id, storage_dir=str(tmp_path / "runs"))
    assert [step.type for step in loaded_run.steps] == [
        "model_decision",
        "error",
    ]
    assert loaded_run.steps[-1].data == {
        "message": "Invalid decision: action requires args"
    }


def test_run_agent_fails_when_decision_has_no_action_or_final(tmp_path):
    run = create_run("do something", storage_dir=str(tmp_path / "runs"))

    def fake_model(task, steps, allowed_tools):
        return {"thought": "I should do something"}

    result = run_agent(
        run.id,
        run.task,
        model=fake_model,
        allowed_tools={},
        storage_dir=str(tmp_path / "runs"),
        workspace_dir=str(tmp_path),
    )

    assert result.status == "failed"
    assert result.error == "Invalid decision: expected final or action"

    loaded_run = get_run(run.id, storage_dir=str(tmp_path / "runs"))
    assert [step.type for step in loaded_run.steps] == [
        "model_decision",
        "error",
    ]
    assert loaded_run.steps[-1].data == {
        "message": "Invalid decision: expected final or action"
    }
