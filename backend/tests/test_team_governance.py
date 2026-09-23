"""Tests for Team Governance, User Authorized Programs, and Program Validation."""

from __future__ import annotations

import io
import uuid
from typing import Any
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException
from openpyxl import Workbook

from src.application.services.access_scope import AccessScopeService
from src.application.services.programa_excel import (
    ProgramaExcelImportService,
    ProgramaExcelValidationError,
    extract_program_header,
)
from src.application.services.team_admin import TeamAdminService
from src.application.services.user_admin import UserAdminService
from src.domain.drafts.types import TipoBloqueBorrador
from src.domain.shared.enums import (
    EstadoBloque,
    EstadoEquipo,
    EstadoScopeProceso,
    EstadoUsuario,
    RolEquipo,
    RolUsuario,
)
from src.infrastructure.db.models.auth import Rol, Usuario, UsuarioProgramaAutorizado
from src.infrastructure.db.models.curriculum import ProgramaFormacion
from src.infrastructure.db.models.drafts import BorradorSesion
from src.infrastructure.db.models.organizacion import (
    Coordinacion,
    EquipoEjecutor,
    EquipoEjecutorMiembro,
    Especialidad,
    ProcesoCurricular,
)
from src.infrastructure.security.password import hash_password
from src.interfaces.http.schemas.auth import UserCreateRequest, UserUpdateRequest
from src.interfaces.http.schemas.organizacion import (
    EquipoEjecutorCreate,
    EquipoEjecutorUpdate,
    MiembroCreate,
    MiembroUpdate,
)

pytestmark = pytest.mark.anyio


class GovernanceMockSession:
    """Async session mock that tracks models in memory."""

    def __init__(self) -> None:
        self.objects: dict[uuid.UUID, Any] = {}
        self.added: list[Any] = []

    def add(self, obj: Any) -> None:
        if hasattr(obj, "id") and obj.id:
            self.objects[obj.id] = obj
        self.added.append(obj)
        if isinstance(obj, EquipoEjecutorMiembro) and obj.equipo_id in self.objects:
            team = self.objects[obj.equipo_id]
            if hasattr(team, "miembros") and obj not in team.miembros:
                team.miembros.append(obj)

    async def get(self, entity_type: type, object_id: uuid.UUID, options=None):
        return self.objects.get(object_id)

    async def flush(self) -> None:
        for obj in self.added:
            if hasattr(obj, "id") and not obj.id:
                obj.id = uuid.uuid4()
                self.objects[obj.id] = obj

    async def commit(self) -> None:
        await self.flush()

    async def refresh(self, obj: Any, attribute_names=None) -> None:
        pass

    async def execute(self, statement: Any) -> MagicMock:
        mock_result = MagicMock()
        text = str(statement).lower()
        params = {}
        try:
            params = statement.compile().params
        except Exception:
            pass

        # 1. Update statements
        if "update" in text:
            return mock_result

        # 2. Roles query
        if "roles" in text and "in" in text:
            role_names = []
            for v in params.values():
                if isinstance(v, (list, tuple)):
                    role_names.extend(v)
                elif isinstance(v, str):
                    role_names.append(v)
            roles = [Rol(id=uuid.uuid4(), nombre=rn) for rn in role_names]
            mock_result.scalars.return_value.all.return_value = roles
            return mock_result

        # 3. UsuarioProgramaAutorizado query
        if "usuarios_programas_autorizados" in text:
            uid = next((v for k, v in params.items() if "usuario_id" in k), None)
            pid = next((v for k, v in params.items() if "programa_id" in k), None)
            matched = [
                m for m in self.added
                if isinstance(m, UsuarioProgramaAutorizado)
                and m.activo
                and (uid is None or m.usuario_id == uid)
                and (pid is None or m.programa_id == pid)
            ]
            if "codigo_programa" in text:
                prog_map = {p.id: p.codigo_programa for p in self.added if isinstance(p, ProgramaFormacion)}
                codes = [prog_map[m.programa_id] for m in matched if m.programa_id in prog_map]
                mock_result.scalars.return_value.all.return_value = codes
                return mock_result
            mock_result.scalars.return_value.all.return_value = matched
            mock_result.scalar_one_or_none.return_value = matched[0] if matched else None
            return mock_result

        # 4. EquipoEjecutorMiembro query
        if "equipos_ejecutores_miembros" in text:
            uid = next((v for k, v in params.items() if "usuario_id" in k), None)
            eid = next((v for k, v in params.items() if "equipo_id" in k), None)
            matched_members = [
                m for m in self.added
                if isinstance(m, EquipoEjecutorMiembro)
                and m.activo
                and (uid is None or m.usuario_id == uid)
                and (eid is None or m.equipo_id == eid)
            ]
            mock_result.scalars.return_value.all.return_value = matched_members
            mock_result.scalar_one_or_none.return_value = matched_members[0] if matched_members else None
            return mock_result

        # 5. ProgramaFormacion query
        if "programas_formacion" in text:
            matched_progs = [p for p in self.added if isinstance(p, ProgramaFormacion)]
            mock_result.scalars.return_value.all.return_value = matched_progs
            mock_result.scalar_one_or_none.return_value = matched_progs[0] if matched_progs else None
            return mock_result

        # 6. ProcesoCurricular query
        if "procesos_curriculares" in text:
            matched_proc = [p for p in self.added if isinstance(p, ProcesoCurricular)]
            mock_result.scalars.return_value.all.return_value = matched_proc
            mock_result.scalar_one_or_none.return_value = matched_proc[0] if matched_proc else None
            return mock_result

        # 7. Default fallbacks
        mock_result.scalars.return_value.all.return_value = []
        mock_result.scalar_one_or_none.return_value = None
        mock_result.scalar_one.return_value = 0
        return mock_result


def _build_user(email: str, role: str, coord_id: uuid.UUID | None = None, esp_id: uuid.UUID | None = None) -> Usuario:
    u = Usuario(
        id=uuid.uuid4(),
        email=email,
        hashed_password=hash_password("Sena1234*"),
        nombre=email.split("@")[0].capitalize(),
        apellido="Tester",
        estado=EstadoUsuario.ACTIVO,
        coordinacion_id=coord_id,
        especialidad_id=esp_id,
    )
    u.roles = [Rol(id=uuid.uuid4(), nombre=role)]
    u.programas_autorizados = []
    return u


def _create_minimal_excel(codigo: str, nombre: str, version: str = "1") -> bytes:
    wb = Workbook()
    ws_prog = wb.active
    ws_prog.title = "Programa"
    ws_prog.append(["codigo_programa", "nombre_programa", "version_programa"])
    ws_prog.append([codigo, nombre, version])
    out = io.BytesIO()
    wb.save(out)
    return out.getvalue()


# ==========================================
# TESTS
# ==========================================


async def test_extract_program_header():
    """extract_program_header reads code, name, and version directly."""
    content = _create_minimal_excel("228106", "ADSO", "1")
    header = extract_program_header(content)
    assert header is not None
    assert header[0] == "228106"
    assert header[1] == "ADSO"
    assert header[2] == "1"


async def test_team_creation_requires_leader_to_have_authorized_program():
    """TeamAdminService rejects team creation if leader doesn't have the authorized program."""
    session = GovernanceMockSession()
    service = TeamAdminService(session)

    admin = _build_user("admin@sena.edu.co", RolUsuario.ADMIN.value)
    coord = Coordinacion(id=uuid.uuid4(), codigo="TIC", nombre="TIC", activo=True)
    esp = Especialidad(id=uuid.uuid4(), coordinacion_id=coord.id, codigo="ADSO", nombre="ADSO", activo=True)
    leader = _build_user("lider@sena.edu.co", RolUsuario.LIDER_EQUIPO_EJECUTOR.value, coord.id, esp.id)
    prog = ProgramaFormacion(id=uuid.uuid4(), codigo_programa="228106", nombre_programa="ADSO", version_programa="1")

    session.add(admin)
    session.add(coord)
    session.add(esp)
    session.add(leader)
    session.add(prog)

    # Leader has NO authorized programs -> Should raise 422
    payload = EquipoEjecutorCreate(
        nombre="Equipo ADSO 1",
        coordinacion_id=coord.id,
        especialidad_id=esp.id,
        lider_id=leader.id,
        programa_id=prog.id,
    )
    with pytest.raises(HTTPException) as exc:
        await service.create_team(admin, payload)
    assert exc.value.status_code == 422
    assert "USUARIO_SIN_PROGRAMA_AUTORIZADO" in exc.value.detail

    # Now authorize leader for this program
    auth_prog = UsuarioProgramaAutorizado(
        id=uuid.uuid4(),
        usuario_id=leader.id,
        programa_id=prog.id,
        activo=True,
    )
    session.add(auth_prog)

    # Now team creation must succeed
    team = await service.create_team(admin, payload)
    assert team.programa_id == prog.id
    assert team.max_members == 5
    assert team.leaders_can_manage_members is True


async def test_team_capacity_and_co_leader_management():
    """Team capacity max_members is enforced and co-leader role is supported."""
    session = GovernanceMockSession()
    service = TeamAdminService(session)

    admin = _build_user("admin@sena.edu.co", RolUsuario.ADMIN.value)
    coord = Coordinacion(id=uuid.uuid4(), codigo="TIC", nombre="TIC", activo=True)
    esp = Especialidad(id=uuid.uuid4(), coordinacion_id=coord.id, codigo="ADSO", nombre="ADSO", activo=True)
    leader = _build_user("lider@sena.edu.co", RolUsuario.LIDER_EQUIPO_EJECUTOR.value, coord.id, esp.id)
    prog = ProgramaFormacion(id=uuid.uuid4(), codigo_programa="228106", nombre_programa="ADSO", version_programa="1")
    session.add(UsuarioProgramaAutorizado(id=uuid.uuid4(), usuario_id=leader.id, programa_id=prog.id, activo=True))
    session.add(admin)
    session.add(coord)
    session.add(esp)
    session.add(leader)
    session.add(prog)

    # Create team with max_members = 2
    team_dto = await service.create_team(
        admin,
        EquipoEjecutorCreate(
            nombre="Equipo Reducido",
            coordinacion_id=coord.id,
            especialidad_id=esp.id,
            lider_id=leader.id,
            programa_id=prog.id,
            max_members=2,
            leaders_can_manage_members=True,
        ),
    )
    team_obj = session.objects[team_dto.id]

    # Team has 1 member (the leader registered as RolEquipo.LIDER)
    assert len(team_obj.miembros) == 1
    assert team_obj.miembros[0].rol_equipo == RolEquipo.LIDER

    # Add member 2 (Co-líder)
    member_user = _build_user("co-lider@sena.edu.co", RolUsuario.USUARIO_ADICIONAL.value, coord.id, esp.id)
    session.add(member_user)
    session.add(UsuarioProgramaAutorizado(id=uuid.uuid4(), usuario_id=member_user.id, programa_id=prog.id, activo=True))

    m2 = await service.add_member(
        leader,  # Leader adding member
        team_dto.id,
        MiembroCreate(usuario_id=member_user.id, rol_equipo=RolEquipo.CO_LIDER),
    )
    assert m2.rol_equipo == RolEquipo.CO_LIDER.value
    assert len(team_obj.miembros) == 2

    # Add member 3 -> Exceeds max_members (2) -> Should raise 422
    member_user_3 = _build_user("m3@sena.edu.co", RolUsuario.USUARIO_ADICIONAL.value, coord.id, esp.id)
    session.add(member_user_3)
    session.add(UsuarioProgramaAutorizado(id=uuid.uuid4(), usuario_id=member_user_3.id, programa_id=prog.id, activo=True))

    with pytest.raises(HTTPException) as exc:
        await service.add_member(
            leader,
            team_dto.id,
            MiembroCreate(usuario_id=member_user_3.id, rol_equipo=RolEquipo.INSTRUCTOR),
        )
    assert exc.value.status_code == 422
    assert "límite máximo" in exc.value.detail.lower() or "cupo" in exc.value.detail.lower()


async def test_leaders_can_manage_members_flag_enforcement():
    """When leaders_can_manage_members is False, leader cannot add members."""
    session = GovernanceMockSession()
    service = TeamAdminService(session)

    admin = _build_user("admin@sena.edu.co", RolUsuario.ADMIN.value)
    coord = Coordinacion(id=uuid.uuid4(), codigo="TIC", nombre="TIC", activo=True)
    esp = Especialidad(id=uuid.uuid4(), coordinacion_id=coord.id, codigo="ADSO", nombre="ADSO", activo=True)
    leader = _build_user("lider@sena.edu.co", RolUsuario.LIDER_EQUIPO_EJECUTOR.value, coord.id, esp.id)
    session.add(admin)
    session.add(coord)
    session.add(esp)
    session.add(leader)

    team_dto = await service.create_team(
        admin,
        EquipoEjecutorCreate(
            nombre="Equipo Gobernanza Estricta",
            coordinacion_id=coord.id,
            especialidad_id=esp.id,
            lider_id=leader.id,
            leaders_can_manage_members=False,
        ),
    )

    member_user = _build_user("m@sena.edu.co", RolUsuario.USUARIO_ADICIONAL.value, coord.id, esp.id)
    session.add(member_user)

    # Leader tries to add member -> Forbidden (403)
    with pytest.raises(HTTPException) as exc:
        await service.add_member(
            leader,
            team_dto.id,
            MiembroCreate(usuario_id=member_user.id, rol_equipo=RolEquipo.INSTRUCTOR),
        )
    assert exc.value.status_code == 403
    assert "No tiene permisos" in exc.value.detail

    # Admin CAN add member
    m = await service.add_member(
        admin,
        team_dto.id,
        MiembroCreate(usuario_id=member_user.id, rol_equipo=RolEquipo.INSTRUCTOR),
    )
    assert m.activo is True


async def test_shared_workspace_access_for_all_team_members():
    """All active team members (leader, co-leader, instructor) share the process workspace."""
    session = GovernanceMockSession()
    scope_service = AccessScopeService(session)

    coord_id = uuid.uuid4()
    esp_id = uuid.uuid4()
    leader = _build_user("lider@sena.edu.co", RolUsuario.LIDER_EQUIPO_EJECUTOR.value, coord_id, esp_id)
    co_leader = _build_user("coleader@sena.edu.co", RolUsuario.USUARIO_ADICIONAL.value, coord_id, esp_id)
    instructor = _build_user("instructor@sena.edu.co", RolUsuario.USUARIO_ADICIONAL.value, coord_id, esp_id)
    outsider = _build_user("outsider@sena.edu.co", RolUsuario.USUARIO_ADICIONAL.value, coord_id, esp_id)

    team = EquipoEjecutor(
        id=uuid.uuid4(),
        nombre="ADSO Compartido",
        coordinacion_id=coord_id,
        especialidad_id=esp_id,
        lider_id=leader.id,
        estado=EstadoEquipo.ACTIVO,
    )
    team.lider = leader

    m_co_leader = EquipoEjecutorMiembro(
        id=uuid.uuid4(),
        equipo_id=team.id,
        usuario_id=co_leader.id,
        rol_equipo=RolEquipo.CO_LIDER,
        activo=True,
    )
    m_instructor = EquipoEjecutorMiembro(
        id=uuid.uuid4(),
        equipo_id=team.id,
        usuario_id=instructor.id,
        rol_equipo=RolEquipo.INSTRUCTOR,
        activo=True,
    )
    team.miembros = [m_co_leader, m_instructor]

    ref_id = uuid.uuid4()
    proceso = ProcesoCurricular(
        id=uuid.uuid4(),
        referencia_id=ref_id,
        coordinacion_id=coord_id,
        especialidad_id=esp_id,
        equipo_ejecutor_id=team.id,
        lider_id=leader.id,
        estado_scope=EstadoScopeProceso.ASIGNADO,
    )
    proceso.equipo_ejecutor = team

    session.add(leader)
    session.add(co_leader)
    session.add(instructor)
    session.add(outsider)
    session.add(team)
    session.add(m_co_leader)
    session.add(m_instructor)
    session.add(proceso)

    # Leader has access
    assert await scope_service.can_access_process(leader, ref_id) is True
    # Co-leader has access (shared workspace)
    assert await scope_service.can_access_process(co_leader, ref_id) is True
    # Instructor has access (shared workspace)
    assert await scope_service.can_access_process(instructor, ref_id) is True
    # Outsider has NO access
    assert await scope_service.can_access_process(outsider, ref_id) is False


async def test_prevalidate_and_preview_program_excel_authorization():
    """Service rejects matrix upload with PROGRAM_NOT_AUTHORIZED when program is not authorized."""
    session = GovernanceMockSession()
    service = ProgramaExcelImportService(
        session=session,
        draft_repository=MagicMock(),
        audit_repository=MagicMock(),
        curriculum_repository=MagicMock(),
        storage_service=MagicMock(),
    )

    user = _build_user("instructor@sena.edu.co", RolUsuario.USUARIO_ADICIONAL.value)
    prog_authorized = ProgramaFormacion(id=uuid.uuid4(), codigo_programa="228106", nombre_programa="ADSO")
    prog_forbidden = ProgramaFormacion(id=uuid.uuid4(), codigo_programa="999999", nombre_programa="COCINA")

    # Authorize user for ADSO only
    session.add(UsuarioProgramaAutorizado(id=uuid.uuid4(), usuario_id=user.id, programa_id=prog_authorized.id, activo=True))
    session.add(prog_authorized)
    session.add(prog_forbidden)

    ref_id = uuid.uuid4()
    proceso = ProcesoCurricular(
        id=uuid.uuid4(),
        referencia_id=ref_id,
        estado_scope=EstadoScopeProceso.ASIGNADO,
    )
    session.add(proceso)

    # 1. Prevalidate authorized program
    content_ok = _create_minimal_excel("228106", "ADSO", "1")
    res_ok = await service.prevalidate_program_excel(
        referencia_id=ref_id,
        filename="matriz_ok.xlsx",
        content=content_ok,
        user=user,
    )
    assert res_ok["autorizado"] is True
    assert res_ok["codigo_programa"] == "228106"

    # 2. Prevalidate forbidden program
    content_forbidden = _create_minimal_excel("999999", "COCINA", "1")
    res_forbidden = await service.prevalidate_program_excel(
        referencia_id=ref_id,
        filename="matriz_forbidden.xlsx",
        content=content_forbidden,
        user=user,
    )
    assert res_forbidden["autorizado"] is False
    assert "PROGRAM_NOT_AUTHORIZED" in str(res_forbidden["mensaje"])

