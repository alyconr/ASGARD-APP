"""Domain types for program PDF documents."""

from __future__ import annotations

from enum import Enum


class EstadoLegibilidadPdf(str, Enum):
    """Supported legibility states for TASK-06 PDF diagnosis."""

    LEGIBLE = "LEGIBLE"
    PARCIALMENTE_LEGIBLE = "PARCIALMENTE_LEGIBLE"
    NO_LEGIBLE = "NO_LEGIBLE"
