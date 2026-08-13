"""allow multiple planeaciones per actividad de proyecto

Elimina el indice unico uq_planeacion_proyecto_actividad para permitir
1..N Actividades de Aprendizaje / Planeaciones Pedagogicas dentro de una
misma Actividad de Proyecto. Preserva todas las relaciones M2M y datos existentes.

Revision ID: e8f901a2b3c4
Revises: a7d41f8c3e29
Create Date: 2026-08-12 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e8f901a2b3c4"
down_revision: Union[str, Sequence[str], None] = "a7d41f8c3e29"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema: drop unique constraint on (proyecto_id, actividad_id)."""
    op.drop_index(
        "uq_planeacion_proyecto_actividad",
        table_name="planeaciones_pedagogicas",
        if_exists=True,
    )


def downgrade() -> None:
    """Downgrade schema safely.

    Nota: No recreamos automaticamente UQ(proyecto_id, actividad_id) en
    downgrade si ya existen multiples planeaciones para una misma actividad.
    Recrear la restriccion causaria fallo de migracion y perdida de datos si
    no se borran registros voluntariamente.
    """
    raise RuntimeError(
        "No es posible revertir la migración e8f901a2b3c4 sin riesgo de "
        "pérdida de datos si existen múltiples planeaciones por actividad."
    )
