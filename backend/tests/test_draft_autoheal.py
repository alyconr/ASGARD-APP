"""Tests for draft auto-healing and process creation lifecycle."""

from __future__ import annotations

import uuid
from typing import Any
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from src.application.services.access_scope import AccessScopeService
from src.domain.shared.enums import EstadoBloque, EstadoEquipo, EstadoScopeProceso, RolUsuario
from src.infrastructure.db.models.auth import Rol, Usuario
from src.infrastructure.db.models.drafts import BorradorSesion
from src.infrastructure.db.models.organizacion import (
    Coordinacion,
    EquipoEjecutor,
    Especialidad,
    ProcesoCurricular,
)

pytestmark = pytest.mark.anyio


class AutoHealDbSession:
    """In-memory async session test double for auto-heal queries."""

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
        mock_result = MagicMock()
        text_query = str(statement).lower()

        if "borradores_sesion" in text_query:
            found_drafts = [o for o in self.added if isinstance(o, BorradorSesion)]
            mock_result.scalar_one_or_none.return_value = found_drafts[0] if found_drafts else None
            return mock_result

        if "procesos_curriculares" in text_query:
            found = [o for o in self.added if isinstance(o, ProcesoCurricular)]
            mock_result.scalar_one_or_none.return_value = found[0] if found else None
            mock_result.scalars.return_value.all.return_value = [f.referencia_id for f in found]
            return mock_result

        if "equipos_ejecutores" in text_query:
            teams = [o for o in self.added if isinstance(o, EquipoEjecutor)]
            mock_result.scalar_one_or_none.return_value = teams[0] if teams else None
            mock_result.scalars.return_value.all.return_value = teams
            return mock_result

        mock_result.scalar_one_or_none.return_value = None
        mock_result.scalars.return_value.all.return_value = []
        return mock_result


async def test_auto_heal_proceso_creates_anchor_for_orphaned_draft() -> None:
    """If a draft exists in BorradorSesion but ProcesoCurricular was not created, auto-heal restores it."""
    session = AutoHealDbSession()
    coord = Coordinacion(id=uuid.uuid4(), codigo="COORD-AUTO", nombre="Coordinacion Auto")
    esp = Especialidad(id=uuid.uuid4(), codigo="ESP-AUTO", nombre="Especialidad Auto", coordinacion_id=coord.id)
    session.add(coord)
    session.add(esp)

    leader = Usuario(
        id=uuid.uuid4(),
        email="leader@sena.edu.co",
        nombre="Leader User",
        coordinacion_id=coord.id,
        especialidad_id=esp.id,
        activo=True,
    )
    leader.roles.append(Rol(nombre=RolUsuario.LIDER_EQUIPO_EJECUTOR.value, descripcion="Lider"))
    session.add(leader)

    equipo = EquipoEjecutor(
        id=uuid.uuid4(),
        nombre="Equipo Auto",
        coordinacion_id=coord.id,
        especialidad_id=esp.id,
        lider_id=leader.id,
        estado=EstadoEquipo.ACTIVO,
    )
    equipo.miembros = []
    session.add(equipo)

    # Create orphaned draft (no ProcesoCurricular registered)
    referencia_id = uuid.uuid4()
    draft = BorradorSesion(
        tipo_bloque="PROGRAMA",
        referencia_id=referencia_id,
        paso_actual="origen-documental",
        payload_json={"programa": {"codigo_programa": "12345"}},
        estado_borrador=EstadoBloque.BORRADOR,
    )
    session.add(draft)

    scope_service = AccessScopeService(session)  # type: ignore

    # Calling require_process_access should auto-heal and return the process
    proceso = await scope_service.require_process_access(leader, referencia_id)
    assert proceso is not None
    assert proceso.referencia_id == referencia_id
    assert proceso.lider_id == leader.id
    assert proceso.equipo_ejecutor_id == equipo.id
    assert proceso.estado_scope == EstadoScopeProceso.ASIGNADO

    # Calling can_access_process should also return True
    can_access = await scope_service.can_access_process(leader, referencia_id)
    assert can_access is True


async def test_auto_heal_proceso_for_admin_user() -> None:
    """Admin assigned to a team auto-heals with their team and gains process access."""
    session = AutoHealDbSession()
    admin = Usuario(
        id=uuid.uuid4(),
        email="admin@sena.edu.co",
        nombre="Admin User",
        activo=True,
    )
    admin.roles.append(Rol(nombre=RolUsuario.SUPERADMIN.value, descripcion="Superadmin"))
    session.add(admin)

    team = EquipoEjecutor(
        id=uuid.uuid4(),
        nombre="Equipo Admin",
        lider_id=admin.id,
        estado=EstadoEquipo.ACTIVO,
    )
    team.miembros = []
    session.add(team)

    referencia_id = uuid.uuid4()
    draft = BorradorSesion(
        tipo_bloque="PROGRAMA",
        referencia_id=referencia_id,
        paso_actual="origen-documental",
        payload_json={},
        estado_borrador=EstadoBloque.BORRADOR,
    )
    session.add(draft)

    scope_service = AccessScopeService(session)  # type: ignore
    proceso = await scope_service.require_process_access(admin, referencia_id)
    assert proceso is not None
    assert proceso.referencia_id == referencia_id
    assert proceso.creado_por == admin.id
    assert proceso.equipo_ejecutor_id == team.id

    can_access = await scope_service.can_access_process(admin, referencia_id)
    assert can_access is True


async def test_non_existent_reference_raises_404() -> None:
    """A reference with neither draft nor process raises 404."""
    session = AutoHealDbSession()
    admin = Usuario(
        id=uuid.uuid4(),
        email="admin2@sena.edu.co",
        nombre="Admin User 2",
        activo=True,
    )
    admin.roles.append(Rol(nombre=RolUsuario.ADMIN.value, descripcion="Admin"))
    session.add(admin)

    random_ref = uuid.uuid4()
    scope_service = AccessScopeService(session)  # type: ignore

    with pytest.raises(HTTPException) as exc_info:
        await scope_service.require_process_access(admin, random_ref)
    assert exc_info.value.status_code == 404
