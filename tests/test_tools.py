from app.models import ToolResult
from app.tools import read_file, run_tests, search_code


def test_read_file_returns_content_for_existing_file(tmp_path):
    target = tmp_path / "README.md"
    target.write_text("hello runtime", encoding="utf-8")

    result = read_file("README.md", workspace_dir=str(tmp_path))

    assert isinstance(result, ToolResult)
    assert result.tool == "read_file"
    assert result.status == "success"
    assert result.data == {
        "path": "README.md",
        "exists": True,
        "content": "hello runtime",
    }
    assert result.error is None


def test_read_file_returns_missing_result_for_absent_file(tmp_path):
    result = read_file("missing.md", workspace_dir=str(tmp_path))

    assert result.tool == "read_file"
    assert result.status == "success"
    assert result.data == {
        "path": "missing.md",
        "exists": False,
        "content": None,
    }
    assert result.error is None


def test_read_file_rejects_path_outside_workspace(tmp_path):
    outside_file = tmp_path.parent / "outside.md"
    outside_file.write_text("secret", encoding="utf-8")

    result = read_file("../outside.md", workspace_dir=str(tmp_path))

    assert result.tool == "read_file"
    assert result.status == "failed"
    assert result.data is None
    assert result.error == "Path escapes workspace"


def test_search_code_returns_matches(tmp_path):
    source = tmp_path / "app.py"
    source.write_text("from fastapi import FastAPI\napp = FastAPI()\n", encoding="utf-8")

    result = search_code("FastAPI", workspace_dir=str(tmp_path))

    assert isinstance(result, ToolResult)
    assert result.tool == "search_code"
    assert result.status == "success"
    assert result.data == {
        "matches": [
            {
                "path": "app.py",
                "line": 1,
                "text": "from fastapi import FastAPI",
            },
            {
                "path": "app.py",
                "line": 2,
                "text": "app = FastAPI()",
            },
        ]
    }
    assert result.error is None


def test_search_code_returns_empty_matches_when_query_is_absent(tmp_path):
    source = tmp_path / "app.py"
    source.write_text("print('hello')\n", encoding="utf-8")

    result = search_code("FastAPI", workspace_dir=str(tmp_path))

    assert result.tool == "search_code"
    assert result.status == "success"
    assert result.data == {"matches": []}
    assert result.error is None


def test_run_tests_runs_all_tests_by_default(tmp_path):
    test_file = tmp_path / "test_sample.py"
    test_file.write_text(
        "def test_sample():\n"
        "    assert True\n",
        encoding="utf-8",
    )

    result = run_tests(workspace_dir=str(tmp_path))

    assert isinstance(result, ToolResult)
    assert result.tool == "run_tests"
    assert result.status == "success"
    assert result.data["command"] == "python -m pytest"
    assert result.data["exit_code"] == 0
    assert "test_sample.py" in result.data["stdout"]
    assert isinstance(result.data["stderr"], str)
    assert result.error is None


def test_run_tests_runs_specific_target(tmp_path):
    passing_test = tmp_path / "test_passing.py"
    passing_test.write_text(
        "def test_passing():\n"
        "    assert True\n",
        encoding="utf-8",
    )
    failing_test = tmp_path / "test_failing.py"
    failing_test.write_text(
        "def test_failing():\n"
        "    assert False\n",
        encoding="utf-8",
    )

    result = run_tests("test_passing.py", workspace_dir=str(tmp_path))

    assert result.tool == "run_tests"
    assert result.status == "success"
    assert result.data["command"] == "python -m pytest test_passing.py"
    assert result.data["exit_code"] == 0
    assert "test_passing.py" in result.data["stdout"]
    assert "test_failing.py" not in result.data["stdout"]
    assert result.error is None


def test_run_tests_returns_exit_code_for_failing_tests(tmp_path):
    test_file = tmp_path / "test_failing.py"
    test_file.write_text(
        "def test_failing():\n"
        "    assert False\n",
        encoding="utf-8",
    )

    result = run_tests(workspace_dir=str(tmp_path))

    assert result.tool == "run_tests"
    assert result.status == "success"
    assert result.data["command"] == "python -m pytest"
    assert result.data["exit_code"] != 0
    assert "test_failing.py" in result.data["stdout"]
    assert result.error is None
