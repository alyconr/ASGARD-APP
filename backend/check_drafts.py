import asyncio

import asyncpg

DB_URL = "postgresql://postgres:postgres@localhost:5432/sena_guias_db"


async def check():
    conn = await asyncpg.connect(DB_URL)
    drafts = await conn.fetch(
        """
        SELECT id, tipo_bloque, estado_borrador, referencia_id
        FROM borradores_sesion
        ORDER BY ultima_edicion DESC
        LIMIT 5
        """,
    )
    for d in drafts:
        print(
            f'{d["tipo_bloque"]}: '
            f'{d["referencia_id"]} - {d["estado_borrador"]}',
        )
    total = await conn.fetchval("SELECT COUNT(*) FROM borradores_sesion")
    print(f"\nTotal drafts: {total}")
    await conn.close()


asyncio.run(check())
