from pydantic import BaseModel, Field

from app.schemas.common import DecimalText


class NutritionFields(BaseModel):
    calories: DecimalText = Field(ge=0)
    protein_g: DecimalText = Field(ge=0)
    carbs_g: DecimalText = Field(ge=0)
    fat_g: DecimalText = Field(ge=0)
    fiber_g: DecimalText = Field(ge=0)
    sugar_g: DecimalText = Field(ge=0)
    sodium_mg: DecimalText = Field(ge=0)


class NutritionTotals(NutritionFields):
    """Backend-calculated totals for a meal preview or a saved meal."""
