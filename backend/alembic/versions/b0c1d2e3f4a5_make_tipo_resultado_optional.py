"""make tipo_resultado optional

Revision ID: b0c1d2e3f4a5
Revises: f9a012b3c4d5
Create Date: 2026-08-21 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "b0c1d2e3f4a5"
down_revision: Union[str, Sequence[str], None] = "f9a012b3c4d5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Allow matrices to omit tipo_resultado without losing the row."""
    op.alter_column(
        "asignaciones_curriculares_proyecto",
        "tipo_resultado",
        existing_type=sa.String(length=50),
        nullable=True,
    )


def downgrade() -> None:
    """Restore the previous required-column contract."""
    op.alter_column(
        "asignaciones_curriculares_proyecto",
        "tipo_resultado",
        existing_type=sa.String(length=50),
        nullable=False,
    )
