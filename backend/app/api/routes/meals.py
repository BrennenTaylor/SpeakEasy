from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.db import get_session
from app.schemas.meal import MealCreate, MealRead
from app.schemas.nutrition import NutritionTotals
from app.services.meals import (
    UnknownFoodError,
    create_meal,
    list_meals,
    meal_to_read,
    preview_totals,
)

router = APIRouter()


@router.post("/meals/preview", response_model=NutritionTotals)
def preview_meal(
    payload: MealCreate, session: Annotated[Session, Depends(get_session)]
) -> NutritionTotals:
    try:
        totals = preview_totals(session, payload)
    except UnknownFoodError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return NutritionTotals.model_validate(totals.as_dict())


@router.post("/meals", response_model=MealRead, status_code=201)
def add_meal(payload: MealCreate, session: Annotated[Session, Depends(get_session)]) -> MealRead:
    try:
        meal = create_meal(session, payload)
    except UnknownFoodError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return meal_to_read(meal)


@router.get("/meals", response_model=list[MealRead])
def read_meals(
    session: Annotated[Session, Depends(get_session)], limit: int = 20
) -> list[MealRead]:
    return [meal_to_read(meal) for meal in list_meals(session, limit)]
