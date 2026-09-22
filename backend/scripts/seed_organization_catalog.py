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
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.append(str(BACKEND_ROOT))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.db.models.organizacion import Coordinacion, Especialidad
from src.infrastructure.db.session import async_session_factory

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("seed_catalog")

DEFAULT_COORDINACIONES = [
    {
        "codigo": "TEL",
        "nombre": "TELEINFORMATICA E INDUSTRIAS CREATIVAS",
        "descripcion": "Coordinación de Teleinformática e Industrias Creativas",
    },
    {
        "codigo": "MER",
        "nombre": "MERCADEO",
        "descripcion": "Coordinación de Mercadeo y Ventas",
    },
    {
        "codigo": "LOG",
        "nombre": "LOGISTICA",
        "descripcion": "Coordinación de Logística y Transporte",
    },
    {
        "codigo": "TRA",
        "nombre": "TRANSVERSALES",
        "descripcion": "Coordinación de Formación Transversal",
    },
]

DEFAULT_ESPECIALIDADES = {
    "TEL": [
        {"codigo": "ADSO", "nombre": "ANALISIS Y DESARROLLO DE SOFTWARE"},
        {"codigo": "REDES", "nombre": "GESTIÓN DE REDES DE DATOS"},
        {"codigo": "DMGV", "nombre": "DESARROLLO DE MEDIOS GRÁFICOS VISUALES"},
        {"codigo": "A3D", "nombre": "ANIMACIÓN 3D"},
        {"codigo": "CSD", "nombre": "CONTROL DE LA SEGURIDAD DIGITAL"},
        {"codigo": "MEC", "nombre": "MANTENIMIENTO DE EQUIPOS DE CÓMPUTO"},
        {"codigo": "DVEI", "nombre": "DESARROLLO DE VIDEOJUEGOS Y ENTORNOS INTERACTIVOS"},
        {"codigo": "IITIC", "nombre": "IMPLEMENTACIÓN DE INFRAESTRUCTURA DE TECNOLOGÍAS DE LA INFORMACIÓN Y LAS COMUNICACIONES"},
        {"codigo": "PSMA", "nombre": "PRODUCCIÓN DE SONIDO PARA MEDIOS AUDIOVISUALES"},
    ],
    "MER": [
        {"codigo": "MEC-MER", "nombre": "MANTENIMIENTO DE EQUIPOS DE CÓMPUTO"},
        {"codigo": "ACOM", "nombre": "ASESORÍA COMERCIAL"},
        {"codigo": "OSOCC", "nombre": "OPERACIÓN DE SERVICIOS OMNICANAL EN CONTACT CENTER Y BPO"},
        {"codigo": "OCRET", "nombre": "OPERACIONES COMERCIALES EN RETAIL"},
        {"codigo": "VPL", "nombre": "VENTA DE PRODUCTOS EN LÍNEA"},
        {"codigo": "CCM", "nombre": "COMUNICACIÓN COMERCIAL Y MARKETING"},
        {"codigo": "SOBPO", "nombre": "SERVICE OPERATION IN BILINGUAL BPO CHANNELS 137500"},
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
            coordinacion.nombre = coord_data["nombre"]
            coordinacion.descripcion = coord_data["descripcion"]
            coordinacion.activo = True
            logger.info("Coordinación actualizada: %s - %s", coordinacion.codigo, coordinacion.nombre)

        # Seed specialties for this coordination if defined
        if coord_data["codigo"] in DEFAULT_ESPECIALIDADES:
            for esp_data in DEFAULT_ESPECIALIDADES[coord_data["codigo"]]:
                esp_stmt = select(Especialidad).where(
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
                    especialidad.coordinacion_id = coordinacion.id
                    especialidad.nombre = esp_data["nombre"]
                    especialidad.activo = True
                    logger.info("  Especialidad actualizada: %s - %s", especialidad.codigo, especialidad.nombre)

    await session.commit()
    logger.info("Seed de catálogo organizacional completado exitosamente.")


async def main() -> None:
    async with async_session_factory() as session:
        await seed_organization_catalog(session)


if __name__ == "__main__":
    asyncio.run(main())
