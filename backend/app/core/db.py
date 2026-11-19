from collections.abc import Iterator
from functools import lru_cache
from typing import Any

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings


@lru_cache
def _engine_for(url: str) -> Engine:
    connect_args: dict[str, Any] = {"check_same_thread": False} if url.startswith("sqlite") else {}
    return create_engine(url, echo=get_settings().sql_echo, connect_args=connect_args)


def build_engine(url: str) -> Engine:
    return _engine_for(url)


def build_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_session() -> Iterator[Session]:
    session_factory = build_session_factory(_engine_for(get_settings().database_url))
    with session_factory() as session:
        yield session
