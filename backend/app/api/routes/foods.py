from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.db import get_session
from app.schemas.food import FoodCreate, FoodRead
from app.services.foods import create_food, search_foods

router = APIRouter()


@router.post("/foods", response_model=FoodRead, status_code=201)
def add_food(payload: FoodCreate, session: Annotated[Session, Depends(get_session)]) -> FoodRead:
    return FoodRead.model_validate(create_food(session, payload))


@router.get("/foods", response_model=list[FoodRead])
def read_foods(
    session: Annotated[Session, Depends(get_session)],
    q: str = "",
    limit: int = 20,
) -> list[FoodRead]:
    return [FoodRead.model_validate(food) for food in search_foods(session, q, limit)]
