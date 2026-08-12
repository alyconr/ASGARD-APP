"""Tests for the master dashboard aggregation service."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.application.services.dashboard import DashboardService
from src.domain.drafts.types import TipoBloqueBorrador
from src.domain.shared.enums import EstadoBloque, TipoConocimiento
from src.infrastructure.db.models.curriculum import (
    Competencia,
    Conocimiento,
    CriterioEvaluacion,
    ProgramaFormacion,
    ResultadoAprendizaje,
)
from src.infrastructure.db.models.drafts import BorradorSesion
from src.infrastructure.db.models.proyecto import (
    ActividadProyecto,
    FaseProyecto,
    ProyectoFormativo,
)


def _scalar_result(value: object) -> MagicMock:
    result = MagicMock()
    result.scalar_one_or_none.return_value = value
    result.scalars.return_value.first.return_value = value
    return result


def _scalars_result(values: list[object]) -> MagicMock:
    scalars = MagicMock()
    scalars.all.return_value = values
    mappings = MagicMock()
    mappings.all.return_value = values
    result = MagicMock()
    result.scalars.return_value = scalars
    result.mappings.return_value = mappings
    return result


def _program_draft(
    referencia_id: uuid.UUID,
    programa_id: uuid.UUID,
    estado: EstadoBloque,
) -> BorradorSesion:
    draft = BorradorSesion(
        tipo_bloque=TipoBloqueBorrador.PROGRAMA.value,
        referencia_id=referencia_id,
        paso_actual="revision-programa",
        payload_json={"curricular": {"programa_formacion_id": str(programa_id)}},
        estado_borrador=estado,
    )
    draft.id = uuid.uuid4()
    return draft


def _programa(estado: EstadoBloque) -> ProgramaFormacion:
    programa = ProgramaFormacion(
        codigo_programa="228118",
        nombre_programa="Analisis de software",
        estado=estado,
    )
    programa.id = uuid.uuid4()
    competencia = Competencia(
        codigo_competencia="220501046",
        nombre_competencia="Desarrollar software",
    )
    competencia.id = uuid.uuid4()
    resultado = ResultadoAprendizaje(descripcion="Resultado 1")
    resultado.id = uuid.uuid4()
    saber = Conocimiento(tipo=TipoConocimiento.SABER, descripcion="Saber 1")
    saber.id = uuid.uuid4()
    proceso = Conocimiento(tipo=TipoConocimiento.PROCESO, descripcion="Proceso 1")
    proceso.id = uuid.uuid4()
    criterio = CriterioEvaluacion(descripcion="Criterio 1")
    criterio.id = uuid.uuid4()
    competencia.resultados = [resultado]
    competencia.conocimientos = [saber, proceso]
    competencia.criterios = [criterio]
    programa.competencias = [competencia]
    return programa


def _proyecto(programa_id: uuid.UUID, estado: EstadoBloque) -> ProyectoFormativo:
    proyecto = ProyectoFormativo(
        programa_id=programa_id,
        codigo_proyecto="PR-001",
        nombre_proyecto="Proyecto formativo",
        version_proyecto="1",
        estado=estado,
    )
    proyecto.id = uuid.uuid4()
    fase = FaseProyecto(
        proyecto_id=proyecto.id,
        nombre_fase="Analisis",
        orden=1,
    )
    fase.id = uuid.uuid4()
    actividad = ActividadProyecto(
        fase_id=fase.id,
        descripcion="Levantar requerimientos",
        orden=1,
    )
    actividad.id = uuid.uuid4()
    fase.actividades = [actividad]
    proyecto.fases = [fase]
    return proyecto


@pytest.mark.anyio
async def test_dashboard_bloquea_proyecto_y_planeacion_hasta_programa() -> None:
    referencia_id = uuid.uuid4()
    programa = _programa(EstadoBloque.EN_REVISION)
    draft = _program_draft(referencia_id, programa.id, EstadoBloque.EN_REVISION)

    session = AsyncMock()
    session.get.return_value = programa
    session.execute.side_effect = [
        _scalar_result(draft),
        _scalar_result(None),
    ]

    dashboard = await DashboardService(session).consultar(referencia_id)

    modules = {module.id: module for module in dashboard.modules}
    assert dashboard.estado_global == "PROGRAMA_EN_CURSO"
    assert modules["programa"].disponible is True
    assert modules["proyecto"].disponible is False
    assert modules["proyecto"].motivo_bloqueo == "PROGRAMA_NO_COMPLETO"
    assert modules["planeacion"].disponible is False
    assert modules["planeacion"].motivo_bloqueo == "PROGRAMA_NO_COMPLETO"
    assert dashboard.metricas.programa.competencias == 1
    assert dashboard.metricas.proyecto.estado == EstadoBloque.BLOQUEADO.value
    assert dashboard.graph_edges[1].estado == "BLOQUEADA"


@pytest.mark.anyio
async def test_dashboard_habilita_planeacion_solo_con_proyecto_completo() -> None:
    referencia_id = uuid.uuid4()
    programa = _programa(EstadoBloque.COMPLETO)
    proyecto = _proyecto(programa.id, EstadoBloque.COMPLETO)
    draft = _program_draft(referencia_id, programa.id, EstadoBloque.COMPLETO)
    planeacion = {
        "planeacion_id": uuid.uuid4(),
        "competencia_id": programa.competencias[0].id,
        "resultado_id": programa.competencias[0].resultados[0].id,
        "actividad_id": proyecto.fases[0].actividades[0].id,
        "tipo_resultado": "ESPECIFICO",
        "estado": EstadoBloque.COMPLETO,
    }

    session = AsyncMock()
    session.get.return_value = programa
    session.execute.side_effect = [
        _scalar_result(draft),
        _scalar_result(proyecto),
        _scalars_result([planeacion]),
    ]

    dashboard = await DashboardService(session).consultar(referencia_id)

    modules = {module.id: module for module in dashboard.modules}
    assert dashboard.estado_global == "PLANEACION_EN_CURSO"
    assert modules["proyecto"].disponible is True
    assert modules["planeacion"].disponible is True
    assert dashboard.metricas.proyecto.fases == 1
    assert dashboard.metricas.proyecto.actividades == 1
    assert dashboard.metricas.planeacion.completas == 1
    assert dashboard.metricas.planeacion.competencias_sin_planear == 0
    assert dashboard.graph_nodes[-1].href == f"/planeacion/{referencia_id}"
    assert dashboard.graph_edges[-1].estado == "ACTIVA"


@pytest.mark.anyio
async def test_dashboard_tolera_borrador_sin_programa_importado() -> None:
    referencia_id = uuid.uuid4()
    draft = BorradorSesion(
        tipo_bloque=TipoBloqueBorrador.PROGRAMA.value,
        referencia_id=referencia_id,
        paso_actual="origen-documental",
        payload_json={},
        estado_borrador=EstadoBloque.BORRADOR,
    )
    draft.id = uuid.uuid4()

    session = AsyncMock()
    session.execute.return_value = _scalar_result(draft)

    dashboard = await DashboardService(session).consultar(referencia_id)

    modules = {module.id: module for module in dashboard.modules}
    assert dashboard.estado_global == "PROGRAMA_EN_CURSO"
    assert dashboard.metricas.programa.competencias == 0
    assert modules["programa"].disponible is True
    assert modules["proyecto"].disponible is False
    session.get.assert_not_called()


@pytest.mark.anyio
async def test_dashboard_lista_flujos_abiertos_de_programa() -> None:
    referencia_id = uuid.uuid4()
    programa = _programa(EstadoBloque.EN_REVISION)
    draft = _program_draft(referencia_id, programa.id, EstadoBloque.EN_REVISION)
    draft.ultima_edicion = datetime(2026, 6, 18, 9, 30, tzinfo=timezone.utc)

    session = AsyncMock()
    session.execute.return_value = _scalars_result([draft])
    session.get.return_value = programa

    flows = await DashboardService(session).listar_flujos_programa()

    assert len(flows) == 1
    assert flows[0].referencia_id == referencia_id
    assert flows[0].estado == EstadoBloque.EN_REVISION.value
    assert flows[0].paso_actual == "revision-programa"
    assert flows[0].codigo_programa == "228118"
    assert flows[0].nombre_programa == "Analisis de software"
    assert flows[0].titulo == "Analisis de software / 228118"
    assert flows[0].href == f"/programa?referencia_id={referencia_id}"


@pytest.mark.anyio
async def test_dashboard_elimina_flujo_abierto_de_programa() -> None:
    referencia_id = uuid.uuid4()
    programa = _programa(EstadoBloque.EN_REVISION)
    program_draft = _program_draft(
        referencia_id,
        programa.id,
        EstadoBloque.EN_REVISION,
    )
    project_draft = BorradorSesion(
        tipo_bloque=TipoBloqueBorrador.PROYECTO.value,
        referencia_id=referencia_id,
        paso_actual="fuente-proyecto",
        payload_json={},
        estado_borrador=EstadoBloque.BORRADOR,
    )
    project_draft.id = uuid.uuid4()

    session = AsyncMock()
    session.execute.side_effect = [
        _scalar_result(program_draft),
        _scalars_result([program_draft, project_draft]),
    ]
    cleanup_service = AsyncMock()

    await DashboardService(
        session,
        cleanup_service=cleanup_service,
    ).eliminar_flujo_programa(referencia_id)

    cleanup_service.eliminar_cargue_completo.assert_awaited_once_with(referencia_id)
    assert session.delete.await_count == 2
    session.delete.assert_any_await(program_draft)
    session.delete.assert_any_await(project_draft)
    session.commit.assert_awaited_once()
