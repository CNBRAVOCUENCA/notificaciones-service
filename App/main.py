"""Entrypoint del microservicio de Notificaciones / Estado."""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from App.api import estado_router
from App.api.exception_handlers import register_exception_handlers
from App.config.settings import settings
from App.utils.database import ensure_indexes


@asynccontextmanager
async def lifespan(app: FastAPI):
    ensure_indexes()
    yield


# Disable API documentation in production (when debug=False)
docs_url = "/docs" if settings.debug else None
redoc_url = "/redoc" if settings.debug else None
openapi_url = "/openapi.json" if settings.debug else None

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    debug=settings.debug,
    docs_url=docs_url,
    redoc_url=redoc_url,
    openapi_url=openapi_url,
    lifespan=lifespan,
)

register_exception_handlers(app)
app.include_router(estado_router, prefix=settings.api_v1_prefix)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": settings.app_name}
