from __future__ import annotations

import json
from typing import Any

import httpx
from pydantic import ValidationError

from app.ai.provider import AIServiceError, MealInterpreter
from app.schemas.interpretation import RawCandidate

_API_URL = "https://api.openai.com/v1/responses"
_SYSTEM_PROMPT = (
    "Interpret the meal description as food candidates. Return per-serving values only. "
    "For every candidate, include a source URL from a web result. Never include meal totals "
    "or amounts calculated from multiple foods. Never estimate nutrition values without a "
    "source URL. Return at most four candidates."
)


def _candidate_properties() -> dict[str, object]:
    string = {"type": "string"}
    number_string = {"type": "string", "description": "Decimal value as a string"}
    return {
        "name": {**string, "minLength": 1},
        "brand": string,
        "serving_label": {**string, "minLength": 1},
        "serving_grams": number_string,
        "quantity": number_string,
        "calories": number_string,
        "protein_g": number_string,
        "carbs_g": number_string,
        "fat_g": number_string,
        "fiber_g": number_string,
        "sugar_g": number_string,
        "sodium_mg": number_string,
        "source_url": {"type": ["string", "null"], "description": "http(s) source URL"},
    }


def _request_body(description: str, model: str) -> dict[str, Any]:
    properties = _candidate_properties()
    return {
        "model": model,
        "input": [
            {"role": "developer", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": f"Meal description: {description}"},
        ],
        "tools": [{"type": "web_search"}],
        "max_output_tokens": 1500,
        "text": {
            "format": {
                "type": "json_schema",
                "name": "meal_candidates",
                "strict": True,
                "schema": {
                    "type": "object",
                    "properties": {
                        "candidates": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": properties,
                                "required": list(properties),
                                "additionalProperties": False,
                            },
                        }
                    },
                    "required": ["candidates"],
                    "additionalProperties": False,
                },
            }
        },
    }


def _extract_output_text(payload: object) -> str:
    if isinstance(payload, dict):
        output = payload.get("output")
        if isinstance(output, list):
            for item in output:
                if not isinstance(item, dict) or item.get("type") != "message":
                    continue
                content = item.get("content")
                if not isinstance(content, list):
                    continue
                for part in content:
                    if (
                        isinstance(part, dict)
                        and part.get("type") == "output_text"
                        and isinstance(part.get("text"), str)
                    ):
                        return str(part["text"])
        fallback = payload.get("output_text")
        if isinstance(fallback, str):
            return fallback
    raise AIServiceError("AI provider returned no structured text")


class OpenAIInterpreter(MealInterpreter):
    """Calls the OpenAI Responses API and validates structured food candidates."""

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-6-luna",
        timeout_seconds: float = 10.0,
        max_candidates: int = 4,
        client: httpx.Client | None = None,
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._timeout_seconds = timeout_seconds
        self._max_candidates = max_candidates
        self._client = client
        self._owns_client = client is None

    def interpret(self, description: str) -> list[RawCandidate]:
        client = self._client or httpx.Client()
        try:
            payload = self._post(client, description)
        finally:
            if self._owns_client:
                client.close()

        text = _extract_output_text(payload)
        try:
            data: object = json.loads(text)
        except json.JSONDecodeError as error:
            raise AIServiceError("AI provider returned invalid JSON") from error
        if not isinstance(data, dict):
            raise AIServiceError("AI provider returned an unexpected shape")
        candidates = data.get("candidates")
        if not isinstance(candidates, list):
            raise AIServiceError("AI provider returned no candidates")

        parsed: list[RawCandidate] = []
        for item in candidates[: self._max_candidates]:
            try:
                parsed.append(RawCandidate.model_validate(item))
            except ValidationError as error:
                raise AIServiceError("AI provider returned an invalid candidate") from error
        return parsed

    def _post(self, client: httpx.Client, description: str) -> object:
        last_error: httpx.TransportError | None = None
        for _ in range(2):
            try:
                response = client.post(
                    _API_URL,
                    headers={
                        "Authorization": f"Bearer {self._api_key}",
                        "Content-Type": "application/json",
                    },
                    json=_request_body(description, self._model),
                    timeout=self._timeout_seconds,
                )
                response.raise_for_status()
            except (httpx.TimeoutException, httpx.TransportError) as error:
                last_error = error
                continue
            except httpx.HTTPStatusError as error:
                raise AIServiceError("AI provider request failed") from error
            try:
                return response.json()
            except ValueError as error:
                raise AIServiceError("AI provider returned invalid JSON") from error
        raise AIServiceError("AI provider is unavailable") from last_error
