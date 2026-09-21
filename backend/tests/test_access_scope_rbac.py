"""Comprehensive test suite for RBAC, executing teams, and data isolation."""

from __future__ import annotations

import uuid
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.application.services.access_scope import AccessScopeService
from src.application.services.dashboard import (
    DashboardAccessForbiddenError,
    DashboardService,
)
from src.domain.drafts.types import TipoBloqueBorrador
from src.domain.shared.enums import (
    EstadoBloque,
    EstadoEquipo,
    EstadoScopeProceso,
    RolUsuario,
    TipoNecesidadProceso,
)
from src.infrastructure.db.models.auth import Rol, Usuario
from src.infrastructure.db.models.curriculum import ProgramaFormacion
from src.infrastructure.db.models.drafts import BorradorSesion
from src.infrastructure.db.models.organizacion import (
    Coordinacion,
    EquipoEjecutor,
    EquipoEjecutorMiembro,
    Especialidad,
    ProcesoCurricular,
)
from src.infrastructure.db.models.planeacion import PlaneacionPedagogica

from src.infrastructure.security.jwt import create_access_token, decode_token
from src.infrastructure.security.password import hash_password, verify_password

pytestmark = pytest.mark.anyio


class FakeDbSession:
    """In-memory async session test double for access scope queries."""

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

    async def execute(self, statement: Any) -> MagicMock:
        return self._mock_result_for(statement)

    def _mock_result_for(self, statement: Any) -> MagicMock:
        mock_result = MagicMock()
        text_query = str(statement).lower()

        if "procesos_curriculares" in text_query and "where" in text_query:
            found = [o for o in self.added if isinstance(o, ProcesoCurricular)]
            mock_result.scalar_one_or_none.return_value = found[0] if found else None
            mock_result.scalars.return_value.all.return_value = [f.referencia_id for f in found]
            return mock_result

        if "equipos_ejecutores_miembros" in text_query:
            active_members = [
                m for m in self.added
                if isinstance(m, EquipoEjecutorMiembro) and m.activo
            ]
            mock_result.scalar_one_or_none.return_value = active_members[0] if active_members else None
            return mock_result

        mock_result.scalar_one_or_none.return_value = None
        mock_result.scalars.return_value.all.return_value = []
        return mock_result


def _create_user(
    *,
    id: uuid.UUID,
    email: str,
    role_name: str,
    coordinacion_id: uuid.UUID | None = None,
    especialidad_id: uuid.UUID | None = None,
    activo: bool = True,
) -> Usuario:
    user = Usuario(
        id=id,
        email=email,
        hashed_password=hash_password("password123"),
        nombre="Test",
        apellido=email.split("@")[0],
        coordinacion_id=coordinacion_id,
        especialidad_id=especialidad_id,
        activo=activo,
    )
    rol = Rol(id=uuid.uuid4(), nombre=role_name)
    user.roles = [rol]
    return user


def test_password_hashing():
    pw = "SuperSecret_2026!"
    hashed = hash_password(pw)
    assert hashed != pw
    assert verify_password(pw, hashed) is True
    assert verify_password("wrong", hashed) is False


def test_jwt_token_flow():
    user_id = uuid.uuid4()
    payload = {"sub": str(user_id), "email": "test@sena.edu.co", "roles": ["ADMIN"]}
    token = create_access_token(payload)
    decoded = decode_token(token)
    assert decoded["sub"] == str(user_id)
    assert decoded["email"] == "test@sena.edu.co"
    assert decoded["roles"] == ["ADMIN"]


async def test_two_leaders_same_specialty_are_isolated():
    """MANDATORY: Two leaders in Teleinformática -> Redes MUST NOT see each other's processes."""
    coord_id = uuid.uuid4()
    esp_id = uuid.uuid4()

    leader1_id = uuid.uuid4()
    leader1 = _create_user(
        id=leader1_id,
        email="lider1@sena.edu.co",
        role_name=RolUsuario.LIDER_EQUIPO_EJECUTOR.value,
        coordinacion_id=coord_id,
        especialidad_id=esp_id,
    )

    leader2_id = uuid.uuid4()
    leader2 = _create_user(
        id=leader2_id,
        email="lider2@sena.edu.co",
        role_name=RolUsuario.LIDER_EQUIPO_EJECUTOR.value,
        coordinacion_id=coord_id,
        especialidad_id=esp_id,
    )

    team1_id = uuid.uuid4()
    team1 = EquipoEjecutor(
        id=team1_id,
        nombre="Equipo Redes 01",
        coordinacion_id=coord_id,
        especialidad_id=esp_id,
        lider_id=leader1_id,
        estado=EstadoEquipo.ACTIVO,
    )
    team1.lider = leader1

    team2_id = uuid.uuid4()
    team2 = EquipoEjecutor(
        id=team2_id,
        nombre="Equipo Redes 02",
        coordinacion_id=coord_id,
        especialidad_id=esp_id,
        lider_id=leader2_id,
        estado=EstadoEquipo.ACTIVO,
    )
    team2.lider = leader2

    ref1 = uuid.uuid4()
    proceso1 = ProcesoCurricular(
        id=uuid.uuid4(),
        referencia_id=ref1,
        coordinacion_id=coord_id,
        especialidad_id=esp_id,
        equipo_ejecutor_id=team1_id,
        lider_id=leader1_id,
        estado_scope=EstadoScopeProceso.ASIGNADO,
        tipo_necesidad=TipoNecesidadProceso.CREAR_PLANEACION,
    )
    proceso1.equipo_ejecutor = team1

    ref2 = uuid.uuid4()
    proceso2 = ProcesoCurricular(
        id=uuid.uuid4(),
        referencia_id=ref2,
        coordinacion_id=coord_id,
        especialidad_id=esp_id,
        equipo_ejecutor_id=team2_id,
        lider_id=leader2_id,
        estado_scope=EstadoScopeProceso.ASIGNADO,
        tipo_necesidad=TipoNecesidadProceso.CREAR_PLANEACION,
    )
    proceso2.equipo_ejecutor = team2

    # Test with custom session double
    session = AsyncMock()

    # When querying proceso1:
    res1 = MagicMock()
    res1.scalar_one_or_none.return_value = proceso1
    # When querying proceso2:
    res2 = MagicMock()
    res2.scalar_one_or_none.return_value = proceso2

    service = AccessScopeService(session)

    # Leader 1 checking Process 1 -> Allowed
    session.execute.return_value = res1
    assert await service.can_access_process(leader1, ref1) is True

    # Leader 1 checking Process 2 -> Forbidden!
    session.execute.return_value = res2
    assert await service.can_access_process(leader1, ref2) is False

    # Leader 2 checking Process 2 -> Allowed
    session.execute.return_value = res2
    assert await service.can_access_process(leader2, ref2) is True

    # Leader 2 checking Process 1 -> Forbidden!
    session.execute.return_value = res1
    assert await service.can_access_process(leader2, ref1) is False


async def test_additional_user_access_limited_to_active_membership():
    """Usuario adicional only has access when active membership exists."""
    team_id = uuid.uuid4()
    ua_id = uuid.uuid4()
    ua_user = _create_user(
        id=ua_id,
        email="apoyo@sena.edu.co",
        role_name=RolUsuario.USUARIO_ADICIONAL.value,
    )

    team = EquipoEjecutor(
        id=team_id,
        nombre="Equipo ADSO",
        coordinacion_id=uuid.uuid4(),
        especialidad_id=uuid.uuid4(),
        lider_id=uuid.uuid4(),
        estado=EstadoEquipo.ACTIVO,
    )

    ref = uuid.uuid4()
    proceso = ProcesoCurricular(
        id=uuid.uuid4(),
        referencia_id=ref,
        equipo_ejecutor_id=team_id,
        lider_id=team.lider_id,
        estado_scope=EstadoScopeProceso.ASIGNADO,
    )
    proceso.equipo_ejecutor = team

    session = AsyncMock()
    service = AccessScopeService(session)

    # 1. Proceso query returns proceso
    proceso_res = MagicMock()
    proceso_res.scalar_one_or_none.return_value = proceso

    # 2. Membership query returns active member
    active_membership = EquipoEjecutorMiembro(
        id=uuid.uuid4(),
        equipo_id=team_id,
        usuario_id=ua_id,
        activo=True,
    )
    member_res_active = MagicMock()
    member_res_active.scalar_one_or_none.return_value = active_membership

    session.execute.side_effect = [proceso_res, member_res_active]
    can_access = await service.can_access_process(ua_user, ref)
    assert can_access is True

    # 3. Inactive membership -> Access revoked immediately
    member_res_inactive = MagicMock()
    member_res_inactive.scalar_one_or_none.return_value = None  # query checks activo=True

    session.execute.side_effect = [proceso_res, member_res_inactive]
    can_access_revoked = await service.can_access_process(ua_user, ref)
    assert can_access_revoked is False


async def test_unassigned_process_only_visible_to_admins():
    """Procesos in SIN_ASIGNAR cannot be accessed by leaders or additional users."""
    ref = uuid.uuid4()
    unassigned = ProcesoCurricular(
        id=uuid.uuid4(),
        referencia_id=ref,
        estado_scope=EstadoScopeProceso.SIN_ASIGNAR,
    )

    leader = _create_user(
        id=uuid.uuid4(),
        email="lider@sena.edu.co",
        role_name=RolUsuario.LIDER_EQUIPO_EJECUTOR.value,
    )
    admin = _create_user(
        id=uuid.uuid4(),
        email="admin@sena.edu.co",
        role_name=RolUsuario.ADMIN.value,
    )
    superadmin = _create_user(
        id=uuid.uuid4(),
        email="superadmin@sena.edu.co",
        role_name=RolUsuario.SUPERADMIN.value,
    )

    session = AsyncMock()
    service = AccessScopeService(session)

    proc_res = MagicMock()
    proc_res.scalar_one_or_none.return_value = unassigned
    session.execute.return_value = proc_res

    # Admin and Superadmin have global visibility
    assert await service.can_access_process(admin, ref) is True
    assert await service.can_access_process(superadmin, ref) is True

    # Leader is blocked from unassigned processes
    assert await service.can_access_process(leader, ref) is False


async def test_dashboard_service_with_scoping():
    """DashboardService applies scoping to listing and access checks."""
    ref1 = uuid.uuid4()
    ref2 = uuid.uuid4()

    draft1 = BorradorSesion(
        tipo_bloque=TipoBloqueBorrador.PROGRAMA.value,
        referencia_id=ref1,
        paso_actual="revision-programa",
        payload_json={},
        estado_borrador=EstadoBloque.BORRADOR,
    )
    draft1.id = uuid.uuid4()

    draft2 = BorradorSesion(
        tipo_bloque=TipoBloqueBorrador.PROGRAMA.value,
        referencia_id=ref2,
        paso_actual="revision-programa",
        payload_json={},
        estado_borrador=EstadoBloque.BORRADOR,
    )
    draft2.id = uuid.uuid4()

    leader1 = _create_user(
        id=uuid.uuid4(),
        email="lider1@sena.edu.co",
        role_name=RolUsuario.LIDER_EQUIPO_EJECUTOR.value,
    )

    session = AsyncMock()
    service = DashboardService(session)

    # Mock list query returning both drafts
    drafts_res = MagicMock()
    drafts_res.scalars.return_value.all.return_value = [draft1, draft2]

    # Mock scope query for allowed references returning only ref1
    allowed_res = MagicMock()
    allowed_res.scalars.return_value.all.return_value = [ref1]

    session.execute.side_effect = [drafts_res, allowed_res]
    session.get.return_value = None

    flows = await service.listar_flujos_programa(user=leader1)
    assert len(flows) == 1
    assert flows[0].referencia_id == ref1



async def test_planning_access_idor_protection():
    """AccessScopeService blocks access to plannings owned by another team."""
    leader_a = _create_user(
        id=uuid.uuid4(),
        email="liderA@sena.edu.co",
        role_name=RolUsuario.LIDER_EQUIPO_EJECUTOR.value,
    )
    leader_b = _create_user(
        id=uuid.uuid4(),
        email="liderB@sena.edu.co",
        role_name=RolUsuario.LIDER_EQUIPO_EJECUTOR.value,
    )

    team_a = EquipoEjecutor(
        id=uuid.uuid4(),
        nombre="Team A",
        coordinacion_id=uuid.uuid4(),
        especialidad_id=uuid.uuid4(),
        lider_id=leader_a.id,
        estado=EstadoEquipo.ACTIVO,
    )
    team_a.lider = leader_a

    proj_id = uuid.uuid4()
    plan_a = PlaneacionPedagogica(
        id=uuid.uuid4(),
        proyecto_id=proj_id,
        estado=EstadoBloque.COMPLETO,
        datos_complementarios={},
    )

    ref_a = uuid.uuid4()
    proceso_a = ProcesoCurricular(
        id=uuid.uuid4(),
        referencia_id=ref_a,
        proyecto_id=proj_id,
        equipo_ejecutor_id=team_a.id,
        lider_id=leader_a.id,
        estado_scope=EstadoScopeProceso.ASIGNADO,
    )
    proceso_a.equipo_ejecutor = team_a

    session = AsyncMock()
    service = AccessScopeService(session)

    # 1. leader_a checks planning_a -> Allowed
    session.get.return_value = plan_a
    proc_stmt_res = MagicMock()
    proc_stmt_res.scalar_one_or_none.return_value = proceso_a
    session.execute.return_value = proc_stmt_res

    assert await service.can_access_planning(leader_a, plan_a.id) is True

    # 2. leader_b checks planning_a -> Denied (403 IDOR blocked!)
    assert await service.can_access_planning(leader_b, plan_a.id) is False

