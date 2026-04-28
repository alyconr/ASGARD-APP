"""Central application settings for the backend service."""

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CORS_ALLOW_ORIGINS = "http://localhost:3000,http://127.0.0.1:3000"


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=BACKEND_ROOT / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = Field(default="SENA Guia Aprendizaje API")
    app_env: str = Field(default="development")
    app_host: str = Field(default="0.0.0.0")
    app_port: int = Field(default=8000)
    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/sena_guias_db",
    )
    alembic_database_url: str = Field(
        default="postgresql+psycopg://postgres:postgres@localhost:5432/sena_guias_db",
    )
    cors_allow_origins: str = Field(default=DEFAULT_CORS_ALLOW_ORIGINS)
    storage_provider: str = Field(default="minio")
    storage_bucket_name: str = Field(default="sena-programa-documentos")
    storage_endpoint: str = Field(default="localhost:9000")
    storage_access_key: str = Field(default="admin")
    storage_secret_key: str = Field(default="admin123")
    storage_secure: bool = Field(default=False)
    storage_region: str | None = Field(default=None)

    @property
    def cors_allow_origin_list(self) -> list[str]:
        """Return CORS origins from a comma-separated environment value."""
        return [
            origin.strip()
            for origin in self.cors_allow_origins.split(",")
            if origin.strip()
        ]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached application settings."""
    return Settings()
