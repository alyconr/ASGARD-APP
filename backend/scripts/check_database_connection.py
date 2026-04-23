"""Verify PostgreSQL connectivity with a real SELECT 1 query."""

import asyncio
import sys
from pathlib import Path

from sqlalchemy import text

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.append(str(BACKEND_ROOT))

from src.infrastructure.config.settings import get_settings  # noqa: E402
from src.infrastructure.db.session import create_database_engine  # noqa: E402


async def check_database_connection() -> int:
    """Run a minimal query against the configured PostgreSQL database."""
    engine = create_database_engine(get_settings())
    try:
        async with engine.connect() as connection:
            result = await connection.execute(text("SELECT 1"))
            return int(result.scalar_one())
    finally:
        await engine.dispose()


def main() -> None:
    """Print the result of the database connectivity check."""
    result = asyncio.run(check_database_connection())
    print(f"Database connection OK: SELECT 1 returned {result}")


if __name__ == "__main__":
    main()
