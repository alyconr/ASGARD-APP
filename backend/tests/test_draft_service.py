"""Unit tests for the draft application service."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

import pytest

from src.application.dto.drafts import SaveDraftCommand
from src.application.services.drafts import DraftNotFoundError, DraftService
from src.domain.drafts.types import TipoBloqueBorrador
from src.domain.shared.enums import EstadoBloque
from src.infrastructure.db.models.drafts import BorradorSesion


class FakeSession:
    """Minimal async session stub used by service tests."""

    def __init__(self) -> None:
        """Track commit and refresh calls."""
        self.commits = 0

    async def commit(self) -> None:
        """Record a commit invocation."""
        self.commits += 1

    async def refresh(self, instance: object) -> None:
        """Populate the logical update timestamp if missing."""
        assert isinstance(instance, BorradorSesion)
        instance.ultima_edicion = datetime.now(UTC)


class FakeDraftRepository:
    """In-memory repository keyed by logical draft identity."""

    def __init__(self) -> None:
        """Initialize empty draft storage."""
        self.storage: dict[tuple[str, uuid.UUID], BorradorSesion] = {}

    async def get_by_block_reference(
        self,
        tipo_bloque: TipoBloqueBorrador,
        referencia_id: uuid.UUID,
    ) -> BorradorSesion | None:
        """Return a stored draft for the given logical key."""
        return self.storage.get((tipo_bloque.value, referencia_id))

    async def add(
        self,
        tipo_bloque: TipoBloqueBorrador,
        referencia_id: uuid.UUID,
        paso_actual: str,
        payload_json: dict[str, object],
        estado_borrador: EstadoBloque,
    ) -> BorradorSesion:
        """Create and store a new in-memory draft."""
        draft = BorradorSesion(
            tipo_bloque=tipo_bloque.value,
            referencia_id=referencia_id,
            paso_actual=paso_actual,
            payload_json=payload_json,
            estado_borrador=estado_borrador,
        )
        draft.id = uuid.uuid4()
        draft.ultima_edicion = datetime.now(UTC)
        self.storage[(tipo_bloque.value, referencia_id)] = draft
        return draft

    async def save(self, draft: BorradorSesion) -> BorradorSesion:
        """Update an existing in-memory draft."""
        draft.ultima_edicion = datetime.now(UTC)
        self.storage[(draft.tipo_bloque, draft.referencia_id)] = draft
        return draft


class FakeAuditRepository:
    """Collect audit events emitted by the draft service."""

    def __init__(self) -> None:
        """Initialize empty audit storage."""
        self.events: list[dict[str, Any]] = []

    async def add_event(
        self,
        entidad: str,
        entidad_id: uuid.UUID,
        accion: str,
        detalle: dict[str, object] | None = None,
    ) -> dict[str, Any]:
        """Append an audit event to in-memory storage."""
        event = {
            "entidad": entidad,
            "entidad_id": entidad_id,
            "accion": accion,
            "detalle": detalle,
        }
        self.events.append(event)
        return event


@pytest.mark.anyio
async def test_save_draft_creates_new_program_draft() -> None:
    """Saving a new logical draft should create one row and audit event."""
    session = FakeSession()
    draft_repository = FakeDraftRepository()
    audit_repository = FakeAuditRepository()
    service = DraftService(session, draft_repository, audit_repository)
    referencia_id = uuid.uuid4()

    result = await service.save_draft(
        SaveDraftCommand(
            tipo_bloque=TipoBloqueBorrador.PROGRAMA,
            referencia_id=referencia_id,
            paso_actual="datos-basicos",
            payload_json={"codigo_programa": "123"},
            estado_borrador=EstadoBloque.BORRADOR,
        ),
    )

    assert result.tipo_bloque is TipoBloqueBorrador.PROGRAMA
    assert result.referencia_id == referencia_id
    assert result.paso_actual == "datos-basicos"
    assert result.payload_json == {"codigo_programa": "123"}
    assert result.estado_borrador is EstadoBloque.BORRADOR
    assert session.commits == 1
    assert len(draft_repository.storage) == 1
    assert audit_repository.events[0]["accion"] == "BORRADOR_CREADO"


@pytest.mark.anyio
async def test_save_draft_updates_existing_project_draft() -> None:
    """Saving the same logical draft twice should update instead of duplicate."""
    session = FakeSession()
    draft_repository = FakeDraftRepository()
    audit_repository = FakeAuditRepository()
    service = DraftService(session, draft_repository, audit_repository)
    referencia_id = uuid.uuid4()

    await service.save_draft(
        SaveDraftCommand(
            tipo_bloque=TipoBloqueBorrador.PROYECTO,
            referencia_id=referencia_id,
            paso_actual="datos-proyecto",
            payload_json={"codigo_proyecto": "ABC"},
            estado_borrador=EstadoBloque.BLOQUEADO,
        ),
    )
    updated = await service.save_draft(
        SaveDraftCommand(
            tipo_bloque=TipoBloqueBorrador.PROYECTO,
            referencia_id=referencia_id,
            paso_actual="fases",
            payload_json={"codigo_proyecto": "ABC", "fases": []},
            estado_borrador=EstadoBloque.BORRADOR,
        ),
    )

    assert len(draft_repository.storage) == 1
    assert updated.paso_actual == "fases"
    assert updated.payload_json == {"codigo_proyecto": "ABC", "fases": []}
    assert updated.estado_borrador is EstadoBloque.BORRADOR
    assert [event["accion"] for event in audit_repository.events] == [
        "BORRADOR_CREADO",
        "BORRADOR_ACTUALIZADO",
    ]


@pytest.mark.anyio
async def test_get_draft_returns_existing_logical_draft() -> None:
    """Recovering a draft should preserve step, payload and state."""
    session = FakeSession()
    draft_repository = FakeDraftRepository()
    audit_repository = FakeAuditRepository()
    service = DraftService(session, draft_repository, audit_repository)
    referencia_id = uuid.uuid4()

    await service.save_draft(
        SaveDraftCommand(
            tipo_bloque=TipoBloqueBorrador.PROGRAMA,
            referencia_id=referencia_id,
            paso_actual="revision",
            payload_json={"nombre_programa": "Guia"},
            estado_borrador=EstadoBloque.EN_REVISION,
        ),
    )

    recovered = await service.get_draft(TipoBloqueBorrador.PROGRAMA, referencia_id)

    assert recovered.referencia_id == referencia_id
    assert recovered.paso_actual == "revision"
    assert recovered.payload_json == {"nombre_programa": "Guia"}
    assert recovered.estado_borrador is EstadoBloque.EN_REVISION


@pytest.mark.anyio
async def test_get_draft_raises_when_missing() -> None:
    """A missing logical draft should raise a domain-level not found error."""
    service = DraftService(FakeSession(), FakeDraftRepository(), FakeAuditRepository())

    with pytest.raises(DraftNotFoundError):
        await service.get_draft(TipoBloqueBorrador.PROGRAMA, uuid.uuid4())


@pytest.mark.anyio
async def test_save_draft_rejects_invalid_state_for_program() -> None:
    """Program drafts should not accept the BLOQUEADO state in TASK-03."""
    service = DraftService(FakeSession(), FakeDraftRepository(), FakeAuditRepository())

    with pytest.raises(
        ValueError,
        match="estado_borrador no es valido para el tipo_bloque solicitado",
    ):
        await service.save_draft(
            SaveDraftCommand(
                tipo_bloque=TipoBloqueBorrador.PROGRAMA,
                referencia_id=uuid.uuid4(),
                paso_actual="inicio",
                payload_json={},
                estado_borrador=EstadoBloque.BLOQUEADO,
            ),
        )
