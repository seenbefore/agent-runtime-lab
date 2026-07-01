from fastapi.testclient import TestClient

from app.main import create_app
from app.models import ToolResult


def test_post_tasks_runs_agent_and_returns_result(tmp_path):
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
            data={"path": path, "exists": True, "content": "hello"},
            error=None,
        )

    app = create_app(
        model=fake_model,
        allowed_tools={"read_file": fake_read_file},
        storage_dir=str(tmp_path / "runs"),
        workspace_dir=str(tmp_path),
    )
    client = TestClient(app)

    response = client.post("/tasks", json={"task": "read README"})

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "completed"
    assert body["result"] == "done"
    assert body["trace_url"] == f"/runs/{body['run_id']}"


def test_get_run_returns_full_trace(tmp_path):
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
            data={"path": path, "exists": True, "content": "hello"},
            error=None,
        )

    app = create_app(
        model=fake_model,
        allowed_tools={"read_file": fake_read_file},
        storage_dir=str(tmp_path / "runs"),
        workspace_dir=str(tmp_path),
    )
    client = TestClient(app)
    task_response = client.post("/tasks", json={"task": "read README"}).json()

    response = client.get(task_response["trace_url"])

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == task_response["run_id"]
    assert body["task"] == "read README"
    assert body["status"] == "completed"
    assert body["result"] == "done"
    assert [step["type"] for step in body["steps"]] == [
        "model_decision",
        "tool_call",
        "tool_result",
        "model_decision",
        "final",
    ]
