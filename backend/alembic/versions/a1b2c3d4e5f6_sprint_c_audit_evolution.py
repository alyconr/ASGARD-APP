"""Sprint C: Audit evolution (actor_usuario_id, referencia_id, audit indexes) and process query filter indexes.

Revision ID: a1b2c3d4e5f6
Revises: f4a5b6c7d8e9
Create Date: 2026-09-21 07:45:00
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "a1b2c3d4e5f6"
down_revision = "f4a5b6c7d8e9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Add structured actor and process reference columns to eventos_auditoria
    op.add_column(
        "eventos_auditoria",
        sa.Column(
            "actor_usuario_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("usuarios.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.add_column(
        "eventos_auditoria",
        sa.Column(
            "referencia_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
    )

    # 2. Add performance query indices to eventos_auditoria
    op.create_index("ix_eventos_auditoria_fecha_evento", "eventos_auditoria", ["fecha_evento"])
    op.create_index("ix_eventos_auditoria_accion", "eventos_auditoria", ["accion"])
    op.create_index("ix_eventos_auditoria_entidad", "eventos_auditoria", ["entidad"])
    op.create_index("ix_eventos_auditoria_actor_usuario_id", "eventos_auditoria", ["actor_usuario_id"])
    op.create_index("ix_eventos_auditoria_referencia_id", "eventos_auditoria", ["referencia_id"])

    # 3. Add optimization filter indices to procesos_curriculares
    op.create_index("ix_procesos_curriculares_coordinacion_id", "procesos_curriculares", ["coordinacion_id"])
    op.create_index("ix_procesos_curriculares_especialidad_id", "procesos_curriculares", ["especialidad_id"])
    op.create_index("ix_procesos_curriculares_programa_id", "procesos_curriculares", ["programa_id"])
    op.create_index("ix_procesos_curriculares_proyecto_id", "procesos_curriculares", ["proyecto_id"])


def downgrade() -> None:
    op.drop_index("ix_procesos_curriculares_proyecto_id", table_name="procesos_curriculares")
    op.drop_index("ix_procesos_curriculares_programa_id", table_name="procesos_curriculares")
    op.drop_index("ix_procesos_curriculares_especialidad_id", table_name="procesos_curriculares")
    op.drop_index("ix_procesos_curriculares_coordinacion_id", table_name="procesos_curriculares")

    op.drop_index("ix_eventos_auditoria_referencia_id", table_name="eventos_auditoria")
    op.drop_index("ix_eventos_auditoria_actor_usuario_id", table_name="eventos_auditoria")
    op.drop_index("ix_eventos_auditoria_entidad", table_name="eventos_auditoria")
    op.drop_index("ix_eventos_auditoria_accion", table_name="eventos_auditoria")
    op.drop_index("ix_eventos_auditoria_fecha_evento", table_name="eventos_auditoria")

    op.drop_column("eventos_auditoria", "referencia_id")
    op.drop_column("eventos_auditoria", "actor_usuario_id")
