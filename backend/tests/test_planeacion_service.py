"""Tests for PlaneacionPedagogicaService."""

from __future__ import annotations

import uuid
from datetime import date
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.application.dto.planeacion import PlaneacionSaveDTO
from src.application.services.planeacion_formato_excel import (
    EXCEL_CONTENT_TYPE,
    FormatoExcelResultado,
    PlaneacionFormatoExcelService,
)
from src.application.services.planeacion_service import (
    PlaneacionAccessError,
    PlaneacionPedagogicaService,
)
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
from src.infrastructure.db.models.planeacion import (
    PlaneacionDocumentoConfig,
    PlaneacionPedagogica,
)
from src.infrastructure.db.models.proyecto import (
    ActividadProyecto,
    FaseProyecto,
    ProyectoFormativo,
)
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
        version_programa="1",
        estado=EstadoBloque.COMPLETO,
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
        estado=EstadoBloque.COMPLETO,
    )
    proyecto.id = proyecto_id
    proyecto.fases = []

    # Configure session execution mocks
    mock_draft_result = MagicMock()
    mock_draft_result.scalar_one_or_none.return_value = draft

    mock_proj_result = MagicMock()
    mock_proj_result.scalar_one_or_none.return_value = proyecto

    mock_project_drafts_result = MagicMock()
    mock_project_drafts_result.scalars.return_value.all.return_value = []

    session.execute.side_effect = [
        mock_draft_result,  # draft lookup
        mock_proj_result,  # project lookup
        mock_project_drafts_result,  # project drafts lookup
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
    assert contexto.version_programa == "1"
    assert contexto.version_proyecto == "1"
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
        resultado_id=resultado_id,
        resultados_ids=[resultado_id],
        conocimientos_ids=[],
        criterios_ids=[],
        datos_complementarios={"estrategias_didacticas": "Estrategia de prueba"},
    )

    resultado = ResultadoAprendizaje(descripcion="Resultado 1")
    resultado.id = resultado_id
    resultado.competencia_id = competencia_id
    proyecto_completo = ProyectoFormativo(
        codigo_proyecto="PR-01",
        nombre_proyecto="Proyecto completo",
        version_proyecto="1",
        estado=EstadoBloque.COMPLETO,
    )
    proyecto_completo.id = proyecto_id
    session.get.side_effect = [proyecto_completo, resultado]

    # Repo mocks
    repository = AsyncMock(spec=PlaneacionPedagogicaRepository)
    repository.get_by_proyecto_and_resultado.return_value = None

    # Re-fetch mock after save
    created_planning = PlaneacionPedagogica(
        proyecto_id=proyecto_id,
        competencia_id=competencia_id,
        resultado_id=resultado_id,
    )
    created_planning.id = uuid.uuid4()

    created_planning.resultado = resultado
    created_planning.resultados = [resultado]

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
    assert res.resultado_id == resultado_id
    assert res.estado == "BORRADOR"
    assert res.datos_complementarios["estrategias_didacticas"] == "Estrategia de prueba"
    assert len(res.resultados_ids) == 1
    repository.save.assert_called_once()


@pytest.mark.anyio
async def test_guardar_borrador_rechaza_proyecto_no_completo() -> None:
    proyecto_id = uuid.uuid4()
    competencia_id = uuid.uuid4()
    resultado_id = uuid.uuid4()
    session = AsyncMock()
    proyecto = ProyectoFormativo(
        codigo_proyecto="PR-01",
        nombre_proyecto="Proyecto incompleto",
        version_proyecto="1",
        estado=EstadoBloque.BORRADOR,
    )
    proyecto.id = proyecto_id
    session.get.return_value = proyecto
    repository = AsyncMock(spec=PlaneacionPedagogicaRepository)
    storage_service = AsyncMock()
    service = PlaneacionPedagogicaService(
        session=session,
        repository=repository,
        storage_service=storage_service,
    )
    dto = PlaneacionSaveDTO(
        proyecto_id=proyecto_id,
        competencia_id=competencia_id,
        resultado_id=resultado_id,
        resultados_ids=[resultado_id],
    )

    with pytest.raises(PlaneacionAccessError) as exc_info:
        await service.guardar_borrador(dto)

    assert "proyecto esta COMPLETO" in str(exc_info.value)
    repository.save.assert_not_called()


@pytest.mark.anyio
async def test_confirmar_y_generar_uploads_to_storage() -> None:
    # Arrange
    planeacion_id = uuid.uuid4()
    proyecto_id = uuid.uuid4()
    programa_id = uuid.uuid4()
    competencia_id = uuid.uuid4()
    resultado_id = uuid.uuid4()

    session = AsyncMock()

    # Model mock
    proyecto = ProyectoFormativo(
        codigo_proyecto="PR-01",
        nombre_proyecto="Proyecto 1",
        version_proyecto="1",
        estado=EstadoBloque.COMPLETO,
    )
    proyecto.id = proyecto_id
    proyecto.programa_id = programa_id
    programa = ProgramaFormacion(
        codigo_programa="228118",
        nombre_programa="Analisis de software",
        version_programa="1",
        modalidad_formacion="Presencial",
        estado=EstadoBloque.COMPLETO,
    )
    programa.id = programa_id
    proyecto.programa = programa

    competencia = Competencia(
        codigo_competencia="220501046",
        nombre_competencia="Desarrollar software",
    )
    competencia.id = competencia_id
    resultado = ResultadoAprendizaje(descripcion="Resultado 1")
    resultado.id = resultado_id
    resultado.competencia_id = competencia_id

    planning = PlaneacionPedagogica(
        proyecto_id=proyecto_id,
        competencia_id=competencia_id,
        resultado_id=resultado_id,
    )
    planning.id = planeacion_id
    planning.proyecto = proyecto
    planning.competencia = competencia
    planning.resultado = resultado
    planning.resultados = [resultado]
    planning.conocimientos = []
    planning.criterios = []
    planning.datos_complementarios = {"horas": 40}
    planning.version = 1

    repository = AsyncMock(spec=PlaneacionPedagogicaRepository)
    repository.get_by_id.return_value = planning
    repository.get_document_config.return_value = PlaneacionDocumentoConfig(
        proyecto_id=proyecto_id,
        fecha_elaboracion=date(2026, 7, 29),
        clasificacion_informacion="PUBLICA",
        equipo_gestion_curricular=["Ana Instructor"],
        regional="Distrito Capital",
        centro_formacion="Centro de prueba",
    )

    storage_service = AsyncMock()
    formato_service = MagicMock(spec=PlaneacionFormatoExcelService)
    formato_service.generar.return_value = FormatoExcelResultado(
        content=b"PK\x03\x04official",
        checksum_sha256="a" * 64,
        filas_generadas=1,
    )

    service = PlaneacionPedagogicaService(
        session=session,
        repository=repository,
        storage_service=storage_service,
        formato_excel_service=formato_service,
    )
    service._collect_gaps = AsyncMock(return_value=[])
    service._build_rows = AsyncMock(return_value=[MagicMock()])
    session.get.return_value = proyecto

    # Act
    res = await service.confirmar_y_generar(planeacion_id)

    # Assert
    assert res.estado == "COMPLETO"
    assert res.storage_key is not None
    assert "planeaciones-pedagogicas/" in res.storage_key
    assert res.file_name == "GPFI-F-134V05-planeacion.xlsx"

    # Verify MinIO upload call
    storage_service.save_excel.assert_called_once()
    assert storage_service.save_excel.call_args[1]["key"] == res.storage_key
    assert (
        storage_service.save_excel.call_args[1]["content_type"]
        == EXCEL_CONTENT_TYPE
    )
    repository.save.assert_called_once()


@pytest.mark.anyio
async def test_formato_oficial_rejects_inconsistent_duration() -> None:
    proyecto_id = uuid.uuid4()
    competencia_id = uuid.uuid4()
    resultado_id = uuid.uuid4()
    phase_id = uuid.uuid4()
    activity_id = uuid.uuid4()

    programa = ProgramaFormacion(
        codigo_programa="228118",
        nombre_programa="Analisis de software",
        version_programa="1",
        modalidad_formacion="Presencial",
        estado=EstadoBloque.COMPLETO,
    )
    programa.id = uuid.uuid4()
    proyecto = ProyectoFormativo(
        programa_id=programa.id,
        codigo_proyecto="PR-01",
        nombre_proyecto="Proyecto",
        version_proyecto="1",
        estado=EstadoBloque.COMPLETO,
    )
    proyecto.id = proyecto_id
    proyecto.programa = programa
    competencia = Competencia(
        codigo_competencia="COMP-01",
        nombre_competencia="Competencia",
    )
    competencia.id = competencia_id
    resultado = ResultadoAprendizaje(
        competencia_id=competencia_id,
        descripcion="Resultado",
    )
    resultado.id = resultado_id
    conocimiento = Conocimiento(
        competencia_id=competencia_id,
        tipo=TipoConocimiento.SABER,
        descripcion="Saber",
    )
    criterio = CriterioEvaluacion(
        competencia_id=competencia_id,
        descripcion="Criterio",
    )
    planning = PlaneacionPedagogica(
        proyecto_id=proyecto_id,
        competencia_id=competencia_id,
        resultado_id=resultado_id,
        fase_id=phase_id,
        actividad_id=activity_id,
        datos_complementarios={
            "actividades_aprendizaje": "Actividad",
            "duracion_actividad_horas": 10,
            "horas_trabajo_directo": 8,
            "horas_trabajo_independiente": 4,
            "descripcion_evidencia_aprendizaje": "Evidencia",
            "estrategias_didacticas": "ABP",
            "ambiente": "Aula",
            "materiales_formacion": "Computador",
            "instructores": "Ana",
        },
    )
    planning.proyecto = proyecto
    planning.competencia = competencia
    planning.resultado = resultado
    planning.conocimientos = [conocimiento]
    planning.criterios = [criterio]

    phase = FaseProyecto(
        proyecto_id=proyecto_id,
        nombre_fase="Analisis",
    )
    phase.id = phase_id
    activity = ActividadProyecto(
        fase_id=phase_id,
        descripcion="Actividad",
    )
    activity.id = activity_id
    repository = AsyncMock(spec=PlaneacionPedagogicaRepository)
    repository.get_document_config.return_value = PlaneacionDocumentoConfig(
        proyecto_id=proyecto_id,
        fecha_elaboracion=date(2026, 7, 29),
        clasificacion_informacion="PUBLICA",
        equipo_gestion_curricular=["Ana"],
        regional="Distrito Capital",
        centro_formacion="Centro",
    )
    service = PlaneacionPedagogicaService(
        session=AsyncMock(),
        repository=repository,
        storage_service=AsyncMock(),
    )
    service._project_structure = AsyncMock(
        return_value=({phase_id: phase}, {activity_id: activity})
    )

    gaps = await service._collect_gaps(planning, require_complete=False)

    assert "DURACION_INCONSISTENTE" in {gap.codigo for gap in gaps}
