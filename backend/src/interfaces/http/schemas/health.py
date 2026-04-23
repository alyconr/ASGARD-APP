"""Schemas for backend health responses."""

from pydantic import BaseModel


class HealthResponse(BaseModel):
    """Response schema returned by the health endpoint."""

    status: str
    service: str
    environment: str
    database_configured: bool
