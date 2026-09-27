"""Unit and integration tests for Pedagogical Review and Download Authorization Workflow."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from src.application.dto.revision_curricular import (
    AjusteReportarDTO,
    AprobacionRequestDTO,
    BandejaRevisionFiltrosDTO,
    EnvioRevisionRequestDTO,
    ObservacionCreateDTO,
)
from src.application.services.access_scope import AccessScopeService
from src.application.services.revision_curricular_service import (
    RevisionCurricularService,
)
from src.domain.shared.enums import (
    EstadoBloque,
    EstadoEntregaRevision,
    EstadoEquipo,
    EstadoObservacionRevision,
    EstadoUsuario,
    RolUsuario,
    TipoElementoObservacion,
)
from src.infrastructure.db.models.auth import Rol, Usuario
from src.infrastructure.db.models.curriculum import Competencia, ProgramaFormacion
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
    ObservacionRevision,
)
from src.interfaces.http.app import app

pytestmark = pytest.mark.anyio


def _make_user(role_name: str, email: str = "user@sena.edu.co") -> Usuario:
    user = Usuario(
        id=uuid.uuid4(),
        email=email,
        hashed_password="hash",
        nombre="Test",
        apellido="User",
        activo=True,
        estado=EstadoUsuario.ACTIVO,
    )
    rol = Rol(id=uuid.uuid4(), nombre=role_name)
    user.roles = [rol]
    return user


def _build_test_entities():
    lider = _make_user(RolUsuario.LIDER_EQUIPO_EJECUTOR.value, "lider@sena.edu.co")
    admin = _make_user(RolUsuario.ADMIN.value, "admin@sena.edu.co")

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

    fase = FaseProyecto(id=uuid.uuid4(), proyecto_id=proy.id, nombre_fase="Fase 1 - Analisis")
    actividad = ActividadProyecto(id=uuid.uuid4(), fase_id=fase.id, descripcion="Definir requerimientos")
    planeacion = PlaneacionPedagogica(
        id=uuid.uuid4(),
        proyecto_id=proy.id,
        fase_id=fase.id,
        actividad_id=actividad.id,
        estado=EstadoBloque.COMPLETO,
        datos_complementarios={
            "horas_directas": 20,
            "horas_independientes": 10,
            "horas_totales": 30,
            "descripcion_actividad": "Actividad de analisis",
        },
        storage_key="programas/adso/consolidado.xlsx",
        version=1,
    )

    from datetime import date
    config = PlaneacionDocumentoConfig(
        proyecto_id=proy.id,
        fecha_elaboracion=date.today(),
        clasificacion_informacion="PUBLICA",
        equipo_gestion_curricular=["Equipo ADSO"],
        regional="Distrito Capital",
        centro_formacion="CSF",
        storage_key="programas/adso/consolidado.xlsx",
    )

    return {
        "lider": lider,
        "admin": admin,
        "equipo": equipo,
        "programa": prog,
        "proyecto": proy,
        "proceso": proceso,
        "fase": fase,
        "actividad": actividad,
        "planeacion": planeacion,
        "config": config,
        "referencia_id": ref_id,
    }


async def test_preflight_validation_blocked_when_no_plannings():
    ctx = _build_test_entities()
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
            mock_res.scalars.return_value.all.return_value = []
        elif "from planeacion_documento_config" in text:
            mock_res.scalar_one_or_none.return_value = None
        return mock_res

    session.execute.side_effect = mock_execute
    service = RevisionCurricularService(session, scope)

    preflight = await service.validate_preflight_envio(ctx["lider"], ctx["referencia_id"])
    assert preflight.listo is False
    assert len(preflight.pendientes) >= 2
    assert any("Falta registrar la planeación" in b or "No se ha registrado" in b for b in preflight.pendientes)


async def test_preflight_validation_ready_when_complete():
    ctx = _build_test_entities()
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
    assert len(preflight.pendientes) == 0
    assert preflight.resumen.get("planeaciones_completas") == 1
    assert preflight.resumen.get("faltantes_count") == 0


async def test_enviar_a_revision_and_versioning():
    ctx = _build_test_entities()
    session = AsyncMock()
    scope = AsyncMock()
    scope.require_process_access.return_value = ctx["proceso"]

    entregas_db: list[EntregaRevisionCurricular] = []

    def mock_add(entity):
        if isinstance(entity, EntregaRevisionCurricular):
            entity.equipo_ejecutor = ctx["equipo"]
            entity.programa = ctx["programa"]
            entity.proyecto = ctx["proyecto"]
            entregas_db.append(entity)

    session.add = MagicMock(side_effect=mock_add)

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
            latest = entregas_db[-1] if entregas_db else None
            mock_res.scalars.return_value.first.return_value = latest
            mock_res.scalar_one_or_none.return_value = latest
            mock_res.scalars.return_value.all.return_value = entregas_db
        return mock_res

    session.execute.side_effect = mock_execute
    service = RevisionCurricularService(session, scope)

    req = EnvioRevisionRequestDTO(notas_entrega="Primera versión completa de ADSO")
    detalle = await service.enviar_a_revision(ctx["lider"], ctx["referencia_id"], req)

    assert detalle.version == 1
    assert detalle.estado == EstadoEntregaRevision.ENVIADO_REVISION
    assert detalle.descarga_habilitada is False
    assert detalle.notas_entrega == "Primera versión completa de ADSO"
    assert session.commit.called


async def test_verify_download_authorization_gatekeeping():
    ctx = _build_test_entities()
    session = AsyncMock()
    scope = AsyncMock()

    # Case 1: No delivery or not approved
    async def mock_execute_unapproved(stmt):
        mock_res = MagicMock()
        mock_res.scalar_one_or_none.return_value = None
        return mock_res

    session.execute.side_effect = mock_execute_unapproved
    service = RevisionCurricularService(session, scope)
    autorizado, motivo = await service.verify_download_authorization(ctx["proyecto"].id)
    assert autorizado is False
    assert "no ha sido aprobada" in motivo

    # Case 2: Approved delivery matches snapshot
    entrega_aprobada = EntregaRevisionCurricular(
        id=uuid.uuid4(),
        proceso_curricular_id=ctx["proceso"].id,
        proyecto_id=ctx["proyecto"].id,
        referencia_id=ctx["referencia_id"],
        version=1,
        estado=EstadoEntregaRevision.APROBADO,
        descarga_habilitada=True,
        snapshot_metadatos={
            "planeaciones_count": 1,
            "horas_directas_total": 20.0,
            "horas_independientes_total": 10.0,
            "checksum_consolidado": "test-checksum",
        },
    )

    async def mock_execute_approved(stmt):
        text = str(stmt).lower()
        mock_res = MagicMock()
        if "from entregas_revision_curricular" in text:
            mock_res.scalar_one_or_none.return_value = entrega_aprobada
        elif "from planeaciones_pedagogicas" in text:
            mock_res.scalars.return_value.all.return_value = [ctx["planeacion"]]
        elif "from planeacion_documento_config" in text:
            mock_res.scalar_one_or_none.return_value = ctx["config"]
        return mock_res

    session.execute.side_effect = mock_execute_approved
    service._build_snapshot_metadatos = AsyncMock(return_value={
        "planeaciones_count": 1,
        "checksum_consolidado": "test-checksum",
    })

    autorizado, motivo = await service.verify_download_authorization(ctx["proyecto"].id)
    assert autorizado is True
    assert motivo is None


async def test_full_pedagogical_review_lifecycle():
    ctx = _build_test_entities()
    session = AsyncMock()
    scope = AsyncMock()

    entrega = EntregaRevisionCurricular(
        id=uuid.uuid4(),
        proceso_curricular_id=ctx["proceso"].id,
        equipo_ejecutor_id=ctx["equipo"].id,
        programa_id=ctx["programa"].id,
        proyecto_id=ctx["proyecto"].id,
        referencia_id=ctx["referencia_id"],
        enviado_por_id=ctx["lider"].id,
        version=1,
        estado=EstadoEntregaRevision.ENVIADO_REVISION,
        descarga_habilitada=False,
        fecha_envio=datetime.now(UTC),
        snapshot_metadatos={"planeaciones_count": 1},
    )
    entrega.observaciones = []
    entrega.proceso_curricular = ctx["proceso"]
    observaciones_db: dict[uuid.UUID, ObservacionRevision] = {}

    def mock_add(entity):
        if isinstance(entity, ObservacionRevision):
            entity.creado_por = ctx["admin"]
            observaciones_db[entity.id] = entity
            if entity not in entrega.observaciones:
                entrega.observaciones.append(entity)

    session.add = MagicMock(side_effect=mock_add)

    async def mock_execute(stmt):
        text = str(stmt).lower()
        mock_res = MagicMock()
        mock_res.scalars.return_value.first.return_value = None
        mock_res.scalars.return_value.all.return_value = []
        mock_res.scalar_one_or_none.return_value = None
        if "from entregas_revision_curricular" in text:
            mock_res.scalar_one_or_none.return_value = entrega
            mock_res.scalars.return_value.first.return_value = entrega
            mock_res.scalars.return_value.all.return_value = [entrega]
        elif "from procesos_curriculares" in text:
            mock_res.scalar_one_or_none.return_value = ctx["proceso"]
        elif "from planeaciones_pedagogicas" in text:
            mock_res.scalars.return_value.all.return_value = [ctx["planeacion"]]
        elif "from planeacion_documento_config" in text:
            mock_res.scalar_one_or_none.return_value = ctx["config"]
        elif "from observaciones_revision_curricular" in text:
            obs_list = list(observaciones_db.values())
            mock_res.scalars.return_value.all.return_value = obs_list
            if obs_list:
                mock_res.scalar_one_or_none.return_value = obs_list[-1]
                mock_res.scalars.return_value.first.return_value = obs_list[-1]
            else:
                mock_res.scalar_one_or_none.return_value = None
        return mock_res

    session.execute.side_effect = mock_execute
    service = RevisionCurricularService(session, scope)

    # 1. Iniciar revision
    detalle = await service.iniciar_revision(ctx["admin"], entrega.id)
    assert detalle.estado == EstadoEntregaRevision.EN_REVISION

    # 2. Non-reviewer trying to start review raises 403
    with pytest.raises(HTTPException) as exc:
        await service.iniciar_revision(ctx["lider"], entrega.id)
    assert exc.value.status_code == 403

    # 3. Crear observacion
    obs_dto = ObservacionCreateDTO(
        target_type=TipoElementoObservacion.PLANEACION,
        target_id=ctx["planeacion"].id,
        section_key="Estrategias Didácticas",
        comentario="Ampliar la justificación de trabajo colaborativo en la actividad.",
    )
    obs = await service.crear_observacion(ctx["admin"], entrega.id, obs_dto)
    assert obs.estado == EstadoObservacionRevision.PENDIENTE
    assert obs.comentario == "Ampliar la justificación de trabajo colaborativo en la actividad."

    # 4. Solicitar ajustes
    detalle = await service.solicitar_ajustes(ctx["admin"], entrega.id)
    assert detalle.estado == EstadoEntregaRevision.AJUSTES_SOLICITADOS
    assert detalle.descarga_habilitada is False

    # 5. Equipo reporta ajuste
    reporte = AjusteReportarDTO(comentario_ajuste="Se incorporó técnica de ABP con rúbrica detallada.")
    obs_reportada = await service.reportar_ajuste(ctx["lider"], obs.id, reporte)
    assert obs_reportada.estado == EstadoObservacionRevision.AJUSTE_REPORTADO
    assert obs_reportada.comentario_ajuste == "Se incorporó técnica de ABP con rúbrica detallada."

    # 6. Intentar aprobar cuando hay observaciones no resueltas falla (422)
    with pytest.raises(HTTPException) as exc:
        await service.aprobar_entrega(ctx["admin"], entrega.id, AprobacionRequestDTO(notas_aprobacion="Ok"))
    assert exc.value.status_code == 422

    # 7. Resolver observacion
    obs_resuelta = await service.resolver_observacion(ctx["admin"], obs.id)
    assert obs_resuelta.estado == EstadoObservacionRevision.RESUELTO

    # 8. Aprobar entrega y habilitar descarga
    detalle_aprobado = await service.aprobar_entrega(
        ctx["admin"],
        entrega.id,
        AprobacionRequestDTO(notas_aprobacion="Planeación institucionalmente aprobada."),
    )
    assert detalle_aprobado.estado == EstadoEntregaRevision.APROBADO
    assert detalle_aprobado.descarga_habilitada is True

    # 9. Anti-tampering invalidation on mutation
    await service.invalidate_approval_on_mutation(ctx["proyecto"].id, ctx["lider"].id)
    assert entrega.estado == EstadoEntregaRevision.BORRADOR
    assert entrega.descarga_habilitada is False


def test_revision_endpoints_registration():
    client = TestClient(app)
    random_ref = uuid.uuid4()
    # Preflight endpoint exists
    res = client.get(f"/api/v1/revision-curricular/proceso/{random_ref}/preflight-envio")
    assert res.status_code != 404 or "detail" in res.json()

    # Detail endpoint exists at /entregas/{entrega_id}
    res_det = client.get(f"/api/v1/revision-curricular/entregas/{random_ref}")
    assert res_det.status_code != 404 or "detail" in res_det.json()

    # Detail endpoint also exists at /entregas/{entrega_id}/detalle-completo
    res_det_comp = client.get(f"/api/v1/revision-curricular/entregas/{random_ref}/detalle-completo")
    assert res_det_comp.status_code != 404 or "detail" in res_det_comp.json()


@pytest.mark.anyio
async def test_preflight_allows_partial_delivery():
    ctx = _build_test_entities()
    session = AsyncMock()
    scope = AsyncMock()
    scope.require_process_access.return_value = ctx["proceso"]

    actividad_2 = ActividadProyecto(
        id=uuid.uuid4(),
        fase_id=ctx["fase"].id,
        descripcion="Segunda actividad sin planeación",
    )

    created_deliveries = []

    def mock_add(entity):
        if isinstance(entity, EntregaRevisionCurricular):
            entity.equipo_ejecutor = ctx["equipo"]
            entity.programa = ctx["programa"]
            entity.proyecto = ctx["proyecto"]
            entity.enviado_por = ctx["lider"]
            entity.observaciones = []
            created_deliveries.append(entity)

    session.add = MagicMock(side_effect=mock_add)

    async def mock_execute(stmt):
        text = str(stmt).lower()
        mock_res = MagicMock()
        mock_res.scalars.return_value.first.return_value = None
        mock_res.scalars.return_value.all.return_value = []
        mock_res.scalar_one_or_none.return_value = None
        if "from procesos_curriculares" in text:
            mock_res.scalar_one_or_none.return_value = ctx["proceso"]
        elif "from actividades_proyecto" in text:
            # 2 activities in project, but only 1 has complete planning
            mock_res.scalars.return_value.all.return_value = [ctx["actividad"], actividad_2]
        elif "from planeaciones_pedagogicas" in text:
            mock_res.scalars.return_value.all.return_value = [ctx["planeacion"]]
        elif "from planeacion_documento_config" in text:
            mock_res.scalar_one_or_none.return_value = ctx["config"]
        elif "from entregas_revision_curricular" in text:
            if created_deliveries:
                mock_res.scalar_one_or_none.return_value = created_deliveries[-1]
                mock_res.scalars.return_value.first.return_value = created_deliveries[-1]
                mock_res.scalars.return_value.all.return_value = created_deliveries
            else:
                mock_res.scalars.return_value.first.return_value = None
        return mock_res

    session.execute.side_effect = mock_execute
    service = RevisionCurricularService(session, scope)

    preflight = await service.validate_preflight_envio(ctx["lider"], ctx["referencia_id"])
    assert preflight.listo is True
    assert len(preflight.pendientes) == 0
    assert preflight.resumen["es_entrega_parcial"] is True
    assert preflight.resumen["planeaciones_completas"] == 1
    assert preflight.resumen["total_actividades_proyecto"] == 2
    assert len(preflight.advertencias) > 0

    # Submission succeeds for partial batch
    entrega = await service.enviar_a_revision(
        ctx["lider"],
        ctx["referencia_id"],
        EnvioRevisionRequestDTO(notas_entrega="Entrega parcial de la primera actividad"),
    )
    assert entrega.version == 1
    assert entrega.estado == EstadoEntregaRevision.ENVIADO_REVISION
    assert entrega.snapshot_metadatos["planeaciones_count"] == 1


