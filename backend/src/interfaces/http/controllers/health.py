"""Healthcheck endpoints for local development."""

from fastapi import APIRouter

from src.infrastructure.config.settings import get_settings
from src.interfaces.http.schemas.health import HealthResponse

router = APIRouter(prefix="/api/v1", tags=["health"])


@router.get("/health", response_model=HealthResponse)
def get_health() -> HealthResponse:
    """Return a minimal health response for the backend service."""
    settings = get_settings()

    return HealthResponse(
        status="ok",
        service=settings.app_name,
        environment=settings.app_env,
        database_configured=bool(settings.database_url),
    )
