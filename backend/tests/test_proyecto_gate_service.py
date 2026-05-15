"""Unit tests for TASK-15 project blocking and unblocking gate."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest

from src.application.services.proyecto_gate import (
    ProyectoBloqueadoError,
    ProyectoGateService,
)
from src.domain.drafts.types import TipoBloqueBorrador
from src.domain.shared.enums import EstadoBloque, TipoFuenteCargue
from src.infrastructure.db.models.curriculum import ProgramaFormacion
from src.infrastructure.db.models.drafts import BorradorSesion


class FakeDraftRepository:
    """In-memory program draft repository."""

    def __init__(self, draft: BorradorSesion) -> None:
        """Store a single draft."""
        self.draft = draft

    async def get_by_block_reference(
        self,
        tipo_bloque: TipoBloqueBorrador,
        referencia_id: uuid.UUID,
    ) -> BorradorSesion | None:
        """Return the stored draft when the logical key matches."""
        if (
            tipo_bloque is TipoBloqueBorrador.PROGRAMA
            and self.draft.referencia_id == referencia_id
        ):
            return self.draft
        return None


class FakeProyectoGateRepository:
    """In-memory program state repository."""

    def __init__(self, programa: ProgramaFormacion | None) -> None:
        """Store the program aggregate."""
        self.programa = programa

    async def get_programa(self, programa_id: uuid.UUID) -> ProgramaFormacion | None:
        """Return the program when ids match."""
        if self.programa is None or self.programa.id != programa_id:
            return None
        return self.programa


def build_programa(estado: EstadoBloque) -> ProgramaFormacion:
    """Create a program with a configurable state."""
    now = datetime.now(UTC)
    programa = ProgramaFormacion(
        codigo_programa="228118",
        nombre_programa="Analisis y desarrollo de software",
        version_programa=None,
        estado=estado,
        fuente_cargue=TipoFuenteCargue.MIXTO,
    )
    programa.id = uuid.uuid4()
    programa.fecha_creacion = now
    programa.fecha_actualizacion = now
    return programa


def build_draft(
    referencia_id: uuid.UUID,
    programa_id: uuid.UUID | None,
    estado: EstadoBloque,
) -> BorradorSesion:
    """Create a program draft with the current persisted block state."""
    draft = BorradorSesion(
        tipo_bloque=TipoBloqueBorrador.PROGRAMA.value,
        referencia_id=referencia_id,
        paso_actual="revision-programa",
        payload_json={
            "meta": {"referenciaId": str(referencia_id)},
            "curricular": {
                "programa_formacion_id": str(programa_id) if programa_id else None,
            },
        },
        estado_borrador=estado,
    )
    draft.id = uuid.uuid4()
    draft.ultima_edicion = datetime.now(UTC)
    return draft


def build_service(
    programa: ProgramaFormacion | None,
    *,
    draft_estado: EstadoBloque = EstadoBloque.BORRADOR,
) -> tuple[ProyectoGateService, BorradorSesion]:
    """Build the gate service with fake dependencies."""
    referencia_id = uuid.uuid4()
    draft = build_draft(
        referencia_id,
        programa.id if programa is not None else None,
        draft_estado,
    )
    service = ProyectoGateService(
        draft_repository=FakeDraftRepository(draft),
        proyecto_repository=FakeProyectoGateRepository(programa),
    )
    return service, draft


@pytest.mark.anyio
async def test_programa_incompleto_bloquea_proyecto() -> None:
    """A non-complete program should keep the project blocked."""
    programa = build_programa(EstadoBloque.EN_REVISION)
    service, draft = build_service(programa, draft_estado=EstadoBloque.EN_REVISION)

    result = await service.consultar_disponibilidad(draft.referencia_id)

    assert result.programa_completo is False
    assert result.proyecto_bloqueado is True
    assert result.estado_proyecto is EstadoBloque.BLOQUEADO
    assert result.motivo == "PROGRAMA_NO_COMPLETO"
    assert "bloqueado" in result.mensaje


@pytest.mark.anyio
async def test_programa_completo_habilita_proyecto() -> None:
    """A complete program should unlock the project module."""
    programa = build_programa(EstadoBloque.COMPLETO)
    service, draft = build_service(programa, draft_estado=EstadoBloque.COMPLETO)

    result = await service.consultar_disponibilidad(draft.referencia_id)

    assert result.programa_completo is True
    assert result.proyecto_bloqueado is False
    assert result.estado_proyecto is EstadoBloque.BORRADOR
    assert result.motivo is None
    assert result.accion_sugerida == "iniciar_proyecto"


@pytest.mark.anyio
async def test_acceso_indebido_rechaza_backend_si_programa_incompleto() -> None:
    """The backend guard should reject project access while blocked."""
    programa = build_programa(EstadoBloque.BORRADOR)
    service, draft = build_service(programa)

    with pytest.raises(ProyectoBloqueadoError) as exc_info:
        await service.validar_acceso(draft.referencia_id)

    assert exc_info.value.disponibilidad.proyecto_bloqueado is True
    assert exc_info.value.disponibilidad.programa_completo is False


@pytest.mark.anyio
async def test_respuesta_estructurada_incluye_mensaje_de_bloqueo() -> None:
    """The gate should return useful context for the UI, not only a boolean."""
    service, draft = build_service(None)

    result = await service.consultar_disponibilidad(draft.referencia_id)

    assert result.programa_completo is False
    assert result.proyecto_bloqueado is True
    assert result.estado_programa is EstadoBloque.BORRADOR
    assert result.mensaje
    assert result.accion_sugerida == "completar_y_cerrar_programa"
