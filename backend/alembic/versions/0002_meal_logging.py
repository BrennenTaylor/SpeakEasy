"""meal logging: foods, meals, and item snapshots

Revision ID: 0002_meal_logging
Revises: 0001_baseline
Create Date: 2026-11-19
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0002_meal_logging"
down_revision: str | None = "0001_baseline"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "foods",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("brand", sa.String(length=200), nullable=False),
        sa.Column("serving_label", sa.String(length=100), nullable=False),
        sa.Column("serving_grams", sa.Numeric(precision=12, scale=4), nullable=False),
        sa.Column("calories", sa.Numeric(precision=12, scale=4), nullable=False),
        sa.Column("protein_g", sa.Numeric(precision=12, scale=4), nullable=False),
        sa.Column("carbs_g", sa.Numeric(precision=12, scale=4), nullable=False),
        sa.Column("fat_g", sa.Numeric(precision=12, scale=4), nullable=False),
        sa.Column("fiber_g", sa.Numeric(precision=12, scale=4), nullable=False),
        sa.Column("sugar_g", sa.Numeric(precision=12, scale=4), nullable=False),
        sa.Column("sodium_mg", sa.Numeric(precision=12, scale=4), nullable=False),
        sa.Column("source", sa.String(length=50), nullable=False),
        sa.Column("confidence", sa.String(length=20), nullable=False),
        sa.Column("aliases", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "meals",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("raw_input", sa.Text(), nullable=False),
        sa.Column("eaten_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "meal_items",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("meal_id", sa.Integer(), nullable=False),
        sa.Column("food_id", sa.Integer(), nullable=False),
        sa.Column("quantity", sa.Numeric(precision=12, scale=4), nullable=False),
        sa.Column("unit", sa.String(length=20), nullable=False),
        sa.Column("serving_label", sa.String(length=100), nullable=False),
        sa.Column("serving_grams", sa.Numeric(precision=12, scale=4), nullable=False),
        sa.Column("calories", sa.Numeric(precision=12, scale=4), nullable=False),
        sa.Column("protein_g", sa.Numeric(precision=12, scale=4), nullable=False),
        sa.Column("carbs_g", sa.Numeric(precision=12, scale=4), nullable=False),
        sa.Column("fat_g", sa.Numeric(precision=12, scale=4), nullable=False),
        sa.Column("fiber_g", sa.Numeric(precision=12, scale=4), nullable=False),
        sa.Column("sugar_g", sa.Numeric(precision=12, scale=4), nullable=False),
        sa.Column("sodium_mg", sa.Numeric(precision=12, scale=4), nullable=False),
        sa.Column("source", sa.String(length=50), nullable=False),
        sa.Column("confidence", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["meal_id"], ["meals.id"]),
        sa.ForeignKeyConstraint(["food_id"], ["foods.id"]),
    )


def downgrade() -> None:
    op.drop_table("meal_items")
    op.drop_table("meals")
    op.drop_table("foods")
