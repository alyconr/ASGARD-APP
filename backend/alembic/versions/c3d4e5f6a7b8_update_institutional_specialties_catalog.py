"""Update institutional specialties catalog for Teleinformatica e Industrias Creativas and Mercadeo.

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-09-22 12:40:00
"""

import uuid
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "c3d4e5f6a7b8"
down_revision = "b2c3d4e5f6a7"
branch_labels = None
depends_on = None

COORDINACIONES_SEED = [
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
]

ESPECIALIDADES_SEED = {
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


def upgrade() -> None:
    bind = op.get_bind()

    for coord_data in COORDINACIONES_SEED:
        # Check if coordinacion exists
        row = bind.execute(
            sa.text("SELECT id FROM coordinaciones WHERE codigo = :codigo"),
            {"codigo": coord_data["codigo"]},
        ).fetchone()

        if row is not None:
            coord_id = row[0]
            bind.execute(
                sa.text(
                    "UPDATE coordinaciones "
                    "SET nombre = :nombre, descripcion = :descripcion, activo = true, fecha_actualizacion = now() "
                    "WHERE id = :id"
                ),
                {
                    "id": coord_id,
                    "nombre": coord_data["nombre"],
                    "descripcion": coord_data["descripcion"],
                },
            )
        else:
            coord_id = str(uuid.uuid4())
            bind.execute(
                sa.text(
                    "INSERT INTO coordinaciones (id, codigo, nombre, descripcion, activo, fecha_creacion, fecha_actualizacion) "
                    "VALUES (:id, :codigo, :nombre, :descripcion, true, now(), now())"
                ),
                {
                    "id": coord_id,
                    "codigo": coord_data["codigo"],
                    "nombre": coord_data["nombre"],
                    "descripcion": coord_data["descripcion"],
                },
            )

        # Upsert specialties for this coordinacion
        if coord_data["codigo"] in ESPECIALIDADES_SEED:
            for esp_data in ESPECIALIDADES_SEED[coord_data["codigo"]]:
                esp_row = bind.execute(
                    sa.text("SELECT id FROM especialidades WHERE codigo = :codigo"),
                    {"codigo": esp_data["codigo"]},
                ).fetchone()

                if esp_row is not None:
                    bind.execute(
                        sa.text(
                            "UPDATE especialidades "
                            "SET nombre = :nombre, coordinacion_id = :coord_id, activo = true, fecha_actualizacion = now() "
                            "WHERE id = :id"
                        ),
                        {
                            "id": esp_row[0],
                            "coord_id": coord_id,
                            "nombre": esp_data["nombre"],
                        },
                    )
                else:
                    esp_id = str(uuid.uuid4())
                    bind.execute(
                        sa.text(
                            "INSERT INTO especialidades (id, coordinacion_id, codigo, nombre, activo, fecha_creacion, fecha_actualizacion) "
                            "VALUES (:id, :coord_id, :codigo, :nombre, true, now(), now())"
                        ),
                        {
                            "id": esp_id,
                            "coord_id": coord_id,
                            "codigo": esp_data["codigo"],
                            "nombre": esp_data["nombre"],
                        },
                    )


def downgrade() -> None:
    # Operational preservation: do not delete catalog entries that may have foreign keys
    pass
