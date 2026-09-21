"""Tests for Sprint C: Institutional Audit Viewer (Visor Institucional de Auditoría)."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any
from unittest.mock import MagicMock

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from src.application.dto.audit_admin import AuditFilterDTO
from src.application.services.audit_admin import AuditQueryService, sanitize_audit_payload
from src.domain.shared.enums import EstadoUsuario, RolUsuario
from src.infrastructure.db.models.audit import EventoAuditoria
from src.infrastructure.db.models.auth import Rol, Usuario
from src.infrastructure.db.session import get_async_session
from src.interfaces.http.app import app
from src.interfaces.http.deps import get_current_user

pytestmark = pytest.mark.anyio


class AuditMockDbSession:
    """Async session double configured for audit queries."""

    def __init__(self) -> None:
        self.events: list[EventoAuditoria] = []

    async def execute(self, statement: Any) -> MagicMock:
        mock_result = MagicMock()
        text = str(statement).lower()

        # Count query
        if "count(eventos_auditoria.id)" in text or "count" in text:
            # Simple filtering count
            matching = self.events
            mock_result.scalar_one.return_value = len(matching)
            mock_result.scalar_one_or_none.return_value = len(matching)
            return mock_result

        # List / scalar query
        if "from eventos_auditoria" in text:
            if "eventos_auditoria.id =" in text or "where eventos_auditoria.id" in text or "id_1" in text:
                matching = None
                try:
                    params = statement.compile().params
                    ev_id = next((v for k, v in params.items() if "id" in k or "pk" in k), None)
                    if ev_id:
                        matching = next((e for e in self.events if str(e.id) == str(ev_id)), None)
                except Exception:
                    pass
                if not matching:
                    matching = self.events[0] if self.events else None
                mock_result.scalar_one_or_none.return_value = matching
                return mock_result

            mock_result.scalars.return_value.all.return_value = self.events
            row_single = self.events[0] if self.events else None
            mock_result.scalar_one_or_none.return_value = row_single
            return mock_result

        mock_result.scalar_one.return_value = 0
        mock_result.scalar_one_or_none.return_value = None
        mock_result.scalars.return_value.all.return_value = []
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


def setup_audit_mock_db() -> tuple[AuditMockDbSession, Usuario, EventoAuditoria]:
    db = AuditMockDbSession()
    actor = make_test_user(RolUsuario.ADMIN, "admin@sena.edu.co")

    ref_id = uuid.uuid4()
    event1 = EventoAuditoria(
        id=uuid.uuid4(),
        entidad="Usuario",
        entidad_id=uuid.uuid4(),
        accion="CREAR_USUARIO",
        actor_usuario_id=actor.id,
        referencia_id=ref_id,
        fecha_evento=datetime(2026, 9, 21, 10, 0, 0, tzinfo=timezone.utc),
        detalle={
            "email": "nuevo@sena.edu.co",
            "password": "plain_password_123",
            "temporary_password": "temp_secret_456",
            "access_token": "jwt.secret.token",
            "cookie_session": "session_cookie_value",
            "rol": "LIDER_EQUIPO_EJECUTOR",
        },
    )
    event1.actor = actor

    event2 = EventoAuditoria(
        id=uuid.uuid4(),
        entidad="ProcesoCurricular",
        entidad_id=uuid.uuid4(),
        accion="ASIGNAR_EQUIPO",
        actor_usuario_id=actor.id,
        referencia_id=ref_id,
        fecha_evento=datetime(2026, 9, 21, 11, 0, 0, tzinfo=timezone.utc),
        detalle={"equipo_id": str(uuid.uuid4()), "lider_id": str(actor.id)},
    )
    event2.actor = actor

    db.events.extend([event2, event1])  # Ordered descending by date
    return db, actor, event1


# ==============================================================================
# 1. RBAC Tests for Institutional Audit
# ==============================================================================

def test_audit_rbac_forbidden_for_leader():
    """Líder de equipo ejecutor must be rejected with 403 Forbidden."""
    db, _, _ = setup_audit_mock_db()
    leader = make_test_user(RolUsuario.LIDER_EQUIPO_EJECUTOR)

    app.dependency_overrides[get_async_session] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: leader
    try:
        client = TestClient(app)
        resp = client.get("/api/v1/admin/audit")
        assert resp.status_code == status.HTTP_403_FORBIDDEN
    finally:
        app.dependency_overrides.clear()


def test_audit_rbac_forbidden_for_additional_user():
    """Usuario adicional must be rejected with 403 Forbidden."""
    db, _, _ = setup_audit_mock_db()
    user = make_test_user(RolUsuario.USUARIO_ADICIONAL)

    app.dependency_overrides[get_async_session] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: user
    try:
        client = TestClient(app)
        resp = client.get("/api/v1/admin/audit")
        assert resp.status_code == status.HTTP_403_FORBIDDEN
    finally:
        app.dependency_overrides.clear()


def test_audit_rbac_allowed_for_superadmin_and_admin():
    """SUPERADMIN and ADMIN can list and view audit logs."""
    db, _, event1 = setup_audit_mock_db()

    for rol in (RolUsuario.SUPERADMIN, RolUsuario.ADMIN):
        admin_user = make_test_user(rol)
        app.dependency_overrides[get_async_session] = lambda: db
        app.dependency_overrides[get_current_user] = lambda: admin_user
        try:
            client = TestClient(app)
            resp = client.get("/api/v1/admin/audit")
            assert resp.status_code == status.HTTP_200_OK
            data = resp.json()
            assert "items" in data
            assert data["total"] == 2

            resp_detail = client.get(f"/api/v1/admin/audit/{event1.id}")
            assert resp_detail.status_code == status.HTTP_200_OK
            assert resp_detail.json()["id"] == str(event1.id)
        finally:
            app.dependency_overrides.clear()


# ==============================================================================
# 2. Sanitization Tests (Invariant: No sensitive secrets leaked)
# ==============================================================================

def test_audit_sensitive_payload_redaction():
    """Sensitive keys (passwords, tokens, cookies, secrets) must be recursively redacted."""
    raw_payload = {
        "user": "pedro",
        "password": "SecretPassword123!",
        "temporary_password": "TempPass!",
        "auth": {
            "token": "bearer.jwt.token",
            "refresh_token": "refresh_secret",
            "cookie": "auth_cookie",
            "api_key": "secret_key_abc",
        },
        "safe_data": {
            "action": "LOGIN",
            "count": 5,
        },
    }

    sanitized = sanitize_audit_payload(raw_payload)

    assert sanitized["password"] == "[REDACTED]"
    assert sanitized["temporary_password"] == "[REDACTED]"
    assert sanitized["auth"]["token"] == "[REDACTED]"
    assert sanitized["auth"]["refresh_token"] == "[REDACTED]"
    assert sanitized["auth"]["cookie"] == "[REDACTED]"
    assert sanitized["auth"]["api_key"] == "[REDACTED]"
    assert sanitized["safe_data"]["action"] == "LOGIN"
    assert sanitized["safe_data"]["count"] == 5


@pytest.mark.anyio
async def test_audit_query_service_redacts_on_read():
    """AuditQueryService redacts sensitive keys in returned DTOs."""
    db, actor, event1 = setup_audit_mock_db()
    service = AuditQueryService(db)  # type: ignore

    res = await service.list_events_paginated(AuditFilterDTO())
    assert len(res.items) == 2

    # Find the user creation event
    user_event = next(it for it in res.items if it.id == event1.id)
    assert user_event.detalle is not None
    assert user_event.detalle["password"] == "[REDACTED]"
    assert user_event.detalle["temporary_password"] == "[REDACTED]"
    assert user_event.detalle["access_token"] == "[REDACTED]"
    assert user_event.detalle["cookie_session"] == "[REDACTED]"
    assert user_event.detalle["email"] == "nuevo@sena.edu.co"
    assert user_event.actor is not None
    assert user_event.actor.email == actor.email


# ==============================================================================
# 3. Read-Only Invariant: No DELETE / Modification Endpoint
# ==============================================================================

def test_audit_no_delete_endpoint_allowed():
    """Audit endpoint is strictly read-only; DELETE requests must return HTTP 405."""
    db, _, event1 = setup_audit_mock_db()
    superadmin = make_test_user(RolUsuario.SUPERADMIN)

    app.dependency_overrides[get_async_session] = lambda: db
    app.dependency_overrides[get_current_user] = lambda: superadmin
    try:
        client = TestClient(app)
        # Attempt DELETE on collection
        resp_coll = client.delete("/api/v1/admin/audit")
        assert resp_coll.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

        # Attempt DELETE on single event
        resp_item = client.delete(f"/api/v1/admin/audit/{event1.id}")
        assert resp_item.status_code == status.HTTP_405_METHOD_NOT_ALLOWED
    finally:
        app.dependency_overrides.clear()
