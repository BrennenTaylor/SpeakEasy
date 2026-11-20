from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

import app.models  # noqa: F401  # registers every table on Base.metadata
from app.core.db import get_session
from app.main import create_app
from app.models.base import Base

BACKEND_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(create_app()) as test_client:
        yield test_client


@pytest.fixture
def alembic_config(tmp_path: Path) -> Config:
    config = Config(str(BACKEND_ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_ROOT / "alembic"))
    config.set_main_option("sqlalchemy.url", f"sqlite:///{tmp_path / 'migrate.db'}")
    return config


@pytest.fixture
def session(tmp_path: Path) -> Iterator[Session]:
    engine = create_engine(
        f"sqlite:///{tmp_path / 'test.db'}", connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    with factory() as db:
        yield db
    engine.dispose()


@pytest.fixture
def client_with_db(session: Session) -> Iterator[TestClient]:
    app = create_app()
    app.dependency_overrides[get_session] = lambda: session
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def food_ids(client_with_db: TestClient) -> list[int]:
    """Save two foods with different calories and return their ids."""
    ids = []
    for name, calories in (("Eggs", "140.0000"), ("Nuggets", "250.0000")):
        payload = {
            "name": name,
            "brand": "Test brand",
            "serving_label": "1 piece",
            "serving_grams": "50",
            "calories": calories,
            "protein_g": "1.0000",
            "carbs_g": "1.0000",
            "fat_g": "1.0000",
            "fiber_g": "1.0000",
            "sugar_g": "1.0000",
            "sodium_mg": "1.0000",
            "confidence": "high",
        }
        response = client_with_db.post("/api/foods", json=payload)
        assert response.status_code == 201
        ids.append(response.json()["id"])
    return ids
