"""persist nutrition source URLs on foods and meal snapshots

Revision ID: 0003_source_url
Revises: 0002_meal_logging
Create Date: 2026-11-20
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0003_source_url"
down_revision: str | None = "0002_meal_logging"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("foods") as batch:
        batch.add_column(sa.Column("source_url", sa.String(length=500), nullable=True))
    with op.batch_alter_table("meal_items") as batch:
        batch.add_column(sa.Column("source_url", sa.String(length=500), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("meal_items") as batch:
        batch.drop_column("source_url")
    with op.batch_alter_table("foods") as batch:
        batch.drop_column("source_url")
