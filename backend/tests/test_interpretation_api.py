import pytest
from fastapi.testclient import TestClient

import app.services.interpretation as interpretation
from app.ai.dependencies import get_interpreter
from app.ai.provider import AIServiceError
from app.schemas.interpretation import CandidateView, RawCandidate
from app.services.interpretation import interpret_description

RAW = {
    "name": "Chick-fil-A sandwich",
    "brand": "Chick-fil-A",
    "serving_label": "1 sandwich",
    "serving_grams": "187",
    "quantity": "1",
    "calories": "249",
    "protein_g": "16",
    "carbs_g": "21",
    "fat_g": "11",
    "fiber_g": "1",
    "sugar_g": "0",
    "sodium_mg": "753",
    "source_url": "https://example.com/menu",
}

VIEW = {
    **RAW,
    "serving_grams": "187.0000",
    "quantity": "1.0000",
    "source": "web_search",
    "confidence": "low",
    "incomplete": False,
    "missing_fields": [],
}


def stub_candidate(name: str = "Chick-fil-A sandwich") -> RawCandidate:
    return RawCandidate.model_validate({**RAW, "name": name})


def resolved_view(monkeypatch: pytest.MonkeyPatch, warning: str | None = None) -> None:
    view = CandidateView.model_validate(VIEW)
    monkeypatch.setattr(interpretation, "resolve_candidate", lambda raw, **kwargs: (view, warning))


class StubInterpreter:
    def __init__(self, candidates: list[RawCandidate] | None = None) -> None:
        self.candidates = candidates or [stub_candidate()]

    def interpret(self, description: str) -> list[RawCandidate]:
        return self.candidates


def test_interpret_returns_candidates_without_writing(
    client_with_db: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    resolved_view(monkeypatch)
    client_with_db.app.dependency_overrides[get_interpreter] = lambda: StubInterpreter()

    response = client_with_db.post(
        "/api/meals/interpret", json={"description": "chick fil a sandwich"}
    )

    assert response.status_code == 200
    assert response.json()["candidates"][0]["source"] == "web_search"
    assert response.json()["warnings"] == []
    assert client_with_db.get("/api/meals").json() == []
    assert client_with_db.get("/api/foods").json() == []


def test_interpret_returns_503_without_key(client_with_db: TestClient) -> None:
    client_with_db.app.dependency_overrides[get_interpreter] = lambda: None

    response = client_with_db.post("/api/meals/interpret", json={"description": "lunch"})

    assert response.status_code == 503
    assert response.json() == {"detail": "AI interpretation is not configured"}


def test_interpret_returns_503_on_provider_error(client_with_db: TestClient) -> None:
    class FailingInterpreter:
        def interpret(self, description: str) -> list[RawCandidate]:
            raise AIServiceError("provider down")

    client_with_db.app.dependency_overrides[get_interpreter] = lambda: FailingInterpreter()

    response = client_with_db.post("/api/meals/interpret", json={"description": "lunch"})

    assert response.status_code == 503
    assert response.json() == {"detail": "AI interpretation is unavailable"}


def test_interpret_rejects_long_description(client_with_db: TestClient) -> None:
    client_with_db.app.dependency_overrides[get_interpreter] = lambda: StubInterpreter()

    response = client_with_db.post("/api/meals/interpret", json={"description": "x" * 501})

    assert response.status_code == 422


def test_interpret_description_caps_candidates(monkeypatch: pytest.MonkeyPatch) -> None:
    resolved_view(monkeypatch)
    candidates = [stub_candidate(f"Food {index}") for index in range(6)]

    result = interpret_description("lunch", StubInterpreter(candidates))

    assert len(result.candidates) == 4
