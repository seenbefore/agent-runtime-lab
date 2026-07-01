import pytest

from app.deepseek_client import (
    DeepSeekClient,
    build_deepseek_messages,
    create_deepseek_http_transport,
    parse_deepseek_decision,
)


def test_build_deepseek_messages_includes_task_steps_and_tools():
    steps = [
        {"type": "tool_result", "data": {"tool": "read_file", "status": "success"}}
    ]
    allowed_tools = {"read_file": object(), "run_tests": object()}

    messages = build_deepseek_messages("read README", steps, allowed_tools)

    assert messages[0]["role"] == "system"
    assert "valid JSON object" in messages[0]["content"]
    assert "read_file" in messages[0]["content"]
    assert "run_tests" in messages[0]["content"]
    assert messages[1]["role"] == "user"
    assert "read README" in messages[1]["content"]
    assert "tool_result" in messages[1]["content"]


def test_deepseek_client_uses_transport_and_returns_parsed_decision():
    calls = []

    def fake_transport(payload):
        calls.append(payload)
        return {
            "choices": [
                {
                    "message": {
                        "content": '{"final": "done"}'
                    }
                }
            ]
        }

    client = DeepSeekClient(
        api_key="test-key",
        model="deepseek-chat",
        transport=fake_transport,
    )

    decision = client.decide("read README", [], {"read_file": object()})

    assert decision == {"final": "done"}
    assert calls[0]["model"] == "deepseek-chat"
    assert calls[0]["messages"][0]["role"] == "system"


def test_deepseek_http_transport_posts_payload(monkeypatch):
    captured = {}

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):
            return None

        def read(self):
            return b'{"choices":[{"message":{"content":"{\\"final\\": \\"done\\"}"}}]}'

    def fake_urlopen(request, timeout):
        captured["url"] = request.full_url
        captured["headers"] = dict(request.header_items())
        captured["body"] = request.data
        captured["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    transport = create_deepseek_http_transport(
        api_key="test-key",
        base_url="https://api.deepseek.com",
        timeout=12,
    )

    response = transport({"model": "deepseek-chat", "messages": []})

    assert captured["url"] == "https://api.deepseek.com/chat/completions"
    assert captured["headers"]["Authorization"] == "Bearer test-key"
    assert captured["headers"]["Content-type"] == "application/json"
    assert captured["timeout"] == 12
    assert b'"model": "deepseek-chat"' in captured["body"]
    assert response["choices"][0]["message"]["content"] == '{"final": "done"}'


def test_parse_deepseek_decision_reads_action_from_response():
    response = {
        "choices": [
            {
                "message": {
                    "content": '{"action": "read_file", "args": {"path": "README.md"}}'
                }
            }
        ]
    }

    decision = parse_deepseek_decision(response)

    assert decision == {
        "action": "read_file",
        "args": {"path": "README.md"},
    }


def test_parse_deepseek_decision_reads_final_from_response():
    response = {
        "choices": [
            {
                "message": {
                    "content": '{"final": "done"}'
                }
            }
        ]
    }

    decision = parse_deepseek_decision(response)

    assert decision == {"final": "done"}


def test_parse_deepseek_decision_rejects_non_json_content():
    response = {
        "choices": [
            {
                "message": {
                    "content": "I should read README.md"
                }
            }
        ]
    }

    with pytest.raises(ValueError, match="DeepSeek response content is not valid JSON"):
        parse_deepseek_decision(response)
