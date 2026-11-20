from fastapi import APIRouter

from app.api.routes import foods, health, meals

api_router = APIRouter(prefix="/api")
api_router.include_router(health.router, tags=["health"])
api_router.include_router(foods.router, tags=["foods"])
api_router.include_router(meals.router, tags=["meals"])
