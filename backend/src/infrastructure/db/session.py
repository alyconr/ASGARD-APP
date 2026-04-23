"""Database session helpers prepared for future tasks."""

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.infrastructure.config.settings import Settings, get_settings


def create_database_engine(settings: Settings | None = None) -> AsyncEngine:
    """Create an async SQLAlchemy engine from configured settings."""
    resolved_settings = settings or get_settings()

    return create_async_engine(
        resolved_settings.database_url,
        future=True,
        pool_pre_ping=True,
    )


async_engine = create_database_engine()
async_session_factory = async_sessionmaker(
    bind=async_engine,
    autoflush=False,
    expire_on_commit=False,
)


async def get_async_session() -> AsyncIterator[AsyncSession]:
    """Yield an async database session for request-scoped usage."""
    async with async_session_factory() as session:
        yield session
