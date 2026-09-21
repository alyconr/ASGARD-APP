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
    jwt_secret_key: str = Field(default="asgard-super-secret-key-change-in-production-2026")
    jwt_algorithm: str = Field(default="HS256")
    jwt_access_token_expire_minutes: int = Field(default=480)
    jwt_refresh_token_expire_days: int = Field(default=7)

    auth_cookie_name: str = Field(default="asgard_refresh_token")
    auth_cookie_secure: bool | None = Field(default=None)
    auth_cookie_samesite: str = Field(default="lax")
    auth_cookie_domain: str | None = Field(default=None)
    auth_cookie_path: str = Field(default="/api/v1/auth")

    @property
    def is_production(self) -> bool:
        """Return whether application is running in production or staging environment."""
        return self.app_env.lower() in ("production", "prod", "staging")

    @property
    def effective_cookie_secure(self) -> bool:
        """Determine if refresh cookie must be marked Secure."""
        if self.auth_cookie_secure is not None:
            return self.auth_cookie_secure
        return self.is_production

    @property
    def cors_allow_origin_list(self) -> list[str]:
        """Return CORS origins excluding dangerous wildcard '*' with credentials."""
        return [
            origin.strip()
            for origin in self.cors_allow_origins.split(",")
            if origin.strip() and origin.strip() != "*"
        ]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached application settings."""
    return Settings()
