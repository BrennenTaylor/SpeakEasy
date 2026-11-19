from collections.abc import Iterator
from functools import lru_cache
from pathlib import Path
from typing import Any

from sqlalchemy import Engine, create_engine
from sqlalchemy.engine import URL, make_url
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings

_BACKEND_DIR = Path(__file__).resolve().parents[2]


def _prepare_url(url: str) -> URL:
    prepared = make_url(url)
    if prepared.get_backend_name() != "sqlite" or not prepared.database:
        return prepared
    if prepared.database == ":memory:":
        return prepared

    database_path = Path(prepared.database)
    if not database_path.is_absolute():
        database_path = _BACKEND_DIR / database_path
    database_path.parent.mkdir(parents=True, exist_ok=True)
    return prepared.set(database=str(database_path))


@lru_cache
def _engine_for(url: str) -> Engine:
    prepared = _prepare_url(url)
    connect_args: dict[str, Any] = (
        {"check_same_thread": False} if prepared.get_backend_name() == "sqlite" else {}
    )
    return create_engine(prepared, echo=get_settings().sql_echo, connect_args=connect_args)


def build_engine(url: str) -> Engine:
    return _engine_for(url)


def build_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_session() -> Iterator[Session]:
    session_factory = build_session_factory(_engine_for(get_settings().database_url))
    with session_factory() as session:
        yield session
