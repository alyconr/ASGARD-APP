"""Unit tests for TASK-08 competence CRUD service."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest

from src.application.dto.competencias import CompetenciaPayloadDTO
from src.application.services.competencias import (
    CompetenciaDuplicateCodeError,
    CompetenciaProgramaIncompleteError,
    CompetenciaValidationError,
    ProgramaCompetenciaService,
)
from src.domain.drafts.types import TipoBloqueBorrador
from src.domain.shared.enums import EstadoBloque, EstadoCampo, TipoFuenteCargue
from src.infrastructure.db.models.curriculum import Competencia, ProgramaFormacion
from src.infrastructure.db.models.drafts import BorradorSesion


class FakeSession:
    """Minimal async session double used by the competence service."""

    def __init__(self) -> None:
        """Track commit calls."""
        self.commits = 0

    async def commit(self) -> None:
        """Record a commit invocation."""
        self.commits += 1

    async def refresh(self, instance: object) -> None:
        """Populate ids and timestamps expected after database flush."""
        now = datetime.now(UTC)
        if isinstance(instance, ProgramaFormacion):
            instance.id = getattr(instance, "id", uuid.uuid4()) or uuid.uuid4()
            instance.fecha_creacion = now
            instance.fecha_actualizacion = now
        if isinstance(instance, Competencia):
            instance.id = getattr(instance, "id", uuid.uuid4()) or uuid.uuid4()
            instance.fecha_creacion = now
            instance.fecha_actualizacion = now


class FakeCompetenciaRepository:
    """In-memory repository for program and competence rows."""

    def __init__(self) -> None:
        """Initialize empty storage."""
        self.programas: dict[uuid.UUID, ProgramaFormacion] = {}
        self.competencias: dict[uuid.UUID, Competencia] = {}

    async def get_programa(self, programa_id: uuid.UUID) -> ProgramaFormacion | None:
        """Return a program by id."""
        return self.programas.get(programa_id)

    async def get_programa_by_code_version(
        self,
        codigo_programa: str,
        version_programa: str | None,
    ) -> ProgramaFormacion | None:
        """Return an existing program matching code and version."""
        for programa in self.programas.values():
            if (
                programa.codigo_programa == codigo_programa
                and programa.version_programa == version_programa
            ):
                return programa
        return None

    async def add_programa(
        self,
        codigo_programa: str,
        nombre_programa: str,
        version_programa: str | None,
    ) -> ProgramaFormacion:
        """Create a program row."""
        now = datetime.now(UTC)
        programa = ProgramaFormacion(
            codigo_programa=codigo_programa,
            nombre_programa=nombre_programa,
            version_programa=version_programa,
            estado=EstadoBloque.BORRADOR,
            fuente_cargue=TipoFuenteCargue.MIXTO,
        )
        programa.id = uuid.uuid4()
        programa.fecha_creacion = now
        programa.fecha_actualizacion = now
        self.programas[programa.id] = programa
        return programa

    async def list_by_programa(self, programa_id: uuid.UUID) -> list[Competencia]:
        """List competences by program."""
        return sorted(
            [
                competencia
                for competencia in self.competencias.values()
                if competencia.programa_id == programa_id
            ],
            key=lambda competencia: competencia.orden or 0,
        )

    async def get_by_id_for_programa(
        self,
        competencia_id: uuid.UUID,
        programa_id: uuid.UUID,
    ) -> Competencia | None:
        """Return a competence only when it belongs to the program."""
        competencia = self.competencias.get(competencia_id)
        if competencia is None or competencia.programa_id != programa_id:
            return None
        return competencia

    async def code_exists(
        self,
        programa_id: uuid.UUID,
        codigo_competencia: str,
        exclude_competencia_id: uuid.UUID | None = None,
    ) -> bool:
        """Check case-insensitive duplicate code inside one program."""
        return any(
            competencia.programa_id == programa_id
            and competencia.codigo_competencia.lower()
            == codigo_competencia.lower()
            and competencia.id != exclude_competencia_id
            for competencia in self.competencias.values()
        )

    async def add_competencia(
        self,
        programa_id: uuid.UUID,
        codigo_competencia: str,
        nombre_competencia: str,
        orden: int,
    ) -> Competencia:
        """Create a competence row."""
        now = datetime.now(UTC)
        competencia = Competencia(
            programa_id=programa_id,
            codigo_competencia=codigo_competencia,
            nombre_competencia=nombre_competencia,
            orden=orden,
            estado=EstadoBloque.BORRADOR,
            origen_campo=EstadoCampo.MANUAL,
        )
        competencia.id = uuid.uuid4()
        competencia.fecha_creacion = now
        competencia.fecha_actualizacion = now
        self.competencias[competencia.id] = competencia
        return competencia

    async def save_competencia(self, competencia: Competencia) -> Competencia:
        """Update a competence row."""
        competencia.fecha_actualizacion = datetime.now(UTC)
        self.competencias[competencia.id] = competencia
        return competencia

    async def delete_competencia(self, competencia: Competencia) -> None:
        """Delete a competence row."""
        self.competencias.pop(competencia.id, None)


class FakeDraftRepository:
    """In-memory draft storage keyed by stable reference."""

    def __init__(self) -> None:
        """Initialize empty draft storage."""
        self.drafts: dict[uuid.UUID, BorradorSesion] = {}

    async def get_by_block_reference(
        self,
        tipo_bloque: TipoBloqueBorrador,
        referencia_id: uuid.UUID,
    ) -> BorradorSesion | None:
        """Return a program draft."""
        if tipo_bloque is not TipoBloqueBorrador.PROGRAMA:
            return None
        return self.drafts.get(referencia_id)

    async def save(self, draft: BorradorSesion) -> BorradorSesion:
        """Persist draft changes."""
        self.drafts[draft.referencia_id] = draft
        return draft


class FakeAuditRepository:
    """Collect audit events emitted by the competence service."""

    def __init__(self) -> None:
        """Initialize empty audit storage."""
        self.events: list[dict[str, object]] = []

    async def add_event(
        self,
        entidad: str,
        entidad_id: uuid.UUID,
        accion: str,
        detalle: dict[str, object] | None = None,
    ) -> object:
        """Append an audit event."""
        event: dict[str, object] = {
            "entidad": entidad,
            "entidad_id": entidad_id,
            "accion": accion,
            "detalle": detalle or {},
        }
        self.events.append(event)
        return event


def build_draft(
    referencia_id: uuid.UUID,
    codigo_programa: str = "228118",
    nombre_programa: str = "Analisis y desarrollo de software",
) -> BorradorSesion:
    """Create a program draft with base program fields."""
    draft = BorradorSesion(
        tipo_bloque=TipoBloqueBorrador.PROGRAMA.value,
        referencia_id=referencia_id,
        paso_actual="estructura-curricular",
        payload_json={
            "meta": {"referenciaId": str(referencia_id)},
            "programa": {
                "codigo_programa": codigo_programa,
                "nombre_programa": nombre_programa,
                "version_programa": "",
            },
            "wizard": {"notesByStep": {}},
            "documental": {"programa_pdf": None},
        },
        estado_borrador=EstadoBloque.BORRADOR,
    )
    draft.id = uuid.uuid4()
    draft.ultima_edicion = datetime.now(UTC)
    return draft


def build_service() -> tuple[
    ProgramaCompetenciaService,
    FakeSession,
    FakeCompetenciaRepository,
    FakeDraftRepository,
    FakeAuditRepository,
]:
    """Build a competence service with fake dependencies."""
    session = FakeSession()
    competencias = FakeCompetenciaRepository()
    drafts = FakeDraftRepository()
    audit = FakeAuditRepository()
    service = ProgramaCompetenciaService(session, competencias, drafts, audit)
    return service, session, competencias, drafts, audit


@pytest.mark.anyio
async def test_create_competencia_materializes_program_and_updates_draft() -> None:
    """Creating a competence should link it to the current program draft."""
    service, session, _, drafts, audit = build_service()
    referencia_id = uuid.uuid4()
    drafts.drafts[referencia_id] = build_draft(referencia_id)

    result = await service.create_competencia(
        referencia_id,
        CompetenciaPayloadDTO(
            codigo_competencia=" 220501046 ",
            nombre_competencia=" Desarrollar software ",
        ),
    )

    assert result.referencia_id == referencia_id
    assert result.programa_id is not None
    assert result.competencias[0].codigo_competencia == "220501046"
    assert result.competencias[0].nombre_competencia == "Desarrollar software"
    assert drafts.drafts[referencia_id].referencia_id == referencia_id
    curricular = drafts.drafts[referencia_id].payload_json["curricular"]
    assert isinstance(curricular, dict)
    assert curricular["programa_formacion_id"] == str(result.programa_id)
    assert len(curricular["competencias"]) == 1
    assert session.commits == 1
    assert audit.events[0]["accion"] == "COMPETENCIA_CREADA"


@pytest.mark.anyio
async def test_create_competencia_rejects_blank_values() -> None:
    """Blank code and name values should be rejected after trim."""
    service, _, _, drafts, _ = build_service()
    referencia_id = uuid.uuid4()
    drafts.drafts[referencia_id] = build_draft(referencia_id)

    with pytest.raises(CompetenciaValidationError):
        await service.create_competencia(
            referencia_id,
            CompetenciaPayloadDTO(
                codigo_competencia=" ",
                nombre_competencia="Desarrollar software",
            ),
        )


@pytest.mark.anyio
async def test_create_competencia_requires_program_base_fields() -> None:
    """A competence cannot be created without a program base in the draft."""
    service, _, _, drafts, _ = build_service()
    referencia_id = uuid.uuid4()
    drafts.drafts[referencia_id] = build_draft(
        referencia_id,
        codigo_programa="",
        nombre_programa="",
    )

    with pytest.raises(CompetenciaProgramaIncompleteError):
        await service.create_competencia(
            referencia_id,
            CompetenciaPayloadDTO(
                codigo_competencia="220501046",
                nombre_competencia="Desarrollar software",
            ),
        )


@pytest.mark.anyio
async def test_create_competencia_rejects_duplicate_code_in_same_program() -> None:
    """Duplicate code validation should run inside the current program."""
    service, _, _, drafts, _ = build_service()
    referencia_id = uuid.uuid4()
    drafts.drafts[referencia_id] = build_draft(referencia_id)

    await service.create_competencia(
        referencia_id,
        CompetenciaPayloadDTO(
            codigo_competencia="220501046",
            nombre_competencia="Desarrollar software",
        ),
    )

    with pytest.raises(CompetenciaDuplicateCodeError):
        await service.create_competencia(
            referencia_id,
            CompetenciaPayloadDTO(
                codigo_competencia="220501046",
                nombre_competencia="Implementar software",
            ),
        )


@pytest.mark.anyio
async def test_update_competencia_preserves_program_and_syncs_draft() -> None:
    """Editing should preserve the program association and draft reference."""
    service, _, _, drafts, _ = build_service()
    referencia_id = uuid.uuid4()
    drafts.drafts[referencia_id] = build_draft(referencia_id)
    created = await service.create_competencia(
        referencia_id,
        CompetenciaPayloadDTO(
            codigo_competencia="220501046",
            nombre_competencia="Desarrollar software",
        ),
    )
    competencia_id = created.competencias[0].id

    updated = await service.update_competencia(
        referencia_id,
        competencia_id,
        CompetenciaPayloadDTO(
            codigo_competencia="220501047",
            nombre_competencia="Implementar soluciones de software",
        ),
    )

    assert updated.referencia_id == referencia_id
    assert updated.programa_id == created.programa_id
    assert updated.competencias[0].id == competencia_id
    assert updated.competencias[0].codigo_competencia == "220501047"
    curricular = drafts.drafts[referencia_id].payload_json["curricular"]
    assert isinstance(curricular, dict)
    assert curricular["competencias"][0]["codigo_competencia"] == "220501047"


@pytest.mark.anyio
async def test_delete_competencia_updates_draft_without_new_reference() -> None:
    """Deleting should remove the competence and keep the same reference id."""
    service, _, _, drafts, _ = build_service()
    referencia_id = uuid.uuid4()
    drafts.drafts[referencia_id] = build_draft(referencia_id)
    created = await service.create_competencia(
        referencia_id,
        CompetenciaPayloadDTO(
            codigo_competencia="220501046",
            nombre_competencia="Desarrollar software",
        ),
    )
    competencia_id = created.competencias[0].id

    result = await service.delete_competencia(referencia_id, competencia_id)

    assert result.referencia_id == referencia_id
    assert result.competencia_id == competencia_id
    assert result.eliminado is True
    curricular = drafts.drafts[referencia_id].payload_json["curricular"]
    assert isinstance(curricular, dict)
    assert curricular["competencias"] == []
