from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.main import create_app


def test_health_returns_ok(client: TestClient) -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_is_documented_in_openapi(client: TestClient) -> None:
    schema = client.get("/openapi.json").json()
    assert "/api/health" in schema["paths"]
    assert schema["paths"]["/api/health"]["get"]["responses"]["200"]["content"]


def test_health_does_not_require_a_database(tmp_path, monkeypatch) -> None:
    """Liveness must work before any migration has run."""
    monkeypatch.setenv("APP_DATABASE_URL", f"sqlite:///{tmp_path / 'absent.db'}")
    get_settings.cache_clear()
    with TestClient(create_app()) as client:
        assert client.get("/api/health").status_code == 200
    assert not (tmp_path / "absent.db").exists()
    get_settings.cache_clear()
