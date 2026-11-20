from datetime import datetime
from typing import Literal

from pydantic import ConfigDict, Field

from app.schemas.common import DecimalText
from app.schemas.nutrition import NutritionFields


class FoodCreate(NutritionFields):
    name: str
    brand: str
    serving_label: str
    serving_grams: DecimalText
    source: Literal["user_label"] = "user_label"
    confidence: Literal["high", "low"]
    aliases: list[str] = Field(default_factory=list)


class FoodRead(FoodCreate):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
