from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

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


class FoodUpdate(BaseModel):
    """Partial edit of a saved food; only explicitly supplied fields are applied."""

    name: str | None = None
    brand: str | None = None
    serving_label: str | None = None
    serving_grams: DecimalText | None = None
    source: Literal["user_label"] | None = None
    confidence: Literal["high", "low"] | None = None
    aliases: list[str] | None = None
    calories: DecimalText | None = Field(default=None, ge=0)
    protein_g: DecimalText | None = Field(default=None, ge=0)
    carbs_g: DecimalText | None = Field(default=None, ge=0)
    fat_g: DecimalText | None = Field(default=None, ge=0)
    fiber_g: DecimalText | None = Field(default=None, ge=0)
    sugar_g: DecimalText | None = Field(default=None, ge=0)
    sodium_mg: DecimalText | None = Field(default=None, ge=0)


class FoodRead(FoodCreate):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
