"""Tests for manual reconciliation of Excel pending curricular rows."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest

from src.application.dto.pendientes_curriculares import (
    PendienteCurricularAsignacionDTO,
)
from src.application.services.pendientes_curriculares import (
    PendientesCurricularesService,
)
from src.domain.drafts.types import TipoBloqueBorrador
from src.domain.shared.enums import (
    EstadoBloque,
    EstadoCampo,
    EstadoConciliacionPendiente,
    MotivoPendienteAsignacion,
    TipoConocimiento,
    TipoElementoCurricularPendiente,
)
from src.infrastructure.db.models.curriculum import (
    Competencia,
    Conocimiento,
    CriterioEvaluacion,
    ElementoCurricularPendiente,
    ProgramaFormacion,
    ResultadoAprendizaje,
)
from src.infrastructure.db.models.drafts import BorradorSesion


class FakeSession:
    """Minimal async session double."""

    def __init__(self) -> None:
        self.commits = 0

    async def commit(self) -> None:
        self.commits += 1

    async def refresh(self, instance: object) -> None:
        now = datetime.now(UTC)
        if hasattr(instance, "id") and getattr(instance, "id", None) is None:
            setattr(instance, "id", uuid.uuid4())
        if hasattr(instance, "fecha_creacion"):
            setattr(instance, "fecha_creacion", now)
        if hasattr(instance, "fecha_actualizacion"):
            setattr(instance, "fecha_actualizacion", now)


class FakeDraftRepository:
    """Single-draft repository."""

    def __init__(self, draft: BorradorSesion) -> None:
        self.draft = draft

    async def get_by_block_reference(
        self,
        tipo_bloque: TipoBloqueBorrador,
        referencia_id: uuid.UUID,
    ) -> BorradorSesion | None:
        if (
            tipo_bloque is TipoBloqueBorrador.PROGRAMA
            and referencia_id == self.draft.referencia_id
        ):
            return self.draft
        return None


class FakeAuditRepository:
    """Collect audit events."""

    def __init__(self) -> None:
        self.events: list[dict[str, object]] = []

    async def add_event(
        self,
        entidad: str,
        entidad_id: uuid.UUID,
        accion: str,
        detalle: dict[str, object] | None = None,
    ) -> object:
        event = {
            "entidad": entidad,
            "entidad_id": entidad_id,
            "accion": accion,
            "detalle": detalle or {},
        }
        self.events.append(event)
        return event


class FakePendientesRepository:
    """In-memory pending reconciliation repository."""

    def __init__(self) -> None:
        self.programa = ProgramaFormacion(
            codigo_programa="228118",
            nombre_programa="ADSO",
            version_programa="1",
        )
        self.programa.id = uuid.uuid4()
        self.competencia = Competencia(
            programa_id=self.programa.id,
            codigo_competencia="220501046",
            nombre_competencia="Desarrollar software",
            estado=EstadoBloque.BORRADOR,
            origen_campo=EstadoCampo.VALIDADO,
        )
        self.competencia.id = uuid.uuid4()
        self.resultado = ResultadoAprendizaje(
            competencia_id=self.competencia.id,
            codigo_resultado="RAP-1",
            descripcion="Construye componentes",
            estado=EstadoCampo.VALIDADO,
        )
        self.resultado.id = uuid.uuid4()
        self.pendientes: dict[uuid.UUID, ElementoCurricularPendiente] = {}
        self.conocimientos: dict[uuid.UUID, Conocimiento] = {}
        self.criterios: dict[uuid.UUID, CriterioEvaluacion] = {}

    async def list_by_reference(
        self,
        referencia_id: uuid.UUID,
    ) -> list[ElementoCurricularPendiente]:
        return [
            item
            for item in self.pendientes.values()
            if item.referencia_id == referencia_id
        ]

    async def get_by_id(
        self,
        referencia_id: uuid.UUID,
        pendiente_id: uuid.UUID,
    ) -> ElementoCurricularPendiente | None:
        item = self.pendientes.get(pendiente_id)
        if item is None or item.referencia_id != referencia_id:
            return None
        return item

    async def get_competencia(
        self,
        competencia_id: uuid.UUID,
        programa_id: uuid.UUID,
    ) -> Competencia | None:
        if (
            self.competencia.id == competencia_id
            and self.competencia.programa_id == programa_id
        ):
            return self.competencia
        return None

    async def get_resultado(
        self,
        resultado_id: uuid.UUID,
        competencia_id: uuid.UUID,
    ) -> ResultadoAprendizaje | None:
        if (
            self.resultado.id == resultado_id
            and self.resultado.competencia_id == competencia_id
        ):
            return self.resultado
        return None

    async def conocimiento_exists(
        self,
        *,
        competencia_id: uuid.UUID,
        tipo: TipoConocimiento,
        descripcion: str,
        resultado_id: uuid.UUID | None,
    ) -> bool:
        return any(
            item.competencia_id == competencia_id
            and item.tipo == tipo
            and item.descripcion.lower() == descripcion.lower()
            and item.resultado_id == resultado_id
            for item in self.conocimientos.values()
        )

    async def criterio_exists(
        self,
        *,
        competencia_id: uuid.UUID,
        descripcion: str,
        resultado_id: uuid.UUID | None,
    ) -> bool:
        return any(
            item.competencia_id == competencia_id
            and item.descripcion.lower() == descripcion.lower()
            and item.resultado_id == resultado_id
            for item in self.criterios.values()
        )

    async def add_conocimiento(
        self,
        *,
        competencia_id: uuid.UUID,
        resultado_id: uuid.UUID | None,
        tipo: TipoConocimiento,
        descripcion: str,
        orden: int | None,
    ) -> Conocimiento:
        item = Conocimiento(
            competencia_id=competencia_id,
            resultado_id=resultado_id,
            tipo=tipo,
            descripcion=descripcion,
            orden=orden,
            estado=EstadoCampo.VALIDADO,
        )
        item.id = uuid.uuid4()
        self.conocimientos[item.id] = item
        return item

    async def add_criterio(
        self,
        *,
        competencia_id: uuid.UUID,
        resultado_id: uuid.UUID | None,
        descripcion: str,
        orden: int | None,
    ) -> CriterioEvaluacion:
        item = CriterioEvaluacion(
            competencia_id=competencia_id,
            resultado_id=resultado_id,
            descripcion=descripcion,
            orden=orden,
            estado=EstadoCampo.VALIDADO,
        )
        item.id = uuid.uuid4()
        self.criterios[item.id] = item
        return item

    async def save(
        self,
        pendiente: ElementoCurricularPendiente,
    ) -> ElementoCurricularPendiente:
        self.pendientes[pendiente.id] = pendiente
        return pendiente

    def add_pending(
        self,
        referencia_id: uuid.UUID,
        tipo_elemento: TipoElementoCurricularPendiente,
    ) -> ElementoCurricularPendiente:
        item = ElementoCurricularPendiente(
            referencia_id=referencia_id,
            programa_id=self.programa.id,
            tipo_elemento=tipo_elemento,
            tipo_conocimiento=TipoConocimiento.SABER
            if tipo_elemento == TipoElementoCurricularPendiente.CONOCIMIENTO
            else None,
            descripcion="Elemento pendiente",
            competencia_id_origen_excel=None,
            rap_id_origen_excel=None,
            motivo=MotivoPendienteAsignacion.RESULTADO_NO_IDENTIFICADO,
            estado=EstadoConciliacionPendiente.PENDIENTE,
            orden=1,
        )
        item.id = uuid.uuid4()
        now = datetime.now(UTC)
        item.fecha_creacion = now
        item.fecha_actualizacion = now
        self.pendientes[item.id] = item
        return item


def build_service() -> tuple[
    PendientesCurricularesService,
    FakeSession,
    FakePendientesRepository,
    BorradorSesion,
]:
    referencia_id = uuid.uuid4()
    repo = FakePendientesRepository()
    draft = BorradorSesion(
        tipo_bloque=TipoBloqueBorrador.PROGRAMA.value,
        referencia_id=referencia_id,
        paso_actual="estructura-curricular",
        payload_json={
            "curricular": {
                "programa_formacion_id": str(repo.programa.id),
                "competencias": [],
            },
        },
        estado_borrador=EstadoBloque.BORRADOR,
    )
    draft.id = uuid.uuid4()
    draft.ultima_edicion = datetime.now(UTC)
    session = FakeSession()
    service = PendientesCurricularesService(
        session=session,
        pending_repository=repo,
        draft_repository=FakeDraftRepository(draft),
        audit_repository=FakeAuditRepository(),
    )
    return service, session, repo, draft


@pytest.mark.anyio
async def test_assigns_pending_conocimiento() -> None:
    """A pending knowledge row can be assigned manually."""
    service, session, repo, draft = build_service()
    pending = repo.add_pending(
        draft.referencia_id,
        TipoElementoCurricularPendiente.CONOCIMIENTO,
    )

    result = await service.asignar_pendiente(
        draft.referencia_id,
        pending.id,
        PendienteCurricularAsignacionDTO(
            competencia_id=repo.competencia.id,
            resultado_id=repo.resultado.id,
        ),
    )

    assert result.pendiente.estado is EstadoConciliacionPendiente.ASIGNADO
    assert len(repo.conocimientos) == 1
    assert next(iter(repo.conocimientos.values())).resultado_id == repo.resultado.id
    assert session.commits == 1


@pytest.mark.anyio
async def test_assigns_pending_criterio() -> None:
    """A pending criterion row can be assigned manually."""
    service, session, repo, draft = build_service()
    pending = repo.add_pending(
        draft.referencia_id,
        TipoElementoCurricularPendiente.CRITERIO,
    )

    result = await service.asignar_pendiente(
        draft.referencia_id,
        pending.id,
        PendienteCurricularAsignacionDTO(
            competencia_id=repo.competencia.id,
            resultado_id=repo.resultado.id,
        ),
    )

    assert result.pendiente.estado is EstadoConciliacionPendiente.ASIGNADO
    assert len(repo.criterios) == 1
    assert next(iter(repo.criterios.values())).resultado_id == repo.resultado.id
    assert session.commits == 1
