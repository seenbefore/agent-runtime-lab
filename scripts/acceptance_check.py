import argparse
import json
import urllib.request


def request_json(method: str, url: str, payload: dict | None = None) -> dict:
    data = None
    headers = {}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    request = urllib.request.Request(
        url,
        data=data,
        headers=headers,
        method=method,
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser(description="Run local API acceptance check.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument(
        "--task",
        default="请查看 README.md，并告诉我这个项目怎么运行。",
    )
    args = parser.parse_args()

    task_response = request_json(
        "POST",
        f"{args.base_url}/tasks",
        {"task": args.task},
    )
    run = request_json("GET", f"{args.base_url}{task_response['trace_url']}")

    print("POST /tasks")
    print(json.dumps(task_response, ensure_ascii=False, indent=2))
    print()
    print(f"GET {task_response['trace_url']}")
    print(json.dumps(run, ensure_ascii=False, indent=2))
    print()
    print("Trace types:")
    print(" -> ".join(step["type"] for step in run["steps"]))


if __name__ == "__main__":
    main()
