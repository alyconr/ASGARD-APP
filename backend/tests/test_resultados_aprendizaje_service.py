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
    ResultadoAprendizajeCompetenciaNotFoundError,
    ResultadoAprendizajeDuplicateError,
    ResultadoAprendizajeNotFoundError,
    ResultadoAprendizajeValidationError,
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


def build_resultado(
    competencia_id: uuid.UUID,
    descripcion: str = "Resultado base",
    codigo_resultado: str | None = None,
) -> ResultadoAprendizaje:
    resultado = ResultadoAprendizaje(
        id=uuid.uuid4(),
        competencia_id=competencia_id,
        descripcion=descripcion,
        codigo_resultado=codigo_resultado,
        orden=1,
        estado=EstadoCampo.MANUAL,
    )
    resultado.fecha_creacion = datetime.datetime.now(datetime.UTC)
    resultado.fecha_actualizacion = datetime.datetime.now(datetime.UTC)
    return resultado


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
    resultado = build_resultado(
        competencia.id,
        descripcion="Test rap",
        codigo_resultado="1",
    )
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
async def test_create_resultado_rejects_blank_description(
    base_setup: ResultadoServiceSetup,
) -> None:
    service, *_ = build_service(
        drafts=[base_setup.draft],
        competencias=[base_setup.competencia],
    )

    with pytest.raises(ResultadoAprendizajeValidationError):
        await service.create_resultado(
            base_setup.referencia_id,
            base_setup.competencia.id,
            ResultadoAprendizajePayloadDTO(descripcion="   "),
        )


@pytest.mark.anyio
async def test_create_resultado_normalizes_blank_codigo_to_none(
    base_setup: ResultadoServiceSetup,
) -> None:
    service, *_ = build_service(
        drafts=[base_setup.draft],
        competencias=[base_setup.competencia],
    )

    dto = await service.create_resultado(
        base_setup.referencia_id,
        base_setup.competencia.id,
        ResultadoAprendizajePayloadDTO(
            descripcion="Resultado con codigo vacio",
            codigo_resultado="   ",
        ),
    )

    assert dto.resultados[0].codigo_resultado is None


@pytest.mark.anyio
async def test_create_resultado_duplicate(
    base_setup: ResultadoServiceSetup,
) -> None:
    draft = base_setup.draft
    competencia = base_setup.competencia
    resultado = build_resultado(competencia.id, descripcion="Duplicate")
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
async def test_create_resultado_allows_same_description_in_different_competencias(
    base_setup: ResultadoServiceSetup,
) -> None:
    other_competencia = Competencia(
        id=uuid.uuid4(),
        programa_id=base_setup.programa_id,
        codigo_competencia="C2",
        nombre_competencia="Comp 2",
        orden=2,
        estado=EstadoBloque.BORRADOR,
        origen_campo=EstadoCampo.MANUAL,
    )
    existing = build_resultado(
        base_setup.competencia.id,
        descripcion="Descripcion compartida",
    )
    service, *_ = build_service(
        drafts=[base_setup.draft],
        competencias=[base_setup.competencia, other_competencia],
        resultados=[existing],
    )

    dto = await service.create_resultado(
        base_setup.referencia_id,
        other_competencia.id,
        ResultadoAprendizajePayloadDTO(descripcion="Descripcion compartida"),
    )

    assert len(dto.resultados) == 1
    assert dto.resultados[0].competencia_id == other_competencia.id


@pytest.mark.anyio
async def test_update_resultado(base_setup: ResultadoServiceSetup) -> None:
    draft = base_setup.draft
    competencia = base_setup.competencia
    resultado = build_resultado(competencia.id, descripcion="Old desc")
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
async def test_update_resultado_rejects_duplicate_description(
    base_setup: ResultadoServiceSetup,
) -> None:
    competencia = base_setup.competencia
    resultado = build_resultado(competencia.id, descripcion="Old desc")
    existing = build_resultado(competencia.id, descripcion="Existing desc")
    service, *_ = build_service(
        drafts=[base_setup.draft],
        competencias=[competencia],
        resultados=[resultado, existing],
    )

    with pytest.raises(ResultadoAprendizajeDuplicateError):
        await service.update_resultado(
            base_setup.referencia_id,
            competencia.id,
            resultado.id,
            ResultadoAprendizajePayloadDTO(descripcion="existing desc"),
        )


@pytest.mark.anyio
async def test_delete_resultado(base_setup: ResultadoServiceSetup) -> None:
    draft = base_setup.draft
    competencia = base_setup.competencia
    resultado = build_resultado(competencia.id, descripcion="To delete")
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


@pytest.mark.anyio
async def test_operations_reject_unknown_or_foreign_competencia(
    base_setup: ResultadoServiceSetup,
) -> None:
    foreign_competencia = Competencia(
        id=uuid.uuid4(),
        programa_id=uuid.uuid4(),
        codigo_competencia="C3",
        nombre_competencia="Comp externa",
        orden=1,
        estado=EstadoBloque.BORRADOR,
        origen_campo=EstadoCampo.MANUAL,
    )
    service, *_ = build_service(
        drafts=[base_setup.draft],
        competencias=[foreign_competencia],
    )

    with pytest.raises(ResultadoAprendizajeCompetenciaNotFoundError):
        await service.list_resultados(
            base_setup.referencia_id,
            foreign_competencia.id,
        )

    with pytest.raises(ResultadoAprendizajeCompetenciaNotFoundError):
        await service.create_resultado(
            base_setup.referencia_id,
            foreign_competencia.id,
            ResultadoAprendizajePayloadDTO(descripcion="No debe guardarse"),
        )


@pytest.mark.anyio
async def test_update_and_delete_reject_resultado_from_other_competencia(
    base_setup: ResultadoServiceSetup,
) -> None:
    other_competencia_id = uuid.uuid4()
    resultado = build_resultado(
        other_competencia_id,
        descripcion="Resultado ajeno",
    )
    service, *_ = build_service(
        drafts=[base_setup.draft],
        competencias=[base_setup.competencia],
        resultados=[resultado],
    )

    with pytest.raises(ResultadoAprendizajeNotFoundError):
        await service.update_resultado(
            base_setup.referencia_id,
            base_setup.competencia.id,
            resultado.id,
            ResultadoAprendizajePayloadDTO(descripcion="Intento invalido"),
        )

    with pytest.raises(ResultadoAprendizajeNotFoundError):
        await service.delete_resultado(
            base_setup.referencia_id,
            base_setup.competencia.id,
            resultado.id,
        )
