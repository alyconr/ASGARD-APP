"""HTTP tests for draft save and recovery endpoints."""

from __future__ import annotations

import uuid

from fastapi.testclient import TestClient

from src.application.dto.drafts import DraftDTO, SaveDraftCommand
from src.application.services.drafts import DraftNotFoundError
from src.domain.drafts.types import TipoBloqueBorrador
from src.interfaces.http.app import app
from src.interfaces.http.controllers.drafts import get_draft_service


class FakeDraftService:
    """Simple service double used by HTTP tests."""

    def __init__(self) -> None:
        """Initialize empty logical draft storage."""
        self.storage: dict[tuple[TipoBloqueBorrador, uuid.UUID], DraftDTO] = {}

    async def save_draft(self, command: SaveDraftCommand) -> DraftDTO:
        """Create or update the in-memory draft representation."""
        draft = DraftDTO(
            id=uuid.uuid4(),
            tipo_bloque=command.tipo_bloque,
            referencia_id=command.referencia_id,
            paso_actual=command.paso_actual,
            payload_json=command.payload_json,
            estado_borrador=command.estado_borrador,
            ultima_edicion=__import__("datetime").datetime.now(
                __import__("datetime").UTC,
            ),
        )
        existing = self.storage.get((command.tipo_bloque, command.referencia_id))
        if existing is not None:
            draft = DraftDTO(
                id=existing.id,
                tipo_bloque=command.tipo_bloque,
                referencia_id=command.referencia_id,
                paso_actual=command.paso_actual,
                payload_json=command.payload_json,
                estado_borrador=command.estado_borrador,
                ultima_edicion=draft.ultima_edicion,
            )
        self.storage[(command.tipo_bloque, command.referencia_id)] = draft
        return draft

    async def get_draft(
        self,
        tipo_bloque: TipoBloqueBorrador,
        referencia_id: uuid.UUID,
    ) -> DraftDTO:
        """Return the stored in-memory draft or raise a not found error."""
        draft = self.storage.get((tipo_bloque, referencia_id))
        if draft is None:
            raise DraftNotFoundError("No existe un borrador para la referencia dada")
        return draft


def test_draft_endpoints_save_and_get() -> None:
    """The API should persist and recover a logical draft through the service."""
    fake_service = FakeDraftService()
    app.dependency_overrides[get_draft_service] = lambda: fake_service
    client = TestClient(app)
    referencia_id = uuid.uuid4()

    save_response = client.put(
        f"/api/v1/drafts/PROGRAMA/{referencia_id}",
        json={
            "paso_actual": "datos-basicos",
            "payload_json": {"codigo_programa": "123"},
            "estado_borrador": "BORRADOR",
        },
    )
    get_response = client.get(f"/api/v1/drafts/PROGRAMA/{referencia_id}")

    app.dependency_overrides.clear()

    assert save_response.status_code == 200
    assert save_response.json()["paso_actual"] == "datos-basicos"
    assert save_response.json()["payload_json"] == {"codigo_programa": "123"}
    assert get_response.status_code == 200
    assert get_response.json()["referencia_id"] == str(referencia_id)


def test_draft_get_returns_not_found_for_missing_reference() -> None:
    """The API should return 404 when no logical draft exists."""
    fake_service = FakeDraftService()
    app.dependency_overrides[get_draft_service] = lambda: fake_service
    client = TestClient(app)

    response = client.get(f"/api/v1/drafts/PROYECTO/{uuid.uuid4()}")

    app.dependency_overrides.clear()

    assert response.status_code == 404
    assert response.json()["detail"] == "No existe un borrador para la referencia dada"


def test_draft_save_rejects_invalid_program_state() -> None:
    """The API should reject states outside TASK-03 scope for program drafts."""
    fake_service = FakeDraftService()
    app.dependency_overrides[get_draft_service] = lambda: fake_service
    client = TestClient(app)

    response = client.put(
        f"/api/v1/drafts/PROGRAMA/{uuid.uuid4()}",
        json={
            "paso_actual": "inicio",
            "payload_json": {},
            "estado_borrador": "BLOQUEADO",
        },
    )

    app.dependency_overrides.clear()

    assert response.status_code == 422
