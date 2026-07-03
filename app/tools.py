"""
Agent Runtime 暴露给模型的本地工具集合。

本模块提供只读/验证类工具：读取文件、搜索代码、运行测试。
所有工具都返回统一的 ToolResult，方便 Agent Loop 记录 tool_result trace。

边界：第一版工具不写文件、不修改代码，也不执行任意 shell 命令。
"""

import subprocess
import sys
from pathlib import Path

from app.models import ToolResult


def read_file(path: str, workspace_dir: str = ".") -> ToolResult:
    workspace_path = Path(workspace_dir).resolve()
    target = (workspace_path / path).resolve()

    if target != workspace_path and workspace_path not in target.parents:
        return ToolResult(
            tool="read_file",
            status="failed",
            data=None,
            error="Path escapes workspace",
        )

    if not target.exists():
        return ToolResult(
            tool="read_file",
            status="success",
            data={
                "path": path,
                "exists": False,
                "content": None,
            },
            error=None,
        )

    content = target.read_text(encoding="utf-8")

    return ToolResult(
        tool="read_file",
        status="success",
        data={
            "path": path,
            "exists": True,
            "content": content,
        },
        error=None,
    )


def search_code(query: str, workspace_dir: str = ".") -> ToolResult:
    workspace_path = Path(workspace_dir).resolve()

    try:
        completed = subprocess.run(
            ["rg", "--line-number", "--no-heading", query, "."],
            cwd=workspace_path,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
    except FileNotFoundError:
        return ToolResult(
            tool="search_code",
            status="failed",
            data=None,
            error="rg not found",
        )

    if completed.returncode == 1:
        return ToolResult(
            tool="search_code",
            status="success",
            data={"matches": []},
            error=None,
        )

    if completed.returncode != 0:
        return ToolResult(
            tool="search_code",
            status="failed",
            data=None,
            error=completed.stderr.strip() or "rg failed",
        )

    matches = []
    for line in completed.stdout.splitlines():
        path, line_number, text = line.split(":", 2)
        normalized_path = path.removeprefix("./").removeprefix(".\\")
        matches.append(
            {
                "path": normalized_path,
                "line": int(line_number),
                "text": text,
            }
        )

    return ToolResult(
        tool="search_code",
        status="success",
        data={"matches": matches},
        error=None,
    )


def run_tests(target: str | None = None, workspace_dir: str = ".") -> ToolResult:
    workspace_path = Path(workspace_dir).resolve()
    command = [sys.executable, "-m", "pytest"]
    command_label = "python -m pytest"

    if target:
        command.append(target)
        command_label = f"{command_label} {target}"

    try:
        completed = subprocess.run(
            command,
            cwd=workspace_path,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
    except FileNotFoundError:
        return ToolResult(
            tool="run_tests",
            status="failed",
            data=None,
            error="pytest not found",
        )

    return ToolResult(
        tool="run_tests",
        status="success",
        data={
            "command": command_label,
            "exit_code": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
        },
        error=None,
    )
