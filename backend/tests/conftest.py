"""Shared pytest fixtures for backend tests."""

from __future__ import annotations

import uuid
from typing import Generator

import pytest

from src.domain.shared.enums import RolUsuario
from src.infrastructure.db.models.auth import Rol, Usuario
from src.infrastructure.db.models.organizacion import ProcesoCurricular
from src.interfaces.http.app import app
from src.interfaces.http.deps import get_access_scope_service, get_current_user


class FakeAccessScope:
    """Mock AccessScopeService for isolated controller tests."""

    async def require_process_access(self, user: Usuario, referencia_id: uuid.UUID) -> ProcesoCurricular:
        return ProcesoCurricular(id=uuid.uuid4(), referencia_id=referencia_id)

    async def can_access_process(self, user: Usuario, referencia_id: uuid.UUID) -> bool:
        return True

    async def can_access_project(self, user: Usuario, proyecto_id: uuid.UUID) -> bool:
        return True

    async def can_access_planning(self, user: Usuario, planeacion_id: uuid.UUID) -> bool:
        return True


@pytest.fixture
def auth_overrides() -> Generator[None, None, None]:
    """Provide default SUPERADMIN user and bypass scope service for mock service tests."""
    mock_user = Usuario(
        id=uuid.uuid4(),
        email="admin-test@sena.edu.co",
        nombre="Admin Test",
        activo=True,
        roles=[Rol(nombre=RolUsuario.SUPERADMIN.value, descripcion="Superadmin")],
    )
    fake_scope = FakeAccessScope()
    app.dependency_overrides[get_current_user] = lambda: mock_user
    app.dependency_overrides[get_access_scope_service] = lambda: fake_scope
    yield
    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(get_access_scope_service, None)
