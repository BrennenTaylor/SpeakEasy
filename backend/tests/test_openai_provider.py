import json

import httpx
import pytest

from app.ai.openai_provider import OpenAIInterpreter
from app.ai.provider import AIServiceError

CANDIDATE = {
    "name": "Chick-fil-A chicken sandwich",
    "brand": "Chick-fil-A",
    "serving_label": "1 sandwich",
    "serving_grams": "187",
    "quantity": "1",
    "calories": "249",
    "protein_g": "16.28",
    "carbs_g": "20.89",
    "fat_g": "11.19",
    "fiber_g": "1.4",
    "sugar_g": "0",
    "sodium_mg": "753",
    "source_url": "https://example.com/menu",
}


def response_with(candidates: list[dict[str, object]]) -> httpx.Response:
    return httpx.Response(
        200,
        json={
            "output": [
                {
                    "type": "message",
                    "content": [
                        {"type": "output_text", "text": json.dumps({"candidates": candidates})}
                    ],
                }
            ]
        },
    )


def test_interpreter_parses_candidates_and_uses_server_key() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return response_with([CANDIDATE])

    client = httpx.Client(transport=httpx.MockTransport(handler))
    interpreter = OpenAIInterpreter("server-only-key", client=client)

    result = interpreter.interpret("chick fil a sandwich")
    assert len(result) == 1
    assert result[0].name == "Chick-fil-A chicken sandwich"
    assert "server-only-key" in seen[0].headers["Authorization"]

    body = json.loads(seen[0].content)
    assert body["model"] == "gpt-6-luna"
    assert body["tools"] == [{"type": "web_search"}]
    assert body["text"]["format"]["type"] == "json_schema"
    assert "source URL" in json.dumps(body["input"])


def test_interpreter_retries_transport_errors_once() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise httpx.ConnectError("temporary failure", request=request)
        return response_with([CANDIDATE])

    client = httpx.Client(transport=httpx.MockTransport(handler))
    interpreter = OpenAIInterpreter("server-only-key", client=client)

    assert len(interpreter.interpret("sandwich")) == 1
    assert calls == 2


def test_interpreter_does_not_retry_http_errors() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(500, json={"error": "boom"})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    interpreter = OpenAIInterpreter("server-only-key", client=client)

    with pytest.raises(AIServiceError):
        interpreter.interpret("sandwich")
    assert calls == 1


def test_interpreter_caps_candidates() -> None:
    candidates = [{**CANDIDATE, "name": f"Food {index}"} for index in range(6)]
    client = httpx.Client(transport=httpx.MockTransport(lambda request: response_with(candidates)))
    interpreter = OpenAIInterpreter("server-only-key", client=client)

    assert len(interpreter.interpret("lunch")) == 4
