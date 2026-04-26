from fastapi import APIRouter

from app.api.v1.routes import health, source_configs

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(source_configs.router)
