"""Domain types and validations for draft persistence."""

from __future__ import annotations

from enum import Enum

from src.domain.shared.enums import EstadoBloque


class TipoBloqueBorrador(str, Enum):
    """Supported draft blocks for Phase 1 flows."""

    PROGRAMA = "PROGRAMA"
    PROYECTO = "PROYECTO"


ALLOWED_DRAFT_STATES: dict[TipoBloqueBorrador, set[EstadoBloque]] = {
    TipoBloqueBorrador.PROGRAMA: {
        EstadoBloque.BORRADOR,
        EstadoBloque.EN_REVISION,
        EstadoBloque.COMPLETO,
    },
    TipoBloqueBorrador.PROYECTO: {
        EstadoBloque.BLOQUEADO,
        EstadoBloque.BORRADOR,
        EstadoBloque.EN_REVISION,
    },
}


def validate_draft_state(
    tipo_bloque: TipoBloqueBorrador,
    estado_borrador: EstadoBloque,
) -> None:
    """Ensure the stored draft state stays within TASK-03 scope."""

    if estado_borrador not in ALLOWED_DRAFT_STATES[tipo_bloque]:
        raise ValueError(
            "estado_borrador no es valido para el tipo_bloque solicitado",
        )
