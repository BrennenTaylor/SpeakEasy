"""Verify migrations upgrade, downgrade, and re-upgrade cleanly on a temporary database."""

import sys
import tempfile
from pathlib import Path

# Insert backend directory to sys.path so app imports resolve
BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from alembic.config import Config  # noqa: E402
from alembic.migration import MigrationContext  # noqa: E402
from sqlalchemy import create_engine, text  # noqa: E402

from alembic import command  # noqa: E402


def check_migrations() -> None:
    ini_path = BACKEND_DIR / "alembic.ini"
    script_path = BACKEND_DIR / "alembic"

    with tempfile.TemporaryDirectory() as tmp_dir:
        db_file = Path(tmp_dir) / "check_migrations.db"
        db_url = f"sqlite:///{db_file}"

        config = Config(str(ini_path))
        config.set_main_option("script_location", str(script_path))
        config.set_main_option("sqlalchemy.url", db_url)

        # Step 1: upgrade to head
        try:
            command.upgrade(config, "head")
        except Exception as e:
            sys.exit(f"Failed at step 'upgrade to head': {e}")

        engine = create_engine(db_url)
        try:
            with engine.connect() as conn:
                context = MigrationContext.configure(conn)
                current_rev = context.get_current_revision()
                if not current_rev:
                    sys.exit(
                        "Failed at step 'assert revision exists after head upgrade': "
                        "no revision found"
                    )
        finally:
            engine.dispose()

        # Step 2: downgrade to base
        try:
            command.downgrade(config, "base")
        except Exception as e:
            sys.exit(f"Failed at step 'downgrade to base': {e}")

        engine = create_engine(db_url)
        try:
            with engine.connect() as conn:
                context = MigrationContext.configure(conn)
                current_rev = context.get_current_revision()
                version_rows = conn.execute(
                    text("SELECT version_num FROM alembic_version")
                ).fetchall()
                if current_rev is not None or len(version_rows) > 0:
                    sys.exit(
                        "Failed at step 'assert alembic_version is gone after downgrade to base': "
                        "version found"
                    )
        finally:
            engine.dispose()

        # Step 3: upgrade again to head
        try:
            command.upgrade(config, "head")
        except Exception as e:
            sys.exit(f"Failed at step 're-upgrade to head': {e}")

        engine = create_engine(db_url)
        try:
            with engine.connect() as conn:
                context = MigrationContext.configure(conn)
                current_rev = context.get_current_revision()
                if not current_rev:
                    sys.exit(
                        "Failed at step 'assert revision exists after second head upgrade': "
                        "no revision found"
                    )
        finally:
            engine.dispose()

        # Step 4: remove file
        if db_file.exists():
            db_file.unlink()

    print("migrations OK: head -> base -> head")


if __name__ == "__main__":
    check_migrations()
