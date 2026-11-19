from sqlalchemy import text

from app.core.config import get_settings
from app.core.db import build_engine, build_session_factory, get_session


def test_session_executes_sql(tmp_path) -> None:
    engine = build_engine(f"sqlite:///{tmp_path / 'unit.db'}")
    session_factory = build_session_factory(engine)
    with session_factory() as session:
        assert session.execute(text("SELECT 1")).scalar_one() == 1


def test_in_memory_engine_works_with_a_single_session() -> None:
    """In-memory SQLite lives per connection; one session is the supported pattern."""
    engine = build_engine("sqlite://")
    session_factory = build_session_factory(engine)
    with session_factory() as session:
        session.execute(text("CREATE TABLE probe (id INTEGER PRIMARY KEY)"))
        session.commit()
        assert session.execute(text("SELECT count(*) FROM probe")).scalar_one() == 0


def test_get_session_yields_a_working_session(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("APP_DATABASE_URL", f"sqlite:///{tmp_path / 'dependency.db'}")
    get_settings.cache_clear()
    session = next(get_session())
    try:
        assert session.execute(text("SELECT 1")).scalar_one() == 1
    finally:
        session.close()
        get_settings.cache_clear()
