from fastapi import APIRouter

from app.api.v1.routes import health, import_jobs, settings, source_configs, vod_sites

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(source_configs.router)
api_router.include_router(import_jobs.router)
api_router.include_router(vod_sites.router)
api_router.include_router(settings.router)
