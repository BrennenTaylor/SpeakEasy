from sqlalchemy import select
from sqlalchemy.orm import Session

from app.domain.nutrition import NutritionValues
from app.models.food import Food
from app.schemas.food import FoodCreate


def normalize(text: str) -> str:
    """Lowercase, strip, and collapse whitespace before matching."""
    return " ".join(text.lower().split())


def food_values(food: Food) -> NutritionValues:
    """Read a food's authoritative macro values without copying or rounding them."""
    return NutritionValues(
        calories=food.calories,
        protein_g=food.protein_g,
        carbs_g=food.carbs_g,
        fat_g=food.fat_g,
        fiber_g=food.fiber_g,
        sugar_g=food.sugar_g,
        sodium_mg=food.sodium_mg,
    )


def create_food(session: Session, payload: FoodCreate) -> Food:
    food = Food(
        name=payload.name,
        brand=payload.brand,
        serving_label=payload.serving_label,
        serving_grams=payload.serving_grams,
        calories=payload.calories,
        protein_g=payload.protein_g,
        carbs_g=payload.carbs_g,
        fat_g=payload.fat_g,
        fiber_g=payload.fiber_g,
        sugar_g=payload.sugar_g,
        sodium_mg=payload.sodium_mg,
        source=payload.source,
        confidence=payload.confidence,
        aliases=payload.aliases,
    )
    session.add(food)
    session.commit()
    session.refresh(food)
    return food


def search_foods(session: Session, query: str, limit: int = 20) -> list[Food]:
    """Match normalized name, brand, or aliases and order deterministically."""
    wanted = normalize(query)
    foods = session.scalars(select(Food)).all()
    matches = [
        food
        for food in foods
        if any(wanted in normalize(text) for text in (food.name, food.brand, *food.aliases))
    ]
    matches.sort(key=lambda food: (normalize(food.name), food.id))
    return matches[:limit]
