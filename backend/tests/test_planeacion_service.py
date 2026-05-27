"""Tests for PlaneacionPedagogicaService."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.application.dto.planeacion import PlaneacionSaveDTO
from src.application.services.planeacion_service import PlaneacionPedagogicaService
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
from src.infrastructure.db.models.planeacion import PlaneacionPedagogica
from src.infrastructure.db.models.proyecto import ProyectoFormativo
from src.infrastructure.repositories.planeacion import PlaneacionPedagogicaRepository


@pytest.mark.anyio
async def test_obtener_contexto_success() -> None:
    # Arrange
    referencia_id = uuid.uuid4()
    programa_id = uuid.uuid4()
    proyecto_id = uuid.uuid4()

    session = AsyncMock()

    # Draft mock
    draft = BorradorSesion(
        tipo_bloque=TipoBloqueBorrador.PROGRAMA.value,
        referencia_id=referencia_id,
        paso_actual="revision-programa",
        payload_json={"curricular": {"programa_formacion_id": str(programa_id)}},
        estado_borrador=EstadoBloque.COMPLETO,
    )

    # Program mock
    programa = ProgramaFormacion(
        codigo_programa="228118",
        nombre_programa="Analisis de software",
    )
    programa.id = programa_id

    competencia = Competencia(
        codigo_competencia="220501046",
        nombre_competencia="Desarrollar software",
    )
    competencia.id = uuid.uuid4()
    competencia.resultados = [
        ResultadoAprendizaje(descripcion="Resultado 1"),
    ]
    competencia.resultados[0].id = uuid.uuid4()
    competencia.conocimientos = [
        Conocimiento(tipo=TipoConocimiento.SABER, descripcion="Saber 1"),
        Conocimiento(tipo=TipoConocimiento.PROCESO, descripcion="Proceso 1"),
    ]
    competencia.conocimientos[0].id = uuid.uuid4()
    competencia.conocimientos[1].id = uuid.uuid4()
    competencia.criterios = [
        CriterioEvaluacion(descripcion="Criterio 1"),
    ]
    competencia.criterios[0].id = uuid.uuid4()

    programa.competencias = [competencia]

    # Project mock
    proyecto = ProyectoFormativo(
        codigo_proyecto="PR-001",
        nombre_proyecto="Proyecto test",
        version_proyecto="1",
        estado=EstadoBloque.BORRADOR,  # Not blocked
    )
    proyecto.id = proyecto_id
    proyecto.fases = []

    # Configure session execution mocks
    mock_draft_result = MagicMock()
    mock_draft_result.scalar_one_or_none.return_value = draft

    mock_proj_result = MagicMock()
    mock_proj_result.scalar_one_or_none.return_value = proyecto

    session.execute.side_effect = [
        mock_draft_result,  # draft lookup
        mock_proj_result,  # project lookup
    ]
    session.get.return_value = programa

    repository = MagicMock(spec=PlaneacionPedagogicaRepository)
    storage_service = AsyncMock()

    service = PlaneacionPedagogicaService(
        session=session,
        repository=repository,
        storage_service=storage_service,
    )

    # Act
    contexto = await service.obtener_contexto(referencia_id)

    # Assert
    assert contexto.programa_id == programa_id
    assert contexto.proyecto_id == proyecto_id
    assert len(contexto.competencias) == 1
    assert contexto.competencias[0].nombre_competencia == "Desarrollar software"
    assert len(contexto.competencias[0].resultados) == 1
    assert len(contexto.competencias[0].conocimientos_saber) == 1
    assert len(contexto.competencias[0].conocimientos_proceso) == 1
    assert len(contexto.competencias[0].criterios) == 1


@pytest.mark.anyio
async def test_guardar_borrador_creates_new_record() -> None:
    # Arrange
    proyecto_id = uuid.uuid4()
    competencia_id = uuid.uuid4()
    resultado_id = uuid.uuid4()

    session = AsyncMock()
    session.add = MagicMock()

    dto = PlaneacionSaveDTO(
        proyecto_id=proyecto_id,
        competencia_id=competencia_id,
        resultados_ids=[resultado_id],
        conocimientos_ids=[],
        criterios_ids=[],
        datos_complementarios={"estrategias_didacticas": "Estrategia de prueba"},
    )

    # Mock DB relations query
    mock_res_query = MagicMock()
    mock_res_query.scalars.return_value.all.return_value = [
        ResultadoAprendizaje(descripcion="Resultado 1"),
    ]
    session.execute.return_value = mock_res_query

    # Repo mocks
    repository = AsyncMock(spec=PlaneacionPedagogicaRepository)
    repository.get_by_proyecto_and_competencia.return_value = None

    # Re-fetch mock after save
    created_planning = PlaneacionPedagogica(
        proyecto_id=proyecto_id,
        competencia_id=competencia_id,
    )
    created_planning.id = uuid.uuid4()

    res_obj = ResultadoAprendizaje(descripcion="Resultado 1")
    res_obj.id = resultado_id
    created_planning.resultados = [res_obj]

    created_planning.conocimientos = []
    created_planning.criterios = []
    created_planning.competencia = Competencia(
        codigo_competencia="C-01",
        nombre_competencia="Competencia 1",
    )
    created_planning.estado = EstadoBloque.BORRADOR
    created_planning.datos_complementarios = {
        "estrategias_didacticas": "Estrategia de prueba"
    }
    created_planning.version = 1

    repository.get_by_id.return_value = created_planning

    storage_service = AsyncMock()

    service = PlaneacionPedagogicaService(
        session=session,
        repository=repository,
        storage_service=storage_service,
    )

    # Act
    res = await service.guardar_borrador(dto)

    # Assert
    assert res.proyecto_id == proyecto_id
    assert res.competencia_id == competencia_id
    assert res.estado == "BORRADOR"
    assert res.datos_complementarios["estrategias_didacticas"] == "Estrategia de prueba"
    assert len(res.resultados_ids) == 1
    repository.save.assert_called_once()


@pytest.mark.anyio
async def test_confirmar_y_generar_uploads_to_storage() -> None:
    # Arrange
    planeacion_id = uuid.uuid4()
    proyecto_id = uuid.uuid4()
    programa_id = uuid.uuid4()
    competencia_id = uuid.uuid4()

    session = AsyncMock()

    # Model mock
    proyecto = ProyectoFormativo(
        codigo_proyecto="PR-01",
        nombre_proyecto="Proyecto 1",
        version_proyecto="1",
    )
    proyecto.id = proyecto_id
    proyecto.programa_id = programa_id

    competencia = Competencia(
        codigo_competencia="220501046",
        nombre_competencia="Desarrollar software",
    )
    competencia.id = competencia_id

    planning = PlaneacionPedagogica(
        proyecto_id=proyecto_id,
        competencia_id=competencia_id,
    )
    planning.id = planeacion_id
    planning.proyecto = proyecto
    planning.competencia = competencia
    planning.resultados = []
    planning.conocimientos = []
    planning.criterios = []
    planning.datos_complementarios = {"horas": 40}
    planning.version = 1

    repository = AsyncMock(spec=PlaneacionPedagogicaRepository)
    repository.get_by_id.return_value = planning

    storage_service = AsyncMock()

    service = PlaneacionPedagogicaService(
        session=session,
        repository=repository,
        storage_service=storage_service,
    )

    # Act
    res = await service.confirmar_y_generar(planeacion_id)

    # Assert
    assert res.estado == "COMPLETO"
    assert res.storage_key is not None
    assert "planeaciones-pedagogicas/" in res.storage_key
    assert res.file_name == f"planeacion_{competencia.codigo_competencia}.json"

    # Verify MinIO upload call
    storage_service.save_pdf.assert_called_once()
    assert storage_service.save_pdf.call_args[1]["key"] == res.storage_key
    assert storage_service.save_pdf.call_args[1]["content_type"] == "application/json"
    repository.save.assert_called_once()
