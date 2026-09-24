"""Complete 11-case test matrix for Executor Team authorization invariants."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from src.application.services.access_scope import AccessScopeService
from src.domain.shared.enums import EstadoEquipo, EstadoScopeProceso, RolUsuario
from src.infrastructure.db.models.auth import Rol, Usuario
from src.infrastructure.db.models.curriculum import ProgramaFormacion
from src.infrastructure.db.models.organizacion import (
    EquipoEjecutor,
    EquipoEjecutorMiembro,
    EquipoEjecutorPrograma,
    ProcesoCurricular,
)

pytestmark = pytest.mark.anyio


def _make_user(role_name: str, email: str = "user@sena.edu.co") -> Usuario:
    user = Usuario(
        id=uuid.uuid4(),
        email=email,
        hashed_password="hash",
        nombre="Test",
        apellido="User",
        activo=True,
    )
    rol = Rol(id=uuid.uuid4(), nombre=role_name)
    user.roles = [rol]
    return user


def _make_team(
    lider_id: uuid.UUID,
    estado: EstadoEquipo = EstadoEquipo.ACTIVO,
    members: list[EquipoEjecutorMiembro] | None = None,
    programas: list[EquipoEjecutorPrograma] | None = None,
) -> EquipoEjecutor:
    team = EquipoEjecutor(
        id=uuid.uuid4(),
        nombre="Equipo Test",
        coordinacion_id=uuid.uuid4(),
        especialidad_id=uuid.uuid4(),
        lider_id=lider_id,
        estado=estado,
    )
    team.miembros = members or []
    team.programas_autorizados = programas or []
    team.procesos = []
    return team


def _mock_session_for_team(team: EquipoEjecutor | None) -> AsyncMock:
    session = AsyncMock()
    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = team
    session.execute.return_value = mock_res
    return session


# Case 1: Usuario sin equipo -> 403 (No pertenece a ningún equipo ejecutor)
async def test_case_1_user_without_team_denied():
    user = _make_user(RolUsuario.USUARIO_ADICIONAL.value)
    team = _make_team(lider_id=uuid.uuid4())  # user is not leader, no members
    session = _mock_session_for_team(team)
    service = AccessScopeService(session)

    with pytest.raises(HTTPException) as exc_info:
        await service.require_start_curricular_process(user, team.id)
    assert exc_info.value.status_code == 403
    assert exc_info.value.detail.get("code") == "EXECUTOR_TEAM_MEMBERSHIP_REQUIRED"


# Case 2: Usuario en equipo inactivo -> 403 (Equipo ejecutor inactivo)
async def test_case_2_user_in_inactive_team_denied():
    user = _make_user(RolUsuario.LIDER_EQUIPO_EJECUTOR.value)
    team = _make_team(lider_id=user.id, estado=EstadoEquipo.INACTIVO)
    session = _mock_session_for_team(team)
    service = AccessScopeService(session)

    with pytest.raises(HTTPException) as exc_info:
        await service.require_start_curricular_process(user, team.id)
    assert exc_info.value.status_code == 403
    assert exc_info.value.detail.get("code") == "EXECUTOR_TEAM_INACTIVE"


# Case 3: Usuario miembro inactivo en equipo activo -> 403 (Membresía inactiva)
async def test_case_3_inactive_member_in_active_team_denied():
    user = _make_user(RolUsuario.USUARIO_ADICIONAL.value)
    team_id = uuid.uuid4()
    inactive_member = EquipoEjecutorMiembro(
        id=uuid.uuid4(),
        equipo_id=team_id,
        usuario_id=user.id,
        activo=False,
    )
    team = _make_team(lider_id=uuid.uuid4(), members=[inactive_member])
    team.id = team_id
    session = _mock_session_for_team(team)
    service = AccessScopeService(session)

    with pytest.raises(HTTPException) as exc_info:
        await service.require_start_curricular_process(user, team.id)
    assert exc_info.value.status_code == 403
    assert exc_info.value.detail.get("code") == "EXECUTOR_TEAM_MEMBERSHIP_REQUIRED"


# Case 4: Usuario líder en equipo activo -> 200 (Permitido iniciar proceso)
async def test_case_4_leader_in_active_team_allowed():
    user = _make_user(RolUsuario.LIDER_EQUIPO_EJECUTOR.value)
    team = _make_team(lider_id=user.id, estado=EstadoEquipo.ACTIVO)
    session = _mock_session_for_team(team)
    service = AccessScopeService(session)

    result_team = await service.require_start_curricular_process(user, team.id)
    assert result_team.id == team.id


# Case 5: Usuario miembro activo en equipo activo -> 200 (Permitido iniciar proceso)
async def test_case_5_active_member_in_active_team_allowed():
    user = _make_user(RolUsuario.USUARIO_ADICIONAL.value)
    team_id = uuid.uuid4()
    active_member = EquipoEjecutorMiembro(
        id=uuid.uuid4(),
        equipo_id=team_id,
        usuario_id=user.id,
        activo=True,
    )
    team = _make_team(lider_id=uuid.uuid4(), members=[active_member])
    team.id = team_id
    session = _mock_session_for_team(team)
    service = AccessScopeService(session)

    result_team = await service.require_start_curricular_process(user, team.id)
    assert result_team.id == team.id


# Case 6: Admin SIN asignación de equipo -> 403 (ADMIN != autorización curricular)
async def test_case_6_admin_without_team_denied():
    admin = _make_user(RolUsuario.ADMIN.value, email="admin@sena.edu.co")
    team = _make_team(lider_id=uuid.uuid4())
    session = _mock_session_for_team(team)
    service = AccessScopeService(session)

    with pytest.raises(HTTPException) as exc_info:
        await service.require_start_curricular_process(admin, team.id)
    assert exc_info.value.status_code == 403
    assert exc_info.value.detail.get("code") == "EXECUTOR_TEAM_MEMBERSHIP_REQUIRED"


# Case 7: Superadmin SIN asignación de equipo -> 403 (SUPERADMIN != autorización curricular)
async def test_case_7_superadmin_without_team_denied():
    superadmin = _make_user(RolUsuario.SUPERADMIN.value, email="superadmin@sena.edu.co")
    team = _make_team(lider_id=uuid.uuid4())
    session = _mock_session_for_team(team)
    service = AccessScopeService(session)

    with pytest.raises(HTTPException) as exc_info:
        await service.require_start_curricular_process(superadmin, team.id)
    assert exc_info.value.status_code == 403
    assert exc_info.value.detail.get("code") == "EXECUTOR_TEAM_MEMBERSHIP_REQUIRED"


# Case 8: Admin COMO líder de equipo activo -> 200 (Permitido por membresía)
async def test_case_8_admin_as_team_leader_allowed():
    admin = _make_user(RolUsuario.ADMIN.value, email="admin@sena.edu.co")
    team = _make_team(lider_id=admin.id, estado=EstadoEquipo.ACTIVO)
    session = _mock_session_for_team(team)
    service = AccessScopeService(session)

    result = await service.require_start_curricular_process(admin, team.id)
    assert result.id == team.id


# Case 9: Admin COMO miembro de equipo activo -> 200 (Permitido por membresía)
async def test_case_9_admin_as_team_member_allowed():
    admin = _make_user(RolUsuario.ADMIN.value, email="admin@sena.edu.co")
    team_id = uuid.uuid4()
    active_member = EquipoEjecutorMiembro(
        id=uuid.uuid4(),
        equipo_id=team_id,
        usuario_id=admin.id,
        activo=True,
    )
    team = _make_team(lider_id=uuid.uuid4(), members=[active_member])
    team.id = team_id
    session = _mock_session_for_team(team)
    service = AccessScopeService(session)

    result = await service.require_start_curricular_process(admin, team.id)
    assert result.id == team.id


# Case 10: Usuario de Equipo A intentando operar en proceso de Equipo B -> 403 (Aislamiento)
async def test_case_10_team_isolation_cross_access_denied():
    user_a = _make_user(RolUsuario.LIDER_EQUIPO_EJECUTOR.value)
    team_b = _make_team(lider_id=uuid.uuid4())
    ref_b = uuid.uuid4()
    proceso_b = ProcesoCurricular(
        id=uuid.uuid4(),
        referencia_id=ref_b,
        equipo_ejecutor_id=team_b.id,
        lider_id=team_b.lider_id,
        estado_scope=EstadoScopeProceso.ASIGNADO,
    )
    proceso_b.equipo_ejecutor = team_b

    session = AsyncMock()
    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = proceso_b
    session.execute.return_value = mock_res
    service = AccessScopeService(session)

    with pytest.raises(HTTPException) as exc_info:
        await service.require_process_access(user_a, ref_b)
    assert exc_info.value.status_code == 403
    assert exc_info.value.detail.get("code") == "EXECUTOR_TEAM_MEMBERSHIP_REQUIRED"


# Case 11: Programa no autorizado para el equipo -> 403 (Programa no autorizado para este equipo)
async def test_case_11_unauthorized_program_for_team_denied():
    leader = _make_user(RolUsuario.LIDER_EQUIPO_EJECUTOR.value)
    authorized_prog = EquipoEjecutorPrograma(
        id=uuid.uuid4(),
        equipo_id=uuid.uuid4(),
        codigo_programa="228118",
        nombre_programa="ADSO",
        activo=True,
    )
    team = _make_team(
        lider_id=leader.id,
        estado=EstadoEquipo.ACTIVO,
        programas=[authorized_prog],
    )
    session = _mock_session_for_team(team)
    service = AccessScopeService(session)

    # Authorized program passes
    result = await service.require_start_curricular_process(
        leader,
        team.id,
        codigo_programa="228118",
    )
    assert result.id == team.id

    # Unauthorized program raises 403
    with pytest.raises(HTTPException) as exc_info:
        await service.require_start_curricular_process(
            leader,
            team.id,
            codigo_programa="999999",
        )
    assert exc_info.value.status_code == 403
    assert exc_info.value.detail.get("code") == "PROGRAM_NOT_AUTHORIZED_FOR_TEAM"
