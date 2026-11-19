from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext

from alembic import command
from app.core.db import build_engine
from app.models.base import Base


def test_upgrade_then_downgrade_then_upgrade(alembic_config: Config) -> None:
    command.upgrade(alembic_config, "head")
    command.downgrade(alembic_config, "base")
    command.upgrade(alembic_config, "head")  # review focus #4


def test_schema_matches_models_after_upgrade(alembic_config: Config) -> None:
    command.upgrade(alembic_config, "head")
    engine = build_engine(alembic_config.get_main_option("sqlalchemy.url"))
    with engine.connect() as connection:
        context = MigrationContext.configure(connection)
        assert compare_metadata(context, Base.metadata) == []
