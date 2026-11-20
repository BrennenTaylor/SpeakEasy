from fastapi import APIRouter

from app.api.routes import foods, health

api_router = APIRouter(prefix="/api")
api_router.include_router(health.router, tags=["health"])
api_router.include_router(foods.router, tags=["foods"])
