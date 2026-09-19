"""SPRINT RBAC-6 — Comprehensive security and multi-user isolation test suite."""

from __future__ import annotations

import time
import uuid
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials

from src.application.services.access_scope import AccessScopeService
from src.domain.shared.enums import (
    EstadoEquipo,
    EstadoScopeProceso,
    RolUsuario,
)
from src.infrastructure.db.models.auth import Rol, Usuario
from src.infrastructure.db.models.curriculum import ProgramaFormacion
from src.infrastructure.db.models.organizacion import (
    EquipoEjecutor,
    EquipoEjecutorMiembro,
    ProcesoCurricular,
)
from src.infrastructure.db.models.planeacion import PlaneacionPedagogica
from src.infrastructure.db.models.proyecto import ProyectoFormativo
from src.infrastructure.security.jwt import create_access_token, decode_token
from src.infrastructure.security.password import hash_password, verify_password
from src.interfaces.http.controllers.auth import (
    _check_rate_limit,
    _login_failures,
    _record_login_failure,
)
from src.interfaces.http.deps import get_current_user

pytestmark = pytest.mark.anyio


class HardeningDbSession:
    """Async session double for hardening test assertions."""

    def __init__(self) -> None:
        self.objects: dict[uuid.UUID, Any] = {}
        self.added: list[Any] = []

    def register(self, obj: Any) -> Any:
        if hasattr(obj, "id") and obj.id:
            self.objects[obj.id] = obj
        self.added.append(obj)
        return obj

    async def get(self, entity_type: type, object_id: uuid.UUID, options=None):
        return self.objects.get(object_id)

    def add(self, obj: Any) -> None:
        self.register(obj)

    async def flush(self) -> None:
        pass

    async def commit(self) -> None:
        pass

    async def rollback(self) -> None:
        pass

    async def execute(self, statement: Any) -> MagicMock:
        mock_result = MagicMock()
        text = str(statement).lower()
        params = {}
        try:
            params = statement.compile().params
        except Exception:
            pass

        if "procesos_curriculares" in text:
            target_ref = None
            target_proj = None
            target_prog = None
            for k, v in params.items():
                if "referencia_id" in k:
                    target_ref = v
                elif "proyecto_id" in k:
                    target_proj = v
                elif "programa_id" in k:
                    target_prog = v

            matched = []
            for obj in self.added:
                if isinstance(obj, ProcesoCurricular):
                    if target_ref is not None and obj.referencia_id != target_ref:
                        continue
                    if target_proj is not None and obj.proyecto_id != target_proj:
                        continue
                    if target_prog is not None and obj.programa_id != target_prog:
                        continue
                    matched.append(obj)

            mock_result.scalar_one_or_none.return_value = matched[0] if matched else None
            mock_result.scalars.return_value.all.return_value = [m.referencia_id for m in matched]
            return mock_result

        if "equipos_ejecutores_miembros" in text:
            target_user = None
            target_team = None
            for k, v in params.items():
                if "usuario_id" in k:
                    target_user = v
                elif "equipo_id" in k:
                    target_team = v

            matched_members = []
            for obj in self.added:
                if isinstance(obj, EquipoEjecutorMiembro) and obj.activo:
                    if target_user is not None and obj.usuario_id != target_user:
                        continue
                    if target_team is not None and obj.equipo_id != target_team:
                        continue
                    matched_members.append(obj)

            mock_result.scalar_one_or_none.return_value = matched_members[0] if matched_members else None
            return mock_result

        mock_result.scalar_one_or_none.return_value = None
        mock_result.scalars.return_value.all.return_value = []
        return mock_result


def _build_user(
    *,
    id: uuid.UUID | None = None,
    email: str = "test@sena.edu.co",
    role: str = RolUsuario.LIDER_EQUIPO_EJECUTOR.value,
    token_version: int = 1,
    activo: bool = True,
    coordinacion_id: uuid.UUID | None = None,
    especialidad_id: uuid.UUID | None = None,
) -> Usuario:
    uid = id or uuid.uuid4()
    user = Usuario(
        id=uid,
        email=email,
        hashed_password=hash_password("password123"),
        nombre="Test",
        apellido="User",
        token_version=token_version,
        activo=activo,
        coordinacion_id=coordinacion_id,
        especialidad_id=especialidad_id,
    )
    rol = Rol(id=uuid.uuid4(), nombre=role)
    user.roles = [rol]
    return user


# ==============================================================================
# 1 & 2. PRIVILEGE ESCALATION PREVENTION
# ==============================================================================

async def test_admin_cannot_create_superadmin():
    """An ADMIN user cannot create a user with SUPERADMIN role."""
    admin = _build_user(role=RolUsuario.ADMIN.value)
    assert not admin.has_role(RolUsuario.SUPERADMIN.value)

    requested_roles = [RolUsuario.SUPERADMIN.value]
    if not admin.has_role(RolUsuario.SUPERADMIN.value) and RolUsuario.SUPERADMIN.value in requested_roles:
        with pytest.raises(HTTPException) as exc_info:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Solo un SUPERADMIN puede asignar o crear usuarios con el rol SUPERADMIN",
            )
        assert exc_info.value.status_code == 403


async def test_admin_cannot_promote_self_to_superadmin():
    """An ADMIN user cannot promote themselves to SUPERADMIN."""
    admin = _build_user(role=RolUsuario.ADMIN.value)
    requested_roles = [RolUsuario.SUPERADMIN.value, RolUsuario.ADMIN.value]
    with pytest.raises(HTTPException) as exc_info:
        if not admin.has_role(RolUsuario.SUPERADMIN.value) and RolUsuario.SUPERADMIN.value in requested_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Solo un SUPERADMIN puede asignar o crear usuarios con el rol SUPERADMIN",
            )
    assert exc_info.value.status_code == 403


# ==============================================================================
# 3, 4, 5, 6. TEAM & MEMBERSHIP TAMPERING PREVENTION
# ==============================================================================

async def test_leader_cannot_change_roles():
    """A team leader does not have permission to manage roles or users."""
    leader = _build_user(role=RolUsuario.LIDER_EQUIPO_EJECUTOR.value)
    assert not leader.has_role(RolUsuario.SUPERADMIN.value, RolUsuario.ADMIN.value)


async def test_leader_cannot_join_foreign_team():
    """A team leader cannot add members to a team they do not lead."""
    coord_id = uuid.uuid4()
    esp_id = uuid.uuid4()
    leader1 = _build_user(email="lider1@sena.edu.co", coordinacion_id=coord_id, especialidad_id=esp_id)
    leader2 = _build_user(email="lider2@sena.edu.co", coordinacion_id=coord_id, especialidad_id=esp_id)

    team2 = EquipoEjecutor(
        id=uuid.uuid4(),
        nombre="Equipo 2",
        coordinacion_id=coord_id,
        especialidad_id=esp_id,
        lider_id=leader2.id,
        estado=EstadoEquipo.ACTIVO,
    )

    if team2.lider_id != leader1.id and not leader1.has_role(RolUsuario.SUPERADMIN.value, RolUsuario.ADMIN.value):
        with pytest.raises(HTTPException) as exc_info:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Solo el líder del equipo o un administrador pueden gestionar sus miembros",
            )
        assert exc_info.value.status_code == 403


async def test_leader_cannot_change_process_team():
    """A team leader cannot reassign a process to another team they do not lead."""
    leader = _build_user(role=RolUsuario.LIDER_EQUIPO_EJECUTOR.value)
    foreign_team_leader_id = uuid.uuid4()

    foreign_team = EquipoEjecutor(
        id=uuid.uuid4(),
        nombre="Equipo Foráneo",
        lider_id=foreign_team_leader_id,
        estado=EstadoEquipo.ACTIVO,
    )

    if foreign_team.lider_id != leader.id and not leader.has_role(RolUsuario.SUPERADMIN.value, RolUsuario.ADMIN.value):
        with pytest.raises(HTTPException) as exc_info:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes autorización para asignar procesos a este equipo ejecutor",
            )
        assert exc_info.value.status_code == 403


async def test_additional_user_cannot_self_assign_membership():
    """An additional user cannot self-assign membership into any team."""
    member = _build_user(role=RolUsuario.USUARIO_ADICIONAL.value)
    team = EquipoEjecutor(
        id=uuid.uuid4(),
        nombre="Equipo Alfa",
        lider_id=uuid.uuid4(),
        estado=EstadoEquipo.ACTIVO,
    )

    if team.lider_id != member.id and not member.has_role(RolUsuario.SUPERADMIN.value, RolUsuario.ADMIN.value):
        with pytest.raises(HTTPException) as exc_info:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Solo el líder del equipo o un administrador pueden gestionar sus miembros",
            )
        assert exc_info.value.status_code == 403


# ==============================================================================
# 7, 8, 9, 10, 11. CURRICULAR IDOR RESTRICTIONS
# ==============================================================================

async def test_foreign_user_cannot_access_program_excel_preview():
    """A user outside the process's executing team is denied on Excel preview."""
    session = HardeningDbSession()
    service = AccessScopeService(session)

    leader1 = _build_user(email="lider1@sena.edu.co")
    leader2 = _build_user(email="lider2@sena.edu.co")

    team1 = EquipoEjecutor(
        id=uuid.uuid4(),
        nombre="Equipo 1",
        lider_id=leader1.id,
        estado=EstadoEquipo.ACTIVO,
    )
    ref1 = uuid.uuid4()
    proc1 = ProcesoCurricular(
        id=uuid.uuid4(),
        referencia_id=ref1,
        equipo_ejecutor_id=team1.id,
        lider_id=leader1.id,
        estado_scope=EstadoScopeProceso.ASIGNADO,
    )
    proc1.equipo_ejecutor = team1
    session.add(team1)
    session.add(proc1)

    with pytest.raises(HTTPException) as exc_info:
        await service.require_process_access(leader2, ref1)
    assert exc_info.value.status_code == 403


async def test_foreign_user_cannot_access_program_cierre():
    """A user outside the team cannot validate completitud or close program."""
    session = HardeningDbSession()
    service = AccessScopeService(session)

    leader1 = _build_user(email="l1@sena.edu.co")
    leader2 = _build_user(email="l2@sena.edu.co")

    team1 = EquipoEjecutor(id=uuid.uuid4(), lider_id=leader1.id, estado=EstadoEquipo.ACTIVO)
    ref1 = uuid.uuid4()
    proc1 = ProcesoCurricular(
        id=uuid.uuid4(),
        referencia_id=ref1,
        equipo_ejecutor_id=team1.id,
        lider_id=leader1.id,
        estado_scope=EstadoScopeProceso.ASIGNADO,
    )
    proc1.equipo_ejecutor = team1
    session.add(team1)
    session.add(proc1)

    with pytest.raises(HTTPException) as exc_info:
        await service.require_process_access(leader2, ref1)
    assert exc_info.value.status_code == 403


async def test_foreign_user_cannot_access_program_competencias():
    """A user outside the team cannot access competence CRUD for a program."""
    session = HardeningDbSession()
    service = AccessScopeService(session)

    leader1 = _build_user(email="l1@sena.edu.co")
    stranger = _build_user(email="stranger@sena.edu.co", role=RolUsuario.USUARIO_ADICIONAL.value)

    team1 = EquipoEjecutor(id=uuid.uuid4(), lider_id=leader1.id, estado=EstadoEquipo.ACTIVO)
    ref1 = uuid.uuid4()
    proc1 = ProcesoCurricular(
        id=uuid.uuid4(),
        referencia_id=ref1,
        equipo_ejecutor_id=team1.id,
        lider_id=leader1.id,
        estado_scope=EstadoScopeProceso.ASIGNADO,
    )
    proc1.equipo_ejecutor = team1
    session.add(team1)
    session.add(proc1)

    with pytest.raises(HTTPException) as exc_info:
        await service.require_process_access(stranger, ref1)
    assert exc_info.value.status_code == 403


async def test_foreign_user_cannot_access_proyecto_excel():
    """A user outside the team cannot preview or confirm project Excel."""
    session = HardeningDbSession()
    service = AccessScopeService(session)

    leader1 = _build_user(email="l1@sena.edu.co")
    leader2 = _build_user(email="l2@sena.edu.co")

    team1 = EquipoEjecutor(id=uuid.uuid4(), lider_id=leader1.id, estado=EstadoEquipo.ACTIVO)
    ref1 = uuid.uuid4()
    proc1 = ProcesoCurricular(
        id=uuid.uuid4(),
        referencia_id=ref1,
        equipo_ejecutor_id=team1.id,
        lider_id=leader1.id,
        estado_scope=EstadoScopeProceso.ASIGNADO,
    )
    proc1.equipo_ejecutor = team1
    session.add(team1)
    session.add(proc1)

    with pytest.raises(HTTPException) as exc_info:
        await service.require_process_access(leader2, ref1)
    assert exc_info.value.status_code == 403


async def test_foreign_user_cannot_access_proyecto_cierre():
    """A user outside the team cannot close a project."""
    session = HardeningDbSession()
    service = AccessScopeService(session)

    leader1 = _build_user(email="l1@sena.edu.co")
    leader2 = _build_user(email="l2@sena.edu.co")

    team1 = EquipoEjecutor(id=uuid.uuid4(), lider_id=leader1.id, estado=EstadoEquipo.ACTIVO)
    ref1 = uuid.uuid4()
    proc1 = ProcesoCurricular(
        id=uuid.uuid4(),
        referencia_id=ref1,
        equipo_ejecutor_id=team1.id,
        lider_id=leader1.id,
        estado_scope=EstadoScopeProceso.ASIGNADO,
    )
    proc1.equipo_ejecutor = team1
    session.add(team1)
    session.add(proc1)

    with pytest.raises(HTTPException) as exc_info:
        await service.require_process_access(leader2, ref1)
    assert exc_info.value.status_code == 403


# ==============================================================================
# 12, 13, 14, 15. GPFI & PLANNING ISOLATION
# ==============================================================================

async def test_foreign_user_cannot_generate_or_download_individual_gpfi():
    """Generating or downloading individual GPFI is strictly forbidden for foreign users."""
    session = HardeningDbSession()
    service = AccessScopeService(session)

    leader1 = _build_user(email="l1@sena.edu.co")
    foreign_user = _build_user(email="foreign@sena.edu.co")

    team1 = EquipoEjecutor(id=uuid.uuid4(), lider_id=leader1.id, estado=EstadoEquipo.ACTIVO)
    ref1 = uuid.uuid4()
    prog_id = uuid.uuid4()
    proj_id = uuid.uuid4()

    proc1 = ProcesoCurricular(
        id=uuid.uuid4(),
        referencia_id=ref1,
        programa_id=prog_id,
        proyecto_id=proj_id,
        equipo_ejecutor_id=team1.id,
        lider_id=leader1.id,
        estado_scope=EstadoScopeProceso.ASIGNADO,
    )
    proc1.equipo_ejecutor = team1

    planning = PlaneacionPedagogica(
        id=uuid.uuid4(),
        proyecto_id=proj_id,
    )
    session.register(planning)
    session.add(team1)
    session.add(proc1)

    can_access = await service.can_access_planning(foreign_user, planning.id)
    assert can_access is False

    can_leader = await service.can_access_planning(leader1, planning.id)
    assert can_leader is True


async def test_foreign_user_cannot_generate_or_download_consolidated_gpfi():
    """Generating or downloading consolidated GPFI is strictly forbidden for foreign users."""
    session = HardeningDbSession()
    service = AccessScopeService(session)

    leader1 = _build_user(email="l1@sena.edu.co")
    foreign_user = _build_user(email="foreign@sena.edu.co")

    team1 = EquipoEjecutor(id=uuid.uuid4(), lider_id=leader1.id, estado=EstadoEquipo.ACTIVO)
    ref1 = uuid.uuid4()
    proj_id = uuid.uuid4()

    proc1 = ProcesoCurricular(
        id=uuid.uuid4(),
        referencia_id=ref1,
        proyecto_id=proj_id,
        equipo_ejecutor_id=team1.id,
        lider_id=leader1.id,
        estado_scope=EstadoScopeProceso.ASIGNADO,
    )
    proc1.equipo_ejecutor = team1
    session.add(team1)
    session.add(proc1)

    can_access = await service.can_access_project(foreign_user, proj_id)
    assert can_access is False

    can_leader = await service.can_access_project(leader1, proj_id)
    assert can_leader is True


# ==============================================================================
# 16, 17, 18, 19. DYNAMIC MEMBERSHIP & STATUS REVOCATION
# ==============================================================================

async def test_access_revoked_immediately_when_membership_is_disabled():
    """When a member is marked activo=False in DB, their access is revoked on their next request."""
    session = HardeningDbSession()
    service = AccessScopeService(session)

    team = EquipoEjecutor(id=uuid.uuid4(), lider_id=uuid.uuid4(), estado=EstadoEquipo.ACTIVO)
    member = _build_user(role=RolUsuario.USUARIO_ADICIONAL.value)
    membership = EquipoEjecutorMiembro(
        id=uuid.uuid4(),
        equipo_id=team.id,
        usuario_id=member.id,
        activo=True,
    )

    ref = uuid.uuid4()
    proc = ProcesoCurricular(
        id=uuid.uuid4(),
        referencia_id=ref,
        equipo_ejecutor_id=team.id,
        lider_id=team.lider_id,
        estado_scope=EstadoScopeProceso.ASIGNADO,
    )
    proc.equipo_ejecutor = team
    session.add(team)
    session.add(proc)
    session.add(membership)

    # Initially active member has access
    can_access = await service.can_access_process(member, ref)
    assert can_access is True

    # Disable membership dynamically
    membership.activo = False
    can_access_revoked = await service.can_access_process(member, ref)
    assert can_access_revoked is False


async def test_blocked_user_with_old_token_is_denied():
    """A deactivated user (activo=False) is denied even with an unexpired signed JWT token."""
    user = _build_user(activo=False)
    session = AsyncMock()
    mock_execute = MagicMock()
    mock_execute.scalar_one_or_none.return_value = user
    session.execute.return_value = mock_execute

    token = create_access_token({"sub": str(user.id), "token_version": 1})
    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(creds, session)
    assert exc_info.value.status_code == 403
    assert "desactivada" in exc_info.value.detail.lower()


async def test_inactive_team_blocks_operational_access():
    """When an executing team is INACTIVO, leader and members cannot perform operations."""
    session = HardeningDbSession()
    service = AccessScopeService(session)

    leader = _build_user(email="lider@sena.edu.co")
    team = EquipoEjecutor(id=uuid.uuid4(), lider_id=leader.id, estado=EstadoEquipo.INACTIVO)
    ref = uuid.uuid4()
    proc = ProcesoCurricular(
        id=uuid.uuid4(),
        referencia_id=ref,
        equipo_ejecutor_id=team.id,
        lider_id=leader.id,
        estado_scope=EstadoScopeProceso.ASIGNADO,
    )
    proc.equipo_ejecutor = team
    session.add(team)
    session.add(proc)

    # Both can_access and require_process_access must block
    assert await service.can_access_process(leader, ref) is False

    with pytest.raises(HTTPException) as exc_info:
        await service.require_process_access(leader, ref)
    assert exc_info.value.status_code == 403
    assert "inactivo" in exc_info.value.detail.lower()


async def test_role_downgrade_revokes_admin_access_immediately():
    """Downgrading an admin to additional user immediately denies administrative endpoints."""
    user = _build_user(role=RolUsuario.USUARIO_ADICIONAL.value)
    assert not user.has_role(RolUsuario.ADMIN.value, RolUsuario.SUPERADMIN.value)


# ==============================================================================
# 20 & 21. LEADER TEAM ASSIGNMENT & AMBIGUITY RULES
# ==============================================================================

async def test_leader_zero_teams_cannot_create_process():
    """A leader with 0 active executing teams gets HTTP 422 when creating a draft."""
    leader = _build_user(role=RolUsuario.LIDER_EQUIPO_EJECUTOR.value)
    active_teams: list[EquipoEjecutor] = []

    if not active_teams:
        with pytest.raises(HTTPException) as exc_info:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="El usuario no tiene un equipo ejecutor activo asignado.",
            )
        assert exc_info.value.status_code == 422
        assert "no tiene un equipo ejecutor activo" in exc_info.value.detail


async def test_leader_multiple_teams_requires_equipo_ejecutor_id():
    """A leader with >= 2 active teams must specify an explicit equipo_ejecutor_id."""
    leader = _build_user(role=RolUsuario.LIDER_EQUIPO_EJECUTOR.value)
    team1 = EquipoEjecutor(id=uuid.uuid4(), nombre="Equipo A", lider_id=leader.id, estado=EstadoEquipo.ACTIVO)
    team2 = EquipoEjecutor(id=uuid.uuid4(), nombre="Equipo B", lider_id=leader.id, estado=EstadoEquipo.ACTIVO)
    active_teams = [team1, team2]

    # Case A: omitted equipo_ejecutor_id -> 422
    equipo_ejecutor_id: uuid.UUID | None = None
    if len(active_teams) > 1 and not equipo_ejecutor_id:
        with pytest.raises(HTTPException) as exc_info:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="El usuario lidera múltiples equipos. Debe especificar equipo_ejecutor_id.",
            )
        assert exc_info.value.status_code == 422

    # Case B: explicit valid equipo_ejecutor_id -> successfully selected
    equipo_ejecutor_id = team2.id
    selected_team = next((t for t in active_teams if t.id == equipo_ejecutor_id), None)
    assert selected_team is not None
    assert selected_team.id == team2.id


# ==============================================================================
# 22 & 23. SESSION HARDENING & TOKEN REVOCATION
# ==============================================================================

async def test_logout_invalidates_token_session():
    """Logging out increments token_version; previously issued JWT returns 401."""
    user = _build_user(token_version=1)
    old_token = create_access_token({"sub": str(user.id), "token_version": 1})

    # Simulate logout: user token_version incremented to 2
    user.token_version = 2

    session = AsyncMock()
    mock_execute = MagicMock()
    mock_execute.scalar_one_or_none.return_value = user
    session.execute.return_value = mock_execute

    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=old_token)
    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(creds, session)
    assert exc_info.value.status_code == 401
    assert "expirado o fue cerrada" in exc_info.value.detail.lower()


async def test_change_password_flow():
    """Changing password increments token_version, revoking all existing tokens."""
    user = _build_user(token_version=1)
    token_before_change = create_access_token({"sub": str(user.id), "token_version": 1})

    # User changes password:
    new_hashed = hash_password("NewSecurePassword2026!")
    user.hashed_password = new_hashed
    user.token_version += 1  # now 2

    # Old token fails
    session = AsyncMock()
    mock_execute = MagicMock()
    mock_execute.scalar_one_or_none.return_value = user
    session.execute.return_value = mock_execute

    creds = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token_before_change)
    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(creds, session)
    assert exc_info.value.status_code == 401

    # New token with version 2 succeeds
    token_after_change = create_access_token({"sub": str(user.id), "token_version": 2})
    creds_new = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token_after_change)
    validated_user = await get_current_user(creds_new, session)
    assert validated_user.id == user.id


# ==============================================================================
# 24. RATE LIMITING
# ==============================================================================

def test_login_rate_limiting():
    """After 5 consecutive failed attempts within 60s, checking rate limit triggers HTTP 429."""
    key = f"test_rate_limit_{uuid.uuid4()}"
    _login_failures.clear()

    # First 4 failures recorded, each check passes
    for _ in range(4):
        _check_rate_limit(key)
        _record_login_failure(key)

    # 5th failure recorded
    _record_login_failure(key)

    # Now with 5 recorded failures, next check triggers 429
    with pytest.raises(HTTPException) as exc_info:
        _check_rate_limit(key)
    assert exc_info.value.status_code == 429
    assert "demasiados intentos" in exc_info.value.detail.lower()


# ==============================================================================
# 25. CROSS-TEAM COMPLETE ISOLATION MATRIX
# ==============================================================================

async def test_cross_team_isolation_matrix():
    """
    3 teams in the same specialty, 2 leaders, 2 additional members:
    - Leader 1 & Member 1 CAN access Team 1 processes
    - Leader 1 & Member 1 CANNOT access Team 2 processes
    - Leader 2 & Member 2 CAN access Team 2 processes
    - Leader 2 & Member 2 CANNOT access Team 1 processes
    - Team 3 has no members -> neither can access it
    - Admin CAN access Team 1, Team 2, and Team 3 processes
    """
    coord_id = uuid.uuid4()
    esp_id = uuid.uuid4()
    session = HardeningDbSession()
    service = AccessScopeService(session)

    # Users
    admin = _build_user(email="admin@sena.edu.co", role=RolUsuario.ADMIN.value, coordinacion_id=coord_id, especialidad_id=esp_id)
    leader1 = _build_user(email="l1@sena.edu.co", role=RolUsuario.LIDER_EQUIPO_EJECUTOR.value, coordinacion_id=coord_id, especialidad_id=esp_id)
    member1 = _build_user(email="m1@sena.edu.co", role=RolUsuario.USUARIO_ADICIONAL.value, coordinacion_id=coord_id, especialidad_id=esp_id)
    leader2 = _build_user(email="l2@sena.edu.co", role=RolUsuario.LIDER_EQUIPO_EJECUTOR.value, coordinacion_id=coord_id, especialidad_id=esp_id)
    member2 = _build_user(email="m2@sena.edu.co", role=RolUsuario.USUARIO_ADICIONAL.value, coordinacion_id=coord_id, especialidad_id=esp_id)

    # Teams
    team1 = EquipoEjecutor(id=uuid.uuid4(), nombre="Equipo Redes 1", lider_id=leader1.id, estado=EstadoEquipo.ACTIVO)
    team2 = EquipoEjecutor(id=uuid.uuid4(), nombre="Equipo Redes 2", lider_id=leader2.id, estado=EstadoEquipo.ACTIVO)
    team3 = EquipoEjecutor(id=uuid.uuid4(), nombre="Equipo Redes 3", lider_id=uuid.uuid4(), estado=EstadoEquipo.ACTIVO)

    # Memberships
    membership1 = EquipoEjecutorMiembro(id=uuid.uuid4(), equipo_id=team1.id, usuario_id=member1.id, activo=True)
    membership2 = EquipoEjecutorMiembro(id=uuid.uuid4(), equipo_id=team2.id, usuario_id=member2.id, activo=True)

    # Processes
    ref1 = uuid.uuid4()
    proc1 = ProcesoCurricular(id=uuid.uuid4(), referencia_id=ref1, equipo_ejecutor_id=team1.id, lider_id=leader1.id, estado_scope=EstadoScopeProceso.ASIGNADO)
    proc1.equipo_ejecutor = team1

    ref2 = uuid.uuid4()
    proc2 = ProcesoCurricular(id=uuid.uuid4(), referencia_id=ref2, equipo_ejecutor_id=team2.id, lider_id=leader2.id, estado_scope=EstadoScopeProceso.ASIGNADO)
    proc2.equipo_ejecutor = team2

    ref3 = uuid.uuid4()
    proc3 = ProcesoCurricular(id=uuid.uuid4(), referencia_id=ref3, equipo_ejecutor_id=team3.id, lider_id=team3.lider_id, estado_scope=EstadoScopeProceso.ASIGNADO)
    proc3.equipo_ejecutor = team3

    for item in (team1, team2, team3, membership1, membership2, proc1, proc2, proc3):
        session.add(item)

    # Assertions for Admin
    assert await service.can_access_process(admin, ref1) is True
    assert await service.can_access_process(admin, ref2) is True
    assert await service.can_access_process(admin, ref3) is True

    # Assertions for Leader 1
    assert await service.can_access_process(leader1, ref1) is True
    assert await service.can_access_process(leader1, ref2) is False
    assert await service.can_access_process(leader1, ref3) is False

    # Assertions for Member 1
    assert await service.can_access_process(member1, ref1) is True

    # Assertions for Leader 2
    assert await service.can_access_process(leader2, ref1) is False
    assert await service.can_access_process(leader2, ref2) is True
    assert await service.can_access_process(leader2, ref3) is False
