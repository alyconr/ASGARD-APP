"""Unit tests for project completion validation and explicit closing."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest

from src.application.services.proyecto_cierre import (
    ProyectoCierreService,
    ProyectoCierreValidationError,
)
from src.domain.drafts.types import TipoBloqueBorrador
from src.domain.shared.enums import EstadoBloque, TipoFuenteCargue
from src.infrastructure.db.models.curriculum import ProgramaFormacion
from src.infrastructure.db.models.drafts import BorradorSesion
from src.infrastructure.db.models.proyecto import (
    ActividadProyecto,
    FaseProyecto,
    ProyectoFormativo,
)


class FakeSession:
    """Tiny async session stand-in for service tests."""

    def __init__(self) -> None:
        """Track transaction operations."""
        self.committed = False
        self.refreshed: list[object] = []

    async def commit(self) -> None:
        """Mark the transaction as committed."""
        self.committed = True

    async def refresh(self, instance: object) -> None:
        """Track refreshed ORM instances."""
        self.refreshed.append(instance)


class FakeDraftRepository:
    """In-memory draft repository."""

    def __init__(self, draft: BorradorSesion) -> None:
        """Store a single project draft."""
        self.draft = draft
        self.saved: list[BorradorSesion] = []

    async def get_by_block_reference(
        self,
        tipo_bloque: TipoBloqueBorrador,
        referencia_id: uuid.UUID,
    ) -> BorradorSesion | None:
        """Return the draft when the logical key matches."""
        if (
            self.draft.tipo_bloque == tipo_bloque.value
            and self.draft.referencia_id == referencia_id
        ):
            return self.draft
        return None

    async def save(self, draft: BorradorSesion) -> BorradorSesion:
        """Track persisted draft changes."""
        self.saved.append(draft)
        return draft


class FakeProyectoRepository:
    """In-memory project aggregate repository."""

    def __init__(self, proyecto: ProyectoFormativo | None) -> None:
        """Store one project aggregate."""
        self.proyecto = proyecto
        self.saved: list[ProyectoFormativo] = []

    async def get_project_with_structure(
        self,
        proyecto_id: uuid.UUID,
    ) -> ProyectoFormativo | None:
        """Return the stored project when ids match."""
        if self.proyecto is None or self.proyecto.id != proyecto_id:
            return None
        return self.proyecto

    async def save_project(
        self,
        proyecto: ProyectoFormativo,
    ) -> ProyectoFormativo:
        """Track persisted project changes."""
        self.saved.append(proyecto)
        return proyecto


class FakeAuditRepository:
    """In-memory audit repository."""

    def __init__(self) -> None:
        """Store emitted events."""
        self.events: list[dict[str, object]] = []

    async def add_event(
        self,
        entidad: str,
        entidad_id: uuid.UUID,
        accion: str,
        detalle: dict[str, object] | None = None,
    ) -> object:
        """Track audit event payloads."""
        event = {
            "entidad": entidad,
            "entidad_id": entidad_id,
            "accion": accion,
            "detalle": detalle,
        }
        self.events.append(event)
        return event


def build_programa() -> ProgramaFormacion:
    """Create a completed training program."""
    programa = ProgramaFormacion(
        codigo_programa="228118",
        nombre_programa="Analisis y desarrollo de software",
        version_programa="1",
        estado=EstadoBloque.COMPLETO,
        fuente_cargue=TipoFuenteCargue.EXCEL_CANONICO,
    )
    programa.id = uuid.uuid4()
    return programa


def build_project(*, with_activity: bool = True) -> ProyectoFormativo:
    """Create a project aggregate with optional activity coverage."""
    proyecto = ProyectoFormativo(
        programa_id=uuid.uuid4(),
        codigo_proyecto="PR-001",
        nombre_proyecto="Proyecto formativo",
        version_proyecto="1",
        estado=EstadoBloque.BORRADOR,
        fuente_cargue=TipoFuenteCargue.EXCEL_CANONICO,
    )
    proyecto.id = uuid.uuid4()
    proyecto.programa = build_programa()

    fase = FaseProyecto(
        proyecto_id=proyecto.id,
        nombre_fase="Analisis",
        orden=1,
    )
    fase.id = uuid.uuid4()
    fase.actividades = []
    if with_activity:
        actividad = ActividadProyecto(
            fase_id=fase.id,
            descripcion="Levantar requerimientos",
            orden=1,
        )
        actividad.id = uuid.uuid4()
        fase.actividades = [actividad]
    proyecto.fases = [fase]
    return proyecto


def build_project_draft(proyecto_id: uuid.UUID, *, with_pdf: bool = True) -> BorradorSesion:
    """Create a project draft pointing at an imported project."""
    referencia_id = uuid.uuid4()
    proyecto_pdf_payload = None
    if with_pdf:
        proyecto_pdf_payload = {
            "documento": {
                "original_filename": "proyecto.pdf",
                "storage_key": "proyectos-formativos/some-key.pdf",
                "size_bytes": 1024,
                "content_type": "application/pdf",
                "checksum_sha256": "some-sha",
                "etag": "some-etag",
            }
        }

    draft = BorradorSesion(
        tipo_bloque=TipoBloqueBorrador.PROYECTO.value,
        referencia_id=referencia_id,
        paso_actual="revision-proyecto",
        payload_json={
            "meta": {
                "referenciaId": str(referencia_id),
                "touchedSteps": ["fuente-proyecto"],
            },
            "documental": {
                "fuente_estructurada": {
                    "confirmacion": {
                        "estado": "IMPORTADO",
                        "confirmed_at": datetime.now(UTC).isoformat(),
                        "proyecto_id": str(proyecto_id),
                    }
                },
                "proyecto_pdf": proyecto_pdf_payload,
            },
        },
        estado_borrador=EstadoBloque.EN_REVISION,
    )
    draft.id = uuid.uuid4()
    return draft


def build_service(
    proyecto: ProyectoFormativo,
    *,
    with_pdf: bool = True,
) -> tuple[
    ProyectoCierreService,
    FakeSession,
    FakeDraftRepository,
    FakeProyectoRepository,
    FakeAuditRepository,
    BorradorSesion,
]:
    """Build the service and fake dependencies."""
    draft = build_project_draft(proyecto.id, with_pdf=with_pdf)
    session = FakeSession()
    draft_repository = FakeDraftRepository(draft)
    proyecto_repository = FakeProyectoRepository(proyecto)
    audit_repository = FakeAuditRepository()
    service = ProyectoCierreService(
        session=session,
        draft_repository=draft_repository,
        proyecto_repository=proyecto_repository,
        audit_repository=audit_repository,
    )
    return (
        service,
        session,
        draft_repository,
        proyecto_repository,
        audit_repository,
        draft,
    )


@pytest.mark.anyio
async def test_cerrar_proyecto_marca_completo_y_audita() -> None:
    """A valid reviewed project should transition to COMPLETO."""
    proyecto = build_project()
    (
        service,
        session,
        draft_repository,
        proyecto_repository,
        audit_repository,
        draft,
    ) = build_service(proyecto)

    result = await service.cerrar_proyecto(draft.referencia_id)

    assert result.estado is EstadoBloque.COMPLETO
    assert result.completitud.cerrable is True
    assert proyecto.estado is EstadoBloque.COMPLETO
    assert draft.estado_borrador is EstadoBloque.COMPLETO
    assert draft.paso_actual == "revision-proyecto"
    assert session.committed is True
    assert proyecto_repository.saved == [proyecto]
    assert draft_repository.saved == [draft]
    assert audit_repository.events[0]["accion"] == "PROYECTO_CERRADO"


@pytest.mark.anyio
async def test_cerrar_proyecto_rechaza_fase_sin_actividades() -> None:
    """A phase without activities should block project closing."""
    proyecto = build_project(with_activity=False)
    service, session, _, proyecto_repository, audit_repository, draft = build_service(
        proyecto,
    )

    with pytest.raises(ProyectoCierreValidationError) as exc_info:
        await service.cerrar_proyecto(draft.referencia_id)

    assert exc_info.value.completitud.cerrable is False
    assert exc_info.value.completitud.faltantes[0].campo == "actividades"
    assert proyecto.estado is EstadoBloque.BORRADOR
    assert session.committed is False
    assert proyecto_repository.saved == []
    assert audit_repository.events == []


@pytest.mark.anyio
async def test_validacion_falla_sin_proyecto_pdf() -> None:
    """If the project PDF evidence is missing, the project is not closable."""
    proyecto = build_project()
    service, _, _, _, _, draft = build_service(proyecto, with_pdf=False)

    result = await service.validar_completitud(draft.referencia_id)

    assert result.cerrable is False
    assert any(f.campo == "proyecto_pdf" for f in result.faltantes)
