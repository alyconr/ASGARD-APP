"""Tests for TASK-12 criteria CRUD application service."""

import datetime
import uuid
from dataclasses import dataclass

import pytest

from src.application.dto.criterios import CriterioPayloadDTO
from src.application.services.criterios import (
    CriterioCompetenciaNotFoundError,
    CriterioDuplicateError,
    CriterioNotFoundError,
    CriterioValidationError,
    ProgramaCriteriosService,
)
from src.domain.drafts.types import TipoBloqueBorrador
from src.domain.shared.enums import EstadoBloque, EstadoCampo
from src.infrastructure.db.models.curriculum import Competencia, CriterioEvaluacion
from src.infrastructure.db.models.drafts import BorradorSesion


class FakeCriterioRepository:
    def __init__(
        self,
        competencias: list[Competencia],
        criterios: list[CriterioEvaluacion],
    ) -> None:
        self.competencias = competencias
        self.criterios = criterios

    async def get_competencia(
        self,
        competencia_id: uuid.UUID,
        programa_id: uuid.UUID | None = None,
    ) -> Competencia | None:
        for c in self.competencias:
            if c.id == competencia_id and (
                programa_id is None or c.programa_id == programa_id
            ):
                return c
        return None

    async def list_by_competencia(
        self,
        competencia_id: uuid.UUID,
    ) -> list[CriterioEvaluacion]:
        return [
            item for item in self.criterios if item.competencia_id == competencia_id
        ]

    async def get_by_id_for_competencia(
        self,
        criterio_id: uuid.UUID,
        competencia_id: uuid.UUID,
    ) -> CriterioEvaluacion | None:
        for item in self.criterios:
            if item.id == criterio_id and item.competencia_id == competencia_id:
                return item
        return None

    async def descripcion_exists(
        self,
        competencia_id: uuid.UUID,
        descripcion: str,
        exclude_criterio_id: uuid.UUID | None = None,
    ) -> bool:
        for item in self.criterios:
            if (
                item.competencia_id == competencia_id
                and item.descripcion.lower() == descripcion.lower()
                and (exclude_criterio_id is None or item.id != exclude_criterio_id)
            ):
                return True
        return False

    async def add_criterio(
        self,
        competencia_id: uuid.UUID,
        descripcion: str,
        orden: int,
    ) -> CriterioEvaluacion:
        criterio = CriterioEvaluacion(
            id=uuid.uuid4(),
            competencia_id=competencia_id,
            resultado_id=None,
            descripcion=descripcion,
            orden=orden,
            estado=EstadoCampo.MANUAL,
            fecha_creacion=datetime.datetime.now(datetime.UTC),
            fecha_actualizacion=datetime.datetime.now(datetime.UTC),
        )
        self.criterios.append(criterio)
        return criterio

    async def save_criterio(
        self,
        criterio: CriterioEvaluacion,
    ) -> CriterioEvaluacion:
        for idx, item in enumerate(self.criterios):
            if item.id == criterio.id:
                self.criterios[idx] = criterio
                return criterio
        self.criterios.append(criterio)
        return criterio

    async def delete_criterio(self, criterio: CriterioEvaluacion) -> None:
        self.criterios = [item for item in self.criterios if item.id != criterio.id]


@dataclass
class FakeDraftRepository:
    drafts: list[BorradorSesion]

    async def get_by_block_reference(
        self,
        tipo_bloque: TipoBloqueBorrador,
        referencia_id: uuid.UUID,
    ) -> BorradorSesion | None:
        for d in self.drafts:
            if d.tipo_bloque == tipo_bloque and d.referencia_id == referencia_id:
                return d
        return None

    async def save(self, draft: BorradorSesion) -> BorradorSesion:
        for idx, d in enumerate(self.drafts):
            if d.id == draft.id:
                self.drafts[idx] = draft
                return draft
        self.drafts.append(draft)
        return draft


@dataclass
class FakeAuditRepository:
    events: list[dict[str, object]]

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
            "detalle": detalle,
        }
        self.events.append(event)
        return event


class FakeAsyncSession:
    def __init__(self) -> None:
        self.committed = False

    async def commit(self) -> None:
        self.committed = True

    async def refresh(self, instance: object) -> None:
        pass


PROGRAMA_ID = uuid.uuid4()
COMPETENCIA_ID = uuid.uuid4()
REFERENCIA_ID = uuid.uuid4()
DRAFT_ID = uuid.uuid4()


def _build_competencia() -> Competencia:
    return Competencia(
        id=COMPETENCIA_ID,
        programa_id=PROGRAMA_ID,
        codigo_competencia="220501046",
        nombre_competencia="Test Competencia",
        orden=1,
        estado=EstadoBloque.BORRADOR,
        origen_campo=EstadoCampo.MANUAL,
        fecha_creacion=datetime.datetime.now(datetime.UTC),
        fecha_actualizacion=datetime.datetime.now(datetime.UTC),
    )


def _build_draft() -> BorradorSesion:
    return BorradorSesion(
        id=DRAFT_ID,
        tipo_bloque=TipoBloqueBorrador.PROGRAMA,
        referencia_id=REFERENCIA_ID,
        paso_actual="estructura-curricular",
        payload_json={
            "curricular": {
                "programa_formacion_id": str(PROGRAMA_ID),
                "competencias": [
                    {"id": str(COMPETENCIA_ID), "nombre": "Test", "criterios": []}
                ],
            }
        },
        estado_borrador=EstadoBloque.BORRADOR,
        ultima_edicion=datetime.datetime.now(datetime.UTC),
    )


def _build_service(repository, draft_repo, audit_repo):
    return ProgramaCriteriosService(
        session=FakeAsyncSession(),
        criterio_repository=repository,
        draft_repository=draft_repo,
        audit_repository=audit_repo,
    )


class TestCreateCriterio:
    def test_creates_valid_criterio(self):
        competencia = _build_competencia()
        draft = _build_draft()
        repo = FakeCriterioRepository([competencia], [])
        draft_repo = FakeDraftRepository([draft])
        audit_repo = FakeAuditRepository([])
        service = _build_service(repo, draft_repo, audit_repo)

        result = _async(
            service.create_criterio(
                REFERENCIA_ID,
                COMPETENCIA_ID,
                CriterioPayloadDTO(descripcion="  Analiza requerimientos  "),
            ),
        )

        assert result.referencia_id == REFERENCIA_ID
        assert result.competencia_id == COMPETENCIA_ID
        assert len(result.criterios) == 1
        assert result.criterios[0].descripcion == "Analiza requerimientos"
        assert result.criterios[0].estado == EstadoCampo.MANUAL
        assert len(audit_repo.events) == 1

    def test_rejects_empty_description(self):
        competencia = _build_competencia()
        draft = _build_draft()
        repo = FakeCriterioRepository([competencia], [])
        draft_repo = FakeDraftRepository([draft])
        audit_repo = FakeAuditRepository([])
        service = _build_service(repo, draft_repo, audit_repo)

        with pytest.raises(CriterioValidationError):
            _async(
                service.create_criterio(
                    REFERENCIA_ID,
                    COMPETENCIA_ID,
                    CriterioPayloadDTO(descripcion="   "),
                ),
            )

    def test_rejects_duplicate_description(self):
        competencia = _build_competencia()
        draft = _build_draft()
        existing = CriterioEvaluacion(
            id=uuid.uuid4(),
            competencia_id=COMPETENCIA_ID,
            resultado_id=None,
            descripcion="Analiza requerimientos",
            orden=1,
            estado=EstadoCampo.MANUAL,
            fecha_creacion=datetime.datetime.now(datetime.UTC),
            fecha_actualizacion=datetime.datetime.now(datetime.UTC),
        )
        repo = FakeCriterioRepository([competencia], [existing])
        draft_repo = FakeDraftRepository([draft])
        audit_repo = FakeAuditRepository([])
        service = _build_service(repo, draft_repo, audit_repo)

        with pytest.raises(CriterioDuplicateError):
            _async(
                service.create_criterio(
                    REFERENCIA_ID,
                    COMPETENCIA_ID,
                    CriterioPayloadDTO(descripcion="Analiza requerimientos"),
                ),
            )

    def test_allows_same_description_in_different_competence(self):
        competencia_a = _build_competencia()
        comp_b_id = uuid.uuid4()
        competencia_b = Competencia(
            id=comp_b_id,
            programa_id=PROGRAMA_ID,
            codigo_competencia="220501047",
            nombre_competencia="Otra",
            orden=2,
            estado=EstadoBloque.BORRADOR,
            origen_campo=EstadoCampo.MANUAL,
            fecha_creacion=datetime.datetime.now(datetime.UTC),
            fecha_actualizacion=datetime.datetime.now(datetime.UTC),
        )
        existing = CriterioEvaluacion(
            id=uuid.uuid4(),
            competencia_id=COMPETENCIA_ID,
            resultado_id=None,
            descripcion="Analiza requerimientos",
            orden=1,
            estado=EstadoCampo.MANUAL,
            fecha_creacion=datetime.datetime.now(datetime.UTC),
            fecha_actualizacion=datetime.datetime.now(datetime.UTC),
        )
        draft = _build_draft()
        repo = FakeCriterioRepository([competencia_a, competencia_b], [existing])
        draft_repo = FakeDraftRepository([draft])
        audit_repo = FakeAuditRepository([])
        service = _build_service(repo, draft_repo, audit_repo)

        result = _async(
            service.create_criterio(
                REFERENCIA_ID,
                comp_b_id,
                CriterioPayloadDTO(descripcion="Analiza requerimientos"),
            ),
        )

        assert len(result.criterios) == 1


class TestUpdateCriterio:
    def test_updates_existing_criterio(self):
        criterio_id = uuid.uuid4()
        competencia = _build_competencia()
        draft = _build_draft()
        existing = CriterioEvaluacion(
            id=criterio_id,
            competencia_id=COMPETENCIA_ID,
            resultado_id=None,
            descripcion="Original",
            orden=1,
            estado=EstadoCampo.MANUAL,
            fecha_creacion=datetime.datetime.now(datetime.UTC),
            fecha_actualizacion=datetime.datetime.now(datetime.UTC),
        )
        repo = FakeCriterioRepository([competencia], [existing])
        draft_repo = FakeDraftRepository([draft])
        audit_repo = FakeAuditRepository([])
        service = _build_service(repo, draft_repo, audit_repo)

        result = _async(
            service.update_criterio(
                REFERENCIA_ID,
                COMPETENCIA_ID,
                criterio_id,
                CriterioPayloadDTO(descripcion="Actualizado"),
            ),
        )

        assert len(result.criterios) == 1
        assert result.criterios[0].descripcion == "Actualizado"

    def test_rejects_update_of_duplicate_description(self):
        criterio_a_id = uuid.uuid4()
        criterio_b_id = uuid.uuid4()
        competencia = _build_competencia()
        draft = _build_draft()
        existing = [
            CriterioEvaluacion(
                id=criterio_a_id,
                competencia_id=COMPETENCIA_ID,
                resultado_id=None,
                descripcion="Uno",
                orden=1,
                estado=EstadoCampo.MANUAL,
                fecha_creacion=datetime.datetime.now(datetime.UTC),
                fecha_actualizacion=datetime.datetime.now(datetime.UTC),
            ),
            CriterioEvaluacion(
                id=criterio_b_id,
                competencia_id=COMPETENCIA_ID,
                resultado_id=None,
                descripcion="Dos",
                orden=2,
                estado=EstadoCampo.MANUAL,
                fecha_creacion=datetime.datetime.now(datetime.UTC),
                fecha_actualizacion=datetime.datetime.now(datetime.UTC),
            ),
        ]
        repo = FakeCriterioRepository([competencia], existing)
        draft_repo = FakeDraftRepository([draft])
        audit_repo = FakeAuditRepository([])
        service = _build_service(repo, draft_repo, audit_repo)

        with pytest.raises(CriterioDuplicateError):
            _async(
                service.update_criterio(
                    REFERENCIA_ID,
                    COMPETENCIA_ID,
                    criterio_a_id,
                    CriterioPayloadDTO(descripcion="Dos"),
                ),
            )


class TestDeleteCriterio:
    def test_deletes_existing_criterio(self):
        criterio_id = uuid.uuid4()
        competencia = _build_competencia()
        draft = _build_draft()
        existing = CriterioEvaluacion(
            id=criterio_id,
            competencia_id=COMPETENCIA_ID,
            resultado_id=None,
            descripcion="Para eliminar",
            orden=1,
            estado=EstadoCampo.MANUAL,
            fecha_creacion=datetime.datetime.now(datetime.UTC),
            fecha_actualizacion=datetime.datetime.now(datetime.UTC),
        )
        repo = FakeCriterioRepository([competencia], [existing])
        draft_repo = FakeDraftRepository([draft])
        audit_repo = FakeAuditRepository([])
        service = _build_service(repo, draft_repo, audit_repo)

        result = _async(
            service.delete_criterio(
                REFERENCIA_ID,
                COMPETENCIA_ID,
                criterio_id,
            ),
        )

        assert result.eliminado is True
        assert result.criterio_id == criterio_id
        assert len(repo.criterios) == 0

    def test_rejects_delete_of_missing_criterio(self):
        competencia = _build_competencia()
        draft = _build_draft()
        repo = FakeCriterioRepository([competencia], [])
        draft_repo = FakeDraftRepository([draft])
        audit_repo = FakeAuditRepository([])
        service = _build_service(repo, draft_repo, audit_repo)

        with pytest.raises(CriterioNotFoundError):
            _async(
                service.delete_criterio(
                    REFERENCIA_ID,
                    COMPETENCIA_ID,
                    uuid.uuid4(),
                ),
            )


class TestListCriterios:
    def test_empty_list(self):
        competencia = _build_competencia()
        draft = _build_draft()
        repo = FakeCriterioRepository([competencia], [])
        draft_repo = FakeDraftRepository([draft])
        audit_repo = FakeAuditRepository([])
        service = _build_service(repo, draft_repo, audit_repo)

        result = _async(
            service.list_criterios(REFERENCIA_ID, COMPETENCIA_ID),
        )

        assert result.criterios == []


class TestCompetenceValidation:
    def test_rejects_competence_from_other_program(self):
        competencia = _build_competencia()
        other_comp = Competencia(
            id=uuid.uuid4(),
            programa_id=uuid.uuid4(),
            codigo_competencia="OTRO",
            nombre_competencia="Other",
            orden=1,
            estado=EstadoBloque.BORRADOR,
            origen_campo=EstadoCampo.MANUAL,
            fecha_creacion=datetime.datetime.now(datetime.UTC),
            fecha_actualizacion=datetime.datetime.now(datetime.UTC),
        )
        draft = _build_draft()
        repo = FakeCriterioRepository([competencia, other_comp], [])
        draft_repo = FakeDraftRepository([draft])
        audit_repo = FakeAuditRepository([])
        service = _build_service(repo, draft_repo, audit_repo)

        with pytest.raises(CriterioCompetenciaNotFoundError):
            _async(
                service.create_criterio(
                    REFERENCIA_ID,
                    other_comp.id,
                    CriterioPayloadDTO(descripcion="Criterio externo"),
                ),
            )


def _async(coro):
    import asyncio

    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop is not None and loop.is_running():
        import concurrent.futures

        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(asyncio.run, coro)
            return future.result()

    return asyncio.run(coro)
