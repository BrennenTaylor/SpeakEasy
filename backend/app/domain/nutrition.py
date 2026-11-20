from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

_QUANTUM = Decimal("0.0001")

MACRO_FIELDS: tuple[str, ...] = (
    "calories",
    "protein_g",
    "carbs_g",
    "fat_g",
    "fiber_g",
    "sugar_g",
    "sodium_mg",
)


def _quantize(value: Decimal) -> Decimal:
    return value.quantize(_QUANTUM, rounding=ROUND_HALF_UP)


@dataclass(frozen=True)
class NutritionValues:
    calories: Decimal
    protein_g: Decimal
    carbs_g: Decimal
    fat_g: Decimal
    fiber_g: Decimal
    sugar_g: Decimal
    sodium_mg: Decimal

    def scaled(self, quantity: Decimal) -> NutritionValues:
        if quantity <= 0:
            raise ValueError("quantity must be positive")
        return NutritionValues(
            **{field: _quantize(value * quantity) for field, value in self.as_dict().items()}
        )

    def plus(self, other: NutritionValues) -> NutritionValues:
        other_values = other.as_dict()
        return NutritionValues(
            **{
                field: _quantize(value + other_values[field])
                for field, value in self.as_dict().items()
            }
        )

    def as_dict(self) -> dict[str, Decimal]:
        return {field: getattr(self, field) for field in MACRO_FIELDS}
