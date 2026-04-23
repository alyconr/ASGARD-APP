"""Opt-in integration test for real PostgreSQL connectivity."""

import asyncio
import os

import pytest
from sqlalchemy import text

from src.infrastructure.config.settings import get_settings
from src.infrastructure.db.session import create_database_engine

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_DATABASE_TESTS") != "1",
    reason="Set RUN_DATABASE_TESTS=1 when local PostgreSQL is running.",
)


async def _select_one() -> int:
    """Execute SELECT 1 using the configured async SQLAlchemy engine."""
    engine = create_database_engine(get_settings())
    try:
        async with engine.connect() as connection:
            result = await connection.execute(text("SELECT 1"))
            return int(result.scalar_one())
    finally:
        await engine.dispose()


def test_database_select_one() -> None:
    """Verify the backend can connect to PostgreSQL and execute SELECT 1."""
    assert asyncio.run(_select_one()) == 1
