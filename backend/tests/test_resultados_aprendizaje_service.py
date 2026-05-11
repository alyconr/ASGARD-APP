"""Tests for TASK-09 learning outcomes CRUD application service."""

import datetime
import uuid
from copy import deepcopy
from dataclasses import dataclass
from typing import cast

import pytest

from src.application.dto.resultados_aprendizaje import ResultadoAprendizajePayloadDTO
from src.application.services.resultados_aprendizaje import (
    ProgramaResultadoAprendizajeService,
    ResultadoAprendizajeDuplicateError,
)
from src.domain.drafts.types import TipoBloqueBorrador
from src.domain.shared.enums import EstadoBloque, EstadoCampo
from src.infrastructure.db.models.curriculum import Competencia, ResultadoAprendizaje
from src.infrastructure.db.models.drafts import BorradorSesion


class FakeResultadoRepository:
    def __init__(
        self,
        competencias: list[Competencia],
        resultados: list[ResultadoAprendizaje],
    ) -> None:
        self.competencias = competencias
        self.resultados = resultados

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
    ) -> list[ResultadoAprendizaje]:
        return [r for r in self.resultados if r.competencia_id == competencia_id]

    async def get_by_id_for_competencia(
        self,
        resultado_id: uuid.UUID,
        competencia_id: uuid.UUID,
    ) -> ResultadoAprendizaje | None:
        for r in self.resultados:
            if r.id == resultado_id and r.competencia_id == competencia_id:
                return r
        return None

    async def descripcion_exists(
        self,
        competencia_id: uuid.UUID,
        descripcion: str,
        exclude_resultado_id: uuid.UUID | None = None,
    ) -> bool:
        for r in self.resultados:
            if (
                r.competencia_id == competencia_id
                and r.descripcion.lower() == descripcion.lower()
                and (exclude_resultado_id is None or r.id != exclude_resultado_id)
            ):
                return True
        return False

    async def add_resultado(
        self,
        competencia_id: uuid.UUID,
        descripcion: str,
        orden: int,
        codigo_resultado: str | None = None,
    ) -> ResultadoAprendizaje:
        r = ResultadoAprendizaje(
            id=uuid.uuid4(),
            competencia_id=competencia_id,
            descripcion=descripcion,
            codigo_resultado=codigo_resultado,
            orden=orden,
            estado=EstadoCampo.MANUAL,
        )
        r.fecha_creacion = datetime.datetime.now(datetime.UTC)
        r.fecha_actualizacion = datetime.datetime.now(datetime.UTC)
        self.resultados.append(r)
        return r

    async def save_resultado(
        self,
        resultado: ResultadoAprendizaje,
    ) -> ResultadoAprendizaje:
        for i, r in enumerate(self.resultados):
            if r.id == resultado.id:
                self.resultados[i] = resultado
                return resultado
        return resultado

    async def delete_resultado(self, resultado: ResultadoAprendizaje) -> None:
        self.resultados = [r for r in self.resultados if r.id != resultado.id]


class FakeDraftRepository:
    def __init__(self, drafts: list[BorradorSesion]) -> None:
        self.drafts = drafts

    async def get_by_block_reference(
        self,
        tipo_bloque: TipoBloqueBorrador,
        referencia_id: uuid.UUID,
    ) -> BorradorSesion | None:
        for d in self.drafts:
            if d.tipo_bloque == tipo_bloque and d.referencia_id == referencia_id:
                return deepcopy(d)
        return None

    async def save(self, draft: BorradorSesion) -> BorradorSesion:
        for i, d in enumerate(self.drafts):
            if d.id == draft.id:
                self.drafts[i] = deepcopy(draft)
                return draft
        return draft


class FakeAuditRepository:
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
            "detalle": detalle,
        }
        self.events.append(event)
        return event


class FakeSession:
    async def commit(self) -> None:
        pass

    async def refresh(self, instance: object) -> None:
        pass


@dataclass(frozen=True)
class ResultadoServiceSetup:
    referencia_id: uuid.UUID
    programa_id: uuid.UUID
    competencia_id: uuid.UUID
    draft: BorradorSesion
    competencia: Competencia


@pytest.fixture
def base_setup() -> ResultadoServiceSetup:
    referencia_id = uuid.uuid4()
    programa_id = uuid.uuid4()
    competencia_id = uuid.uuid4()
    draft = BorradorSesion(
        id=uuid.uuid4(),
        referencia_id=referencia_id,
        tipo_bloque=TipoBloqueBorrador.PROGRAMA,
        estado_borrador=EstadoBloque.BORRADOR,
        paso_actual="competencias",
        payload_json={
            "curricular": {
                "programa_formacion_id": str(programa_id),
                "competencias": [{"id": str(competencia_id), "resultados": []}],
            }
        },
    )
    competencia = Competencia(
        id=competencia_id,
        programa_id=programa_id,
        codigo_competencia="C1",
        nombre_competencia="Comp 1",
        orden=1,
        estado=EstadoBloque.BORRADOR,
        origen_campo=EstadoCampo.MANUAL,
    )
    return ResultadoServiceSetup(
        referencia_id=referencia_id,
        programa_id=programa_id,
        competencia_id=competencia_id,
        draft=draft,
        competencia=competencia,
    )


def build_service(
    drafts: list[BorradorSesion] | None = None,
    competencias: list[Competencia] | None = None,
    resultados: list[ResultadoAprendizaje] | None = None,
) -> tuple[
    ProgramaResultadoAprendizajeService,
    FakeDraftRepository,
    FakeResultadoRepository,
    FakeAuditRepository,
]:
    draft_repo = FakeDraftRepository(drafts or [])
    resultado_repo = FakeResultadoRepository(competencias or [], resultados or [])
    audit_repo = FakeAuditRepository()
    session = FakeSession()
    service = ProgramaResultadoAprendizajeService(
        session, resultado_repo, draft_repo, audit_repo
    )
    return service, draft_repo, resultado_repo, audit_repo


@pytest.mark.anyio
async def test_list_resultados(base_setup: ResultadoServiceSetup) -> None:
    draft = base_setup.draft
    competencia = base_setup.competencia
    resultado = ResultadoAprendizaje(
        id=uuid.uuid4(),
        competencia_id=competencia.id,
        descripcion="Test rap",
        codigo_resultado="1",
        orden=1,
        estado=EstadoCampo.MANUAL,
    )
    resultado.fecha_creacion = datetime.datetime.now(datetime.UTC)
    resultado.fecha_actualizacion = datetime.datetime.now(datetime.UTC)
    service, *_ = build_service(
        drafts=[draft],
        competencias=[competencia],
        resultados=[resultado],
    )

    dto = await service.list_resultados(base_setup.referencia_id, competencia.id)
    assert len(dto.resultados) == 1
    assert dto.resultados[0].descripcion == "Test rap"


@pytest.mark.anyio
async def test_create_resultado(base_setup: ResultadoServiceSetup) -> None:
    draft = base_setup.draft
    competencia = base_setup.competencia
    service, draft_repo, *_ = build_service(
        drafts=[draft],
        competencias=[competencia],
    )

    payload = ResultadoAprendizajePayloadDTO(descripcion=" Nuevo Rap ")
    dto = await service.create_resultado(
        base_setup.referencia_id, competencia.id, payload
    )

    assert len(dto.resultados) == 1
    assert dto.resultados[0].descripcion == "Nuevo Rap"

    updated_draft = await draft_repo.get_by_block_reference(
        TipoBloqueBorrador.PROGRAMA, base_setup.referencia_id
    )
    assert updated_draft is not None
    curricular = cast(dict[str, object], updated_draft.payload_json["curricular"])
    payload_comps = cast(list[dict[str, object]], curricular["competencias"])
    resultados = cast(list[dict[str, object]], payload_comps[0]["resultados"])
    assert len(resultados) == 1


@pytest.mark.anyio
async def test_create_resultado_duplicate(
    base_setup: ResultadoServiceSetup,
) -> None:
    draft = base_setup.draft
    competencia = base_setup.competencia
    resultado = ResultadoAprendizaje(
        id=uuid.uuid4(),
        competencia_id=competencia.id,
        descripcion="Duplicate",
        orden=1,
        estado=EstadoCampo.MANUAL,
    )
    resultado.fecha_creacion = datetime.datetime.now(datetime.UTC)
    resultado.fecha_actualizacion = datetime.datetime.now(datetime.UTC)
    service, *_ = build_service(
        drafts=[draft],
        competencias=[competencia],
        resultados=[resultado],
    )

    payload = ResultadoAprendizajePayloadDTO(descripcion="duplicate")
    with pytest.raises(ResultadoAprendizajeDuplicateError):
        await service.create_resultado(
            base_setup.referencia_id, competencia.id, payload
        )


@pytest.mark.anyio
async def test_update_resultado(base_setup: ResultadoServiceSetup) -> None:
    draft = base_setup.draft
    competencia = base_setup.competencia
    resultado = ResultadoAprendizaje(
        id=uuid.uuid4(),
        competencia_id=competencia.id,
        descripcion="Old desc",
        orden=1,
        estado=EstadoCampo.MANUAL,
    )
    resultado.fecha_creacion = datetime.datetime.now(datetime.UTC)
    resultado.fecha_actualizacion = datetime.datetime.now(datetime.UTC)
    service, *_ = build_service(
        drafts=[draft],
        competencias=[competencia],
        resultados=[resultado],
    )

    payload = ResultadoAprendizajePayloadDTO(
        descripcion="New desc",
        codigo_resultado="RAP-2",
    )
    dto = await service.update_resultado(
        base_setup.referencia_id, competencia.id, resultado.id, payload
    )

    assert dto.resultados[0].descripcion == "New desc"
    assert dto.resultados[0].codigo_resultado == "RAP-2"


@pytest.mark.anyio
async def test_delete_resultado(base_setup: ResultadoServiceSetup) -> None:
    draft = base_setup.draft
    competencia = base_setup.competencia
    resultado = ResultadoAprendizaje(
        id=uuid.uuid4(),
        competencia_id=competencia.id,
        descripcion="To delete",
        orden=1,
        estado=EstadoCampo.MANUAL,
    )
    resultado.fecha_creacion = datetime.datetime.now(datetime.UTC)
    resultado.fecha_actualizacion = datetime.datetime.now(datetime.UTC)
    service, draft_repo, resultado_repo, _ = build_service(
        drafts=[draft],
        competencias=[competencia],
        resultados=[resultado],
    )

    await service.delete_resultado(
        base_setup.referencia_id, competencia.id, resultado.id
    )

    assert len(resultado_repo.resultados) == 0
    updated_draft = await draft_repo.get_by_block_reference(
        TipoBloqueBorrador.PROGRAMA, base_setup.referencia_id
    )
    assert updated_draft is not None
    curricular = cast(dict[str, object], updated_draft.payload_json["curricular"])
    payload_comps = cast(list[dict[str, object]], curricular["competencias"])
    resultados = cast(list[dict[str, object]], payload_comps[0]["resultados"])
    assert len(resultados) == 0
