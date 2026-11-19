from sqlalchemy import text

from app.core.config import get_settings
from app.core.db import _engine_for, build_engine, build_session_factory, get_session


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
    _engine_for.cache_clear()
    session = next(get_session())
    try:
        assert session.execute(text("SELECT 1")).scalar_one() == 1
    finally:
        session.close()
        _engine_for.cache_clear()
        get_settings.cache_clear()


def test_get_session_shares_cached_engine(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("APP_DATABASE_URL", f"sqlite:///{tmp_path / 'shared.db'}")
    get_settings.cache_clear()
    _engine_for.cache_clear()
    session1 = next(get_session())
    session2 = next(get_session())
    try:
        assert session1.bind is not None
        assert session1.bind is session2.bind
    finally:
        session1.close()
        session2.close()
        _engine_for.cache_clear()
        get_settings.cache_clear()


def test_build_engine_creates_missing_parent_directory(tmp_path) -> None:
    db_path = tmp_path / "nested" / "dir" / "app.db"
    engine = build_engine(f"sqlite:///{db_path}")
    try:
        with engine.connect() as conn:
            assert conn.execute(text("SELECT 1")).scalar_one() == 1
        assert db_path.exists()
    finally:
        engine.dispose()
        _engine_for.cache_clear()


def test_relative_sqlite_path_is_anchored_to_backend(monkeypatch, tmp_path) -> None:
    from app.core import db as db_module

    monkeypatch.chdir(tmp_path)
    engine = build_engine("sqlite:///./data/relative.db")
    try:
        assert engine.url.database == str(db_module._BACKEND_DIR / "data" / "relative.db")
        assert not (tmp_path / "data").exists()
    finally:
        engine.dispose()
        _engine_for.cache_clear()
