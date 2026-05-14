"""Tests for TASK-10 SABER knowledge CRUD application service."""

import datetime
import uuid
from copy import deepcopy
from dataclasses import dataclass
from typing import cast

import pytest

from src.application.dto.conocimientos_saber import ConocimientoSaberPayloadDTO
from src.application.services.conocimientos_saber import (
    ConocimientoSaberCompetenciaNotFoundError,
    ConocimientoSaberDuplicateError,
    ConocimientoSaberNotFoundError,
    ConocimientoSaberValidationError,
    ProgramaConocimientoSaberService,
)
from src.domain.drafts.types import TipoBloqueBorrador
from src.domain.shared.enums import EstadoBloque, EstadoCampo, TipoConocimiento
from src.infrastructure.db.models.curriculum import Competencia, Conocimiento
from src.infrastructure.db.models.drafts import BorradorSesion


class FakeConocimientoSaberRepository:
    def __init__(
        self,
        competencias: list[Competencia],
        conocimientos: list[Conocimiento],
    ) -> None:
        self.competencias = competencias
        self.conocimientos = conocimientos

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
    ) -> list[Conocimiento]:
        return [
            c
            for c in self.conocimientos
            if c.competencia_id == competencia_id
            and c.tipo == TipoConocimiento.SABER
        ]

    async def get_by_id_for_competencia(
        self,
        conocimiento_id: uuid.UUID,
        competencia_id: uuid.UUID,
    ) -> Conocimiento | None:
        for c in self.conocimientos:
            if (
                c.id == conocimiento_id
                and c.competencia_id == competencia_id
                and c.tipo == TipoConocimiento.SABER
            ):
                return c
        return None

    async def descripcion_exists(
        self,
        competencia_id: uuid.UUID,
        descripcion: str,
        exclude_conocimiento_id: uuid.UUID | None = None,
    ) -> bool:
        for c in self.conocimientos:
            if (
                c.competencia_id == competencia_id
                and c.tipo == TipoConocimiento.SABER
                and c.descripcion.lower() == descripcion.lower()
                and (exclude_conocimiento_id is None or c.id != exclude_conocimiento_id)
            ):
                return True
        return False

    async def add_conocimiento(
        self,
        competencia_id: uuid.UUID,
        descripcion: str,
        orden: int,
    ) -> Conocimiento:
        conocimiento = build_conocimiento(
            competencia_id=competencia_id,
            descripcion=descripcion,
            orden=orden,
            tipo=TipoConocimiento.SABER,
        )
        self.conocimientos.append(conocimiento)
        return conocimiento

    async def save_conocimiento(self, conocimiento: Conocimiento) -> Conocimiento:
        for i, item in enumerate(self.conocimientos):
            if item.id == conocimiento.id:
                self.conocimientos[i] = conocimiento
                return conocimiento
        return conocimiento

    async def delete_conocimiento(self, conocimiento: Conocimiento) -> None:
        self.conocimientos = [
            item for item in self.conocimientos if item.id != conocimiento.id
        ]


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
class ConocimientoSaberServiceSetup:
    referencia_id: uuid.UUID
    programa_id: uuid.UUID
    competencia_id: uuid.UUID
    draft: BorradorSesion
    competencia: Competencia


def build_conocimiento(
    competencia_id: uuid.UUID,
    descripcion: str = "Conocimiento base",
    tipo: TipoConocimiento = TipoConocimiento.SABER,
    orden: int = 1,
) -> Conocimiento:
    conocimiento = Conocimiento(
        id=uuid.uuid4(),
        competencia_id=competencia_id,
        resultado_id=None,
        tipo=tipo,
        descripcion=descripcion,
        orden=orden,
        estado=EstadoCampo.MANUAL,
    )
    conocimiento.fecha_creacion = datetime.datetime.now(datetime.UTC)
    conocimiento.fecha_actualizacion = datetime.datetime.now(datetime.UTC)
    return conocimiento


@pytest.fixture
def base_setup() -> ConocimientoSaberServiceSetup:
    referencia_id = uuid.uuid4()
    programa_id = uuid.uuid4()
    competencia_id = uuid.uuid4()
    proceso_payload_id = uuid.uuid4()
    draft = BorradorSesion(
        id=uuid.uuid4(),
        referencia_id=referencia_id,
        tipo_bloque=TipoBloqueBorrador.PROGRAMA,
        estado_borrador=EstadoBloque.BORRADOR,
        paso_actual="competencias",
        payload_json={
            "curricular": {
                "programa_formacion_id": str(programa_id),
                "competencias": [
                    {
                        "id": str(competencia_id),
                        "conocimientos": [
                            {
                                "id": str(proceso_payload_id),
                                "competencia_id": str(competencia_id),
                                "resultado_id": None,
                                "tipo": "PROCESO",
                                "descripcion": "Proceso importado",
                                "orden": 1,
                                "estado": "VALIDADO",
                                "fecha_creacion": "2026-05-13T00:00:00+00:00",
                                "fecha_actualizacion": "2026-05-13T00:00:00+00:00",
                            }
                        ],
                    }
                ],
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
    return ConocimientoSaberServiceSetup(
        referencia_id=referencia_id,
        programa_id=programa_id,
        competencia_id=competencia_id,
        draft=draft,
        competencia=competencia,
    )


def build_service(
    drafts: list[BorradorSesion] | None = None,
    competencias: list[Competencia] | None = None,
    conocimientos: list[Conocimiento] | None = None,
) -> tuple[
    ProgramaConocimientoSaberService,
    FakeDraftRepository,
    FakeConocimientoSaberRepository,
    FakeAuditRepository,
]:
    draft_repo = FakeDraftRepository(drafts or [])
    conocimiento_repo = FakeConocimientoSaberRepository(
        competencias or [], conocimientos or []
    )
    audit_repo = FakeAuditRepository()
    session = FakeSession()
    service = ProgramaConocimientoSaberService(
        session, conocimiento_repo, draft_repo, audit_repo
    )
    return service, draft_repo, conocimiento_repo, audit_repo


@pytest.mark.anyio
async def test_create_conocimiento_saber(
    base_setup: ConocimientoSaberServiceSetup,
) -> None:
    service, draft_repo, *_ = build_service(
        drafts=[base_setup.draft],
        competencias=[base_setup.competencia],
    )

    dto = await service.create_conocimiento(
        base_setup.referencia_id,
        base_setup.competencia.id,
        ConocimientoSaberPayloadDTO(descripcion=" Arquitectura limpia "),
    )

    assert len(dto.conocimientos) == 1
    assert dto.conocimientos[0].tipo == TipoConocimiento.SABER
    assert dto.conocimientos[0].descripcion == "Arquitectura limpia"
    assert dto.conocimientos[0].resultado_id is None

    updated_draft = await draft_repo.get_by_block_reference(
        TipoBloqueBorrador.PROGRAMA, base_setup.referencia_id
    )
    assert updated_draft is not None
    curricular = cast(dict[str, object], updated_draft.payload_json["curricular"])
    payload_comps = cast(list[dict[str, object]], curricular["competencias"])
    conocimientos = cast(list[dict[str, object]], payload_comps[0]["conocimientos"])
    assert {item["tipo"] for item in conocimientos} == {"SABER", "PROCESO"}


@pytest.mark.anyio
async def test_create_conocimiento_saber_rejects_blank_description(
    base_setup: ConocimientoSaberServiceSetup,
) -> None:
    service, *_ = build_service(
        drafts=[base_setup.draft],
        competencias=[base_setup.competencia],
    )

    with pytest.raises(ConocimientoSaberValidationError):
        await service.create_conocimiento(
            base_setup.referencia_id,
            base_setup.competencia.id,
            ConocimientoSaberPayloadDTO(descripcion="   "),
        )


@pytest.mark.anyio
async def test_create_conocimiento_saber_duplicate(
    base_setup: ConocimientoSaberServiceSetup,
) -> None:
    existing = build_conocimiento(
        base_setup.competencia.id,
        descripcion="Base de datos",
    )
    service, *_ = build_service(
        drafts=[base_setup.draft],
        competencias=[base_setup.competencia],
        conocimientos=[existing],
    )

    with pytest.raises(ConocimientoSaberDuplicateError):
        await service.create_conocimiento(
            base_setup.referencia_id,
            base_setup.competencia.id,
            ConocimientoSaberPayloadDTO(descripcion="base de datos"),
        )


@pytest.mark.anyio
async def test_create_conocimiento_saber_allows_same_description_in_other_competencia(
    base_setup: ConocimientoSaberServiceSetup,
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
    existing = build_conocimiento(
        base_setup.competencia.id,
        descripcion="Base compartida",
    )
    service, *_ = build_service(
        drafts=[base_setup.draft],
        competencias=[base_setup.competencia, other_competencia],
        conocimientos=[existing],
    )

    dto = await service.create_conocimiento(
        base_setup.referencia_id,
        other_competencia.id,
        ConocimientoSaberPayloadDTO(descripcion="Base compartida"),
    )

    assert len(dto.conocimientos) == 1
    assert dto.conocimientos[0].competencia_id == other_competencia.id


@pytest.mark.anyio
async def test_update_conocimiento_saber(
    base_setup: ConocimientoSaberServiceSetup,
) -> None:
    conocimiento = build_conocimiento(base_setup.competencia.id, descripcion="Old")
    service, *_ = build_service(
        drafts=[base_setup.draft],
        competencias=[base_setup.competencia],
        conocimientos=[conocimiento],
    )

    dto = await service.update_conocimiento(
        base_setup.referencia_id,
        base_setup.competencia.id,
        conocimiento.id,
        ConocimientoSaberPayloadDTO(descripcion="New"),
    )

    assert dto.conocimientos[0].descripcion == "New"
    assert dto.conocimientos[0].tipo == TipoConocimiento.SABER


@pytest.mark.anyio
async def test_update_conocimiento_saber_rejects_duplicate(
    base_setup: ConocimientoSaberServiceSetup,
) -> None:
    conocimiento = build_conocimiento(base_setup.competencia.id, descripcion="Old")
    existing = build_conocimiento(base_setup.competencia.id, descripcion="Existing")
    service, *_ = build_service(
        drafts=[base_setup.draft],
        competencias=[base_setup.competencia],
        conocimientos=[conocimiento, existing],
    )

    with pytest.raises(ConocimientoSaberDuplicateError):
        await service.update_conocimiento(
            base_setup.referencia_id,
            base_setup.competencia.id,
            conocimiento.id,
            ConocimientoSaberPayloadDTO(descripcion="existing"),
        )


@pytest.mark.anyio
async def test_delete_conocimiento_saber(
    base_setup: ConocimientoSaberServiceSetup,
) -> None:
    conocimiento = build_conocimiento(base_setup.competencia.id, descripcion="Delete")
    service, draft_repo, conocimiento_repo, _ = build_service(
        drafts=[base_setup.draft],
        competencias=[base_setup.competencia],
        conocimientos=[conocimiento],
    )

    await service.delete_conocimiento(
        base_setup.referencia_id,
        base_setup.competencia.id,
        conocimiento.id,
    )

    assert len(conocimiento_repo.conocimientos) == 0
    updated_draft = await draft_repo.get_by_block_reference(
        TipoBloqueBorrador.PROGRAMA, base_setup.referencia_id
    )
    assert updated_draft is not None
    curricular = cast(dict[str, object], updated_draft.payload_json["curricular"])
    payload_comps = cast(list[dict[str, object]], curricular["competencias"])
    conocimientos = cast(list[dict[str, object]], payload_comps[0]["conocimientos"])
    assert [item["tipo"] for item in conocimientos] == ["PROCESO"]


@pytest.mark.anyio
async def test_operations_reject_unknown_or_foreign_competencia(
    base_setup: ConocimientoSaberServiceSetup,
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

    with pytest.raises(ConocimientoSaberCompetenciaNotFoundError):
        await service.list_conocimientos(
            base_setup.referencia_id,
            foreign_competencia.id,
        )

    with pytest.raises(ConocimientoSaberCompetenciaNotFoundError):
        await service.create_conocimiento(
            base_setup.referencia_id,
            foreign_competencia.id,
            ConocimientoSaberPayloadDTO(descripcion="No debe guardarse"),
        )


@pytest.mark.anyio
async def test_update_and_delete_reject_proceso_or_other_competencia(
    base_setup: ConocimientoSaberServiceSetup,
) -> None:
    proceso = build_conocimiento(
        base_setup.competencia.id,
        descripcion="Proceso ajeno a TASK-10",
        tipo=TipoConocimiento.PROCESO,
    )
    other_competencia_saber = build_conocimiento(
        uuid.uuid4(),
        descripcion="Saber de otra competencia",
    )
    service, *_ = build_service(
        drafts=[base_setup.draft],
        competencias=[base_setup.competencia],
        conocimientos=[proceso, other_competencia_saber],
    )

    with pytest.raises(ConocimientoSaberNotFoundError):
        await service.update_conocimiento(
            base_setup.referencia_id,
            base_setup.competencia.id,
            proceso.id,
            ConocimientoSaberPayloadDTO(descripcion="Intento invalido"),
        )

    with pytest.raises(ConocimientoSaberNotFoundError):
        await service.delete_conocimiento(
            base_setup.referencia_id,
            base_setup.competencia.id,
            other_competencia_saber.id,
        )
