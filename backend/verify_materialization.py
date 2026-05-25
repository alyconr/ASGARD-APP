import asyncio

import asyncpg

DB_URL = "postgresql://postgres:postgres@localhost:5432/sena_guias_db"


async def check():
    conn = await asyncpg.connect(DB_URL)

    resultados = await conn.fetch("SELECT COUNT(*) FROM resultados_aprendizaje")
    print("Resultados:", resultados[0][0])

    conocimientos = await conn.fetch("SELECT COUNT(*) FROM conocimientos")
    print("Conocimientos:", conocimientos[0][0])

    criterios = await conn.fetch("SELECT COUNT(*) FROM criterios_evaluacion")
    print("Criterios:", criterios[0][0])

    programa = await conn.fetch(
        "SELECT estado, fuente_cargue FROM programas_formacion LIMIT 1",
    )
    print(
        "\nPrograma estado:",
        programa[0]["estado"],
        "| fuente:",
        programa[0]["fuente_cargue"],
    )

    await conn.close()


asyncio.run(check())
