from decimal import Decimal

from sqlalchemy import Numeric
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.nutrition import MACRO_FIELDS


class NutritionColumns:
    """Seven non-null ``Numeric(12, 4)`` macro columns shared by foods and snapshots."""

    calories: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    protein_g: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    carbs_g: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    fat_g: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    fiber_g: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    sugar_g: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    sodium_mg: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)


# Columns are declared explicitly so static typing sees them on every model;
# this guard keeps them aligned with the domain's authoritative field list.
assert frozenset(NutritionColumns.__annotations__) == frozenset(MACRO_FIELDS)
