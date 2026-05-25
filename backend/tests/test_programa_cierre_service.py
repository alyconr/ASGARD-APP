"""Unit tests for TASK-14 program completion validation and closing."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest

from src.application.services.programa_cierre import (
    ProgramaCierreService,
    ProgramaCierreValidationError,
)
from src.domain.drafts.types import TipoBloqueBorrador
from src.domain.shared.enums import (
    EstadoBloque,
    EstadoCampo,
    TipoConocimiento,
    TipoFuenteCargue,
)
from src.infrastructure.db.models.curriculum import (
    Competencia,
    Conocimiento,
    CriterioEvaluacion,
    ProgramaFormacion,
    ResultadoAprendizaje,
)
from src.infrastructure.db.models.drafts import BorradorSesion


class FakeSession:
    """Minimal async session double used by the close service."""

    def __init__(self) -> None:
        """Track commit calls."""
        self.commits = 0

    async def commit(self) -> None:
        """Record a commit invocation."""
        self.commits += 1

    async def refresh(self, instance: object) -> None:
        """Refresh timestamps expected by callers."""
        now = datetime.now(UTC)
        if hasattr(instance, "fecha_actualizacion"):
            setattr(instance, "fecha_actualizacion", now)
        if isinstance(instance, BorradorSesion):
            instance.ultima_edicion = now


class FakeDraftRepository:
    """In-memory draft storage keyed by stable reference."""

    def __init__(self, draft: BorradorSesion) -> None:
        """Store a single draft."""
        self.draft = draft

    async def get_by_block_reference(
        self,
        tipo_bloque: TipoBloqueBorrador,
        referencia_id: uuid.UUID,
    ) -> BorradorSesion | None:
        """Return the program draft when the logical key matches."""
        if (
            tipo_bloque is TipoBloqueBorrador.PROGRAMA
            and self.draft.referencia_id == referencia_id
        ):
            return self.draft
        return None

    async def save(self, draft: BorradorSesion) -> BorradorSesion:
        """Persist draft changes."""
        self.draft = draft
        return draft


class FakeProgramaCierreRepository:
    """In-memory program aggregate repository."""

    def __init__(self, programa: ProgramaFormacion | None) -> None:
        """Store the program aggregate."""
        self.programa = programa

    async def get_programa_with_curriculum(
        self,
        programa_id: uuid.UUID,
    ) -> ProgramaFormacion | None:
        """Return the stored program when ids match."""
        if self.programa is None or self.programa.id != programa_id:
            return None
        return self.programa

    async def save_programa(self, programa: ProgramaFormacion) -> ProgramaFormacion:
        """Persist program changes."""
        self.programa = programa
        return programa


class FakeAuditRepository:
    """Collect audit events emitted by the close service."""

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
    programa_id: uuid.UUID | None,
    *,
    codigo_programa: str = "228118",
    nombre_programa: str = "Analisis y desarrollo de software",
) -> BorradorSesion:
    """Create a program draft tied to a stable reference."""
    draft = BorradorSesion(
        tipo_bloque=TipoBloqueBorrador.PROGRAMA.value,
        referencia_id=referencia_id,
        paso_actual="revision-programa",
        payload_json={
            "meta": {
                "referenciaId": str(referencia_id),
                "entryMode": "EXCEL",
                "touchedSteps": ["origen-documental", "revision-programa"],
            },
            "programa": {
                "codigo_programa": codigo_programa,
                "nombre_programa": nombre_programa,
                "version_programa": "",
            },
            "documental": {"programa_pdf": None, "programa_excel": None},
            "curricular": {
                "programa_formacion_id": str(programa_id) if programa_id else None,
                "competencias": [],
            },
        },
        estado_borrador=EstadoBloque.BORRADOR,
    )
    draft.id = uuid.uuid4()
    draft.ultima_edicion = datetime.now(UTC)
    return draft


def build_programa(
    *,
    codigo_programa: str = "228118",
    nombre_programa: str = "Analisis y desarrollo de software",
) -> ProgramaFormacion:
    """Create a program aggregate."""
    now = datetime.now(UTC)
    programa = ProgramaFormacion(
        codigo_programa=codigo_programa,
        nombre_programa=nombre_programa,
        version_programa=None,
        estado=EstadoBloque.BORRADOR,
        fuente_cargue=TipoFuenteCargue.MIXTO,
    )
    programa.id = uuid.uuid4()
    programa.fecha_creacion = now
    programa.fecha_actualizacion = now
    programa.competencias = []
    return programa


def build_competencia(
    programa_id: uuid.UUID,
    *,
    nombre_competencia: str = "Desarrollar software",
    codigo_competencia: str = "220501046",
    resultados: int = 1,
    saberes: int = 1,
    procesos: int = 1,
    criterios: int = 1,
) -> Competencia:
    """Create a competence with configurable curricular children."""
    now = datetime.now(UTC)
    competencia = Competencia(
        programa_id=programa_id,
        codigo_competencia=codigo_competencia,
        nombre_competencia=nombre_competencia,
        orden=1,
        estado=EstadoBloque.BORRADOR,
        origen_campo=EstadoCampo.MANUAL,
    )
    competencia.id = uuid.uuid4()
    competencia.fecha_creacion = now
    competencia.fecha_actualizacion = now
    competencia.resultados = [
        _resultado(competencia.id, f"Resultado {index}")
        for index in range(resultados)
    ]
    competencia.conocimientos = [
        _conocimiento(competencia.id, TipoConocimiento.SABER, f"Saber {index}")
        for index in range(saberes)
    ] + [
        _conocimiento(competencia.id, TipoConocimiento.PROCESO, f"Proceso {index}")
        for index in range(procesos)
    ]
    competencia.criterios = [
        _criterio(competencia.id, f"Criterio {index}") for index in range(criterios)
    ]
    return competencia


def _resultado(competencia_id: uuid.UUID, descripcion: str) -> ResultadoAprendizaje:
    item = ResultadoAprendizaje(
        competencia_id=competencia_id,
        codigo_resultado=None,
        descripcion=descripcion,
        orden=1,
        estado=EstadoCampo.MANUAL,
    )
    item.id = uuid.uuid4()
    return item


def _conocimiento(
    competencia_id: uuid.UUID,
    tipo: TipoConocimiento,
    descripcion: str,
) -> Conocimiento:
    item = Conocimiento(
        competencia_id=competencia_id,
        tipo=tipo,
        descripcion=descripcion,
        orden=1,
        estado=EstadoCampo.MANUAL,
    )
    item.id = uuid.uuid4()
    return item


def _criterio(competencia_id: uuid.UUID, descripcion: str) -> CriterioEvaluacion:
    item = CriterioEvaluacion(
        competencia_id=competencia_id,
        descripcion=descripcion,
        orden=1,
        estado=EstadoCampo.MANUAL,
    )
    item.id = uuid.uuid4()
    return item


def build_service(
    programa: ProgramaFormacion | None,
    *,
    codigo_programa: str = "228118",
    nombre_programa: str = "Analisis y desarrollo de software",
) -> tuple[
    ProgramaCierreService,
    FakeSession,
    FakeDraftRepository,
    FakeProgramaCierreRepository,
    FakeAuditRepository,
]:
    """Build the service with fake dependencies."""
    referencia_id = uuid.uuid4()
    draft = build_draft(
        referencia_id,
        programa.id if programa is not None else None,
        codigo_programa=codigo_programa,
        nombre_programa=nombre_programa,
    )
    session = FakeSession()
    drafts = FakeDraftRepository(draft)
    repository = FakeProgramaCierreRepository(programa)
    audit = FakeAuditRepository()
    service = ProgramaCierreService(session, drafts, repository, audit)
    return service, session, drafts, repository, audit


@pytest.mark.anyio
async def test_validacion_falla_si_falta_codigo() -> None:
    """The validator should report a missing program code."""
    programa = build_programa(codigo_programa=" ")
    service, _, drafts, _, _ = build_service(programa, codigo_programa=" ")

    result = await service.validar_completitud(drafts.draft.referencia_id)

    assert result.cerrable is False
    assert any(item.campo == "codigo_programa" for item in result.faltantes)


@pytest.mark.anyio
async def test_validacion_falla_si_falta_nombre() -> None:
    """The validator should report a missing program name."""
    programa = build_programa(nombre_programa=" ")
    service, _, drafts, _, _ = build_service(programa, nombre_programa=" ")

    result = await service.validar_completitud(drafts.draft.referencia_id)

    assert result.cerrable is False
    assert any(item.campo == "nombre_programa" for item in result.faltantes)


@pytest.mark.anyio
async def test_validacion_falla_si_no_hay_competencias() -> None:
    """The validator should require at least one competence."""
    programa = build_programa()
    service, _, drafts, _, _ = build_service(programa)

    result = await service.validar_completitud(drafts.draft.referencia_id)

    assert result.cerrable is False
    assert any(item.campo == "competencias" for item in result.faltantes)


@pytest.mark.anyio
async def test_validacion_falla_si_falta_estructura_curricular_minima() -> None:
    """A non-practical competence must have result, saber, process and criteria."""
    programa = build_programa()
    programa.competencias = [
        build_competencia(
            programa.id,
            resultados=0,
            saberes=0,
            procesos=0,
            criterios=0,
        )
    ]
    service, _, drafts, _, _ = build_service(programa)

    result = await service.validar_completitud(drafts.draft.referencia_id)

    campos = {item.campo for item in result.faltantes}
    assert result.cerrable is False
    required_fields = {
        "resultados",
        "conocimientos_saber",
        "conocimientos_proceso",
        "criterios",
    }
    assert required_fields.issubset(campos)


@pytest.mark.anyio
async def test_validacion_pasa_con_estructura_completa_y_etapa_practica() -> None:
    """A complete regular competence may coexist with empty practical stage."""
    programa = build_programa()
    programa.competencias = [
        build_competencia(programa.id),
        build_competencia(
            programa.id,
            codigo_competencia="999999999",
            nombre_competencia="Aplicar etapa practica",
            resultados=0,
            saberes=0,
            procesos=0,
            criterios=0,
        ),
    ]
    service, _, drafts, _, _ = build_service(programa)

    result = await service.validar_completitud(drafts.draft.referencia_id)

    assert result.cerrable is True
    assert result.faltantes == []


@pytest.mark.anyio
async def test_validacion_pasa_con_estructura_completa_y_etapa_productiva() -> None:
    """A complete regular competence may coexist with empty practical stage named etapa productiva with standard code."""
    programa = build_programa()
    programa.competencias = [
        build_competencia(programa.id),
        build_competencia(
            programa.id,
            codigo_competencia="220501046",
            nombre_competencia="REGISTRAR ETAPA PRODUCTIVA DEL APRENDIZ",
            resultados=0,
            saberes=0,
            procesos=0,
            criterios=0,
        ),
    ]
    service, _, drafts, _, _ = build_service(programa)

    result = await service.validar_completitud(drafts.draft.referencia_id)

    assert result.cerrable is True
    assert result.faltantes == []


@pytest.mark.anyio
async def test_cierre_rechaza_programa_incompleto() -> None:
    """Closing should reject an incomplete program with structured details."""
    programa = build_programa()
    service, session, drafts, repository, audit = build_service(programa)

    with pytest.raises(ProgramaCierreValidationError) as exc_info:
        await service.cerrar_programa(drafts.draft.referencia_id)

    assert exc_info.value.completitud.cerrable is False
    assert repository.programa is not None
    assert repository.programa.estado is EstadoBloque.BORRADOR
    assert drafts.draft.estado_borrador is EstadoBloque.BORRADOR
    assert audit.events == []
    assert session.commits == 0


@pytest.mark.anyio
async def test_cierre_cambia_estado_a_completo() -> None:
    """Closing a complete program should update program and draft states."""
    programa = build_programa()
    programa.competencias = [build_competencia(programa.id)]
    service, session, drafts, repository, audit = build_service(programa)

    result = await service.cerrar_programa(drafts.draft.referencia_id)

    assert result.estado is EstadoBloque.COMPLETO
    assert repository.programa is not None
    assert repository.programa.estado is EstadoBloque.COMPLETO
    assert drafts.draft.estado_borrador is EstadoBloque.COMPLETO
    assert drafts.draft.paso_actual == "revision-programa"
    assert audit.events[0]["accion"] == "PROGRAMA_CERRADO"
    assert session.commits == 1
