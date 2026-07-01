from fastapi.testclient import TestClient

from app.main import build_default_model, create_app
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


def test_build_default_model_returns_fallback_without_api_key(monkeypatch):
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)

    model = build_default_model()

    assert model("task", [], {}) == {"final": "No model configured"}


def test_build_default_model_uses_deepseek_when_api_key_exists(monkeypatch):
    calls = []

    def fake_transport_factory(api_key):
        calls.append(api_key)

        def fake_transport(payload):
            return {
                "choices": [
                    {
                        "message": {
                            "content": '{"final": "from deepseek"}'
                        }
                    }
                ]
            }

        return fake_transport

    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")

    model = build_default_model(transport_factory=fake_transport_factory)
    decision = model("task", [], {})

    assert calls == ["test-key"]
    assert decision == {"final": "from deepseek"}
