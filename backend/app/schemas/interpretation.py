from typing import Annotated, Literal

from pydantic import BaseModel, Field, HttpUrl

from app.schemas.common import DecimalText

Calories = Annotated[DecimalText, Field(ge=0, le=5_000)]
MacroGrams = Annotated[DecimalText, Field(ge=0, le=50_000)]
SodiumMg = Annotated[DecimalText, Field(ge=0, le=50_000)]


class RawCandidate(BaseModel):
    """A food proposed by the model. Values are per serving, never meal totals."""

    name: str = Field(min_length=1, max_length=200)
    brand: str = Field(max_length=200)
    serving_label: str = Field(min_length=1, max_length=100)
    serving_grams: DecimalText = Field(gt=0, le=50_000)
    quantity: DecimalText = Field(gt=0, le=20)
    calories: Calories
    protein_g: MacroGrams
    carbs_g: MacroGrams
    fat_g: MacroGrams
    fiber_g: MacroGrams
    sugar_g: MacroGrams
    sodium_mg: SodiumMg
    source_url: HttpUrl | None = None


class MatchView(BaseModel):
    """A ranked match ready for user review. Missing macros stay null. Rank starts at 1."""

    name: str = Field(min_length=1, max_length=200)
    brand: str = Field(max_length=200)
    serving_label: str = Field(min_length=1, max_length=100)
    serving_grams: DecimalText
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
