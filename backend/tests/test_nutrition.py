from decimal import Decimal

import pytest

from app.domain.nutrition import NutritionValues


def make(**overrides: Decimal) -> NutritionValues:
    values = {
        "calories": Decimal("100"),
        "protein_g": Decimal("10"),
        "carbs_g": Decimal("20"),
        "fat_g": Decimal("3"),
        "fiber_g": Decimal("2"),
        "sugar_g": Decimal("5"),
        "sodium_mg": Decimal("50"),
    }
    values.update(overrides)
    return NutritionValues(**values)


def test_scales_fractional_servings_exactly() -> None:
    scaled = make(calories=Decimal("140.0000"), protein_g=Decimal("13.0000")).scaled(Decimal("1.5"))
    assert scaled.calories == Decimal("210.0000")
    assert scaled.protein_g == Decimal("19.5000")


def test_rejects_non_positive_quantity() -> None:
    with pytest.raises(ValueError, match="quantity must be positive"):
        make().scaled(Decimal("0"))


def test_adds_two_nutrition_sets() -> None:
    total = make(calories=Decimal("140")).plus(make(calories=Decimal("80")))
    assert total.calories == Decimal("220")
    assert total.sodium_mg == Decimal("100")
