"""Tests for Sprint C: Hierarchical Administrative Dashboard (Supervisión Institucional)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any
from unittest.mock import MagicMock

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from src.application.dto.admin_dashboard import AdminDashboardFilterDTO
from src.application.services.admin_dashboard import AdminDashboardQueryService
from src.domain.shared.enums import (
    EstadoBloque,
    EstadoEquipo,
    EstadoScopeProceso,
    EstadoUsuario,
    RolUsuario,
)
from src.infrastructure.db.models.auth import Rol, Usuario
from src.infrastructure.db.models.curriculum import ProgramaFormacion
from src.infrastructure.db.models.organizacion import (
    Coordinacion,
    EquipoEjecutor,
    Especialidad,
    ProcesoCurricular,
)
from src.infrastructure.db.models.planeacion import PlaneacionPedagogica
from src.infrastructure.db.models.proyecto import ProyectoFormativo
from src.infrastructure.db.session import get_async_session
from src.interfaces.http.app import app
from src.interfaces.http.deps import get_current_user

pytestmark = pytest.mark.anyio


class AdminDashboardMockDbSession:
    """Async session double configured for administrative supervision aggregations."""

    def __init__(self) -> None:
        self.coordinaciones: list[Coordinacion] = []
        self.especialidades: list[Especialidad] = []
        self.equipos: list[EquipoEjecutor] = []
        self.usuarios: list[Usuario] = []
        self.programas: list[ProgramaFormacion] = []
        self.proyectos: list[ProyectoFormativo] = []
        self.procesos: list[ProcesoCurricular] = []
        self.planeaciones: list[PlaneacionPedagogica] = []

    async def execute(self, statement: Any) -> MagicMock:
        mock_result = MagicMock()
        text = str(statement).lower()

        # Resumen aggregations & counts
        if "count" in text:
            if "planeaciones_pedagogicas" in text:
                if "select planeaciones_pedagogicas.proyecto_id" in text:
                    rows = []
                    tally_3: dict[tuple[uuid.UUID, EstadoBloque], int] = {}
                    for p in self.planeaciones:
                        k3 = (p.proyecto_id, p.estado)
                        tally_3[k3] = tally_3.get(k3, 0) + 1
                    for (p_id, st), cnt in tally_3.items():
                        rows.append((p_id, st, cnt))
                    mock_result.all.return_value = rows
                else:
                    rows = []
                    tally_2: dict[EstadoBloque, int] = {}
                    for p in self.planeaciones:
                        tally_2[p.estado] = tally_2.get(p.estado, 0) + 1
                    for st, cnt in tally_2.items():
                        rows.append((st, cnt))
                    mock_result.all.return_value = rows
                mock_result.scalar_one.return_value = len(self.planeaciones)
                mock_result.scalar_one_or_none.return_value = len(self.planeaciones)
                return mock_result

            if "procesos_curriculares" in text:
                mock_result.scalar_one.return_value = len(self.procesos)
                mock_result.scalar_one_or_none.return_value = len(self.procesos)
                return mock_result
            if "coordinacion" in text:
                mock_result.scalar_one.return_value = len(self.coordinaciones)
                mock_result.scalar_one_or_none.return_value = len(self.coordinaciones)
                return mock_result
            if "especialidad" in text:
                mock_result.scalar_one.return_value = len(self.especialidades)
                mock_result.scalar_one_or_none.return_value = len(self.especialidades)
                return mock_result
            if "equipo_ejecutor" in text or "equipos_ejecutores" in text:
                rows = []
                tally_eq: dict[Any, int] = {}
                for e in self.equipos:
                    tally_eq[e.estado] = tally_eq.get(e.estado, 0) + 1
                for st, cnt in tally_eq.items():
                    rows.append((st, cnt))
                mock_result.all.return_value = rows
                mock_result.scalar_one.return_value = len(self.equipos)
                mock_result.scalar_one_or_none.return_value = len(self.equipos)
                return mock_result
            if "programas_formacion" in text:
                rows = []
                tally_prog: dict[Any, int] = {}
                for pr in self.programas:
                    tally_prog[pr.estado] = tally_prog.get(pr.estado, 0) + 1
                for st, cnt in tally_prog.items():
                    rows.append((st, cnt))
                mock_result.all.return_value = rows
                mock_result.scalar_one.return_value = len(self.programas)
                mock_result.scalar_one_or_none.return_value = len(self.programas)
                return mock_result
            if "proyectos_formativos" in text:
                rows = []
                tally_proy: dict[Any, int] = {}
                for py in self.proyectos:
                    tally_proy[py.estado] = tally_proy.get(py.estado, 0) + 1
                for st, cnt in tally_proy.items():
                    rows.append((st, cnt))
                mock_result.all.return_value = rows
                mock_result.scalar_one.return_value = len(self.proyectos)
                mock_result.scalar_one_or_none.return_value = len(self.proyectos)
                return mock_result

        # Process IDs query for resumen
        if "from procesos_curriculares" in text and "id, procesos_curriculares.estado_scope" in text:
            rows = []
            for p in self.procesos:
                rows.append((p.id, p.estado_scope, p.programa_id, p.proyecto_id))
            mock_result.all.return_value = rows
            return mock_result

        # Paginated processes query
        if "from procesos_curriculares" in text:
            mock_result.scalars.return_value.all.return_value = self.procesos
            row_single = self.procesos[0] if self.procesos else None
            mock_result.scalar_one_or_none.return_value = row_single
            return mock_result

        # Generic fallback
        mock_result.scalar_one.return_value = 0
        mock_result.scalar_one_or_none.return_value = 0
        mock_result.scalars.return_value.all.return_value = []
        mock_result.all.return_value = []
        return mock_result


def make_test_user(rol: RolUsuario, email: str = "user@test.com") -> Usuario:
    u = Usuario(
        id=uuid.uuid4(),
        email=email,
        hashed_password="hash",
        nombre="Test",
        apellido="User",
        estado=EstadoUsuario.ACTIVO,
        debe_cambiar_password=False,
    )
    r = Rol(id=uuid.uuid4(), nombre=rol.value)
    u.roles = [r]
    return u


def setup_mock_db() -> tuple[AdminDashboardMockDbSession, ProcesoCurricular]:
    db = AdminDashboardMockDbSession()
    coord = Coordinacion(id=uuid.uuid4(), codigo="COORD-TIC", nombre="Coordinación TIC", activo=True)
    db.coordinaciones.append(coord)

    esp = Especialidad(id=uuid.uuid4(), coordinacion_id=coord.id, codigo="ESP-SOFT", nombre="Software", activo=True)
    esp.coordinacion = coord
    db.especialidades.append(esp)

    lider = make_test_user(RolUsuario.LIDER_EQUIPO_EJECUTOR, "lider@sena.edu.co")
    db.usuarios.append(lider)

    equipo = EquipoEjecutor(
        id=uuid.uuid4(),
        coordinacion_id=coord.id,
        especialidad_id=esp.id,
        lider_id=lider.id,
        nombre="ADSO Nocturno",
        estado=EstadoEquipo.ACTIVO,
    )
    equipo.coordinacion = coord
    equipo.especialidad = esp
    equipo.lider = lider
    db.equipos.append(equipo)

    prog = ProgramaFormacion(
        id=uuid.uuid4(),
        codigo_programa="228106",
        version_programa="v1",
        nombre_programa="ADSO",
        estado=EstadoBloque.COMPLETO,
    )
    db.programas.append(prog)

    proy = ProyectoFormativo(
        id=uuid.uuid4(),
        programa_id=prog.id,
        codigo_proyecto="PROY-2026-001",
        nombre_proyecto="Sistema ASGARD",
        version_proyecto="1",
        estado=EstadoBloque.COMPLETO,
    )
    db.proyectos.append(proy)

    proceso = ProcesoCurricular(
        id=uuid.uuid4(),
        referencia_id=uuid.uuid4(),
        coordinacion_id=coord.id,
        especialidad_id=esp.id,
        equipo_ejecutor_id=equipo.id,
        lider_id=lider.id,
        programa_id=prog.id,
        proyecto_id=proy.id,
        estado_scope=EstadoScopeProceso.ASIGNADO,
    )
    proceso.coordinacion = coord
    proceso.especialidad = esp
    proceso.equipo_ejecutor = equipo
    proceso.lider = lider
    proceso.programa = prog
    proceso.proyecto = proy
    db.procesos.append(proceso)

    # 2 planeaciones
    plan1 = PlaneacionPedagogica(
        id=uuid.uuid4(),
        proyecto_id=proy.id,
        actividad_id=uuid.uuid4(),
        estado=EstadoBloque.COMPLETO,
    )
    plan2 = PlaneacionPedagogica(
        id=uuid.uuid4(),
        proyecto_id=proy.id,
        actividad_id=uuid.uuid4(),
        estado=EstadoBloque.BORRADOR,
    )
    db.planeaciones.extend([plan1, plan2])

    return db, proceso


# ==============================================================================
# 1. RBAC Tests for Admin Dashboard
# ==============================================================================

def test_admin_dashboard_rbac_forbidden_for_leader():
    """Líder de equipo ejecutor must be denied access with HTTP 403."""
    db, _ = setup_mock_db()
    leader = make_test_user(RolUsuario.LIDER_EQUIPO_EJECUTOR)

    app.dependency_overrides[get_async_session] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: leader
    try:
        client = TestClient(app)
        resp = client.get("/api/v1/admin/dashboard/resumen")
        assert resp.status_code == status.HTTP_403_FORBIDDEN
        assert "Acceso denegado" in resp.json()["detail"]
    finally:
        app.dependency_overrides.clear()


def test_admin_dashboard_rbac_forbidden_for_additional_user():
    """Usuario adicional must be denied access with HTTP 403."""
    db, _ = setup_mock_db()
    user = make_test_user(RolUsuario.USUARIO_ADICIONAL)

    app.dependency_overrides[get_async_session] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: user
    try:
        client = TestClient(app)
        resp = client.get("/api/v1/admin/dashboard/procesos")
        assert resp.status_code == status.HTTP_403_FORBIDDEN
    finally:
        app.dependency_overrides.clear()


def test_admin_dashboard_rbac_allowed_for_superadmin_and_admin():
    """SUPERADMIN and ADMIN can successfully access dashboard endpoints."""
    db, proceso = setup_mock_db()

    for rol in (RolUsuario.SUPERADMIN, RolUsuario.ADMIN):
        admin_user = make_test_user(rol)
        app.dependency_overrides[get_async_session] = lambda: db
        app.dependency_overrides[get_current_user] = lambda: admin_user
        try:
            client = TestClient(app)
            resp = client.get("/api/v1/admin/dashboard/resumen")
            assert resp.status_code == status.HTTP_200_OK

            resp_list = client.get("/api/v1/admin/dashboard/procesos")
            assert resp_list.status_code == status.HTTP_200_OK
            assert len(resp_list.json()["items"]) >= 1

            resp_detail = client.get(f"/api/v1/admin/dashboard/procesos/{proceso.referencia_id}")
            assert resp_detail.status_code == status.HTTP_200_OK
            assert resp_detail.json()["referencia_id"] == str(proceso.referencia_id)
        finally:
            app.dependency_overrides.clear()


# ==============================================================================
# 2. Service Unit Tests for Aggregations and Filtering
# ==============================================================================

@pytest.mark.anyio
async def test_admin_dashboard_service_resumen():
    """Service returns accurate aggregations reacting to data state."""
    db, _ = setup_mock_db()
    admin_user = make_test_user(RolUsuario.ADMIN)
    service = AdminDashboardQueryService(db)  # type: ignore

    resumen = await service.get_resumen(admin_user)
    assert resumen.procesos_totales == 1
    assert resumen.procesos_asignados == 1
    assert resumen.procesos_sin_asignar == 0
    assert resumen.programas_completo == 1
    assert resumen.proyectos_completo == 1
    assert resumen.planeaciones_totales == 2
    assert resumen.planeaciones_completo == 1
    assert resumen.planeaciones_borrador == 1


@pytest.mark.anyio
async def test_admin_dashboard_service_list_procesos():
    """Service paginates processes and binds hierarchical relations and plannings."""
    db, proceso = setup_mock_db()
    admin_user = make_test_user(RolUsuario.SUPERADMIN)
    service = AdminDashboardQueryService(db)  # type: ignore

    filters = AdminDashboardFilterDTO(page=1, page_size=10) if hasattr(AdminDashboardFilterDTO, "page") else AdminDashboardFilterDTO()
    result = await service.list_procesos_paginated(admin_user, filters, page=1, page_size=10)

    assert result.total == 1
    assert len(result.items) == 1
    item = result.items[0]
    assert item.referencia_id == str(proceso.referencia_id)
    assert item.coordinacion is not None
    assert item.coordinacion.codigo == "COORD-TIC"
    assert item.especialidad is not None
    assert item.especialidad.codigo == "ESP-SOFT"
    assert item.equipo is not None
    assert item.equipo.nombre == "ADSO Nocturno"
    assert item.lider is not None
    assert item.lider.email == "lider@sena.edu.co"
    assert item.programa is not None
    assert item.programa.codigo == "228106"
    assert item.proyecto is not None
    assert item.proyecto.codigo == "PROY-2026-001"
    # Plannings count: 1 COMPLETO, 1 BORRADOR
    assert item.planeaciones.completas == 1
    assert item.planeaciones.borrador == 1
    assert item.planeaciones.total == 2


@pytest.mark.anyio
async def test_admin_dashboard_service_detail():
    """Service returns detailed view for a single process by referencia_id."""
    db, proceso = setup_mock_db()
    admin_user = make_test_user(RolUsuario.ADMIN)
    service = AdminDashboardQueryService(db)  # type: ignore

    detail = await service.get_proceso_detail(admin_user, proceso.referencia_id)
    assert detail is not None
    assert detail.referencia_id == str(proceso.referencia_id)
    assert detail.planeaciones.total == 2

    # Non-existent ID returns None
    missing = await service.get_proceso_detail(admin_user, uuid.uuid4())
    assert missing is None


def test_admin_dashboard_proceso_detail_404_when_not_found():
    """HTTP 404 is returned when referencing an unknown proceso."""
    db, _ = setup_mock_db()
    admin_user = make_test_user(RolUsuario.ADMIN)
    app.dependency_overrides[get_async_session] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: admin_user

    # Mock empty result on db
    db.procesos.clear()
    try:
        client = TestClient(app)
        resp = client.get(f"/api/v1/admin/dashboard/procesos/{uuid.uuid4()}")
        assert resp.status_code == status.HTTP_404_NOT_FOUND
    finally:
        app.dependency_overrides.clear()
