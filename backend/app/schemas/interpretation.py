from typing import Annotated, Literal

from pydantic import BaseModel, Field, HttpUrl, field_validator

from app.schemas.common import DecimalText

Calories = Annotated[DecimalText, Field(ge=0, le=5_000)]
MacroGrams = Annotated[DecimalText, Field(ge=0, le=50_000)]
SodiumMg = Annotated[DecimalText, Field(ge=0, le=50_000)]


class RawCandidate(BaseModel):
    """A food proposed by the model. Values are per serving, never meal totals."""

    name: str = Field(min_length=1, max_length=200)
    brand: str = Field(max_length=200)
    serving_label: str = Field(min_length=1, max_length=100)
    serving_grams: DecimalText | None = None
    quantity: DecimalText = Field(gt=0, le=20)
    calories: Calories | None = None
    protein_g: MacroGrams | None = None
    carbs_g: MacroGrams | None = None
    fat_g: MacroGrams | None = None
    fiber_g: MacroGrams | None = None
    sugar_g: MacroGrams | None = None
    sodium_mg: SodiumMg | None = None
    source_url: HttpUrl | None = None

    @field_validator(
        "serving_grams",
        "calories",
        "protein_g",
        "carbs_g",
        "fat_g",
        "fiber_g",
        "sugar_g",
        "sodium_mg",
        mode="before",
    )
    @classmethod
    def _blank_number_is_missing(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @field_validator("source_url", mode="before")
    @classmethod
    def _blank_url_is_missing(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            return None
        return value


class MatchView(BaseModel):
    """A ranked match ready for user review. Missing macros stay null. Rank starts at 1."""

    name: str = Field(min_length=1, max_length=200)
    brand: str = Field(max_length=200)
    serving_label: str = Field(min_length=1, max_length=100)
    serving_grams: DecimalText | None = None
    quantity: DecimalText
    source: Literal["usda_fdc", "web_search"]
    source_url: HttpUrl | None = None
    confidence: Literal["high", "low"]
    incomplete: bool
    missing_fields: list[str] = Field(default_factory=list)
    calories: DecimalText | None = None
    protein_g: DecimalText | None = None
    carbs_g: DecimalText | None = None
    fat_g: DecimalText | None = None
    fiber_g: DecimalText | None = None
    sugar_g: DecimalText | None = None
    sodium_mg: DecimalText | None = None
    match_id: str
    source_key: str | None
    rank: int = Field(ge=1)
    rank_reasons: list[str]


class FoodMatchGroup(BaseModel):
    """One interpreted food item and its ranked match options."""

    group_id: str
    label: str
    quantity: DecimalText
    matches: list[MatchView]


class InterpretRequest(BaseModel):
    description: str = Field(min_length=1, max_length=500)


class InterpretResponse(BaseModel):
    groups: list[FoodMatchGroup] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
