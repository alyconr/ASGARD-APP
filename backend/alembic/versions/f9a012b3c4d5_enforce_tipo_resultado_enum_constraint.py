"""enforce tipo_resultado check constraint

Replaces check constraint asignacion_curricular_tipo_resultado_not_blank
with asignacion_curricular_tipo_resultado_enum requiring
tipo_resultado IN ('ESPECIFICO', 'TRANSVERSAL').

Revision ID: f9a012b3c4d5
Revises: e8f901a2b3c4
Create Date: 2026-08-12 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f9a012b3c4d5"
down_revision: Union[str, Sequence[str], None] = "e8f901a2b3c4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema: enforce strict enum values for tipo_resultado."""
    op.execute(
        "ALTER TABLE asignaciones_curriculares_proyecto "
        "DROP CONSTRAINT IF EXISTS ck_asignaciones_curriculares_proyecto_asignacion_curric_20e9;"
    )
    op.execute(
        "ALTER TABLE asignaciones_curriculares_proyecto "
        "DROP CONSTRAINT IF EXISTS asignacion_curricular_tipo_resultado_not_blank;"
    )
    op.execute(
        "ALTER TABLE asignaciones_curriculares_proyecto "
        "DROP CONSTRAINT IF EXISTS asignacion_curricular_tipo_resultado_enum;"
    )
    op.create_check_constraint(
        "asignacion_curricular_tipo_resultado_enum",
        "asignaciones_curriculares_proyecto",
        "tipo_resultado IN ('ESPECIFICO', 'TRANSVERSAL', 'BASICO')",
    )


def downgrade() -> None:
    """Downgrade schema: revert to non-blank check constraint."""
    op.drop_constraint(
        "asignacion_curricular_tipo_resultado_enum",
        "asignaciones_curriculares_proyecto",
        type_="check",
    )
    op.create_check_constraint(
        "asignacion_curricular_tipo_resultado_not_blank",
        "asignaciones_curriculares_proyecto",
        "btrim(tipo_resultado) <> ''",
    )
