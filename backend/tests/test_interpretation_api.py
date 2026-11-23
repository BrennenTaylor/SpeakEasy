import threading

import pytest
from fastapi.testclient import TestClient

import app.services.interpretation as interpretation
from app.ai.dependencies import get_interpreter
from app.ai.provider import AIServiceError
from app.schemas.interpretation import MatchView, RawCandidate
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

MATCH = {
    **VIEW,
    "match_id": "web:0",
    "source_key": None,
    "rank": 1,
    "rank_reasons": ["web source"],
}


def stub_candidate(name: str = "Chick-fil-A sandwich") -> RawCandidate:
    return RawCandidate.model_validate({**RAW, "name": name})


def resolved_matches(monkeypatch: pytest.MonkeyPatch, warnings: list[str] | None = None) -> None:
    match = MatchView.model_validate(MATCH)
    monkeypatch.setattr(
        interpretation, "resolve_matches", lambda raw, **kwargs: ([match], warnings or [])
    )


class StubInterpreter:
    def __init__(self, candidates: list[RawCandidate] | None = None) -> None:
        self.candidates = candidates or [stub_candidate()]

    def interpret(self, description: str) -> list[RawCandidate]:
        return self.candidates


def test_interpret_returns_groups_without_writing(
    client_with_db: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    from app.schemas.interpretation import MatchView
    from app.services import interpretation

    match = MatchView.model_validate(
        {
            **VIEW,
            "match_id": "web:0",
            "source_key": None,
            "rank": 1,
            "rank_reasons": ["web source"],
        }
    )
    monkeypatch.setattr(
        interpretation,
        "resolve_matches",
        lambda raw, **kwargs: ([match], ["USDA lookup unavailable"]),
    )
    client_with_db.app.dependency_overrides[get_interpreter] = lambda: StubInterpreter()

    response = client_with_db.post(
        "/api/meals/interpret", json={"description": "chick fil a sandwich"}
    )

    assert response.status_code == 200
    body = response.json()
    assert body["groups"][0]["group_id"] == "0"
    assert body["groups"][0]["label"] == "Chick-fil-A sandwich"
    assert body["groups"][0]["matches"][0]["match_id"] == "web:0"
    assert body["warnings"] == ["USDA lookup unavailable"]
    assert "candidates" not in body
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
    resolved_matches(monkeypatch)
    candidates = [stub_candidate(f"Food {index}") for index in range(6)]

    result = interpret_description("lunch", StubInterpreter(candidates))

    assert len(result.groups) == 4


def test_interpret_description_resolves_candidates_concurrently(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    barrier = threading.Barrier(4, timeout=2)
    match = MatchView.model_validate(MATCH)

    def fake_resolve(raw: RawCandidate, **kwargs: object) -> tuple[list[MatchView], list[str]]:
        barrier.wait()
        return [match], []

    monkeypatch.setattr(interpretation, "resolve_matches", fake_resolve)
    candidates = [stub_candidate(f"Food {index}") for index in range(4)]

    result = interpret_description("lunch", StubInterpreter(candidates))

    assert len(result.groups) == 4


def test_interpret_description_deduplicates_warnings_across_groups(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    resolved_matches(monkeypatch, ["USDA lookup unavailable"])
    candidates = [stub_candidate(f"Food {index}") for index in range(2)]

    result = interpret_description("lunch", StubInterpreter(candidates))

    assert [group.group_id for group in result.groups] == ["0", "1"]
    assert result.warnings == ["USDA lookup unavailable"]
