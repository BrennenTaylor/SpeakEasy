from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import DecimalText
from app.schemas.nutrition import NutritionFields, NutritionTotals


class MealItemCreate(BaseModel):
    food_id: int
    quantity: DecimalText = Field(gt=0)
    unit: Literal["serving"] = "serving"


class MealCreate(BaseModel):
    raw_input: str = Field(min_length=1)
    eaten_at: datetime
    items: list[MealItemCreate] = Field(min_length=1)


class MealItemRead(NutritionFields):
    id: int
    food_id: int
    quantity: DecimalText
    unit: Literal["serving"]
    serving_label: str
    serving_grams: DecimalText
    source: str
    source_url: str | None = None
    confidence: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MealRead(BaseModel):
    id: int
    raw_input: str
    eaten_at: datetime
    created_at: datetime
    items: list[MealItemRead]
    totals: NutritionTotals

    model_config = ConfigDict(from_attributes=True)
