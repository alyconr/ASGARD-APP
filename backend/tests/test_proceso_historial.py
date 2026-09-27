"""Tests for ProcesoHistorialService and process change tracking on a single process."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException, status
from fastapi.testclient import TestClient

from src.application.services.access_scope import AccessScopeService
from src.application.services.proceso_historial import ProcesoHistorialService
from src.domain.shared.enums import (
    EstadoBloque,
    EstadoEquipo,
    EstadoScopeProceso,
    EstadoUsuario,
    RolUsuario,
    TipoNecesidadProceso,
)
from src.infrastructure.db.models.audit import EventoAuditoria
from src.infrastructure.db.models.auth import Rol, Usuario
from src.infrastructure.db.models.curriculum import Competencia, ProgramaFormacion
from src.infrastructure.db.models.drafts import BorradorSesion
from src.infrastructure.db.models.organizacion import (
    Coordinacion,
    EquipoEjecutor,
    Especialidad,
    ProcesoCurricular,
)
from src.infrastructure.db.models.planeacion import PlaneacionPedagogica
from src.infrastructure.db.models.proyecto import FaseProyecto, ProyectoFormativo
from src.infrastructure.db.session import get_async_session
from src.interfaces.http.app import app
from src.interfaces.http.deps import get_access_scope_service, get_current_user

pytestmark = pytest.mark.anyio


def make_test_user(rol_name: RolUsuario, user_id: uuid.UUID | None = None) -> Usuario:
    u_id = user_id or uuid.uuid4()
    rol = Rol(id=uuid.uuid4(), nombre=rol_name.value)
    user = Usuario(
        id=u_id,
        nombre="Test",
        apellido="User",
        email=f"user-{u_id.hex[:6]}@sena.edu.co",
        hashed_password="hash",
        estado=EstadoUsuario.ACTIVO,
    )
    user.roles = [rol]
    return user


class ProcesoHistorialMockDbSession:
    """Async session double configured for process history and audit checks."""

    def __init__(self) -> None:
        self.procesos: list[ProcesoCurricular] = []
        self.drafts: list[BorradorSesion] = []
        self.planeaciones: list[PlaneacionPedagogica] = []
        self.eventos: list[EventoAuditoria] = []
        self.committed = False

    async def execute(self, statement: Any) -> MagicMock:
        mock_result = MagicMock()
        text = str(statement).lower()

        if "from procesos_curriculares" in text:
            # Check for filter by referencia_id
            for p in self.procesos:
                if str(p.referencia_id) in str(statement):
                    mock_result.scalar_one_or_none.return_value = p
                    mock_result.scalars.return_value.all.return_value = [p]
                    return mock_result
            if self.procesos:
                mock_result.scalar_one_or_none.return_value = self.procesos[0]
                mock_result.scalars.return_value.all.return_value = self.procesos
            else:
                mock_result.scalar_one_or_none.return_value = None
                mock_result.scalars.return_value.all.return_value = []
            return mock_result

        if "from borradores_sesiones" in text:
            mock_result.scalar_one_or_none.return_value = self.drafts[0] if self.drafts else None
            mock_result.scalars.return_value.all.return_value = self.drafts
            return mock_result

        if "from planeaciones_pedagogicas" in text:
            mock_result.scalars.return_value.all.return_value = self.planeaciones
            return mock_result

        if "from eventos_auditoria" in text:
            mock_result.scalars.return_value.all.return_value = self.eventos
            return mock_result

        mock_result.scalar_one_or_none.return_value = None
        mock_result.scalars.return_value.all.return_value = []
        return mock_result

    def add(self, obj: Any) -> None:
        if isinstance(obj, EventoAuditoria):
            self.eventos.append(obj)
        elif isinstance(obj, ProcesoCurricular):
            self.procesos.append(obj)

    async def commit(self) -> None:
        self.committed = True

    async def refresh(self, obj: Any) -> None:
        pass


def setup_mock_environment():
    db = ProcesoHistorialMockDbSession()
    ref_id = uuid.uuid4()
    coord = Coordinacion(id=uuid.uuid4(), codigo="COORD-01", nombre="Coordinación TIC", activo=True)
    esp = Especialidad(id=uuid.uuid4(), coordinacion_id=coord.id, codigo="ESP-01", nombre="Software", activo=True)
    lider = make_test_user(RolUsuario.LIDER_EQUIPO_EJECUTOR)
    equipo = EquipoEjecutor(
        id=uuid.uuid4(),
        nombre="ADSO-NOCTURNO",
        coordinacion_id=coord.id,
        especialidad_id=esp.id,
        lider_id=lider.id,
        estado=EstadoEquipo.ACTIVO,
    )
    equipo.lider = lider

    prog = ProgramaFormacion(
        id=uuid.uuid4(),
        codigo_programa="228118",
        nombre_programa="ADSO",
        version_programa="1",
        modalidad_formacion="PRESENCIAL",
    )
    prog.competencias = [
        Competencia(
            id=uuid.uuid4(),
            programa_id=prog.id,
            codigo_competencia="COMP-01",
            nombre_competencia="Desarrollo Backend",
        )
    ]

    proy = ProyectoFormativo(
        id=uuid.uuid4(),
        programa_id=prog.id,
        codigo_proyecto="PROY-2026",
        nombre_proyecto="Plataforma Integrada",
        version_proyecto="1",
    )
    proy.fases = [
        FaseProyecto(
            id=uuid.uuid4(),
            proyecto_id=proy.id,
            nombre_fase="FASE 1",
            actividades=[],
        )
    ]

    proceso = ProcesoCurricular(
        id=uuid.uuid4(),
        referencia_id=ref_id,
        coordinacion_id=coord.id,
        especialidad_id=esp.id,
        equipo_ejecutor_id=equipo.id,
        lider_id=lider.id,
        tipo_necesidad=TipoNecesidadProceso.CREAR_PLANEACION,
        estado_scope=EstadoScopeProceso.ASIGNADO,
        programa_id=prog.id,
        proyecto_id=proy.id,
        creado_por=lider.id,
    )
    proceso.coordinacion = coord
    proceso.especialidad = esp
    proceso.equipo_ejecutor = equipo
    proceso.programa = prog
    proceso.proyecto = proy

    db.procesos.append(proceso)

    # Add initial creation event
    ev1 = EventoAuditoria(
        id=uuid.uuid4(),
        entidad="ProcesoCurricular",
        entidad_id=proceso.id,
        accion="CURRICULAR_PROCESS_STARTED",
        actor_usuario_id=lider.id,
        referencia_id=ref_id,
        detalle={"codigo_programa": "228118"},
        fecha_evento=datetime(2026, 9, 20, 10, 0, tzinfo=UTC),
    )
    ev1.actor = lider
    db.eventos.append(ev1)

    return db, proceso, lider


@pytest.mark.anyio
async def test_obtener_historial_proceso_unit():
    """Service returns consolidated process history with uniqueness guarantee."""
    db, proceso, lider = setup_mock_environment()

    scope_mock = AsyncMock(spec=AccessScopeService)
    scope_mock.require_process_access.return_value = proceso

    service = ProcesoHistorialService(db, scope_service=scope_mock)  # type: ignore
    historial = await service.obtener_historial(actor=lider, referencia_id=proceso.referencia_id)

    assert historial.proceso_id == proceso.id
    assert historial.referencia_id == proceso.referencia_id
    assert historial.garantia_unicidad is True
    assert historial.equipo is not None
    assert historial.equipo["nombre"] == "ADSO-NOCTURNO"
    assert historial.programa is not None
    assert historial.programa["codigo"] == "228118"
    assert historial.total_cambios >= 1
    assert len(historial.cambios) >= 1
    assert historial.cambios[0].tipo_evento == "CREACION"
    assert "iniciado" in historial.cambios[0].descripcion.lower()
    assert historial.cambios[0].actor is not None
    assert historial.cambios[0].actor.id == lider.id
    assert historial.cambios[0].actor.email == lider.email
    assert historial.cambios[0].actor.rol == RolUsuario.LIDER_EQUIPO_EJECUTOR.value


@pytest.mark.anyio
async def test_obtener_historial_fallback_actor():
    """Events without explicit actor fallback to process leader so user is always visible."""
    db, proceso, lider = setup_mock_environment()

    ev_no_actor = EventoAuditoria(
        id=uuid.uuid4(),
        entidad="ProgramaFormacion",
        entidad_id=proceso.programa_id,
        accion="EXCEL_CANONICO_IMPORTADO",
        actor_usuario_id=None,
        referencia_id=proceso.referencia_id,
        detalle={"criterios": 10},
        fecha_evento=datetime(2026, 9, 21, 10, 0, tzinfo=UTC),
    )
    ev_no_actor.actor = None
    db.eventos.append(ev_no_actor)

    scope_mock = AsyncMock(spec=AccessScopeService)
    scope_mock.require_process_access.return_value = proceso

    service = ProcesoHistorialService(db, scope_service=scope_mock)  # type: ignore
    historial = await service.obtener_historial(actor=lider, referencia_id=proceso.referencia_id)

    # ev_no_actor is the newest event (Sept 21) so it comes first
    assert historial.cambios[0].actor is not None
    assert historial.cambios[0].actor.id == lider.id
    assert historial.cambios[0].actor.email == lider.email


@pytest.mark.anyio
async def test_registrar_cambio_operates_on_same_process():
    """Registering changes modifies the existing process and guarantees NO new process is created."""
    db, proceso, lider = setup_mock_environment()

    scope_mock = AsyncMock(spec=AccessScopeService)
    scope_mock.require_process_access.return_value = proceso

    service = ProcesoHistorialService(db, scope_service=scope_mock)  # type: ignore

    initial_procs_count = len(db.procesos)
    assert initial_procs_count == 1

    cambio = await service.registrar_cambio(
        actor=lider,
        referencia_id=proceso.referencia_id,
        accion="ACTUALIZACION_METADATOS",
        descripcion="Se ajustó la configuración didáctica",
        detalle={"horas_didacticas": 40},
    )

    # Invariant: Total processes remains exactly 1
    assert len(db.procesos) == 1
    assert db.committed is True
    assert cambio.accion == "ACTUALIZACION_METADATOS"
    assert cambio.descripcion == "Se ajustó la configuración didáctica"
    assert cambio.tipo_evento == "CAMBIO_REGISTRADO"
    assert cambio.entidad_id == proceso.id


def test_api_get_proceso_historial_endpoint():
    """GET /api/v1/procesos/{referencia_id}/historial returns 200 with change history."""
    db, proceso, lider = setup_mock_environment()

    scope_mock = AsyncMock(spec=AccessScopeService)
    scope_mock.require_process_access.return_value = proceso

    app.dependency_overrides[get_async_session] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: lider
    app.dependency_overrides[get_access_scope_service] = lambda: scope_mock

    try:
        client = TestClient(app)
        resp = client.get(f"/api/v1/procesos/{proceso.referencia_id}/historial")
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert data["referencia_id"] == str(proceso.referencia_id)
        assert data["garantia_unicidad"] is True
        assert data["total_cambios"] >= 1
        assert len(data["cambios"]) >= 1
    finally:
        app.dependency_overrides.clear()


def test_api_registrar_cambio_proceso_endpoint():
    """POST /api/v1/procesos/{referencia_id}/cambios registers note on the same process."""
    db, proceso, lider = setup_mock_environment()

    scope_mock = AsyncMock(spec=AccessScopeService)
    scope_mock.require_process_access.return_value = proceso

    app.dependency_overrides[get_async_session] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: lider
    app.dependency_overrides[get_access_scope_service] = lambda: scope_mock

    try:
        client = TestClient(app)
        payload = {
            "accion": "REVISION_OBSERVACION",
            "descripcion": "Verificación de coherencia curricular aprobada",
            "detalle": {"aprobado": True},
        }
        resp = client.post(f"/api/v1/procesos/{proceso.referencia_id}/cambios", json=payload)
        assert resp.status_code == status.HTTP_201_CREATED
        data = resp.json()
        assert data["accion"] == "REVISION_OBSERVACION"
        assert data["descripcion"] == "Verificación de coherencia curricular aprobada"
        assert data["entidad"] == "ProcesoCurricular"
    finally:
        app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_historial_incluye_eventos_de_planeacion_pedagogica():
    """Service classifies and displays planning draft, complete, and format generation events."""
    db, proceso, lider = setup_mock_environment()

    scope_mock = AsyncMock(spec=AccessScopeService)
    scope_mock.require_process_access.return_value = proceso

    plan_id = uuid.uuid4()
    # 1. Evento de creación de borrador de planeación
    ev_draft = EventoAuditoria(
        id=uuid.uuid4(),
        entidad="PlaneacionPedagogica",
        entidad_id=plan_id,
        accion="PLANEACION_CREADA",
        actor_usuario_id=lider.id,
        referencia_id=proceso.referencia_id,
        detalle={
            "planeacion_id": str(plan_id),
            "descripcion_actividad": "Construir prototipo de arquitectura microservicios",
            "resultados_count": 2,
        },
        fecha_evento=datetime(2026, 9, 21, 14, 0, tzinfo=UTC),
    )
    ev_draft.actor = lider
    db.eventos.append(ev_draft)

    # 2. Evento de planeación completada
    ev_complete = EventoAuditoria(
        id=uuid.uuid4(),
        entidad="PlaneacionPedagogica",
        entidad_id=plan_id,
        accion="PLANEACION_COMPLETADA",
        actor_usuario_id=lider.id,
        referencia_id=proceso.referencia_id,
        detalle={
            "planeacion_id": str(plan_id),
            "descripcion_actividad": "Construir prototipo de arquitectura microservicios",
            "file_name": "GPFI-F-134V05-planeacion.xlsx",
        },
        fecha_evento=datetime(2026, 9, 22, 16, 0, tzinfo=UTC),
    )
    ev_complete.actor = lider
    db.eventos.append(ev_complete)

    # 3. Evento de generación de formato consolidado GPFI-F-134
    ev_excel = EventoAuditoria(
        id=uuid.uuid4(),
        entidad="ProyectoFormativo",
        entidad_id=proceso.proyecto_id,
        accion="GPFI_F_134_CONSOLIDADO_GENERADO",
        actor_usuario_id=lider.id,
        referencia_id=proceso.referencia_id,
        detalle={
            "file_name": "GPFI-F-134V05-planeacion-consolidada.xlsx",
            "planeaciones_incluidas": 1,
            "filas_generadas": 2,
        },
        fecha_evento=datetime(2026, 9, 23, 11, 0, tzinfo=UTC),
    )
    ev_excel.actor = lider
    db.eventos.append(ev_excel)

    # Sort events in descending order like in real DB query
    db.eventos.sort(key=lambda e: e.fecha_evento, reverse=True)

    service = ProcesoHistorialService(db, scope_service=scope_mock)  # type: ignore
    historial = await service.obtener_historial(actor=lider, referencia_id=proceso.referencia_id)

    # Validate that planning events are present and categorized as PLANEACION
    planning_events = [c for c in historial.cambios if c.tipo_evento == "PLANEACION"]
    assert len(planning_events) == 3

    excel_event = next(c for c in planning_events if c.accion == "GPFI_F_134_CONSOLIDADO_GENERADO")
    assert "Formato consolidado GPFI-F-134 V05 generado" in excel_event.descripcion
    assert excel_event.actor is not None
    assert excel_event.actor.id == lider.id

    complete_event = next(c for c in planning_events if c.accion == "PLANEACION_COMPLETADA")
    assert "Planeación pedagógica validada y cerrada" in complete_event.descripcion
    assert "Construir prototipo de arquitectura microservicios" in complete_event.descripcion
    assert complete_event.actor is not None
    assert lider.nombre in complete_event.actor.nombre

    draft_event = next(c for c in planning_events if c.accion == "PLANEACION_CREADA")
    assert "Borrador de planeación pedagógica creado" in draft_event.descripcion
    assert "Construir prototipo de arquitectura microservicios" in draft_event.descripcion
    assert draft_event.actor is not None

