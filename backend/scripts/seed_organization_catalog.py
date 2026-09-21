"""Seed script for ASGARD institutional organization catalog.

Idempotently configures default SENA academic coordinations and specialties.
Coordinations:
- TEL: TELEINFORMATICA
- CRE: INDUSTRIAS CREATIVAS
- LOG: LOGISTICA
- MER: MERCADEO
- TRA: TRANSVERSALES

Specialties under TELEINFORMATICA:
- REDES: REDES DE DATOS
- ADSO: ANALISIS Y DESARROLLO DE SOFTWARE
"""

from __future__ import annotations

import asyncio
import logging
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.db.models.organizacion import Coordinacion, Especialidad
from src.infrastructure.db.session import async_session_factory

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("seed_catalog")

DEFAULT_COORDINACIONES = [
    {"codigo": "TEL", "nombre": "TELEINFORMATICA", "descripcion": "Coordinación de Teleinformática"},
    {"codigo": "CRE", "nombre": "INDUSTRIAS CREATIVAS", "descripcion": "Coordinación de Industrias Creativas"},
    {"codigo": "LOG", "nombre": "LOGISTICA", "descripcion": "Coordinación de Logística y Transporte"},
    {"codigo": "MER", "nombre": "MERCADEO", "descripcion": "Coordinación de Mercadeo y Ventas"},
    {"codigo": "TRA", "nombre": "TRANSVERSALES", "descripcion": "Coordinación de Formación Transversal"},
]

DEFAULT_ESPECIALIDADES = {
    "TEL": [
        {"codigo": "REDES", "nombre": "REDES DE DATOS"},
        {"codigo": "ADSO", "nombre": "ANALISIS Y DESARROLLO DE SOFTWARE"},
    ],
}


async def seed_organization_catalog(session: AsyncSession) -> None:
    """Idempotently populate coordinations and specialties."""
    for coord_data in DEFAULT_COORDINACIONES:
        stmt = select(Coordinacion).where(Coordinacion.codigo == coord_data["codigo"])
        res = await session.execute(stmt)
        coordinacion = res.scalar_one_or_none()

        if coordinacion is None:
            coordinacion = Coordinacion(
                codigo=coord_data["codigo"],
                nombre=coord_data["nombre"],
                descripcion=coord_data["descripcion"],
                activo=True,
            )
            session.add(coordinacion)
            await session.flush()
            logger.info("Coordinación creada: %s - %s", coordinacion.codigo, coordinacion.nombre)
        else:
            logger.info("Coordinación ya existe: %s - %s", coordinacion.codigo, coordinacion.nombre)

        # Seed specialties for this coordination if defined
        if coord_data["codigo"] in DEFAULT_ESPECIALIDADES:
            for esp_data in DEFAULT_ESPECIALIDADES[coord_data["codigo"]]:
                esp_stmt = select(Especialidad).where(
                    Especialidad.coordinacion_id == coordinacion.id,
                    Especialidad.codigo == esp_data["codigo"],
                )
                esp_res = await session.execute(esp_stmt)
                especialidad = esp_res.scalar_one_or_none()

                if especialidad is None:
                    especialidad = Especialidad(
                        coordinacion_id=coordinacion.id,
                        codigo=esp_data["codigo"],
                        nombre=esp_data["nombre"],
                        activo=True,
                    )
                    session.add(especialidad)
                    await session.flush()
                    logger.info("  Especialidad creada: %s - %s", especialidad.codigo, especialidad.nombre)
                else:
                    logger.info("  Especialidad ya existe: %s - %s", especialidad.codigo, especialidad.nombre)

    await session.commit()
    logger.info("Seed de catálogo organizacional completado exitosamente.")


async def main() -> None:
    async with async_session_factory() as session:
        await seed_organization_catalog(session)


if __name__ == "__main__":
    asyncio.run(main())
