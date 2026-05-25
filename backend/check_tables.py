import asyncio

import asyncpg

DB_URL = "postgresql://postgres:postgres@localhost:5432/sena_guias_db"


async def check():
    conn = await asyncpg.connect(DB_URL)
    rows = await conn.fetch(
        """
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public'
        ORDER BY table_name
        """,
    )
    for table in rows:
        print(table[0])
    await conn.close()


asyncio.run(check())
