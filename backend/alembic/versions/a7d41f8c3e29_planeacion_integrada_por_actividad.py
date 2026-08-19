"""planeacion integrada por actividad de aprendizaje

Crea la tabla asignaciones_curriculares_proyecto para materializar las
filas de la matriz Planeacion_Proyecto, convierte planeacion_resultados
en la fuente de verdad de los RAP y elimina la identidad singular por
resultado (resultado_id / competencia_id / uq_planeacion_proyecto_resultado).

Revision ID: a7d41f8c3e29
Revises: d4a9c1e7f205
Create Date: 2026-08-12 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a7d41f8c3e29"
down_revision: Union[str, Sequence[str], None] = "d4a9c1e7f205"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_UUID_PATTERN = (
    "^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}"
    "-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "asignaciones_curriculares_proyecto",
        sa.Column("proyecto_id", sa.UUID(), nullable=False),
        sa.Column("actividad_proyecto_id", sa.UUID(), nullable=False),
        sa.Column("competencia_id", sa.UUID(), nullable=False),
        sa.Column("resultado_id", sa.UUID(), nullable=True),
        sa.Column("tipo_resultado", sa.String(length=50), nullable=False),
        sa.Column("orden_resultado", sa.Integer(), nullable=True),
        sa.Column("pagina_origen", sa.String(length=100), nullable=True),
        sa.Column("observaciones", sa.Text(), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "fecha_creacion",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "fecha_actualizacion",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["actividad_proyecto_id"],
            ["actividades_proyecto.id"],
            name=op.f(
                "fk_asignaciones_curriculares_actividad_actividades_proyecto"
            ),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["competencia_id"],
            ["competencias.id"],
            name=op.f("fk_asignaciones_curriculares_competencia_competencias"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["proyecto_id"],
            ["proyectos_formativos.id"],
            name=op.f("fk_asignaciones_curriculares_proyecto_proyectos"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["resultado_id"],
            ["resultados_aprendizaje.id"],
            name=op.f(
                "fk_asignaciones_curriculares_resultado_resultados_aprendizaje"
            ),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "id", name=op.f("pk_asignaciones_curriculares_proyecto")
        ),
        sa.CheckConstraint(
            "btrim(tipo_resultado) <> ''",
            name="asignacion_curricular_tipo_resultado_not_blank",
        ),
    )
    op.create_index(
        "uq_asignacion_curricular_act_comp_rap",
        "asignaciones_curriculares_proyecto",
        ["actividad_proyecto_id", "competencia_id", "resultado_id"],
        unique=True,
        postgresql_where=sa.text("resultado_id IS NOT NULL"),
    )
    op.create_index(
        "uq_asignacion_curricular_act_comp_norap",
        "asignaciones_curriculares_proyecto",
        ["actividad_proyecto_id", "competencia_id"],
        unique=True,
        postgresql_where=sa.text("resultado_id IS NULL"),
    )
    op.create_index(
        "ix_asignaciones_curriculares_proyecto_id",
        "asignaciones_curriculares_proyecto",
        ["proyecto_id"],
        unique=False,
    )
    op.create_index(
        "ix_asignaciones_curriculares_actividad_id",
        "asignaciones_curriculares_proyecto",
        ["actividad_proyecto_id"],
        unique=False,
    )
    op.create_index(
        "ix_asignaciones_curriculares_competencia_id",
        "asignaciones_curriculares_proyecto",
        ["competencia_id"],
        unique=False,
    )
    op.create_index(
        "ix_asignaciones_curriculares_resultado_id",
        "asignaciones_curriculares_proyecto",
        ["resultado_id"],
        unique=False,
    )

    # Backfill: planeacion_resultados becomes the source of truth.
    op.execute(
        """
        INSERT INTO planeacion_resultados (planeacion_id, resultado_id)
        SELECT pp.id, pp.resultado_id
        FROM planeaciones_pedagogicas pp
        WHERE pp.resultado_id IS NOT NULL
        ON CONFLICT DO NOTHING
        """
    )

    # Backfill: recover phase/activity from the first stored assignment
    # for legacy rows that only kept the pair inside datos_complementarios.
    op.execute(
        f"""
        UPDATE planeaciones_pedagogicas
        SET fase_id = (
            datos_complementarios->'asignaciones_proyecto'->0->>'fase_id'
        )::uuid
        WHERE fase_id IS NULL
          AND jsonb_typeof(datos_complementarios->'asignaciones_proyecto')
              = 'array'
          AND datos_complementarios->'asignaciones_proyecto'->0->>'fase_id'
              ~ '{_UUID_PATTERN}'
        """
    )
    op.execute(
        f"""
        UPDATE planeaciones_pedagogicas
        SET actividad_id = (
            datos_complementarios->'asignaciones_proyecto'->0->>'actividad_id'
        )::uuid
        WHERE actividad_id IS NULL
          AND jsonb_typeof(datos_complementarios->'asignaciones_proyecto')
              = 'array'
          AND datos_complementarios->'asignaciones_proyecto'->0->>'actividad_id'
              ~ '{_UUID_PATTERN}'
        """
    )

    # Remove the singular-result identity.
    op.drop_constraint(
        "uq_planeacion_proyecto_resultado",
        "planeaciones_pedagogicas",
        type_="unique",
    )
    op.drop_index(
        "ix_planeaciones_pedagogicas_resultado_id",
        table_name="planeaciones_pedagogicas",
    )
    op.drop_index(
        "ix_planeaciones_pedagogicas_competencia_id",
        table_name="planeaciones_pedagogicas",
    )
    op.drop_constraint(
        "fk_planeaciones_pedagogicas_resultado_id_resultados_aprendizaje",
        "planeaciones_pedagogicas",
        type_="foreignkey",
    )
    op.drop_constraint(
        "fk_planeaciones_pedagogicas_competencia_id_competencias",
        "planeaciones_pedagogicas",
        type_="foreignkey",
    )
    op.drop_column("planeaciones_pedagogicas", "resultado_id")
    op.drop_column("planeaciones_pedagogicas", "competencia_id")

    # One integrated planning per project activity.
    op.create_index(
        "uq_planeacion_proyecto_actividad",
        "planeaciones_pedagogicas",
        ["proyecto_id", "actividad_id"],
        unique=True,
        postgresql_where=sa.text("actividad_id IS NOT NULL"),
    )
    op.create_index(
        "ix_planeaciones_pedagogicas_actividad_id",
        "planeaciones_pedagogicas",
        ["actividad_id"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        "ix_planeaciones_pedagogicas_actividad_id",
        table_name="planeaciones_pedagogicas",
    )
    op.drop_index(
        "uq_planeacion_proyecto_actividad",
        table_name="planeaciones_pedagogicas",
    )

    op.add_column(
        "planeaciones_pedagogicas",
        sa.Column("competencia_id", sa.UUID(), nullable=True),
    )
    op.add_column(
        "planeaciones_pedagogicas",
        sa.Column("resultado_id", sa.UUID(), nullable=True),
    )
    op.execute(
        """
        UPDATE planeaciones_pedagogicas pp
        SET resultado_id = pr.resultado_id
        FROM (
            SELECT DISTINCT ON (planeacion_id) planeacion_id, resultado_id
            FROM planeacion_resultados
            ORDER BY planeacion_id, resultado_id
        ) pr
        WHERE pp.id = pr.planeacion_id
        """
    )
    op.execute(
        """
        UPDATE planeaciones_pedagogicas pp
        SET resultado_id = rap.resultado_id
        FROM (
            SELECT DISTINCT ON (competencia_id) competencia_id, id AS resultado_id
            FROM resultados_aprendizaje
            ORDER BY competencia_id, orden NULLS LAST, id
        ) rap
        WHERE pp.resultado_id IS NULL
          AND pp.competencia_id = rap.competencia_id
        """
    )
    op.execute(
        """
        UPDATE planeaciones_pedagogicas pp
        SET competencia_id = ra.competencia_id
        FROM resultados_aprendizaje ra
        WHERE pp.resultado_id = ra.id
          AND pp.competencia_id IS NULL
        """
    )
    op.execute(
        """
        DELETE FROM planeaciones_pedagogicas
        WHERE resultado_id IS NULL OR competencia_id IS NULL
        """
    )
    op.alter_column(
        "planeaciones_pedagogicas", "resultado_id", nullable=False
    )
    op.alter_column(
        "planeaciones_pedagogicas", "competencia_id", nullable=False
    )
    op.create_foreign_key(
        "fk_planeaciones_pedagogicas_resultado_id_resultados_aprendizaje",
        "planeaciones_pedagogicas",
        "resultados_aprendizaje",
        ["resultado_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_planeaciones_pedagogicas_competencia_id_competencias",
        "planeaciones_pedagogicas",
        "competencias",
        ["competencia_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index(
        "ix_planeaciones_pedagogicas_resultado_id",
        "planeaciones_pedagogicas",
        ["resultado_id"],
        unique=False,
    )
    op.create_index(
        "ix_planeaciones_pedagogicas_competencia_id",
        "planeaciones_pedagogicas",
        ["competencia_id"],
        unique=False,
    )
    op.create_unique_constraint(
        "uq_planeacion_proyecto_resultado",
        "planeaciones_pedagogicas",
        ["proyecto_id", "resultado_id"],
    )

    op.drop_index(
        "ix_asignaciones_curriculares_resultado_id",
        table_name="asignaciones_curriculares_proyecto",
    )
    op.drop_index(
        "ix_asignaciones_curriculares_competencia_id",
        table_name="asignaciones_curriculares_proyecto",
    )
    op.drop_index(
        "ix_asignaciones_curriculares_actividad_id",
        table_name="asignaciones_curriculares_proyecto",
    )
    op.drop_index(
        "ix_asignaciones_curriculares_proyecto_id",
        table_name="asignaciones_curriculares_proyecto",
    )
    op.drop_index(
        "uq_asignacion_curricular_act_comp_norap",
        table_name="asignaciones_curriculares_proyecto",
    )
    op.drop_index(
        "uq_asignacion_curricular_act_comp_rap",
        table_name="asignaciones_curriculares_proyecto",
    )
    op.drop_table("asignaciones_curriculares_proyecto")
