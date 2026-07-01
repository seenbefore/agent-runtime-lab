import json
import urllib.request
from collections.abc import Callable, Mapping
from typing import Any


Transport = Callable[[dict[str, Any]], dict[str, Any]]


def _missing_transport(payload: dict[str, Any]) -> dict[str, Any]:
    raise RuntimeError("DeepSeek transport is not configured")


def create_deepseek_http_transport(
    api_key: str,
    base_url: str = "https://api.deepseek.com",
    timeout: int = 30,
) -> Transport:
    endpoint = f"{base_url.rstrip('/')}/chat/completions"

    def transport(payload: dict[str, Any]) -> dict[str, Any]:
        body = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            endpoint,
            data=body,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        with urllib.request.urlopen(request, timeout=timeout) as response:
            response_body = response.read().decode("utf-8")

        return json.loads(response_body)

    return transport


class DeepSeekClient:
    def __init__(
        self,
        api_key: str,
        model: str = "deepseek-chat",
        transport: Transport = _missing_transport,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.transport = transport

    def decide(
        self,
        task: str,
        steps: list[dict[str, Any]],
        allowed_tools: Mapping[str, Any],
    ) -> dict[str, Any]:
        messages = build_deepseek_messages(task, steps, allowed_tools)
        payload = {
            "model": self.model,
            "messages": messages,
        }
        response = self.transport(payload)
        return parse_deepseek_decision(response)


def build_deepseek_messages(
    task: str,
    steps: list[dict[str, Any]],
    allowed_tools: Mapping[str, Any],
) -> list[dict[str, str]]:
    tool_names = ", ".join(sorted(allowed_tools.keys()))
    system_prompt = (
        "You are an agent decision engine. "
        "Return only a valid JSON object. "
        'To call a tool, return {"action": "<tool_name>", "args": {...}}. '
        'To finish, return {"final": "<answer>"}. '
        f"Allowed tools: {tool_names}."
    )
    user_prompt = (
        f"Task:\n{task}\n\n"
        "Steps so far:\n"
        f"{json.dumps(steps, ensure_ascii=False, indent=2)}"
    )

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]


def parse_deepseek_decision(response: dict[str, Any]) -> dict[str, Any]:
    content = response["choices"][0]["message"]["content"]

    try:
        decision = json.loads(content)
    except json.JSONDecodeError as exc:
        raise ValueError("DeepSeek response content is not valid JSON") from exc

    if not isinstance(decision, dict):
        raise ValueError("DeepSeek response content must be a JSON object")

    return decision
