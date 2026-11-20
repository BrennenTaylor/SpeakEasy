from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.nutrition import MACRO_FIELDS, NutritionValues
from app.models.food import Food
from app.models.meal import Meal, MealItem
from app.schemas.meal import MealCreate, MealItemCreate, MealItemRead, MealRead
from app.schemas.nutrition import NutritionTotals
from app.services.foods import food_values

_ZERO = NutritionValues(**{field: Decimal("0") for field in MACRO_FIELDS})


class UnknownFoodError(LookupError):
    """A meal item references a food id that is not saved."""


def _resolve_items(session: Session, payload: MealCreate) -> list[tuple[MealItemCreate, Food]]:
    """Load every referenced food before the caller writes any rows."""
    resolved: list[tuple[MealItemCreate, Food]] = []
    for item in payload.items:
        food = session.get(Food, item.food_id)
        if food is None:
            raise UnknownFoodError(f"Unknown food id: {item.food_id}")
        resolved.append((item, food))
    return resolved


def _item_values(item: MealItem) -> NutritionValues:
    """Read an item's immutable snapshot for backend-calculated totals."""
    return NutritionValues(
        calories=item.calories,
        protein_g=item.protein_g,
        carbs_g=item.carbs_g,
        fat_g=item.fat_g,
        fiber_g=item.fiber_g,
        sugar_g=item.sugar_g,
        sodium_mg=item.sodium_mg,
    )


def preview_totals(session: Session, payload: MealCreate) -> NutritionValues:
    """Calculate totals without adding or committing any rows."""
    totals = _ZERO
    for item, food in _resolve_items(session, payload):
        totals = totals.plus(food_values(food).scaled(item.quantity))
    return totals


def create_meal(session: Session, payload: MealCreate) -> Meal:
    """Save a meal with a nutrition snapshot copied from each referenced food."""
    resolved = _resolve_items(session, payload)
    meal = Meal(raw_input=payload.raw_input, eaten_at=payload.eaten_at)
    meal.items = [
        MealItem(
            food_id=food.id,
            quantity=item.quantity,
            unit=item.unit,
            serving_label=food.serving_label,
            serving_grams=food.serving_grams,
            source=food.source,
            confidence=food.confidence,
            **food_values(food).as_dict(),
        )
        for item, food in resolved
    ]
    session.add(meal)
    session.commit()
    session.refresh(meal)
    return meal


def list_meals(session: Session, limit: int) -> list[Meal]:
    """Return the most recently eaten meals first."""
    statement = select(Meal).order_by(Meal.eaten_at.desc(), Meal.id.desc()).limit(limit)
    return list(session.scalars(statement).all())


def meal_to_read(meal: Meal) -> MealRead:
    """Build the API view from snapshots, never from the current food rows."""
    totals = _ZERO
    items: list[MealItemRead] = []
    for item in meal.items:
        totals = totals.plus(_item_values(item).scaled(item.quantity))
        items.append(MealItemRead.model_validate(item))
    return MealRead(
        id=meal.id,
        raw_input=meal.raw_input,
        eaten_at=meal.eaten_at,
        created_at=meal.created_at,
        items=items,
        totals=NutritionTotals.model_validate(totals.as_dict()),
    )
