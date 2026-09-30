"""Tests for Official Format Generation, MinIO Sync Status, Assisted Review Submission, and Consolidated Download."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.application.dto.planeacion import PlaneacionSaveDTO
from src.application.dto.revision_curricular import EnvioRevisionRequestDTO
from src.application.services.planeacion_service import (
    OfficialDocumentStorageError,
    PlaneacionPedagogicaService,
)
from src.application.services.revision_curricular_service import (
    RevisionCurricularService,
)
from src.domain.shared.enums import (
    EstadoBloque,
    EstadoDocumentoOficial,
    EstadoEntregaRevision,
    EstadoEquipo,
    EstadoRevisionPlaneacion,
    EstadoUsuario,
    RolUsuario,
)
from src.infrastructure.db.models.audit import EventoAuditoria
from src.infrastructure.db.models.auth import Rol, Usuario
from src.infrastructure.db.models.curriculum import (
    Competencia,
    ProgramaFormacion,
    ResultadoAprendizaje,
)
from src.infrastructure.db.models.organizacion import (
    Coordinacion,
    EquipoEjecutor,
    Especialidad,
    ProcesoCurricular,
)
from src.infrastructure.db.models.planeacion import (
    PlaneacionDocumentoConfig,
    PlaneacionPedagogica,
)
from src.infrastructure.db.models.proyecto import (
    ActividadProyecto,
    FaseProyecto,
    ProyectoFormativo,
)
from src.infrastructure.db.models.revision_curricular import (
    EntregaRevisionCurricular,
)

pytestmark = pytest.mark.anyio


def _make_user(role_name: str, email: str = "lider@sena.edu.co") -> Usuario:
    user = Usuario(
        id=uuid.uuid4(),
        email=email,
        hashed_password="hash",
        nombre="Test",
        apellido="Lider",
        activo=True,
        estado=EstadoUsuario.ACTIVO,
    )
    rol = Rol(id=uuid.uuid4(), nombre=role_name)
    user.roles = [rol]
    return user


def _build_entities():
    lider = _make_user(RolUsuario.LIDER_EQUIPO_EJECUTOR.value)
    coord = Coordinacion(id=uuid.uuid4(), codigo="COORD-01", nombre="Coordinacion Teleinformatica")
    esp = Especialidad(id=uuid.uuid4(), coordinacion_id=coord.id, codigo="ESP-01", nombre="Software")
    equipo = EquipoEjecutor(
        id=uuid.uuid4(),
        coordinacion_id=coord.id,
        especialidad_id=esp.id,
        nombre="Equipo ADSO 2026",
        lider_id=lider.id,
        estado=EstadoEquipo.ACTIVO,
    )
    equipo.coordinacion = coord
    equipo.especialidad = esp
    equipo.lider = lider

    prog = ProgramaFormacion(
        id=uuid.uuid4(),
        codigo_programa="228106",
        version_programa="v1",
        nombre_programa="Analisis y Desarrollo de Software",
        modalidad_formacion="PRESENCIAL",
        estado=EstadoBloque.COMPLETO,
    )
    proy = ProyectoFormativo(
        id=uuid.uuid4(),
        codigo_proyecto="PRY-ADSO-01",
        version_proyecto="1",
        nombre_proyecto="Sistema de Informacion Empresarial",
        estado=EstadoBloque.COMPLETO,
    )
    ref_id = uuid.uuid4()
    proceso = ProcesoCurricular(
        id=uuid.uuid4(),
        referencia_id=ref_id,
        equipo_ejecutor_id=equipo.id,
        programa_id=prog.id,
        proyecto_id=proy.id,
        lider_id=lider.id,
    )
    proceso.equipo_ejecutor = equipo
    proceso.programa = prog
    proceso.proyecto = proy

    fase = FaseProyecto(id=uuid.uuid4(), proyecto_id=proy.id, nombre_fase="Fase 1 - Analisis", orden=1)
    actividad = ActividadProyecto(id=uuid.uuid4(), fase_id=fase.id, descripcion="Definir requerimientos", orden=1)
    comp = Competencia(id=uuid.uuid4(), codigo_competencia="220501096", nombre_competencia="Desarrollo de Software")
    rap = ResultadoAprendizaje(id=uuid.uuid4(), codigo_resultado="RAP-01", descripcion="Diseñar la solución")
    rap.competencia = comp

    base_time = datetime(2026, 9, 30, 12, 0, 0, tzinfo=UTC)
    planeacion = PlaneacionPedagogica(
        id=uuid.uuid4(),
        proyecto_id=proy.id,
        fase_id=fase.id,
        actividad_id=actividad.id,
        estado=EstadoBloque.COMPLETO,
        review_status=EstadoRevisionPlaneacion.DRAFT.value,
        datos_complementarios={
            "actividades_aprendizaje": "Diseñar arquitectura de software",
            "horas_trabajo_directo": 20,
            "horas_trabajo_independiente": 10,
            "duracion_actividad_horas": 30,
            "ambiente": "Ambiente de Computo 302",
            "instructores": "Instructor de Software",
            "estrategias_didacticas": "Aprendizaje Basado en Proyectos",
            "descripcion_evidencia_aprendizaje": "Diagrama de componentes",
        },
        storage_key=None,
        fecha_generacion=None,
        fecha_creacion=base_time,
        fecha_actualizacion=base_time,
        version=1,
    )
    planeacion.fase = fase
    planeacion.actividad = actividad
    planeacion.resultados = [rap]
    planeacion.conocimientos = []
    planeacion.criterios = []

    config = PlaneacionDocumentoConfig(
        proyecto_id=proy.id,
        fecha_elaboracion=date.today(),
        clasificacion_informacion="PUBLICA",
        equipo_gestion_curricular=["Equipo ADSO"],
        regional="Distrito Capital",
        centro_formacion="CSF",
        storage_key=None,
        fecha_generacion=None,
        fecha_creacion=base_time,
        fecha_actualizacion=base_time,
        version=1,
    )

    return {
        "lider": lider,
        "equipo": equipo,
        "programa": prog,
        "proyecto": proy,
        "proceso": proceso,
        "fase": fase,
        "actividad": actividad,
        "comp": comp,
        "rap": rap,
        "planeacion": planeacion,
        "config": config,
        "referencia_id": ref_id,
        "base_time": base_time,
    }


async def test_1_create_planning_without_official_format_requires_assisted_generation():
    """Case 1: Planning created without generated official format -> preflight returns NOT_GENERATED & requiere_generar_formato=True, and assisted submit generates + submits."""
    ctx = _build_entities()
    session = AsyncMock()
    scope = AsyncMock()
    scope.require_process_access.return_value = ctx["proceso"]
    planeacion_service = AsyncMock()

    audit_events: list[EventoAuditoria] = []
    entregas_db: list[EntregaRevisionCurricular] = []

    def mock_add(entity):
        if isinstance(entity, EventoAuditoria):
            audit_events.append(entity)
        elif isinstance(entity, EntregaRevisionCurricular):
            entity.equipo_ejecutor = ctx["equipo"]
            entity.programa = ctx["programa"]
            entity.proyecto = ctx["proyecto"]
            entregas_db.append(entity)

    session.add = MagicMock(side_effect=mock_add)

    async def mock_generate_consolidated(proyecto_id, actor_id=None):
        now = datetime.now(UTC)
        ctx["config"].storage_key = "proyectos/adso/planeacion/consolidado/GPFI-F-134V05.xlsx"
        ctx["config"].file_name = "GPFI-F-134V05.xlsx"
        ctx["config"].checksum_sha256 = "abc123sha256"
        ctx["config"].fecha_generacion = now
        ctx["config"].fecha_actualizacion = now

    planeacion_service.generar_formato_consolidado.side_effect = mock_generate_consolidated

    async def mock_execute(stmt):
        text = str(stmt).lower()
        mock_res = MagicMock()
        mock_res.scalars.return_value.first.return_value = None
        mock_res.scalars.return_value.all.return_value = []
        mock_res.scalar_one_or_none.return_value = None
        if "from procesos_curriculares" in text:
            mock_res.scalar_one_or_none.return_value = ctx["proceso"]
        elif "from actividades_proyecto" in text:
            mock_res.scalars.return_value.all.return_value = [ctx["actividad"]]
        elif "from planeaciones_pedagogicas" in text:
            mock_res.scalars.return_value.all.return_value = [ctx["planeacion"]]
        elif "from planeacion_documento_config" in text:
            mock_res.scalar_one_or_none.return_value = ctx["config"]
        elif "from entregas_revision_curricular" in text:
            mock_res.scalars.return_value.first.return_value = entregas_db[-1] if entregas_db else None
            mock_res.scalars.return_value.all.return_value = list(reversed(entregas_db))
            mock_res.scalar_one_or_none.return_value = entregas_db[-1] if entregas_db else None
        return mock_res

    session.execute.side_effect = mock_execute
    service = RevisionCurricularService(session, scope, planeacion_service=planeacion_service)

    preflight = await service.validate_preflight_envio(ctx["lider"], ctx["referencia_id"])
    assert preflight.listo is False
    assert preflight.official_document_status == EstadoDocumentoOficial.NOT_GENERATED.value
    assert preflight.requiere_generar_formato is True

    # Assisted submission with auto_generar_formato=True
    entrega = await service.enviar_a_revision(
        ctx["lider"],
        ctx["referencia_id"],
        EnvioRevisionRequestDTO(notas_entrega="Entrega asistida", auto_generar_formato=True),
    )
    assert entrega.estado == EstadoEntregaRevision.ENVIADO_REVISION.value
    planeacion_service.generar_formato_consolidado.assert_awaited_once_with(
        ctx["proyecto"].id, actor_id=ctx["lider"].id
    )
    assert any(e.accion == "PLANNING_SUBMITTED_FOR_REVIEW" for e in audit_events)


async def test_2_planning_with_current_official_format_submits_directly():
    """Case 2: Planning with up-to-date official format (CURRENT) -> preflight returns listo=True, requiere_generar_formato=False."""
    ctx = _build_entities()
    gen_time = ctx["base_time"] + timedelta(minutes=5)
    ctx["config"].storage_key = "proyectos/adso/planeacion/consolidado/GPFI-F-134V05.xlsx"
    ctx["config"].fecha_generacion = gen_time
    ctx["config"].fecha_actualizacion = gen_time

    session = AsyncMock()
    scope = AsyncMock()
    scope.require_process_access.return_value = ctx["proceso"]

    async def mock_execute(stmt):
        text = str(stmt).lower()
        mock_res = MagicMock()
        mock_res.scalars.return_value.first.return_value = None
        mock_res.scalars.return_value.all.return_value = []
        mock_res.scalar_one_or_none.return_value = None
        if "from procesos_curriculares" in text:
            mock_res.scalar_one_or_none.return_value = ctx["proceso"]
        elif "from actividades_proyecto" in text:
            mock_res.scalars.return_value.all.return_value = [ctx["actividad"]]
        elif "from planeaciones_pedagogicas" in text:
            mock_res.scalars.return_value.all.return_value = [ctx["planeacion"]]
        elif "from planeacion_documento_config" in text:
            mock_res.scalar_one_or_none.return_value = ctx["config"]
        return mock_res

    session.execute.side_effect = mock_execute
    service = RevisionCurricularService(session, scope)

    preflight = await service.validate_preflight_envio(ctx["lider"], ctx["referencia_id"])
    assert preflight.listo is True
    assert preflight.official_document_status == EstadoDocumentoOficial.CURRENT.value
    assert preflight.requiere_generar_formato is False
    assert len(preflight.pendientes) == 0


async def test_3_editing_planning_marks_official_document_outdated():
    """Case 3: Modifying a planning or RAP after generating the official format transitions status to OUTDATED."""
    ctx = _build_entities()
    gen_time = ctx["base_time"] + timedelta(minutes=5)
    edit_time = ctx["base_time"] + timedelta(minutes=15)

    ctx["config"].storage_key = "proyectos/adso/planeacion/consolidado/GPFI-F-134V05.xlsx"
    ctx["config"].fecha_generacion = gen_time
    ctx["config"].fecha_actualizacion = gen_time

    # Simulate an edit on the planning (or RAP) after the document was generated
    ctx["planeacion"].fecha_actualizacion = edit_time

    session = AsyncMock()
    scope = AsyncMock()
    scope.require_process_access.return_value = ctx["proceso"]

    async def mock_execute(stmt):
        text = str(stmt).lower()
        mock_res = MagicMock()
        mock_res.scalars.return_value.first.return_value = None
        mock_res.scalars.return_value.all.return_value = []
        mock_res.scalar_one_or_none.return_value = None
        if "from procesos_curriculares" in text:
            mock_res.scalar_one_or_none.return_value = ctx["proceso"]
        elif "from actividades_proyecto" in text:
            mock_res.scalars.return_value.all.return_value = [ctx["actividad"]]
        elif "from planeaciones_pedagogicas" in text:
            mock_res.scalars.return_value.all.return_value = [ctx["planeacion"]]
        elif "from planeacion_documento_config" in text:
            mock_res.scalar_one_or_none.return_value = ctx["config"]
        return mock_res

    session.execute.side_effect = mock_execute
    service = RevisionCurricularService(session, scope)

    preflight = await service.validate_preflight_envio(ctx["lider"], ctx["referencia_id"])
    assert preflight.listo is False
    assert preflight.official_document_status == EstadoDocumentoOficial.OUTDATED.value
    assert preflight.requiere_generar_formato is True
    assert any("versión oficial almacenada todavía no contiene los últimos cambios" in p for p in preflight.pendientes)


async def test_4_minio_storage_failure_prevents_submission_and_audits_failure():
    """Case 4: When MinIO fails during format generation, OfficialDocumentStorageError is raised, audit is recorded, and planning is NOT submitted."""
    ctx = _build_entities()
    ctx["proyecto"].programa = ctx["programa"]
    ctx["proyecto"].programa_id = ctx["programa"].id
    ctx["planeacion"].proyecto = ctx["proyecto"]

    session = AsyncMock()
    repo = AsyncMock()
    file_storage = AsyncMock()
    exporter = MagicMock()
    exporter.generar.return_value = MagicMock(
        content=b"fake-excel-bytes",
        checksum_sha256="sha256hash",
        filas_generadas=4,
    )
    file_storage.save_excel.side_effect = RuntimeError("MinIO connection refused")

    audit_events: list[EventoAuditoria] = []
    session.add = MagicMock(
        side_effect=lambda e: audit_events.append(e) if isinstance(e, EventoAuditoria) else None
    )

    repo.list_full_by_proyecto.return_value = [ctx["planeacion"]]
    repo.get_document_config.return_value = ctx["config"]

    p_service = PlaneacionPedagogicaService(
        session=session,
        repository=repo,
        storage_service=file_storage,
        formato_excel_service=exporter,
    )
    p_service._ensure_project_complete = AsyncMock()  # type: ignore[method-assign]
    p_service._collect_gaps = AsyncMock(return_value=[])  # type: ignore[method-assign]
    p_service._build_rows = AsyncMock(return_value=[])  # type: ignore[method-assign]

    with pytest.raises(OfficialDocumentStorageError) as exc_info:
        await p_service.generar_formato_consolidado(ctx["proyecto"].id, actor_id=ctx["lider"].id)

    assert "No fue posible almacenar el formato oficial en el repositorio documental" in str(exc_info.value)
    assert any(e.accion == "OFFICIAL_DOCUMENT_GENERATION_FAILED" for e in audit_events)


async def test_5_consolidated_download_never_mutates_planning_or_regenerates():
    """Case 5: Downloading the consolidated document only reads from MinIO and does not alter state or regenerate."""
    ctx = _build_entities()
    ctx["config"].storage_key = "proyectos/adso/planeacion/consolidado/GPFI-F-134V05.xlsx"
    ctx["config"].file_name = "GPFI-F-134V05.xlsx"
    ctx["config"].content_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

    session = AsyncMock()
    repo = AsyncMock()
    repo.list_full_by_proyecto.return_value = [ctx["planeacion"]]
    repo.get_document_config.return_value = ctx["config"]

    file_storage = AsyncMock()
    file_storage.read_excel.return_value = b"consolidated-xlsx-bytes"
    exporter = MagicMock()

    p_service = PlaneacionPedagogicaService(
        session=session,
        repository=repo,
        storage_service=file_storage,
        formato_excel_service=exporter,
    )

    content, filename = await p_service.descargar_formato_consolidado(ctx["proyecto"].id)
    assert content == b"consolidated-xlsx-bytes"
    assert filename == "GPFI-F-134V05.xlsx"

    # Ensure neither exporter nor save_excel was called during download
    exporter.generar.assert_not_called()
    file_storage.save_excel.assert_not_called()
    repo.save.assert_not_called()

