"""Importing this package registers every domain table on ``Base.metadata``."""

from app.models.food import Food
from app.models.meal import Meal, MealItem

__all__ = ["Food", "Meal", "MealItem"]
