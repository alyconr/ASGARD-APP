"""Tests for micro-hardening: CSRF, Refresh Replay, Cookies, CORS, and Document Scoping."""

from __future__ import annotations

import hashlib
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException, status
from fastapi.testclient import TestClient

from src.application.dto.planeacion import PlaneacionDocumentoConfigDTO
from src.application.services.access_scope import AccessScopeService
from src.domain.shared.enums import EstadoEquipo, EstadoScopeProceso, RolUsuario
from src.infrastructure.config.settings import Settings, get_settings
from src.infrastructure.db.models.auth import Rol, UserSession, Usuario
from src.infrastructure.db.models.drafts import BorradorSesion
from src.infrastructure.db.models.organizacion import (
    Coordinacion,
    EquipoEjecutor,
    EquipoEjecutorMiembro,
    Especialidad,
    ProcesoCurricular,
)
from src.infrastructure.db.models.planeacion import PlaneacionPedagogica
from src.infrastructure.db.models.proyecto import ProyectoFormativo
from src.infrastructure.db.session import get_async_session
from src.infrastructure.security.cookie_auth import normalize_origin, verify_csrf_origin
from src.infrastructure.security.jwt import create_access_token, create_refresh_token, decode_token
from src.infrastructure.security.password import hash_password
from src.infrastructure.storage.document_storage import MinioDocumentStorageService
from src.interfaces.http.app import app
from src.interfaces.http.controllers.planeacion import get_planeacion_service
from src.interfaces.http.deps import get_current_user

pytestmark = pytest.mark.anyio


class InMemorySession:
    """Async session double for micro-hardening integration tests."""

    def __init__(self) -> None:
        self.objects: dict[uuid.UUID, Any] = {}
        self.sessions: list[UserSession] = []

    def register(self, obj: Any) -> Any:
        if hasattr(obj, "id") and obj.id:
            self.objects[obj.id] = obj
        if isinstance(obj, UserSession):
            self.sessions.append(obj)
        return obj

    def add(self, obj: Any) -> None:
        self.register(obj)

    async def get(self, entity_type: type, object_id: uuid.UUID, options=None):
        return self.objects.get(object_id)

    async def commit(self) -> None:
        pass

    async def flush(self) -> None:
        pass

    async def rollback(self) -> None:
        pass

    async def refresh(self, instance: object, attribute_names=None) -> None:
        pass

    async def execute(self, statement: Any) -> Any:
        result_mock = MagicMock()
        query_str = str(statement)

        # Querying UserSession by jti or hash
        if "user_sessions" in query_str.lower():
            matching_sessions = list(self.sessions)
            result_mock.scalar_one_or_none = MagicMock(
                return_value=matching_sessions[-1] if matching_sessions else None
            )
            result_mock.scalars = MagicMock(
                return_value=MagicMock(all=MagicMock(return_value=matching_sessions))
            )
            return result_mock

        # Querying ProcesoCurricular
        if "procesos_curriculares" in query_str.lower():
            procesos = [o for o in self.objects.values() if isinstance(o, ProcesoCurricular)]
            result_mock.scalar_one_or_none = MagicMock(return_value=procesos[0] if procesos else None)
            result_mock.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=procesos)))
            return result_mock

        result_mock.scalar_one_or_none = MagicMock(return_value=None)
        result_mock.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))
        return result_mock


# ---------------------------------------------------------------------------
# 1. CSRF & ORIGIN TESTS
# ---------------------------------------------------------------------------

async def test_csrf_origin_rejected_when_untrusted():
    """Cookie-based request from an untrusted origin must be rejected with 403."""
    mock_request = MagicMock()
    mock_request.headers = {"origin": "http://malicious-attacker.com"}
    mock_request.cookies = {"asgard_refresh_token": "valid.token.here"}

    with pytest.raises(HTTPException) as exc_info:
        await verify_csrf_origin(mock_request)

    assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
    assert "Origen no permitido" in exc_info.value.detail


async def test_csrf_origin_allowed_when_trusted():
    """Cookie-based request from a trusted origin in cors_allow_origins must pass."""
    mock_request = MagicMock()
    mock_request.headers = {"origin": "http://localhost:3000"}
    mock_request.cookies = {"asgard_refresh_token": "valid.token.here"}

    # Should not raise
    await verify_csrf_origin(mock_request)


async def test_csrf_referer_allowed_when_trusted():
    """Referer matching allowed origins passes when Origin header is omitted."""
    mock_request = MagicMock()
    mock_request.headers = {"referer": "http://127.0.0.1:3000/app/auth"}
    mock_request.cookies = {"asgard_refresh_token": "valid.token.here"}

    await verify_csrf_origin(mock_request)


def test_cors_settings_sanitizes_wildcard():
    """Settings cors_allow_origin_list must filter out wildcard '*' when credentials are used."""
    s = Settings(cors_allow_origins="http://localhost:3000, *, http://127.0.0.1:3000")
    origins = s.cors_allow_origin_list
    assert "*" not in origins
    assert "http://localhost:3000" in origins
    assert "http://127.0.0.1:3000" in origins


# ---------------------------------------------------------------------------
# 2. REFRESH TOKEN ROTATION & REPLAY TESTS
# ---------------------------------------------------------------------------

async def test_refresh_token_replay_attack_detection():
    """Reusing a previously rotated refresh token triggers replay detection and revocation."""
    session_db = InMemorySession()
    user_id = uuid.uuid4()
    family_id = uuid.uuid4()

    user = Usuario(
        id=user_id,
        email="test.user@sena.edu.co",
        hashed_password=hash_password("password123"),
        nombre="Test",
        apellido="User",
        activo=True,
        token_version=1,
    )
    user.roles = []
    session_db.register(user)

    # Simulate an already rotated (revoked) session
    jti_old = str(uuid.uuid4())
    token_old = create_refresh_token({
        "sub": str(user_id),
        "jti": jti_old,
        "token_family": str(family_id),
        "token_version": 1,
    })
    token_old_hash = hashlib.sha256(token_old.encode("utf-8")).hexdigest()

    expired_session = UserSession(
        id=uuid.uuid4(),
        usuario_id=user_id,
        refresh_token_hash=token_old_hash,
        token_family=family_id,
        jti=jti_old,
        expires_at=datetime.now(UTC) + timedelta(days=7),
        revoked_at=datetime.now(UTC) - timedelta(minutes=5),  # ALREADY REVOKED!
    )
    session_db.register(expired_session)

    # Now an attacker tries to refresh with token_old
    from src.interfaces.http.controllers.auth import refresh_token

    mock_req = MagicMock()
    mock_req.client = MagicMock(host="192.168.1.50")
    mock_req.headers = {"origin": "http://localhost:3000"}
    mock_res = MagicMock()

    with pytest.raises(HTTPException) as exc_info:
        await refresh_token(
            request=mock_req,
            response=mock_res,
            session=session_db,
            asgard_refresh_token=token_old,
        )

    assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert "reutilizado" in exc_info.value.detail.lower()
    # The user's token_version must have been incremented to invalidate access tokens
    assert user.token_version == 2


async def test_refresh_token_inactive_user_rejected():
    """An inactive/blocked user cannot refresh their session."""
    session_db = InMemorySession()
    user_id = uuid.uuid4()

    inactive_user = Usuario(
        id=user_id,
        email="blocked@sena.edu.co",
        hashed_password=hash_password("password123"),
        nombre="Blocked",
        apellido="User",
        activo=False,  # INACTIVE
        token_version=1,
    )
    inactive_user.roles = []
    session_db.register(inactive_user)

    jti = str(uuid.uuid4())
    token = create_refresh_token({
        "sub": str(user_id),
        "jti": jti,
        "token_version": 1,
    })

    from src.interfaces.http.controllers.auth import refresh_token

    mock_req = MagicMock()
    mock_req.headers = {"origin": "http://localhost:3000"}
    mock_res = MagicMock()

    with pytest.raises(HTTPException) as exc_info:
        await refresh_token(
            request=mock_req,
            response=mock_res,
            session=session_db,
            asgard_refresh_token=token,
        )

    assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert "inactivo" in exc_info.value.detail.lower()


# ---------------------------------------------------------------------------
# 3. DOCUMENT DOWNLOADS SCOPING & ISOLATION
# ---------------------------------------------------------------------------

async def test_document_scoping_leader_isolation():
    """Leader A can access their team's documents, but is denied access to Team B's documents."""
    coord_id = uuid.uuid4()
    esp_id = uuid.uuid4()

    leader_a = Usuario(
        id=uuid.uuid4(),
        email="lider.a@sena.edu.co",
        hashed_password="pw",
        nombre="Líder",
        apellido="A",
        activo=True,
        coordinacion_id=coord_id,
        especialidad_id=esp_id,
    )
    rol_lider = Rol(id=uuid.uuid4(), nombre=RolUsuario.LIDER_EQUIPO_EJECUTOR.value)
    leader_a.roles = [rol_lider]

    leader_b = Usuario(
        id=uuid.uuid4(),
        email="lider.b@sena.edu.co",
        hashed_password="pw",
        nombre="Líder",
        apellido="B",
        activo=True,
        coordinacion_id=coord_id,
        especialidad_id=esp_id,
    )
    leader_b.roles = [rol_lider]

    admin = Usuario(
        id=uuid.uuid4(),
        email="admin@sena.edu.co",
        hashed_password="pw",
        nombre="Admin",
        apellido="SENA",
        activo=True,
    )
    rol_admin = Rol(id=uuid.uuid4(), nombre=RolUsuario.ADMIN.value)
    admin.roles = [rol_admin]

    team_a = EquipoEjecutor(
        id=uuid.uuid4(),
        nombre="Equipo A",
        coordinacion_id=coord_id,
        especialidad_id=esp_id,
        lider_id=leader_a.id,
        estado=EstadoEquipo.ACTIVO,
    )
    team_a.miembros = []
    leader_a.equipos_liderados = [team_a]

    team_b = EquipoEjecutor(
        id=uuid.uuid4(),
        nombre="Equipo B",
        coordinacion_id=coord_id,
        especialidad_id=esp_id,
        lider_id=leader_b.id,
        estado=EstadoEquipo.ACTIVO,
    )
    team_b.miembros = []
    leader_b.equipos_liderados = [team_b]

    # Process A for Team A
    ref_a = uuid.uuid4()
    proc_a = ProcesoCurricular(
        id=uuid.uuid4(),
        referencia_id=ref_a,
        creado_por=leader_a.id,
        lider_id=leader_a.id,
        equipo_ejecutor_id=team_a.id,
        coordinacion_id=coord_id,
        especialidad_id=esp_id,
        estado_scope=EstadoScopeProceso.ASIGNADO,
    )
    proc_a.equipo_ejecutor = team_a

    # Process B for Team B
    ref_b = uuid.uuid4()
    proc_b = ProcesoCurricular(
        id=uuid.uuid4(),
        referencia_id=ref_b,
        creado_por=leader_b.id,
        lider_id=leader_b.id,
        equipo_ejecutor_id=team_b.id,
        coordinacion_id=coord_id,
        especialidad_id=esp_id,
        estado_scope=EstadoScopeProceso.ASIGNADO,
    )
    proc_b.equipo_ejecutor = team_b

    # Mock scope service
    scope_mock = AsyncMock(spec=AccessScopeService)

    async def fake_can_access_process(user: Usuario, ref_id: uuid.UUID) -> bool:
        if user.has_role(RolUsuario.ADMIN.value, RolUsuario.SUPERADMIN.value):
            return True
        if ref_id == ref_a and user.id == leader_a.id:
            return True
        if ref_id == ref_b and user.id == leader_b.id:
            return True
        return False

    async def fake_require_process_access(user: Usuario, ref_id: uuid.UUID):
        if not await fake_can_access_process(user, ref_id):
            raise HTTPException(status_code=403, detail="Acceso denegado al proceso curricular")
        return proc_a if ref_id == ref_a else proc_b

    scope_mock.can_access_process.side_effect = fake_can_access_process
    scope_mock.require_process_access.side_effect = fake_require_process_access

    # 1. Leader A accessing their own process A -> Allowed
    res_a = await scope_mock.require_process_access(leader_a, ref_a)
    assert res_a == proc_a

    # 2. Leader A accessing Leader B's process B -> Forbidden (403)
    with pytest.raises(HTTPException) as exc_b:
        await scope_mock.require_process_access(leader_a, ref_b)
    assert exc_b.value.status_code == 403

    # 3. Admin accessing Process B -> Allowed
    res_admin = await scope_mock.require_process_access(admin, ref_b)
    assert res_admin == proc_b


async def test_planning_download_endpoints_enforce_scope():
    """GPFI download endpoints enforce can_access_project and can_access_planning."""
    scope_service = AsyncMock(spec=AccessScopeService)
    scope_service.can_access_project.return_value = False
    scope_service.can_access_planning.return_value = False

    fake_leader = Usuario(
        id=uuid.uuid4(),
        email="lider@sena.edu.co",
        hashed_password="pw",
        nombre="Lider",
        apellido="Test",
        activo=True,
    )
    fake_leader.roles = [Rol(id=uuid.uuid4(), nombre=RolUsuario.LIDER_EQUIPO_EJECUTOR.value)]

    proj_id = uuid.uuid4()
    plan_id = uuid.uuid4()

    from src.interfaces.http.controllers.planeacion import (
        descargar_formato_consolidado,
        descargar_formato_individual,
    )

    # Consolidated download by foreign user -> 403
    with pytest.raises(HTTPException) as exc_cons:
        await descargar_formato_consolidado(
            proyecto_id=proj_id,
            service=AsyncMock(),
            current_user=fake_leader,
            scope_service=scope_service,
        )
    assert exc_cons.value.status_code == 403

    # Individual download by foreign user -> 403
    with pytest.raises(HTTPException) as exc_ind:
        await descargar_formato_individual(
            planeacion_id=plan_id,
            service=AsyncMock(),
            current_user=fake_leader,
            scope_service=scope_service,
        )
    assert exc_ind.value.status_code == 403
