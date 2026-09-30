"""Comprehensive backend tests for Learning Result (RA) locking and controlled reopening workflow."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from src.application.dto.planeacion import PlaneacionSaveDTO
from src.application.dto.resultados_aprendizaje import ResultadoAprendizajePayloadDTO
from src.application.dto.revision_curricular import (
    AprobacionRequestDTO,
    EnvioRevisionRequestDTO,
    PlanningEditRequestApproveDTO,
    PlanningEditRequestCreateDTO,
    PlanningEditRequestRejectDTO,
)
from src.application.services.notification_events import notification_dispatcher
from src.application.services.planeacion_service import (
    LearningResultLockedError,
    PlaneacionPedagogicaService,
)
from src.application.services.resultados_aprendizaje import (
    ProgramaResultadoAprendizajeService,
)
from src.application.services.revision_curricular_service import (
    RevisionCurricularService,
)
from src.domain.shared.enums import (
    EstadoAprobacionPlaneacion,
    EstadoBloque,
    EstadoCampo,
    EstadoEdicionRA,
    EstadoEntregaRevision,
    EstadoEquipo,
    EstadoRevisionPlaneacion,
    EstadoSolicitudReapertura,
    EstadoUsuario,
    RolUsuario,
    TipoConocimiento,
)
from src.infrastructure.db.models.auth import Rol, Usuario
from src.infrastructure.db.models.curriculum import (
    Competencia,
    Conocimiento,
    CriterioEvaluacion,
    ProgramaFormacion,
    ResultadoAprendizaje,
)
from src.infrastructure.db.models.organizacion import (
    EquipoEjecutor,
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
    LearningResultVersion,
    PlanningEditRequest,
    PlanningEditRequestItem,
)
from src.interfaces.http.app import create_application

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


def _make_user(role_code: str, nombre: str = "Test", apellido: str = "User") -> Usuario:
    rol = Rol(id=uuid.uuid4(), nombre=role_code)
    user = Usuario(
        id=uuid.uuid4(),
        email=f"{nombre.lower()}.{uuid.uuid4().hex[:6]}@sena.edu.co",
        nombre=nombre,
        apellido=apellido,
        hashed_password="hash",
        estado=EstadoUsuario.ACTIVO,
        activo=True,
        debe_cambiar_password=False,
    )
    user.roles = [rol]
    return user


def _build_full_scenario():
    lider = _make_user(RolUsuario.LIDER_EQUIPO_EJECUTOR.value, "Carlos", "Lider")
    miembro = _make_user(RolUsuario.USUARIO_ADICIONAL.value, "Ana", "Integrante")
    otro_lider = _make_user(RolUsuario.LIDER_EQUIPO_EJECUTOR.value, "Pedro", "OtroLider")
    admin = _make_user(RolUsuario.ADMIN.value, "Marta", "Pedagogica")

    equipo = EquipoEjecutor(
        id=uuid.uuid4(),
        especialidad_id=uuid.uuid4(),
        nombre="Equipo ADSO 01",
        lider_id=lider.id,
        estado=EstadoEquipo.ACTIVO,
    )
    equipo.lider = lider

    programa = ProgramaFormacion(
        id=uuid.uuid4(),
        codigo_programa="228118",
        version_programa="1",
        nombre_programa="Análisis y Desarrollo de Software",
        estado=EstadoBloque.COMPLETO,
    )
    comp = Competencia(
        id=uuid.uuid4(),
        programa_id=programa.id,
        codigo_competencia="220501096",
        nombre_competencia="Desarrollar la solución de software",
        orden=1,
    )
    comp.programa = programa

    ra1 = ResultadoAprendizaje(
        id=uuid.uuid4(),
        competencia_id=comp.id,
        codigo_resultado="RA-01",
        descripcion="Analizar requerimientos técnicos de la solución",
        orden=1,
    )
    ra1.competencia = comp

    ra2 = ResultadoAprendizaje(
        id=uuid.uuid4(),
        competencia_id=comp.id,
        codigo_resultado="RA-02",
        descripcion="Construir componentes backend y frontend",
        orden=2,
    )
    ra2.competencia = comp

    ra3 = ResultadoAprendizaje(
        id=uuid.uuid4(),
        competencia_id=comp.id,
        codigo_resultado="RA-03",
        descripcion="Validar la calidad e integración del software",
        orden=3,
    )
    ra3.competencia = comp

    conocimiento = Conocimiento(
        id=uuid.uuid4(),
        competencia_id=comp.id,
        tipo=TipoConocimiento.PROCESO,
        descripcion="Arquitectura limpia y pruebas automatizadas",
    )
    criterio = CriterioEvaluacion(
        id=uuid.uuid4(),
        competencia_id=comp.id,
        descripcion="Implementa módulos cumpliendo estándares de seguridad",
    )

    proyecto = ProyectoFormativo(
        id=uuid.uuid4(),
        programa_id=programa.id,
        codigo_proyecto="PRJ-ADSO-2026",
        nombre_proyecto="Sistema de Gestión Curricular ASGARD",
        estado=EstadoBloque.COMPLETO,
    )
    proyecto.programa = programa

    fase = FaseProyecto(
        id=uuid.uuid4(),
        proyecto_id=proyecto.id,
        nombre_fase="EJECUCIÓN",
        orden=1,
    )
    actividad = ActividadProyecto(
        id=uuid.uuid4(),
        fase_id=fase.id,
        descripcion="Desarrollar servicios centrales",
        orden=1,
    )
    actividad.fase = fase

    referencia_id = uuid.uuid4()
    proceso = ProcesoCurricular(
        id=uuid.uuid4(),
        referencia_id=referencia_id,
        programa_id=programa.id,
        proyecto_id=proyecto.id,
        equipo_ejecutor_id=equipo.id,
        lider_id=lider.id,
    )
    proceso.equipo_ejecutor = equipo
    proceso.programa = programa
    proceso.proyecto = proyecto

    planeacion = PlaneacionPedagogica(
        id=uuid.uuid4(),
        proyecto_id=proyecto.id,
        fase_id=fase.id,
        actividad_id=actividad.id,
        estado=EstadoBloque.COMPLETO,
        datos_complementarios={
            "actividades_aprendizaje": "Construir API RESTful y UI",
            "horas_trabajo_directo": 40,
            "horas_trabajo_independiente": 10,
            "duracion_actividad_horas": 50,
            "estrategias_didacticas": "Aprendizaje basado en proyectos",
            "descripcion_evidencia_aprendizaje": "Repositorio y despliegue funcional",
            "ambiente": "Ambiente dotado con equipos de cómputo",
            "materiales_formacion": " Servidores de prueba y documentación",
            "instructores": "Instructor Técnico ADSO",
            "rap_complementary_map": {
                str(ra1.id): {
                    "actividades_aprendizaje": "Modelar casos de uso",
                    "horas_trabajo_directo": 15,
                    "horas_trabajo_independiente": 5,
                    "duracion_actividad_horas": 20,
                    "estrategias_didacticas": "Estudio de caso",
                    "descripcion_evidencia_aprendizaje": "Documento de arquitectura",
                },
                str(ra2.id): {
                    "actividades_aprendizaje": "Codificar endpoints",
                    "horas_trabajo_directo": 15,
                    "horas_trabajo_independiente": 3,
                    "duracion_actividad_horas": 18,
                    "estrategias_didacticas": "Taller práctico",
                    "descripcion_evidencia_aprendizaje": "Código fuente",
                },
                str(ra3.id): {
                    "actividades_aprendizaje": "Ejecutar suite pytest",
                    "horas_trabajo_directo": 10,
                    "horas_trabajo_independiente": 2,
                    "duracion_actividad_horas": 12,
                    "estrategias_didacticas": "Pruebas guiadas",
                    "descripcion_evidencia_aprendizaje": "Reporte de cobertura",
                },
            },
        },
        storage_key="planeaciones/individual_v1.xlsx",
        file_name="individual_v1.xlsx",
        checksum_sha256="sha256-v1-individual",
    )
    planeacion.proyecto = proyecto
    planeacion.fase = fase
    planeacion.actividad = actividad
    planeacion.resultados = [ra1, ra2, ra3]
    planeacion.conocimientos = [conocimiento]
    planeacion.criterios = [criterio]

    doc_config = PlaneacionDocumentoConfig(
        id=uuid.uuid4(),
        proyecto_id=proyecto.id,
        fecha_elaboracion=date(2026, 9, 30),
        clasificacion_informacion="PUBLICA",
        equipo_gestion_curricular=[{"nombre": "Carlos Lider", "rol": "Líder"}],
        regional="Distrito Capital",
        centro_formacion="CSF",
        storage_key="planeaciones/consolidado_v1.xlsx",
        file_name="consolidado_v1.xlsx",
        checksum_sha256="sha256-v1-consolidado",
        version=1,
    )

    entrega = EntregaRevisionCurricular(
        id=uuid.uuid4(),
        proceso_curricular_id=proceso.id,
        referencia_id=referencia_id,
        equipo_ejecutor_id=equipo.id,
        programa_id=programa.id,
        proyecto_id=proyecto.id,
        version=1,
        estado=EstadoEntregaRevision.EN_REVISION,
        enviado_por_id=lider.id,
        fecha_envio=datetime.now(UTC),
        descarga_habilitada=False,
        snapshot_metadatos={
            "planeaciones_count": 1,
            "planeaciones_ids": [str(planeacion.id)],
            "checksum_consolidado": "sha256-v1-consolidado",
        },
    )
    entrega.equipo_ejecutor = equipo
    entrega.programa = programa
    entrega.proyecto = proyecto
    entrega.enviado_por = lider
    entrega.observaciones = []

    return {
        "lider": lider,
        "miembro": miembro,
        "otro_lider": otro_lider,
        "admin": admin,
        "equipo": equipo,
        "programa": programa,
        "comp": comp,
        "ra1": ra1,
        "ra2": ra2,
        "ra3": ra3,
        "conocimiento": conocimiento,
        "criterio": criterio,
        "proyecto": proyecto,
        "fase": fase,
        "actividad": actividad,
        "referencia_id": referencia_id,
        "proceso": proceso,
        "planeacion": planeacion,
        "doc_config": doc_config,
        "entrega": entrega,
    }


# -----------------------------------------------------------------------------
# Scenario 1: Approving planning + enabling download locks all RAs transactionally
# -----------------------------------------------------------------------------
async def test_1_approve_planning_and_enable_download_locks_all_ras():
    ctx = _build_full_scenario()
    notification_dispatcher.clear_history()

    session = AsyncMock()
    added_objects: list[object] = []
    session.add = MagicMock(side_effect=lambda obj: added_objects.append(obj))
    scope = AsyncMock()

    # Sequence of session.execute calls in aprobar_entrega:
    # 1. select(EntregaRevisionCurricular) with_for_update
    # 2. _get_latest_delivery_by_ref -> select(EntregaRevisionCurricular)
    # 3. select(PlaneacionDocumentoConfig) with_for_update
    # 4. select(PlaneacionPedagogica) with_for_update
    # 5. update(LearningResultVersion)
    # 6..8. update(planeacion_resultados) for ra1, ra2, ra3
    # 9. select(PlanningEditRequest) active requests
    # 10..11. _build_snapshot_metadatos: select(PlaneacionPedagogica), select(PlaneacionDocumentoConfig)
    # 12..13. obtener_detalle_entrega: select(EntregaRevisionCurricular), select(history)
    call_idx = {"n": 0}

    async def side_effect_execute(stmt):
        call_idx["n"] += 1
        sql_str = str(stmt)
        res = MagicMock()
        if "entregas_revision_curricular" in sql_str:
            res.scalar_one_or_none.return_value = ctx["entrega"]
            res.scalars.return_value.first.return_value = ctx["entrega"]
            res.scalars.return_value.all.return_value = [ctx["entrega"]]
        elif "planeacion_documento_config" in sql_str:
            res.scalar_one_or_none.return_value = ctx["doc_config"]
        elif "planeaciones_pedagogicas" in sql_str:
            res.scalars.return_value.all.return_value = [ctx["planeacion"]]
            res.scalar_one_or_none.return_value = ctx["planeacion"]
        elif "planning_edit_requests" in sql_str:
            res.scalars.return_value.all.return_value = []
        else:
            res.scalars.return_value.all.return_value = []
        return res

    session.execute.side_effect = side_effect_execute
    service = RevisionCurricularService(session, scope)

    result = await service.aprobar_entrega(
        ctx["admin"],
        ctx["entrega"].id,
        AprobacionRequestDTO(notas_aprobacion="Aprobación pedagógica v1"),
    )

    assert result.estado == EstadoEntregaRevision.APROBADO
    assert result.descarga_habilitada is True

    # Verify planning state
    plan = ctx["planeacion"]
    assert plan.review_status == EstadoRevisionPlaneacion.APPROVED
    assert plan.approval_status == EstadoAprobacionPlaneacion.APPROVED
    assert plan.edit_status == EstadoEdicionRA.LOCKED
    assert plan.locked_by == ctx["admin"].id
    assert plan.locked_at is not None
    assert plan.official_storage_key == "planeaciones/individual_v1.xlsx"
    assert plan.official_version == 1

    # Verify all 3 RAs are LOCKED
    for ra in (ctx["ra1"], ctx["ra2"], ctx["ra3"]):
        assert ra.edit_status == EstadoEdicionRA.LOCKED
        assert ra.locked_by == ctx["admin"].id
        assert ra.locked_at is not None
        assert ra.approved_version == 1
        assert ra.approved_at is not None
        assert plan.datos_complementarios["ra_locks"][str(ra.id)]["edit_status"] == "LOCKED"

    # Verify LearningResultVersion snapshots created
    versions = [obj for obj in added_objects if isinstance(obj, LearningResultVersion)]
    assert len(versions) == 3
    assert all(v.version_number == 1 and v.is_official is True for v in versions)

    # Verify audit events
    from src.infrastructure.db.models.audit import EventoAuditoria

    audits = [obj.accion for obj in added_objects if isinstance(obj, EventoAuditoria)]
    assert "PLANNING_APPROVED" in audits
    assert audits.count("LEARNING_RESULT_LOCKED") == 3
    assert "ENTREGA_CURRICULAR_APROBADA" in audits
    assert "DESCARGA_CONSOLIDADO_HABILITADA" in audits


# -----------------------------------------------------------------------------
# Scenario 2: Attempting to edit a locked RA fails in backend (service & HTTP 423)
# -----------------------------------------------------------------------------
async def test_2_editing_locked_ra_fails_with_423_locked():
    ctx = _build_full_scenario()
    plan = ctx["planeacion"]
    plan.review_status = EstadoRevisionPlaneacion.APPROVED
    plan.approval_status = EstadoAprobacionPlaneacion.APPROVED
    plan.edit_status = EstadoEdicionRA.LOCKED
    for ra in (ctx["ra1"], ctx["ra2"], ctx["ra3"]):
        ra.edit_status = EstadoEdicionRA.LOCKED
        ra.approved_version = 1

    session = AsyncMock()
    session.get.side_effect = lambda model, pk: {
        ProyectoFormativo: ctx["proyecto"],
        ProgramaFormacion: ctx["programa"],
        FaseProyecto: ctx["fase"],
        ActividadProyecto: ctx["actividad"],
    }.get(model)
    repo = AsyncMock()
    storage = AsyncMock()

    repo.get_by_id.return_value = plan
    repo.save.return_value = plan

    plan_service = PlaneacionPedagogicaService(session=session, repository=repo, storage_service=storage)

    # 2a. Attempt to update planning draft with locked RAs
    save_dto = PlaneacionSaveDTO(
        planeacion_id=plan.id,
        proyecto_id=ctx["proyecto"].id,
        fase_id=ctx["fase"].id,
        actividad_id=ctx["actividad"].id,
        resultados_ids=[ctx["ra1"].id, ctx["ra2"].id, ctx["ra3"].id],
        conocimientos_ids=[ctx["conocimiento"].id],
        criterios_ids=[ctx["criterio"].id],
        datos_complementarios={"actividades_aprendizaje": "Intento de cambio no autorizado"},
    )
    with pytest.raises(LearningResultLockedError) as exc_info:
        await plan_service.guardar_borrador(save_dto, actor_id=ctx["lider"].id)
    assert exc_info.value.code == "LEARNING_RESULT_LOCKED"

    # 2b. Attempt to confirm/regenerate locked planning
    with pytest.raises(LearningResultLockedError):
        await plan_service.confirmar_y_generar(plan.id, actor_id=ctx["lider"].id)

    # 2c. Attempt to delete planning containing locked RAs
    with pytest.raises(LearningResultLockedError):
        await plan_service.eliminar_planeacion(plan.id, actor_id=ctx["lider"].id)

    # 2d. Attempt to modify or delete locked RA directly in ProgramaResultadoAprendizajeService
    ra_repo = AsyncMock()
    draft_repo = AsyncMock()
    audit_repo = AsyncMock()
    mock_draft = MagicMock()
    mock_draft.payload_json = {"curricular": {"programa_formacion_id": str(ctx["programa"].id)}}
    draft_repo.get_by_block_reference.return_value = mock_draft
    ra_repo.get_competencia.return_value = ctx["comp"]
    ra_repo.get_by_id_for_competencia.return_value = ctx["ra1"]

    ra_service = ProgramaResultadoAprendizajeService(session, ra_repo, draft_repo, audit_repo)
    with pytest.raises(LearningResultLockedError):
        await ra_service.update_resultado(
            ctx["referencia_id"],
            ctx["comp"].id,
            ctx["ra1"].id,
            ResultadoAprendizajePayloadDTO(descripcion="Modificación ilegal", codigo_resultado="RA-01"),
        )
    with pytest.raises(LearningResultLockedError):
        await ra_service.delete_resultado(ctx["referencia_id"], ctx["comp"].id, ctx["ra1"].id)

    # 2e. Verify FastAPI exception handler returns HTTP 423 Locked with exact JSON structure
    app = create_application()

    @app.get("/test-locked-ra")
    async def _trigger_locked():
        raise LearningResultLockedError()

    client = TestClient(app)
    resp = client.get("/test-locked-ra")
    assert resp.status_code == 423
    body = resp.json()
    assert body["code"] == "LEARNING_RESULT_LOCKED"
    assert "bloqueado para edición" in body["message"]


# -----------------------------------------------------------------------------
# Scenario 3 & 4: Non-leader member cannot create edit request; Leader can
# -----------------------------------------------------------------------------
async def test_3_and_4_only_team_leader_can_create_edit_request():
    ctx = _build_full_scenario()
    notification_dispatcher.clear_history()
    plan = ctx["planeacion"]
    plan.review_status = EstadoRevisionPlaneacion.APPROVED
    plan.approval_status = EstadoAprobacionPlaneacion.APPROVED
    plan.edit_status = EstadoEdicionRA.LOCKED
    for ra in (ctx["ra1"], ctx["ra2"], ctx["ra3"]):
        ra.edit_status = EstadoEdicionRA.LOCKED
        ra.approved_version = 1
    ctx["entrega"].estado = EstadoEntregaRevision.APROBADO
    ctx["entrega"].descarga_habilitada = True

    session = AsyncMock()
    added_objects: list[object] = []
    session.add = MagicMock(side_effect=lambda obj: added_objects.append(obj))
    scope = AsyncMock()
    scope.can_access_planning.return_value = True

    created_req_holder: dict[str, PlanningEditRequest | None] = {"req": None}

    async def side_effect_execute(stmt):
        sql_str = str(stmt)
        res = MagicMock()
        if "planeaciones_pedagogicas" in sql_str:
            res.scalar_one_or_none.return_value = plan
        elif "procesos_curriculares" in sql_str:
            res.scalar_one_or_none.return_value = ctx["proceso"]
        elif "entregas_revision_curricular" in sql_str:
            res.scalars.return_value.first.return_value = ctx["entrega"]
        elif "planning_edit_requests" in sql_str:
            if created_req_holder["req"] is not None and "planning_edit_request_items" not in sql_str:
                res.scalar_one_or_none.return_value = created_req_holder["req"]
            else:
                res.scalars.return_value.first.return_value = None
                res.scalar_one_or_none.return_value = created_req_holder["req"]
        return res

    session.execute.side_effect = side_effect_execute
    service = RevisionCurricularService(session, scope)

    create_dto = PlanningEditRequestCreateDTO(
        planning_id=plan.id,
        learning_result_ids=[ctx["ra2"].id],
        reason="Ajuste en horas y actividades del RA-02 por actualización tecnológica.",
        requested_changes="Actualizar actividad de aprendizaje y distribuir 18 horas.",
    )

    # 3a. Non-leader member (USUARIO_ADICIONAL) is rejected with 403
    with pytest.raises(HTTPException) as exc_member:
        await service.crear_solicitud_reapertura(ctx["miembro"], create_dto)
    assert exc_member.value.status_code == 403

    # 3b. Leader of another team is rejected with 403
    with pytest.raises(HTTPException) as exc_other:
        await service.crear_solicitud_reapertura(ctx["otro_lider"], create_dto)
    assert exc_other.value.status_code == 403

    # 4. Team Leader creates request successfully
    def capture_add(obj):
        added_objects.append(obj)
        if isinstance(obj, PlanningEditRequest):
            obj.planning = plan
            obj.team = ctx["equipo"]
            obj.requester = ctx["lider"]
            obj.reviewer = None
            obj.items = []
            created_req_holder["req"] = obj
        elif isinstance(obj, PlanningEditRequestItem) and created_req_holder["req"] is not None:
            obj.learning_result = ctx["ra2"]
            created_req_holder["req"].items.append(obj)

    session.add = MagicMock(side_effect=capture_add)

    req_dto = await service.crear_solicitud_reapertura(ctx["lider"], create_dto)
    assert req_dto.status == EstadoSolicitudReapertura.PENDING
    assert req_dto.planning_id == plan.id
    assert len(req_dto.items) == 1
    assert req_dto.items[0].learning_result_id == ctx["ra2"].id
    assert req_dto.items[0].requested is True
    assert req_dto.items[0].approved is False

    # RAs must remain LOCKED while request is PENDING
    assert ctx["ra2"].edit_status == EstadoEdicionRA.LOCKED
    assert any(e.event_type == "edit_request.created" for e in notification_dispatcher.get_recent_events())


# -----------------------------------------------------------------------------
# Scenario 5: Duplicate pending requests for the same RA are rejected (409)
# -----------------------------------------------------------------------------
async def test_5_duplicate_pending_edit_request_for_same_ra_is_rejected():
    ctx = _build_full_scenario()
    plan = ctx["planeacion"]
    plan.approval_status = EstadoAprobacionPlaneacion.APPROVED
    ctx["ra2"].edit_status = EstadoEdicionRA.LOCKED

    existing_pending = PlanningEditRequest(
        id=uuid.uuid4(),
        planning_id=plan.id,
        team_id=ctx["equipo"].id,
        requested_by=ctx["lider"].id,
        reason="Motivo previo",
        requested_changes="Cambios previos",
        status=EstadoSolicitudReapertura.PENDING,
    )

    session = AsyncMock()
    scope = AsyncMock()

    async def side_effect_execute(stmt):
        sql_str = str(stmt)
        res = MagicMock()
        if "planeaciones_pedagogicas" in sql_str:
            res.scalar_one_or_none.return_value = plan
        elif "procesos_curriculares" in sql_str:
            res.scalar_one_or_none.return_value = ctx["proceso"]
        elif "entregas_revision_curricular" in sql_str:
            res.scalars.return_value.first.return_value = ctx["entrega"]
        elif "planning_edit_requests" in sql_str:
            res.scalars.return_value.first.return_value = existing_pending
        return res

    session.execute.side_effect = side_effect_execute
    service = RevisionCurricularService(session, scope)

    dto = PlanningEditRequestCreateDTO(
        planning_id=plan.id,
        learning_result_ids=[ctx["ra2"].id],
        reason="Intento duplicado de solicitud sobre RA-02",
        requested_changes="Cambio duplicado sobre RA-02",
    )
    with pytest.raises(HTTPException) as exc_dup:
        await service.crear_solicitud_reapertura(ctx["lider"], dto)
    assert exc_dup.value.status_code == 409
    assert exc_dup.value.detail["code"] == "DUPLICATE_PENDING_EDIT_REQUEST"


# -----------------------------------------------------------------------------
# Scenario 6, 7, 8: Full approval, Partial approval, and Selective RA editing
# -----------------------------------------------------------------------------
async def test_6_7_8_partial_and_full_approval_unlocks_only_authorized_ras():
    ctx = _build_full_scenario()
    notification_dispatcher.clear_history()
    plan = ctx["planeacion"]
    plan.review_status = EstadoRevisionPlaneacion.APPROVED
    plan.approval_status = EstadoAprobacionPlaneacion.APPROVED
    plan.edit_status = EstadoEdicionRA.LOCKED
    for ra in (ctx["ra1"], ctx["ra2"], ctx["ra3"]):
        ra.edit_status = EstadoEdicionRA.LOCKED
        ra.approved_version = 1

    # Request asks for RA1, RA2, and RA3; Admin authorizes ONLY RA1 and RA3 (partial approval)
    req = PlanningEditRequest(
        id=uuid.uuid4(),
        planning_id=plan.id,
        team_id=ctx["equipo"].id,
        referencia_id=ctx["referencia_id"],
        requested_by=ctx["lider"].id,
        reason="Necesitamos actualizar RA-01, RA-02 y RA-03.",
        requested_changes="Ajustar evidencias y actividades.",
        status=EstadoSolicitudReapertura.PENDING,
    )
    item1 = PlanningEditRequestItem(id=uuid.uuid4(), request_id=req.id, learning_result_id=ctx["ra1"].id, requested=True, approved=False)
    item1.learning_result = ctx["ra1"]
    item2 = PlanningEditRequestItem(id=uuid.uuid4(), request_id=req.id, learning_result_id=ctx["ra2"].id, requested=True, approved=False)
    item2.learning_result = ctx["ra2"]
    item3 = PlanningEditRequestItem(id=uuid.uuid4(), request_id=req.id, learning_result_id=ctx["ra3"].id, requested=True, approved=False)
    item3.learning_result = ctx["ra3"]
    req.items = [item1, item2, item3]
    req.planning = plan
    req.team = ctx["equipo"]
    req.requester = ctx["lider"]
    req.reviewer = ctx["admin"]

    session = AsyncMock()
    added_objects: list[object] = []
    session.add = MagicMock(side_effect=lambda obj: added_objects.append(obj))
    scope = AsyncMock()

    async def side_effect_execute(stmt):
        sql_str = str(stmt)
        res = MagicMock()
        if "planning_edit_requests" in sql_str:
            res.scalar_one_or_none.return_value = req
        elif "planeaciones_pedagogicas" in sql_str:
            res.scalar_one_or_none.return_value = plan
        elif "planeacion_documento_config" in sql_str:
            res.scalar_one_or_none.return_value = ctx["doc_config"]
        elif "learning_result_versions" in sql_str:
            res.scalars.return_value.first.return_value = None
        elif "procesos_curriculares" in sql_str:
            res.scalar_one_or_none.return_value = ctx["proceso"]
        elif "resultados_aprendizaje" in sql_str:
            # Return the subset requested
            if str(ctx["ra2"].id) in sql_str or len(plan.resultados) == 3:
                res.scalars.return_value.all.return_value = [ctx["ra1"], ctx["ra2"], ctx["ra3"]]
            else:
                res.scalars.return_value.all.return_value = [ctx["ra1"], ctx["ra3"]]
        elif "conocimientos" in sql_str:
            res.scalars.return_value.all.return_value = [ctx["conocimiento"]]
        elif "criterios_evaluacion" in sql_str:
            res.scalars.return_value.all.return_value = [ctx["criterio"]]
        else:
            res.scalars.return_value.all.return_value = []
        return res

    session.execute.side_effect = side_effect_execute
    rev_service = RevisionCurricularService(session, scope)

    # Admin approves ONLY RA1 and RA3
    approved_dto = await rev_service.aprobar_solicitud_reapertura(
        ctx["admin"],
        req.id,
        PlanningEditRequestApproveDTO(
            approved_learning_result_ids=[ctx["ra1"].id, ctx["ra3"].id],
            admin_response="Se autoriza modificar únicamente RA-01 y RA-03. RA-02 permanece bloqueado.",
        ),
    )

    assert approved_dto.status == EstadoSolicitudReapertura.PARTIALLY_APPROVED
    assert plan.review_status == EstadoRevisionPlaneacion.CHANGES_ALLOWED
    assert plan.approval_status == EstadoAprobacionPlaneacion.PREVIOUS_VERSION_APPROVED
    assert plan.edit_status == EstadoEdicionRA.EDITABLE

    # Check per-RA lock status
    assert ctx["ra1"].edit_status == EstadoEdicionRA.EDITABLE
    assert ctx["ra1"].unlock_request_id == req.id
    assert ctx["ra3"].edit_status == EstadoEdicionRA.EDITABLE
    assert ctx["ra3"].unlock_request_id == req.id
    assert ctx["ra2"].edit_status == EstadoEdicionRA.LOCKED

    # Concurrency/Idempotency check: trying to approve or reject the same request again raises 409 Conflict
    with pytest.raises(HTTPException) as exc_conflict:
        await rev_service.aprobar_solicitud_reapertura(
            ctx["admin"],
            req.id,
            PlanningEditRequestApproveDTO(approved_learning_result_ids=[ctx["ra2"].id]),
        )
    assert exc_conflict.value.status_code == 409

    # Scenario 8: Now test PlaneacionPedagogicaService with partial reopening!
    # Attempting to modify locked RA2's complementary map entry must fail with LearningResultLockedError
    session.get.side_effect = lambda model, pk: {
        ProyectoFormativo: ctx["proyecto"],
        ProgramaFormacion: ctx["programa"],
        FaseProyecto: ctx["fase"],
        ActividadProyecto: ctx["actividad"],
    }.get(model)
    repo = AsyncMock()
    storage = AsyncMock()
    repo.get_by_id.return_value = plan
    repo.save.return_value = plan

    plan_service = PlaneacionPedagogicaService(session=session, repository=repo, storage_service=storage)
    asig1 = MagicMock(resultado_id=ctx["ra1"].id, competencia=ctx["comp"], resultado=ctx["ra1"], tipo_resultado=None)
    asig2 = MagicMock(resultado_id=ctx["ra2"].id, competencia=ctx["comp"], resultado=ctx["ra2"], tipo_resultado=None)
    asig3 = MagicMock(resultado_id=ctx["ra3"].id, competencia=ctx["comp"], resultado=ctx["ra3"], tipo_resultado=None)
    plan_service._load_asignaciones_for_actividad = AsyncMock(return_value=[asig1, asig2, asig3])
    plan_service._load_tipos_resultado = AsyncMock(return_value={})

    # 8a. Attempt to remove locked RA2 from the planning -> fails with LearningResultLockedError
    async def exec_missing_ra2(stmt):
        sql_str = str(stmt)
        res = MagicMock()
        if "resultados_aprendizaje" in sql_str:
            res.scalars.return_value.all.return_value = [ctx["ra1"], ctx["ra3"]]
        elif "conocimientos" in sql_str:
            res.scalars.return_value.all.return_value = [ctx["conocimiento"]]
        elif "criterios_evaluacion" in sql_str:
            res.scalars.return_value.all.return_value = [ctx["criterio"]]
        else:
            res.scalars.return_value.all.return_value = []
        return res

    session.execute.side_effect = exec_missing_ra2
    with pytest.raises(LearningResultLockedError):
        await plan_service.guardar_borrador(
            PlaneacionSaveDTO(
                planeacion_id=plan.id,
                proyecto_id=ctx["proyecto"].id,
                fase_id=ctx["fase"].id,
                actividad_id=ctx["actividad"].id,
                resultados_ids=[ctx["ra1"].id, ctx["ra3"].id],  # Missing locked RA2!
                conocimientos_ids=[ctx["conocimiento"].id],
                criterios_ids=[ctx["criterio"].id],
                datos_complementarios=plan.datos_complementarios,
            ),
            actor_id=ctx["lider"].id,
        )

    # 8b. Attempt to modify locked RA2's specific entry in rap_complementary_map -> fails with LearningResultLockedError
    async def exec_all_three(stmt):
        sql_str = str(stmt)
        res = MagicMock()
        if "resultados_aprendizaje" in sql_str:
            res.scalars.return_value.all.return_value = [ctx["ra1"], ctx["ra2"], ctx["ra3"]]
        elif "conocimientos" in sql_str:
            res.scalars.return_value.all.return_value = [ctx["conocimiento"]]
        elif "criterios_evaluacion" in sql_str:
            res.scalars.return_value.all.return_value = [ctx["criterio"]]
        else:
            res.scalars.return_value.all.return_value = []
        return res

    session.execute.side_effect = exec_all_three
    mutated_ra2_datos = {
        **plan.datos_complementarios,
        "rap_complementary_map": {
            **plan.datos_complementarios["rap_complementary_map"],
            str(ctx["ra2"].id): {
                **plan.datos_complementarios["rap_complementary_map"][str(ctx["ra2"].id)],
                "actividades_aprendizaje": "Cambio no autorizado sobre RA-02 bloqueado",
            },
        },
    }
    with pytest.raises(LearningResultLockedError):
        await plan_service.guardar_borrador(
            PlaneacionSaveDTO(
                planeacion_id=plan.id,
                proyecto_id=ctx["proyecto"].id,
                fase_id=ctx["fase"].id,
                actividad_id=ctx["actividad"].id,
                resultados_ids=[ctx["ra1"].id, ctx["ra2"].id, ctx["ra3"].id],
                conocimientos_ids=[ctx["conocimiento"].id],
                criterios_ids=[ctx["criterio"].id],
                datos_complementarios=mutated_ra2_datos,
            ),
            actor_id=ctx["lider"].id,
        )

    # 8c. Modifying unlocked RA1's entry while keeping RA2 intact succeeds and logs LEARNING_RESULT_MODIFIED!
    valid_ra1_datos = {
        **plan.datos_complementarios,
        "rap_complementary_map": {
            **plan.datos_complementarios["rap_complementary_map"],
            str(ctx["ra1"].id): {
                **plan.datos_complementarios["rap_complementary_map"][str(ctx["ra1"].id)],
                "actividades_aprendizaje": "Modelar casos de uso actualizados v2",
            },
        },
    }
    saved_res = await plan_service.guardar_borrador(
        PlaneacionSaveDTO(
            planeacion_id=plan.id,
            proyecto_id=ctx["proyecto"].id,
            fase_id=ctx["fase"].id,
            actividad_id=ctx["actividad"].id,
            resultados_ids=[ctx["ra1"].id, ctx["ra2"].id, ctx["ra3"].id],
            conocimientos_ids=[ctx["conocimiento"].id],
            criterios_ids=[ctx["criterio"].id],
            datos_complementarios=valid_ra1_datos,
        ),
        actor_id=ctx["lider"].id,
    )
    assert saved_res.id == plan.id
    from src.infrastructure.db.models.audit import EventoAuditoria

    audits = [obj.accion for obj in added_objects if isinstance(obj, EventoAuditoria)]
    assert "EDIT_REQUEST_PARTIALLY_APPROVED" in audits
    assert "LEARNING_RESULT_UNLOCKED" in audits
    assert "LEARNING_RESULT_MODIFIED" in audits


# -----------------------------------------------------------------------------
# Scenario 9: Admin can reject edit request and all RAs remain LOCKED
# -----------------------------------------------------------------------------
async def test_9_admin_rejects_edit_request_keeps_all_ras_locked():
    ctx = _build_full_scenario()
    notification_dispatcher.clear_history()
    plan = ctx["planeacion"]
    for ra in (ctx["ra1"], ctx["ra2"], ctx["ra3"]):
        ra.edit_status = EstadoEdicionRA.LOCKED

    req = PlanningEditRequest(
        id=uuid.uuid4(),
        planning_id=plan.id,
        team_id=ctx["equipo"].id,
        referencia_id=ctx["referencia_id"],
        requested_by=ctx["lider"].id,
        reason="Solicitud para ajustar RA-01",
        requested_changes="Cambiar duración",
        status=EstadoSolicitudReapertura.PENDING,
    )
    item1 = PlanningEditRequestItem(id=uuid.uuid4(), request_id=req.id, learning_result_id=ctx["ra1"].id, requested=True, approved=False)
    item1.learning_result = ctx["ra1"]
    req.items = [item1]
    req.planning = plan
    req.team = ctx["equipo"]
    req.requester = ctx["lider"]
    req.reviewer = ctx["admin"]

    session = AsyncMock()
    added_objects: list[object] = []
    session.add = MagicMock(side_effect=lambda obj: added_objects.append(obj))
    scope = AsyncMock()

    async def side_effect_execute(stmt):
        sql_str = str(stmt)
        res = MagicMock()
        if "planning_edit_requests" in sql_str:
            res.scalar_one_or_none.return_value = req
        elif "procesos_curriculares" in sql_str:
            res.scalar_one_or_none.return_value = ctx["proceso"]
        return res

    session.execute.side_effect = side_effect_execute
    service = RevisionCurricularService(session, scope)

    rejected = await service.rechazar_solicitud_reapertura(
        ctx["admin"],
        req.id,
        PlanningEditRequestRejectDTO(admin_response="No procede el cambio de duración en esta vigencia."),
    )

    assert rejected.status == EstadoSolicitudReapertura.REJECTED
    assert rejected.admin_response == "No procede el cambio de duración en esta vigencia."
    assert ctx["ra1"].edit_status == EstadoEdicionRA.LOCKED
    assert any(e.event_type == "edit_request.rejected" for e in notification_dispatcher.get_recent_events())


# -----------------------------------------------------------------------------
# Scenario 10, 11, 12: Resubmission re-locks RAs & completes request; Re-approval creates v2
# -----------------------------------------------------------------------------
async def test_10_11_12_resubmit_relocks_and_reapprove_creates_version_2_and_audits():
    ctx = _build_full_scenario()
    notification_dispatcher.clear_history()
    plan = ctx["planeacion"]
    plan.review_status = EstadoRevisionPlaneacion.CHANGES_ALLOWED
    plan.approval_status = EstadoAprobacionPlaneacion.PREVIOUS_VERSION_APPROVED
    plan.edit_status = EstadoEdicionRA.EDITABLE
    plan.official_storage_key = "planeaciones/individual_v1.xlsx"
    plan.official_version = 1

    # RA1 was unlocked by an approved edit request; RA2 and RA3 remained locked
    req = PlanningEditRequest(
        id=uuid.uuid4(),
        planning_id=plan.id,
        team_id=ctx["equipo"].id,
        referencia_id=ctx["referencia_id"],
        requested_by=ctx["lider"].id,
        reason="Ajustar RA-01",
        requested_changes="Ajustar actividad de RA-01",
        status=EstadoSolicitudReapertura.APPROVED,
    )
    ctx["ra1"].edit_status = EstadoEdicionRA.EDITABLE
    ctx["ra1"].unlock_request_id = req.id
    ctx["ra1"].approved_version = 1
    ctx["ra2"].edit_status = EstadoEdicionRA.LOCKED
    ctx["ra2"].approved_version = 1
    ctx["ra3"].edit_status = EstadoEdicionRA.LOCKED
    ctx["ra3"].approved_version = 1

    ctx["entrega"].estado = EstadoEntregaRevision.APROBADO
    ctx["entrega"].descarga_habilitada = True
    ctx["entrega"].version = 1

    session = AsyncMock()
    added_objects: list[object] = []
    latest_delivery_holder = {"entrega": ctx["entrega"]}

    def capture_add(obj):
        added_objects.append(obj)
        if isinstance(obj, EntregaRevisionCurricular):
            obj.equipo_ejecutor = ctx["equipo"]
            obj.programa = ctx["programa"]
            obj.proyecto = ctx["proyecto"]
            obj.enviado_por = ctx["lider"]
            obj.observaciones = []
            latest_delivery_holder["entrega"] = obj

    session.add = MagicMock(side_effect=capture_add)
    scope = AsyncMock()

    async def side_effect_execute(stmt):
        sql_str = str(stmt)
        res = MagicMock()
        if "procesos_curriculares" in sql_str:
            res.scalar_one_or_none.return_value = ctx["proceso"]
        elif "actividades_proyecto" in sql_str:
            res.scalars.return_value.all.return_value = [ctx["actividad"]]
        elif "planeaciones_pedagogicas" in sql_str:
            res.scalars.return_value.all.return_value = [plan]
            res.scalar_one_or_none.return_value = plan
        elif "planeacion_documento_config" in sql_str:
            res.scalar_one_or_none.return_value = ctx["doc_config"]
        elif "entregas_revision_curricular" in sql_str:
            res.scalars.return_value.first.return_value = latest_delivery_holder["entrega"]
            res.scalar_one_or_none.return_value = latest_delivery_holder["entrega"]
            res.scalars.return_value.all.return_value = [latest_delivery_holder["entrega"], ctx["entrega"]]
        elif "planning_edit_requests" in sql_str:
            res.scalars.return_value.all.return_value = [req]
        else:
            res.scalars.return_value.all.return_value = []
        return res

    session.execute.side_effect = side_effect_execute
    service = RevisionCurricularService(session, scope)

    # 10. Leader resubmits planning to pedagogical review
    resubmitted = await service.enviar_a_revision(
        ctx["lider"],
        ctx["referencia_id"],
        EnvioRevisionRequestDTO(notas_entrega="Se realizaron los ajustes autorizados en RA-01"),
    )

    assert resubmitted.version == 2
    assert resubmitted.estado == EstadoEntregaRevision.REENVIADO
    assert plan.review_status == EstadoRevisionPlaneacion.IN_REVIEW
    assert plan.edit_status == EstadoEdicionRA.LOCKED
    assert ctx["ra1"].edit_status == EstadoEdicionRA.LOCKED
    assert req.status == EstadoSolicitudReapertura.COMPLETED

    # 11. Admin approves the new submission (v2)
    approved_v2 = await service.aprobar_entrega(
        ctx["admin"],
        latest_delivery_holder["entrega"].id,
        AprobacionRequestDTO(notas_aprobacion="Aprobada versión 2 con cambios en RA-01"),
    )

    assert approved_v2.estado == EstadoEntregaRevision.APROBADO
    assert approved_v2.descarga_habilitada is True
    assert plan.review_status == EstadoRevisionPlaneacion.APPROVED
    assert plan.approval_status == EstadoAprobacionPlaneacion.APPROVED
    assert plan.edit_status == EstadoEdicionRA.LOCKED
    assert plan.official_version == 2

    for ra in (ctx["ra1"], ctx["ra2"], ctx["ra3"]):
        assert ra.edit_status == EstadoEdicionRA.LOCKED
        assert ra.approved_version == 2
        assert ra.unlock_request_id is None

    # 12. Verify complete audit trail and notification events
    from src.infrastructure.db.models.audit import EventoAuditoria

    audits = [obj.accion for obj in added_objects if isinstance(obj, EventoAuditoria)]
    assert "PLANNING_RESUBMITTED" in audits
    assert "LEARNING_RESULT_RELOCKED" in audits
    assert "LEARNING_RESULT_REAPPROVED" in audits
    assert "PLANNING_APPROVED" in audits

    events = [e.event_type for e in notification_dispatcher.get_recent_events()]
    assert "planning.resubmitted" in events
    assert "planning.reapproved" in events
