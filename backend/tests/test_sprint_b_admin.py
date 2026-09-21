"""SPRINT B — Comprehensive tests for organizational administration, RBAC, scope, and integrity."""

from __future__ import annotations

import uuid
from typing import Any
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from src.application.services.access_scope import AccessScopeService
from src.application.services.organization_admin import OrganizationAdminService
from src.application.services.team_admin import TeamAdminService
from src.application.services.user_admin import UserAdminService
from src.domain.shared.enums import (
    EstadoEquipo,
    EstadoScopeProceso,
    EstadoUsuario,
    RolUsuario,
)
from src.infrastructure.db.models.auth import Rol, UserSession, Usuario
from src.infrastructure.db.models.organizacion import (
    Coordinacion,
    EquipoEjecutor,
    EquipoEjecutorMiembro,
    Especialidad,
    ProcesoCurricular,
)
from src.infrastructure.security.password import hash_password
from src.interfaces.http.deps import get_current_user
from src.interfaces.http.schemas.auth import (
    UserCreateRequest,
    UserResetPasswordRequest,
    UserStatusUpdateRequest,
    UserUpdateRequest,
)
from src.interfaces.http.schemas.organizacion import (
    CoordinacionCreate,
    CoordinacionUpdate,
    EquipoEjecutorCreate,
    EquipoEjecutorUpdate,
    EspecialidadCreate,
    EspecialidadUpdate,
    MiembroCreate,
    MiembroUpdate,
    ProcesoAsignarRequest,
)

pytestmark = pytest.mark.anyio


class AdminMockDbSession:
    """Async session double for Sprint B administrative assertions."""

    def __init__(self) -> None:
        self.objects: dict[uuid.UUID, Any] = {}
        self.added: list[Any] = []
        self.events: list[Any] = []

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
        for obj in self.added:
            if hasattr(obj, "id") and not obj.id:
                obj.id = uuid.uuid4()
                self.objects[obj.id] = obj

    async def commit(self) -> None:
        await self.flush()

    async def refresh(self, obj: Any, attribute_names=None) -> None:
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

        # 1. Update statements (must be before generic selects)
        if "update" in text:
            if "procesos_curriculares" in text:
                eq_id = next((v for k, v in params.items() if "equipo_ejecutor" in k), None)
                new_lider = next((v for k, v in params.items() if "lider_id" in k), None)
                for p in self.added:
                    if isinstance(p, ProcesoCurricular) and (eq_id is None or p.equipo_ejecutor_id == eq_id):
                        if new_lider:
                            p.lider_id = new_lider
            return mock_result

        # 2. Count active superadmins
        if "count" in text and ("superadmin" in str(statement).lower() or any("superadmin" in str(v).lower() for v in params.values())):
            count = sum(
                1
                for u in self.added
                if isinstance(u, Usuario)
                and u.has_role(RolUsuario.SUPERADMIN.value)
                and u.estado == EstadoUsuario.ACTIVO
            )
            mock_result.scalar_one.return_value = count
            return mock_result

        # 3. Unicidad de email en usuarios
        if "usuarios" in text and "email" in text and "select" in text and "count" not in text:
            email_val = None
            for k, v in params.items():
                if "email" in k:
                    email_val = v.lower()
            matched = [u for u in self.added if isinstance(u, Usuario) and u.email.lower() == email_val]
            mock_result.scalar_one_or_none.return_value = matched[0] if matched else None
            mock_result.scalars.return_value.all.return_value = matched
            return mock_result

        # 3. Roles por nombres
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

        # 4. UserSession activas para revocación
        if "user_sessions" in text and "select" in text:
            user_id = None
            for k, v in params.items():
                if "usuario_id" in k:
                    user_id = v
            matched_sess = [
                s for s in self.added
                if isinstance(s, UserSession)
                and s.usuario_id == user_id
                and s.revoked_at is None
            ]
            mock_result.scalars.return_value.all.return_value = matched_sess
            return mock_result

        # 5. Coordinaciones por código
        if "coordinaciones" in text and "codigo" in text and "count" not in text:
            code_val = None
            for k, v in params.items():
                if "codigo" in k:
                    code_val = v.upper()
            matched = [c for c in self.added if isinstance(c, Coordinacion) and c.codigo.upper() == code_val]
            mock_result.scalar_one_or_none.return_value = matched[0] if matched else None
            return mock_result

        # 6. Especialidades por código o por coordinacion_id
        if "especialidades" in text and "count" not in text:
            code_val = None
            coord_val = None
            for k, v in params.items():
                if "codigo" in k:
                    code_val = v.upper()
                if "coordinacion_id" in k:
                    coord_val = v
            matched = [
                e for e in self.added
                if isinstance(e, Especialidad)
                and (code_val is None or e.codigo.upper() == code_val)
                and (coord_val is None or e.coordinacion_id == coord_val)
            ]
            mock_result.scalar_one_or_none.return_value = matched[0] if matched else None
            mock_result.scalars.return_value.all.return_value = matched
            return mock_result

        # 7. Count queries for dependencies
        if "count" in text:
            # Especialidades activas
            if "especialidades" in text and "activo" in text:
                coord_id = next((v for k, v in params.items() if "coordinacion_id" in k), None)
                cnt = sum(1 for e in self.added if isinstance(e, Especialidad) and e.coordinacion_id == coord_id and e.activo)
                mock_result.scalar_one.return_value = cnt
                return mock_result
            # Equipos activos
            if "equipos_ejecutores" in text and "estado" in text:
                coord_id = next((v for k, v in params.items() if "coordinacion_id" in k), None)
                esp_id = next((v for k, v in params.items() if "especialidad_id" in k), None)
                cnt = sum(
                    1 for eq in self.added
                    if isinstance(eq, EquipoEjecutor)
                    and eq.estado == EstadoEquipo.ACTIVO
                    and (coord_id is None or eq.coordinacion_id == coord_id)
                    and (esp_id is None or eq.especialidad_id == esp_id)
                )
                mock_result.scalar_one.return_value = cnt
                return mock_result
            # Usuarios activos asociados
            if "usuarios" in text:
                coord_id = next((v for k, v in params.items() if "coordinacion_id" in k), None)
                esp_id = next((v for k, v in params.items() if "especialidad_id" in k), None)
                cnt = sum(
                    1 for u in self.added
                    if isinstance(u, Usuario)
                    and u.estado == EstadoUsuario.ACTIVO
                    and (coord_id is None or u.coordinacion_id == coord_id)
                    and (esp_id is None or u.especialidad_id == esp_id)
                )
                mock_result.scalar_one.return_value = cnt
                return mock_result
            # Procesos asignados a un equipo
            if "procesos_curriculares" in text:
                eq_id = next((v for k, v in params.items() if "equipo_ejecutor_id" in k), None)
                cnt = sum(1 for p in self.added if isinstance(p, ProcesoCurricular) and p.equipo_ejecutor_id == eq_id)
                mock_result.scalar_one.return_value = cnt
                return mock_result

            # General count
            mock_result.scalar_one.return_value = len(self.added)
            return mock_result

        # 8. Membresía existente
        if "equipos_ejecutores_miembros" in text:
            eq_id = next((v for k, v in params.items() if "equipo_id" in k), None)
            u_id = next((v for k, v in params.items() if "usuario_id" in k), None)
            matched = [
                m for m in self.added
                if isinstance(m, EquipoEjecutorMiembro)
                and (eq_id is None or m.equipo_id == eq_id)
                and (u_id is None or m.usuario_id == u_id)
            ]
            mock_result.scalar_one_or_none.return_value = matched[0] if matched else None
            mock_result.scalars.return_value.all.return_value = matched
            return mock_result

        # 9. Procesos curriculares por referencia_id
        if "procesos_curriculares" in text:
            ref_id = next((v for k, v in params.items() if "referencia_id" in k), None)
            matched = [p for p in self.added if isinstance(p, ProcesoCurricular) and (ref_id is None or p.referencia_id == ref_id)]
            mock_result.scalar_one_or_none.return_value = matched[0] if matched else None
            mock_result.scalars.return_value.all.return_value = matched
            return mock_result

        # 10. Update statements
        if "update" in text:
            if "procesos_curriculares" in text and "lider_id" in text:
                eq_id = next((v for k, v in params.items() if "equipo_ejecutor_id" in k), None)
                new_lider = next((v for k, v in params.items() if "lider_id" in k), None)
                for p in self.added:
                    if isinstance(p, ProcesoCurricular) and p.equipo_ejecutor_id == eq_id:
                        p.lider_id = new_lider
            return mock_result

        # Default fallback
        mock_result.scalars.return_value.all.return_value = [o for o in self.added if not isinstance(o, (UserSession, Rol))]
        mock_result.scalars.return_value.unique.return_value.all.return_value = [o for o in self.added if not isinstance(o, (UserSession, Rol))]
        mock_result.scalar_one_or_none.return_value = None
        mock_result.scalar_one.return_value = len(self.added)
        return mock_result


def _build_user(
    email: str = "user@sena.edu.co",
    role: str = RolUsuario.ADMIN.value,
    coordinacion_id: uuid.UUID | None = None,
    especialidad_id: uuid.UUID | None = None,
    estado: EstadoUsuario = EstadoUsuario.ACTIVO,
    debe_cambiar_password: bool = False,
) -> Usuario:
    u = Usuario(
        id=uuid.uuid4(),
        email=email,
        hashed_password=hash_password("password123"),
        nombre="Test",
        apellido="User",
        telefono="3001234567",
        area="Sistemas",
        coordinacion_id=coordinacion_id,
        especialidad_id=especialidad_id,
        estado=estado,
        debe_cambiar_password=debe_cambiar_password,
        token_version=1,
    )
    u.roles = [Rol(id=uuid.uuid4(), nombre=role)]
    u.equipos_liderados = []
    u.membresias = []
    return u


# ==============================================================================
# 1. TESTS USUARIO & PRIVILEGE ESCALATION
# ==============================================================================


async def test_superadmin_can_create_admin():
    session = AdminMockDbSession()
    service = UserAdminService(session)
    superadmin = _build_user("super@sena.edu.co", RolUsuario.SUPERADMIN.value)
    session.add(superadmin)

    dto = UserCreateRequest(
        email="newadmin@sena.edu.co",
        password="password123",
        password_confirmation="password123",
        nombre="Nuevo",
        apellido="Admin",
        roles=[RolUsuario.ADMIN.value],
    )
    res = await service.create_user(superadmin, dto)
    assert res.email == "newadmin@sena.edu.co"
    assert RolUsuario.ADMIN.value in res.roles
    assert res.debe_cambiar_password is True


async def test_admin_cannot_create_superadmin():
    session = AdminMockDbSession()
    service = UserAdminService(session)
    admin = _build_user("admin@sena.edu.co", RolUsuario.ADMIN.value)
    session.add(admin)

    dto = UserCreateRequest(
        email="escalated@sena.edu.co",
        password="password123",
        password_confirmation="password123",
        nombre="Attacker",
        apellido="Admin",
        roles=[RolUsuario.SUPERADMIN.value],
    )
    with pytest.raises(HTTPException) as exc:
        await service.create_user(admin, dto)
    assert exc.value.status_code == 403


async def test_admin_cannot_create_admin():
    session = AdminMockDbSession()
    service = UserAdminService(session)
    admin = _build_user("admin@sena.edu.co", RolUsuario.ADMIN.value)
    session.add(admin)

    dto = UserCreateRequest(
        email="secondadmin@sena.edu.co",
        password="password123",
        password_confirmation="password123",
        nombre="Second",
        apellido="Admin",
        roles=[RolUsuario.ADMIN.value],
    )
    with pytest.raises(HTTPException) as exc:
        await service.create_user(admin, dto)
    assert exc.value.status_code == 403


async def test_admin_can_create_leader_and_additional_user():
    session = AdminMockDbSession()
    service = UserAdminService(session)
    admin = _build_user("admin@sena.edu.co", RolUsuario.ADMIN.value)
    session.add(admin)

    coord = Coordinacion(id=uuid.uuid4(), codigo="TEL", nombre="TELEINFORMATICA", activo=True)
    esp = Especialidad(id=uuid.uuid4(), coordinacion_id=coord.id, codigo="ADSO", nombre="ADSO", activo=True)
    session.add(coord)
    session.add(esp)

    # Leader
    dto_leader = UserCreateRequest(
        email="lider@sena.edu.co",
        password="password123",
        password_confirmation="password123",
        nombre="Lider",
        apellido="Equipo",
        telefono="3101112233",
        area="Tecnologia",
        coordinacion_id=coord.id,
        especialidad_id=esp.id,
        roles=[RolUsuario.LIDER_EQUIPO_EJECUTOR.value],
    )
    res_lider = await service.create_user(admin, dto_leader)
    assert res_lider.email == "lider@sena.edu.co"
    assert res_lider.estado == "ACTIVO"
    assert res_lider.debe_cambiar_password is True

    # Additional user
    dto_apoyo = UserCreateRequest(
        email="apoyo@sena.edu.co",
        password="password123",
        password_confirmation="password123",
        nombre="Apoyo",
        apellido="Docente",
        telefono="3101112234",
        area="Tecnologia",
        coordinacion_id=coord.id,
        especialidad_id=esp.id,
        roles=[RolUsuario.USUARIO_ADICIONAL.value],
    )
    res_apoyo = await service.create_user(admin, dto_apoyo)
    assert res_apoyo.email == "apoyo@sena.edu.co"


async def test_leader_and_additional_require_coordination_and_specialty():
    session = AdminMockDbSession()
    service = UserAdminService(session)
    admin = _build_user("admin@sena.edu.co", RolUsuario.ADMIN.value)
    session.add(admin)

    # Missing coordination
    dto = UserCreateRequest(
        email="lider_err@sena.edu.co",
        password="password123",
        password_confirmation="password123",
        nombre="Lider",
        apellido="Error",
        telefono="3111234567",
        area="Sistemas",
        roles=[RolUsuario.LIDER_EQUIPO_EJECUTOR.value],
    )
    with pytest.raises(HTTPException) as exc:
        await service.create_user(admin, dto)
    assert exc.value.status_code == 422


async def test_password_confirmation_is_required():
    session = AdminMockDbSession()
    service = UserAdminService(session)
    superadmin = _build_user("super@sena.edu.co", RolUsuario.SUPERADMIN.value)
    session.add(superadmin)

    dto = UserCreateRequest(
        email="pass_err@sena.edu.co",
        password="password123",
        password_confirmation="different_pass",
        nombre="Pass",
        apellido="Mismatch",
        roles=[RolUsuario.ADMIN.value],
    )
    with pytest.raises(HTTPException) as exc:
        await service.create_user(superadmin, dto)
    assert exc.value.status_code == 422


async def test_duplicate_email_is_rejected():
    session = AdminMockDbSession()
    service = UserAdminService(session)
    superadmin = _build_user("super@sena.edu.co", RolUsuario.SUPERADMIN.value)
    existing = _build_user("dup@sena.edu.co", RolUsuario.ADMIN.value)
    session.add(superadmin)
    session.add(existing)

    dto = UserCreateRequest(
        email="dup@sena.edu.co",
        password="password123",
        password_confirmation="password123",
        nombre="Dup",
        apellido="User",
        roles=[RolUsuario.ADMIN.value],
    )
    with pytest.raises(HTTPException) as exc:
        await service.create_user(superadmin, dto)
    assert exc.value.status_code == 409


async def test_admin_cannot_edit_or_view_superadmin():
    session = AdminMockDbSession()
    service = UserAdminService(session)
    admin = _build_user("admin@sena.edu.co", RolUsuario.ADMIN.value)
    superadmin = _build_user("super@sena.edu.co", RolUsuario.SUPERADMIN.value)
    session.add(admin)
    session.add(superadmin)

    # View superadmin detail
    with pytest.raises(HTTPException) as exc_get:
        await service.get_user(admin, superadmin.id)
    assert exc_get.value.status_code == 403

    # Edit superadmin
    with pytest.raises(HTTPException) as exc_patch:
        await service.update_user(admin, superadmin.id, UserUpdateRequest(nombre="Modified"))
    assert exc_patch.value.status_code == 403

    # Change status
    with pytest.raises(HTTPException) as exc_status:
        await service.change_user_status(admin, superadmin.id, UserStatusUpdateRequest(estado="BLOQUEADO"))
    assert exc_status.value.status_code == 403

    # Reset password
    with pytest.raises(HTTPException) as exc_reset:
        await service.reset_password(
            admin,
            superadmin.id,
            UserResetPasswordRequest(temporary_password="newtemp123", confirm_temporary_password="newtemp123"),
        )
    assert exc_reset.value.status_code == 403


async def test_user_can_be_inactivated_and_blocked_revoking_sessions():
    session = AdminMockDbSession()
    service = UserAdminService(session)
    superadmin = _build_user("super@sena.edu.co", RolUsuario.SUPERADMIN.value)
    target = _build_user("target@sena.edu.co", RolUsuario.LIDER_EQUIPO_EJECUTOR.value)
    user_sess = UserSession(id=uuid.uuid4(), usuario_id=target.id, token_family=uuid.uuid4(), jti="j1")
    session.add(superadmin)
    session.add(target)
    session.add(user_sess)

    # Inactivate
    res_inact = await service.change_user_status(superadmin, target.id, UserStatusUpdateRequest(estado="INACTIVO"))
    assert res_inact.estado == "INACTIVO"
    assert target.token_version == 2
    assert user_sess.revoked_at is not None

    # Block
    user_sess2 = UserSession(id=uuid.uuid4(), usuario_id=target.id, token_family=uuid.uuid4(), jti="j2")
    session.add(user_sess2)
    res_block = await service.change_user_status(superadmin, target.id, UserStatusUpdateRequest(estado="BLOQUEADO"))
    assert res_block.estado == "BLOQUEADO"
    assert target.token_version == 3
    assert user_sess2.revoked_at is not None


async def test_last_active_superadmin_cannot_be_disabled_or_demoted():
    session = AdminMockDbSession()
    service = UserAdminService(session)
    superadmin = _build_user("sole_super@sena.edu.co", RolUsuario.SUPERADMIN.value)
    session.add(superadmin)

    # Inactivate attempt
    with pytest.raises(HTTPException) as exc_inact:
        await service.change_user_status(superadmin, superadmin.id, UserStatusUpdateRequest(estado="INACTIVO"))
    assert exc_inact.value.status_code == 409

    # Demotion attempt
    with pytest.raises(HTTPException) as exc_demote:
        await service.update_user(superadmin, superadmin.id, UserUpdateRequest(roles=[RolUsuario.ADMIN.value]))
    assert exc_demote.value.status_code == 409


async def test_user_cannot_inactivate_themselves():
    session = AdminMockDbSession()
    service = UserAdminService(session)
    admin = _build_user("admin@sena.edu.co", RolUsuario.ADMIN.value)
    session.add(admin)

    with pytest.raises(HTTPException) as exc:
        await service.change_user_status(admin, admin.id, UserStatusUpdateRequest(estado="INACTIVO"))
    assert exc.value.status_code == 409


async def test_admin_password_reset_forces_password_change_and_revokes():
    session = AdminMockDbSession()
    service = UserAdminService(session)
    superadmin = _build_user("super@sena.edu.co", RolUsuario.SUPERADMIN.value)
    target = _build_user("target@sena.edu.co", RolUsuario.USUARIO_ADICIONAL.value)
    target_sess = UserSession(id=uuid.uuid4(), usuario_id=target.id, token_family=uuid.uuid4(), jti="jt")
    session.add(superadmin)
    session.add(target)
    session.add(target_sess)

    res = await service.reset_password(
        superadmin,
        target.id,
        UserResetPasswordRequest(temporary_password="tempPassword123", confirm_temporary_password="tempPassword123"),
    )
    assert "exitosamente" in res["message"]
    assert target.debe_cambiar_password is True
    assert target.token_version == 2
    assert target_sess.revoked_at is not None


# ==============================================================================
# 2. TESTS ORGANIZACIÓN (COORDINACIONES & ESPECIALIDADES)
# ==============================================================================


async def test_coordination_crud_and_invariants():
    session = AdminMockDbSession()
    service = OrganizationAdminService(session)
    admin = _build_user("admin@sena.edu.co", RolUsuario.ADMIN.value)
    session.add(admin)

    # Create
    coord = await service.create_coordinacion(admin, CoordinacionCreate(codigo="TEL", nombre="TELEINFORMATICA"))
    assert coord.codigo == "TEL"

    # Duplicate code rejected
    with pytest.raises(HTTPException) as exc_dup:
        await service.create_coordinacion(admin, CoordinacionCreate(codigo="TEL", nombre="Otra"))
    assert exc_dup.value.status_code == 409

    # Update
    updated = await service.update_coordinacion(admin, coord.id, CoordinacionUpdate(nombre="TELEINFORMATICA MOD"))
    assert updated.nombre == "TELEINFORMATICA MOD"


async def test_specialty_crud_and_invariants():
    session = AdminMockDbSession()
    service = OrganizationAdminService(session)
    admin = _build_user("admin@sena.edu.co", RolUsuario.ADMIN.value)
    coord = Coordinacion(id=uuid.uuid4(), codigo="TEL", nombre="TELEINFORMATICA", activo=True)
    session.add(admin)
    session.add(coord)

    # Create specialty
    esp = await service.create_especialidad(admin, coord.id, EspecialidadCreate(codigo="ADSO", nombre="ADSO"))
    assert esp.codigo == "ADSO"
    assert esp.coordinacion_id == coord.id

    # Inactive coordination rejects specialty
    coord_inact = Coordinacion(id=uuid.uuid4(), codigo="INACT", nombre="Inactiva", activo=False)
    session.add(coord_inact)
    with pytest.raises(HTTPException) as exc_inact:
        await service.create_especialidad(admin, coord_inact.id, EspecialidadCreate(codigo="SUB", nombre="Sub"))
    assert exc_inact.value.status_code == 422


async def test_coordination_with_active_dependencies_cannot_be_disabled():
    session = AdminMockDbSession()
    service = OrganizationAdminService(session)
    admin = _build_user("admin@sena.edu.co", RolUsuario.ADMIN.value)
    coord = Coordinacion(id=uuid.uuid4(), codigo="TEL", nombre="TELEINFORMATICA", activo=True)
    esp = Especialidad(id=uuid.uuid4(), coordinacion_id=coord.id, codigo="REDES", nombre="REDES", activo=True)
    session.add(admin)
    session.add(coord)
    session.add(esp)

    with pytest.raises(HTTPException) as exc:
        await service.update_coordinacion(admin, coord.id, CoordinacionUpdate(activo=False))
    assert exc.value.status_code == 409
    assert "especialidad(es) activa(s)" in exc.value.detail


async def test_specialty_with_active_dependencies_cannot_be_disabled():
    session = AdminMockDbSession()
    service = OrganizationAdminService(session)
    admin = _build_user("admin@sena.edu.co", RolUsuario.ADMIN.value)
    coord = Coordinacion(id=uuid.uuid4(), codigo="TEL", nombre="TELEINFORMATICA", activo=True)
    esp = Especialidad(id=uuid.uuid4(), coordinacion_id=coord.id, codigo="REDES", nombre="REDES", activo=True)
    leader = _build_user("leader@sena.edu.co", RolUsuario.LIDER_EQUIPO_EJECUTOR.value, coord.id, esp.id)
    team = EquipoEjecutor(id=uuid.uuid4(), coordinacion_id=coord.id, especialidad_id=esp.id, lider_id=leader.id, estado=EstadoEquipo.ACTIVO)
    session.add(admin)
    session.add(coord)
    session.add(esp)
    session.add(leader)
    session.add(team)

    with pytest.raises(HTTPException) as exc:
        await service.update_especialidad(admin, esp.id, EspecialidadUpdate(activo=False))
    assert exc.value.status_code == 409
    assert "equipo(s) ejecutor(es) activo(s)" in exc.value.detail


# ==============================================================================
# 3. TESTS EQUIPOS EJECUTORES & CAMBIO DE LÍDER
# ==============================================================================


async def test_team_leader_must_have_leader_role_and_matching_scope():
    session = AdminMockDbSession()
    service = TeamAdminService(session)
    admin = _build_user("admin@sena.edu.co", RolUsuario.ADMIN.value)
    coord1 = Coordinacion(id=uuid.uuid4(), codigo="TEL", nombre="TELEINFORMATICA", activo=True)
    esp1 = Especialidad(id=uuid.uuid4(), coordinacion_id=coord1.id, codigo="ADSO", nombre="ADSO", activo=True)
    coord2 = Coordinacion(id=uuid.uuid4(), codigo="CRE", nombre="CREATIVAS", activo=True)
    esp2 = Especialidad(id=uuid.uuid4(), coordinacion_id=coord2.id, codigo="DIS", nombre="DISENO", activo=True)

    # Leader belongs to coord1, but team assigned to coord2
    mismatched_leader = _build_user("mismatch@sena.edu.co", RolUsuario.LIDER_EQUIPO_EJECUTOR.value, coord1.id, esp1.id)
    session.add(admin)
    session.add(coord1)
    session.add(esp1)
    session.add(coord2)
    session.add(esp2)
    session.add(mismatched_leader)

    dto = EquipoEjecutorCreate(
        nombre="Equipo ADSO",
        coordinacion_id=coord2.id,
        especialidad_id=esp2.id,
        lider_id=mismatched_leader.id,
    )
    with pytest.raises(HTTPException) as exc:
        await service.create_team(admin, dto)
    assert exc.value.status_code == 422


async def test_member_must_have_additional_user_role_and_matching_scope():
    session = AdminMockDbSession()
    service = TeamAdminService(session)
    admin = _build_user("admin@sena.edu.co", RolUsuario.ADMIN.value)
    coord = Coordinacion(id=uuid.uuid4(), codigo="TEL", nombre="TELEINFORMATICA", activo=True)
    esp = Especialidad(id=uuid.uuid4(), coordinacion_id=coord.id, codigo="ADSO", nombre="ADSO", activo=True)
    leader = _build_user("lider@sena.edu.co", RolUsuario.LIDER_EQUIPO_EJECUTOR.value, coord.id, esp.id)
    team = EquipoEjecutor(id=uuid.uuid4(), nombre="ADSO 1", coordinacion_id=coord.id, especialidad_id=esp.id, lider_id=leader.id, estado=EstadoEquipo.ACTIVO)
    team.miembros = []

    foreign_member = _build_user("foreign@sena.edu.co", RolUsuario.USUARIO_ADICIONAL.value, uuid.uuid4(), uuid.uuid4())
    session.add(admin)
    session.add(coord)
    session.add(esp)
    session.add(leader)
    session.add(team)
    session.add(foreign_member)

    with pytest.raises(HTTPException) as exc:
        await service.add_member(admin, team.id, MiembroCreate(usuario_id=foreign_member.id))
    assert exc.value.status_code == 422


async def test_changing_team_leader_revokes_old_leader_process_access():
    """Critical invariant: Changing team leader synchronizes ProcesoCurricular and immediately flips access."""
    session = AdminMockDbSession()
    team_service = TeamAdminService(session)
    scope_service = AccessScopeService(session)

    admin = _build_user("admin@sena.edu.co", RolUsuario.ADMIN.value)
    coord = Coordinacion(id=uuid.uuid4(), codigo="TEL", nombre="TELEINFORMATICA", activo=True)
    esp = Especialidad(id=uuid.uuid4(), coordinacion_id=coord.id, codigo="ADSO", nombre="ADSO", activo=True)

    leader1 = _build_user("lider1@sena.edu.co", RolUsuario.LIDER_EQUIPO_EJECUTOR.value, coord.id, esp.id)
    leader2 = _build_user("lider2@sena.edu.co", RolUsuario.LIDER_EQUIPO_EJECUTOR.value, coord.id, esp.id)

    team = EquipoEjecutor(
        id=uuid.uuid4(),
        nombre="ADSO Core",
        coordinacion_id=coord.id,
        especialidad_id=esp.id,
        lider_id=leader1.id,
        estado=EstadoEquipo.ACTIVO,
    )
    team.lider = leader1
    team.miembros = []

    ref_id = uuid.uuid4()
    proceso = ProcesoCurricular(
        id=uuid.uuid4(),
        referencia_id=ref_id,
        coordinacion_id=coord.id,
        especialidad_id=esp.id,
        equipo_ejecutor_id=team.id,
        lider_id=leader1.id,
        estado_scope=EstadoScopeProceso.ASIGNADO,
    )
    proceso.equipo_ejecutor = team

    session.add(admin)
    session.add(coord)
    session.add(esp)
    session.add(leader1)
    session.add(leader2)
    session.add(team)
    session.add(proceso)

    # Initial state: leader1 has access, leader2 does not
    assert await scope_service.can_access_process(leader1, ref_id) is True
    assert await scope_service.can_access_process(leader2, ref_id) is False

    # Execute leader change
    await team_service.update_team(admin, team.id, EquipoEjecutorUpdate(lider_id=leader2.id))
    team.lider = leader2

    # Verification: leader1 revoked immediately, leader2 authorized
    assert await scope_service.can_access_process(leader1, ref_id) is False
    assert await scope_service.can_access_process(leader2, ref_id) is True


async def test_team_with_process_cannot_change_organizational_scope():
    session = AdminMockDbSession()
    service = TeamAdminService(session)
    admin = _build_user("admin@sena.edu.co", RolUsuario.ADMIN.value)
    coord = Coordinacion(id=uuid.uuid4(), codigo="TEL", nombre="TELEINFORMATICA", activo=True)
    esp = Especialidad(id=uuid.uuid4(), coordinacion_id=coord.id, codigo="ADSO", nombre="ADSO", activo=True)
    leader = _build_user("lider@sena.edu.co", RolUsuario.LIDER_EQUIPO_EJECUTOR.value, coord.id, esp.id)
    team = EquipoEjecutor(id=uuid.uuid4(), nombre="ADSO 1", coordinacion_id=coord.id, especialidad_id=esp.id, lider_id=leader.id, estado=EstadoEquipo.ACTIVO)
    team.lider = leader
    team.miembros = []

    proceso = ProcesoCurricular(
        id=uuid.uuid4(),
        referencia_id=uuid.uuid4(),
        coordinacion_id=coord.id,
        especialidad_id=esp.id,
        equipo_ejecutor_id=team.id,
        lider_id=leader.id,
        estado_scope=EstadoScopeProceso.ASIGNADO,
    )
    session.add(admin)
    session.add(coord)
    session.add(esp)
    session.add(leader)
    session.add(team)
    session.add(proceso)

    new_coord_id = uuid.uuid4()
    with pytest.raises(HTTPException) as exc:
        await service.update_team(admin, team.id, EquipoEjecutorUpdate(coordinacion_id=new_coord_id))
    assert exc.value.status_code == 409
    assert "procesos curriculares asignados" in exc.value.detail


async def test_inactive_team_blocks_operational_access():
    session = AdminMockDbSession()
    scope_service = AccessScopeService(session)
    coord = Coordinacion(id=uuid.uuid4(), codigo="TEL", nombre="TELEINFORMATICA", activo=True)
    esp = Especialidad(id=uuid.uuid4(), coordinacion_id=coord.id, codigo="ADSO", nombre="ADSO", activo=True)
    leader = _build_user("lider@sena.edu.co", RolUsuario.LIDER_EQUIPO_EJECUTOR.value, coord.id, esp.id)
    team = EquipoEjecutor(id=uuid.uuid4(), nombre="ADSO Inactivo", coordinacion_id=coord.id, especialidad_id=esp.id, lider_id=leader.id, estado=EstadoEquipo.INACTIVO)
    team.lider = leader
    team.miembros = []

    ref_id = uuid.uuid4()
    proceso = ProcesoCurricular(
        id=uuid.uuid4(),
        referencia_id=ref_id,
        coordinacion_id=coord.id,
        especialidad_id=esp.id,
        equipo_ejecutor_id=team.id,
        lider_id=leader.id,
        estado_scope=EstadoScopeProceso.ASIGNADO,
    )
    proceso.equipo_ejecutor = team

    session.add(coord)
    session.add(esp)
    session.add(leader)
    session.add(team)
    session.add(proceso)

    # Inactive team blocks operational access even if user is the assigned leader
    assert await scope_service.can_access_process(leader, ref_id) is False


async def test_process_assignment_rejects_foreign_leader():
    session = AdminMockDbSession()
    service = TeamAdminService(session)
    admin = _build_user("admin@sena.edu.co", RolUsuario.ADMIN.value)
    coord = Coordinacion(id=uuid.uuid4(), codigo="TEL", nombre="TELEINFORMATICA", activo=True)
    esp = Especialidad(id=uuid.uuid4(), coordinacion_id=coord.id, codigo="ADSO", nombre="ADSO", activo=True)
    leader1 = _build_user("l1@sena.edu.co", RolUsuario.LIDER_EQUIPO_EJECUTOR.value, coord.id, esp.id)
    foreign_leader = _build_user("foreign@sena.edu.co", RolUsuario.LIDER_EQUIPO_EJECUTOR.value, coord.id, esp.id)
    team = EquipoEjecutor(id=uuid.uuid4(), nombre="ADSO", coordinacion_id=coord.id, especialidad_id=esp.id, lider_id=leader1.id, estado=EstadoEquipo.ACTIVO)
    session.add(admin)
    session.add(coord)
    session.add(esp)
    session.add(leader1)
    session.add(foreign_leader)
    session.add(team)

    ref = uuid.uuid4()
    with pytest.raises(HTTPException) as exc:
        await service.assign_process(admin, ref, ProcesoAsignarRequest(equipo_ejecutor_id=team.id, lider_id=foreign_leader.id))
    assert exc.value.status_code == 422
    assert "no coincide" in exc.value.detail
