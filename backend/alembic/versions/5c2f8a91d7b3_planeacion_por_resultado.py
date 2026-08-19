"""planeacion_por_resultado

Revision ID: 5c2f8a91d7b3
Revises: 1ea7505db4e4
Create Date: 2026-06-06 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "5c2f8a91d7b3"
down_revision: Union[str, Sequence[str], None] = "1ea7505db4e4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
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
    op.alter_column("planeaciones_pedagogicas", "resultado_id", nullable=False)
    op.create_foreign_key(
        op.f("fk_planeaciones_pedagogicas_resultado_id_resultados_aprendizaje"),
        "planeaciones_pedagogicas",
        "resultados_aprendizaje",
        ["resultado_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.drop_constraint(
        "uq_planeacion_proyecto_competencia",
        "planeaciones_pedagogicas",
        type_="unique",
    )
    op.create_unique_constraint(
        "uq_planeacion_proyecto_resultado",
        "planeaciones_pedagogicas",
        ["proyecto_id", "resultado_id"],
    )
    op.create_index(
        "ix_planeaciones_pedagogicas_resultado_id",
        "planeaciones_pedagogicas",
        ["resultado_id"],
        unique=False,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        "ix_planeaciones_pedagogicas_resultado_id",
        table_name="planeaciones_pedagogicas",
    )
    op.drop_constraint(
        "uq_planeacion_proyecto_resultado",
        "planeaciones_pedagogicas",
        type_="unique",
    )
    op.create_unique_constraint(
        "uq_planeacion_proyecto_competencia",
        "planeaciones_pedagogicas",
        ["proyecto_id", "competencia_id"],
    )
    op.drop_constraint(
        op.f("fk_planeaciones_pedagogicas_resultado_id_resultados_aprendizaje"),
        "planeaciones_pedagogicas",
        type_="foreignkey",
    )
    op.drop_column("planeaciones_pedagogicas", "resultado_id")
