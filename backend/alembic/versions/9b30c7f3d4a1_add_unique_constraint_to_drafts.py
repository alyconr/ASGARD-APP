"""add unique constraint to logical drafts

Revision ID: 9b30c7f3d4a1
Revises: 61df9cc6b86d
Create Date: 2026-04-25 09:25:00.000000

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "9b30c7f3d4a1"
down_revision: Union[str, Sequence[str], None] = "61df9cc6b86d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_unique_constraint(
        "uq_borradores_sesion_tipo_bloque_referencia_id",
        "borradores_sesion",
        ["tipo_bloque", "referencia_id"],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(
        "uq_borradores_sesion_tipo_bloque_referencia_id",
        "borradores_sesion",
        type_="unique",
    )
