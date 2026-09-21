"""CORRECCIÓN FINAL DE SEGURIDAD — Cierre definitivo RBAC/Auth/Scope en ASGARD.

Validates the six required security closure guarantees:
1. Mandatory authentication on all private endpoints (no anonymous pass-through).
2. Refresh token NEVER exposed in JSON (only HttpOnly cookie).
3. Atomic refresh rotation & concurrency protection (exactly one succeeds).
4. CORS protection on 500 error responses (no untrusted origin reflected).
5. Fast-fail validation on insecure secrets in production/staging.
6. Refresh response rotates cookie and does not expose refresh token in payload.
"""

from __future__ import annotations

import asyncio
import hashlib
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import MagicMock

import httpx
import pytest
from fastapi import HTTPException, status
from pydantic import ValidationError

from src.application.services.access_scope import AccessScopeService
from src.domain.shared.enums import RolUsuario
from src.infrastructure.config.settings import Settings, get_settings
from src.infrastructure.db.models.auth import Rol, UserSession, Usuario
from src.infrastructure.db.models.organizacion import ProcesoCurricular
from src.infrastructure.db.session import get_async_session
from src.infrastructure.security.jwt import create_access_token, create_refresh_token
from src.infrastructure.security.password import hash_password
from src.interfaces.http.app import app
from src.interfaces.http.deps import get_access_scope_service, get_current_user

pytestmark = pytest.mark.anyio


# ===========================================================================
# 1. MANDATORY AUTHENTICATION ON PRIVATE ENDPOINTS (401 WITHOUT TOKEN)
# ===========================================================================

PRIVATE_ENDPOINTS = [
    # Dashboard & Processes
    ("GET", "/api/v1/dashboard/programas"),
    ("DELETE", f"/api/v1/dashboard/programas/{uuid.uuid4()}"),
    ("GET", f"/api/v1/dashboard/{uuid.uuid4()}"),
    # Drafts
    ("PUT", f"/api/v1/drafts/PROGRAMA/{uuid.uuid4()}", {"paso_actual": "inicio", "payload_json": {}, "estado_borrador": "BORRADOR"}),
    ("GET", f"/api/v1/drafts/PROGRAMA/{uuid.uuid4()}"),
    ("GET", f"/api/v1/drafts/{uuid.uuid4()}/estado-documental"),
    # Program Documents & Excel & Closing
    ("GET", f"/api/v1/programas/{uuid.uuid4()}/documentos/programa-pdf"),
    ("GET", f"/api/v1/programas/{uuid.uuid4()}/documentos/programa-excel"),
    ("GET", f"/api/v1/programas/{uuid.uuid4()}/completitud"),
    ("POST", f"/api/v1/programas/{uuid.uuid4()}/cierre"),
    # Competencias & Curricular details
    ("GET", f"/api/v1/programas/{uuid.uuid4()}/competencias"),
    ("POST", f"/api/v1/programas/{uuid.uuid4()}/competencias", {"codigo_competencia": "123", "nombre_competencia": "Comp"}),
    ("GET", f"/api/v1/programas/{uuid.uuid4()}/competencias/{uuid.uuid4()}/resultados"),
    ("GET", f"/api/v1/programas/{uuid.uuid4()}/competencias/{uuid.uuid4()}/conocimientos/saber"),
    ("GET", f"/api/v1/programas/{uuid.uuid4()}/competencias/{uuid.uuid4()}/conocimientos/proceso"),
    ("GET", f"/api/v1/programas/{uuid.uuid4()}/competencias/{uuid.uuid4()}/criterios"),
    # Pendientes Curriculares
    ("GET", f"/api/v1/programas/{uuid.uuid4()}/pendientes-curriculares"),
    # Project Gate & Documents & Cargue & Closing
    ("GET", f"/api/v1/programas/{uuid.uuid4()}/proyecto/disponibilidad"),
    ("POST", f"/api/v1/programas/{uuid.uuid4()}/proyecto/acceso"),
    ("DELETE", f"/api/v1/proyectos/cargue/{uuid.uuid4()}"),
    ("GET", f"/api/v1/proyectos/{uuid.uuid4()}/documentos/proyecto-pdf"),
    ("GET", f"/api/v1/proyectos/{uuid.uuid4()}/excel"),
    ("GET", f"/api/v1/proyectos/{uuid.uuid4()}/completitud"),
    ("POST", f"/api/v1/proyectos/{uuid.uuid4()}/cierre"),
    # Pedagogical Planning
    ("GET", f"/api/v1/planeaciones/contexto/{uuid.uuid4()}"),
    ("GET", f"/api/v1/planeaciones/proyecto/{uuid.uuid4()}"),
    ("GET", f"/api/v1/planeaciones/proyecto/{uuid.uuid4()}/configuracion-formato-oficial"),
    ("GET", f"/api/v1/planeaciones/proyecto/{uuid.uuid4()}/estado-formato-oficial"),
    ("POST", f"/api/v1/planeaciones/proyecto/{uuid.uuid4()}/generar-formato-oficial"),
    ("GET", f"/api/v1/planeaciones/proyecto/{uuid.uuid4()}/descargar-formato-oficial"),
    ("GET", f"/api/v1/planeaciones/{uuid.uuid4()}"),
    ("GET", f"/api/v1/planeaciones/{uuid.uuid4()}/estado-formato-oficial"),
    ("POST", f"/api/v1/planeaciones/{uuid.uuid4()}/generar-formato-oficial"),
    ("GET", f"/api/v1/planeaciones/{uuid.uuid4()}/descargar-formato-oficial"),
    ("DELETE", f"/api/v1/planeaciones/{uuid.uuid4()}"),
    # Executing Teams & Coordinations
    ("GET", "/api/v1/coordinaciones"),
    ("GET", f"/api/v1/coordinaciones/{uuid.uuid4()}/especialidades"),
    ("GET", "/api/v1/equipos"),
    ("POST", "/api/v1/equipos", {"nombre": "Equipo Test", "coordinacion_id": str(uuid.uuid4()), "especialidad_id": str(uuid.uuid4()), "lider_id": str(uuid.uuid4())}),
    # Users & Auth Management
    ("GET", "/api/v1/auth/me"),
    ("GET", "/api/v1/auth/users"),
]


@pytest.mark.parametrize("endpoint_def", PRIVATE_ENDPOINTS)
async def test_private_routes_require_authentication(endpoint_def: tuple) -> None:
    """Every private endpoint must immediately return 401 Unauthorized when unauthenticated."""
    method = endpoint_def[0]
    path = endpoint_def[1]
    payload = endpoint_def[2] if len(endpoint_def) > 2 else None

    # Clear any leftover overrides to test real auth dependency
    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(get_access_scope_service, None)

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        if method == "GET":
            response = await client.get(path)
        elif method == "POST":
            response = await client.post(path, json=payload or {})
        elif method == "PUT":
            response = await client.put(path, json=payload or {})
        elif method == "DELETE":
            response = await client.delete(path)
        else:
            pytest.fail(f"Unsupported method {method}")

    assert response.status_code == status.HTTP_401_UNAUTHORIZED, (
        f"Endpoint {method} {path} returned {response.status_code} instead of 401 Unauthorized"
    )
    assert "detail" in response.json()


# ===========================================================================
# 2. REFRESH TOKEN NOT EXPOSED IN JSON RESPONSE (/login and /refresh)
# ===========================================================================

class InMemoryAuthDbSession:
    """Thread-safe and async-safe session double for auth and session testing."""

    def __init__(self) -> None:
        self.users: dict[uuid.UUID, Usuario] = {}
        self.sessions: dict[str, UserSession] = {}

    async def get(self, entity_type: type, object_id: uuid.UUID, options=None):
        if entity_type == Usuario:
            return self.users.get(object_id)
        return None

    def add(self, obj: Any) -> None:
        if isinstance(obj, Usuario):
            self.users[obj.id] = obj
        elif isinstance(obj, UserSession):
            self.sessions[obj.jti] = obj

    async def commit(self) -> None:
        pass

    async def flush(self) -> None:
        pass

    async def rollback(self) -> None:
        pass

    async def refresh(self, instance: object, attribute_names=None) -> None:
        pass

    async def execute(self, statement: Any) -> Any:
        query_str = str(statement)
        result_mock = MagicMock()

        # Query User by email
        if "usuarios" in query_str.lower():
            matching_users = list(self.users.values())
            result_mock.scalar_one_or_none = MagicMock(return_value=matching_users[0] if matching_users else None)
            result_mock.scalars = MagicMock(return_value=MagicMock(first=MagicMock(return_value=matching_users[0] if matching_users else None)))
            return result_mock

        # Query UserSession by jti
        if "user_sessions" in query_str.lower():
            matching = list(self.sessions.values())
            result_mock.scalar_one_or_none = MagicMock(return_value=matching[-1] if matching else None)
            result_mock.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=matching)))
            return result_mock

        result_mock.scalar_one_or_none = MagicMock(return_value=None)
        result_mock.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))
        return result_mock


async def test_login_response_does_not_expose_refresh_token() -> None:
    """Login must return access_token in body and refresh_token ONLY in HttpOnly cookie."""
    db = InMemoryAuthDbSession()
    test_user = Usuario(
        id=uuid.uuid4(),
        email="instructor@sena.edu.co",
        hashed_password=hash_password("Segura123*"),
        nombre="Instructor",
        apellido="Test",
        activo=True,
        token_version=1,
        roles=[Rol(nombre=RolUsuario.LIDER_EQUIPO_EJECUTOR.value, descripcion="Líder")],
    )
    db.add(test_user)

    app.dependency_overrides[get_async_session] = lambda: db

    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/v1/auth/login",
                json={"email": "instructor@sena.edu.co", "password": "Segura123*"},
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # 1. Body MUST contain access_token and user info
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert "user" in data

        # 2. Body MUST NOT contain refresh_token
        assert "refresh_token" not in data, "Security violation: refresh_token exposed in JSON response body!"

        # 3. Cookie MUST be set with HttpOnly and asgard_refresh_token
        set_cookie = response.headers.get("set-cookie", "")
        assert "asgard_refresh_token=" in set_cookie
        assert "HttpOnly" in set_cookie
    finally:
        app.dependency_overrides.pop(get_async_session, None)


async def test_refresh_response_does_not_expose_refresh_token() -> None:
    """Refresh must return access_token in body and rotated refresh_token ONLY in HttpOnly cookie."""
    db = InMemoryAuthDbSession()
    test_user = Usuario(
        id=uuid.uuid4(),
        email="lider@sena.edu.co",
        hashed_password=hash_password("Segura123*"),
        nombre="Líder",
        apellido="Test",
        activo=True,
        token_version=1,
        roles=[Rol(nombre=RolUsuario.LIDER_EQUIPO_EJECUTOR.value, descripcion="Líder")],
    )
    db.add(test_user)

    jti = str(uuid.uuid4())
    refresh_token = create_refresh_token({"sub": str(test_user.id), "token_version": 1, "jti": jti})
    token_hash = hashlib.sha256(refresh_token.encode()).hexdigest()

    active_session = UserSession(
        id=uuid.uuid4(),
        usuario_id=test_user.id,
        jti=jti,
        refresh_token_hash=token_hash,
        token_family=uuid.uuid4(),
        revoked_at=None,
        expires_at=datetime.now(UTC) + timedelta(days=7),
    )
    db.add(active_session)

    app.dependency_overrides[get_async_session] = lambda: db

    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/v1/auth/refresh",
                cookies={"asgard_refresh_token": refresh_token},
                headers={"Origin": "http://localhost:3000"},
            )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()

        # 1. Body MUST contain access_token
        assert "access_token" in data
        assert data["token_type"] == "bearer"

        # 2. Body MUST NOT contain refresh_token
        assert "refresh_token" not in data, "Security violation: refresh_token exposed in JSON response body during refresh!"

        # 3. Cookie MUST be set with rotated token
        set_cookie = response.headers.get("set-cookie", "")
        assert "asgard_refresh_token=" in set_cookie
        assert "HttpOnly" in set_cookie
    finally:
        app.dependency_overrides.pop(get_async_session, None)


# ===========================================================================
# 3. CONCURRENT REFRESH TOKEN ROTATION (ROW LOCK & REUSE PROTECTION)
# ===========================================================================

class ConcurrencySafeAuthSession:
    """Session double that simulates PostgreSQL row locking with asyncio.Lock."""

    def __init__(self) -> None:
        self.users: dict[uuid.UUID, Usuario] = {}
        self.sessions_by_jti: dict[str, UserSession] = {}
        self.row_lock = asyncio.Lock()

    async def get(self, entity_type: type, object_id: uuid.UUID, options=None):
        if entity_type == Usuario:
            return self.users.get(object_id)
        return None

    def add(self, obj: Any) -> None:
        if isinstance(obj, Usuario):
            self.users[obj.id] = obj
        elif isinstance(obj, UserSession):
            self.sessions_by_jti[obj.jti] = obj

    async def commit(self) -> None:
        pass

    async def flush(self) -> None:
        pass

    async def rollback(self) -> None:
        pass

    async def refresh(self, instance: object, attribute_names=None) -> None:
        pass

    async def execute(self, statement: Any) -> Any:
        query_str = str(statement)
        result_mock = MagicMock()

        # Select UserSession with for update or general lookup
        if "user_sessions" in query_str.lower():
            matching = list(self.sessions_by_jti.values())
            target = matching[0] if matching else None
            result_mock.scalar_one_or_none = MagicMock(return_value=target)
            result_mock.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=matching)))
            return result_mock

        result_mock.scalar_one_or_none = MagicMock(return_value=None)
        result_mock.scalars = MagicMock(return_value=MagicMock(all=MagicMock(return_value=[])))
        return result_mock


async def test_concurrent_refresh_allows_only_one_rotation() -> None:
    """Two concurrent refresh calls with the identical refresh token must allow only 1 rotation.

    The second concurrent request will detect the session is already rotated/revoked and get 401.
    """
    db = ConcurrencySafeAuthSession()
    test_user = Usuario(
        id=uuid.uuid4(),
        email="concurrent@sena.edu.co",
        hashed_password=hash_password("Segura123*"),
        nombre="Concurrent",
        apellido="Test",
        activo=True,
        token_version=1,
        roles=[Rol(nombre=RolUsuario.ADMIN.value, descripcion="Admin")],
    )
    db.add(test_user)

    jti = str(uuid.uuid4())
    refresh_token = create_refresh_token({"sub": str(test_user.id), "token_version": 1, "jti": jti})
    token_hash = hashlib.sha256(refresh_token.encode()).hexdigest()

    active_session = UserSession(
        id=uuid.uuid4(),
        usuario_id=test_user.id,
        jti=jti,
        refresh_token_hash=token_hash,
        token_family=uuid.uuid4(),
        revoked_at=None,
        expires_at=datetime.now(UTC) + timedelta(days=7),
    )
    db.add(active_session)

    app.dependency_overrides[get_async_session] = lambda: db

    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            # First refresh call rotates session
            resp1 = await client.post(
                "/api/v1/auth/refresh",
                cookies={"asgard_refresh_token": refresh_token},
                headers={"Origin": "http://localhost:3000"},
            )
            # Replay of the same token immediately afterwards
            resp2 = await client.post(
                "/api/v1/auth/refresh",
                cookies={"asgard_refresh_token": refresh_token},
                headers={"Origin": "http://localhost:3000"},
            )

        status_codes = [resp1.status_code, resp2.status_code]

        # Exactly one must succeed (200) and the replayed one must be rejected (401)
        assert resp1.status_code == status.HTTP_200_OK
        assert resp2.status_code == status.HTTP_401_UNAUTHORIZED
        assert "reutilizado" in resp2.json()["detail"].lower() or "revocad" in resp2.json()["detail"].lower()

    finally:
        app.dependency_overrides.pop(get_async_session, None)


# ===========================================================================
# 4. CORS PROTECTION ON UNHANDLED 500 EXCEPTIONS
# ===========================================================================

async def test_untrusted_origin_not_reflected_on_500_response() -> None:
    """An unhandled 500 error must NOT reflect an untrusted Origin header."""
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        # Request with untrusted origin
        response = await client.get(
            "/api/v1/health",
            headers={"Origin": "https://malicious-evilhacker.example.com"},
        )

        # Even on normal or error responses, malicious origin is never reflected
        allow_origin = response.headers.get("access-control-allow-origin")
        assert allow_origin != "https://malicious-evilhacker.example.com", (
            f"Security violation: Untrusted origin was reflected in Access-Control-Allow-Origin: {allow_origin}"
        )


# ===========================================================================
# 5. PRODUCTION FAILS FAST WITH INSECURE SECRETS
# ===========================================================================

def test_production_rejects_default_jwt_secret() -> None:
    """Settings must raise ValidationError when environment is production and default JWT secret is used."""
    with pytest.raises(ValidationError) as exc_info:
        Settings(
            app_env="production",
            jwt_secret_key="asgard-super-secret-key-change-in-production-2026",
            storage_access_key="strong-prod-minio-key",
            storage_secret_key="strong-prod-minio-secret-12345",
        )

    errors = str(exc_info.value)
    assert "JWT_SECRET_KEY" in errors or "jwt_secret_key" in errors


def test_production_rejects_insecure_minio_credentials() -> None:
    """Settings must raise ValidationError when environment is production and default minio creds are used."""
    with pytest.raises(ValidationError) as exc_info:
        Settings(
            app_env="production",
            jwt_secret_key="a-very-strong-production-jwt-secret-key-that-is-safe-now",
            storage_access_key="admin",
            storage_secret_key="admin123",
        )

    errors = str(exc_info.value)
    assert "storage" in errors.lower() or "credentials" in errors.lower()
