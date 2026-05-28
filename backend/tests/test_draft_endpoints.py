"""HTTP tests for draft save and recovery endpoints."""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock

from fastapi.testclient import TestClient

from src.application.dto.drafts import DraftDTO, SaveDraftCommand
from src.application.services.drafts import DraftNotFoundError
from src.domain.drafts.types import TipoBloqueBorrador
from src.domain.shared.enums import EstadoBloque
from src.infrastructure.db.models.drafts import BorradorSesion
from src.infrastructure.db.session import get_async_session
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


def test_get_estado_documental_empty() -> None:
    """The endpoint should return default/empty values when no drafts exist."""
    session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    session.execute.return_value = mock_result

    app.dependency_overrides[get_async_session] = lambda: session
    client = TestClient(app)
    referencia_id = uuid.uuid4()

    response = client.get(f"/api/v1/drafts/{referencia_id}/estado-documental")

    app.dependency_overrides.clear()

    assert response.status_code == 200
    res_json = response.json()
    assert res_json["programa_excel"] is None
    assert res_json["proyecto_excel"] is None
    assert res_json["programa_pdf"] is None
    assert res_json["proyecto_pdf"] is None
    assert res_json["programa_importado"] is False
    assert res_json["proyecto_importado"] is False
    assert res_json["documentos_habilitados"] is False
    assert res_json["cargue_pdf_habilitado"] is False


def test_get_estado_documental_with_data() -> None:
    """The endpoint should parse metadata from loaded program and project drafts."""
    referencia_id = uuid.uuid4()
    draft_programa = BorradorSesion(
        tipo_bloque="PROGRAMA",
        referencia_id=referencia_id,
        paso_actual="revision-programa",
        payload_json={
            "documental": {
                "programa_excel": {
                    "documento": {
                        "original_filename": "programa.xlsx",
                        "storage_key": "programas/prog/excel/matriz-programa.xlsx",
                        "size_bytes": 1024,
                        "content_type": (
                            "application/vnd.openxmlformats-officedocument."
                            "spreadsheetml.sheet"
                        ),
                        "checksum_sha256": "hash123",
                    },
                    "confirmacion": {"estado": "IMPORTADO"},
                    "updated_at": "2026-05-27T20:13:00Z",
                },
                "programa_pdf": {
                    "documento": {
                        "original_filename": "programa.pdf",
                        "storage_key": (
                            "programas/prog/documentos/programa-formacion.pdf"
                        ),
                        "size_bytes": 2048,
                        "content_type": "application/pdf",
                        "checksum_sha256": "pdfhash",
                    },
                    "updated_at": "2026-05-27T20:14:00Z",
                },
            }
        },
        estado_borrador=EstadoBloque.COMPLETO,
    )
    draft_proyecto = BorradorSesion(
        tipo_bloque="PROYECTO",
        referencia_id=referencia_id,
        paso_actual="fuente-proyecto",
        payload_json={
            "documental": {
                "fuente_estructurada": {
                    "documento": {
                        "original_filename": "proyecto.xlsx",
                        "storage_key": "proyectos/proj/excel/matriz-proyecto.xlsx",
                        "size_bytes": 4096,
                        "content_type": (
                            "application/vnd.openxmlformats-officedocument."
                            "spreadsheetml.sheet"
                        ),
                        "checksum_sha256": "hash456",
                    },
                    "confirmacion": {"estado": "IMPORTADO"},
                    "updated_at": "2026-05-27T20:15:00Z",
                },
                "proyecto_pdf": {
                    "documento": {
                        "original_filename": "proyecto.pdf",
                        "storage_key": (
                            "proyectos/proj/documentos/proyecto-formativo.pdf"
                        ),
                        "size_bytes": 8192,
                        "content_type": "application/pdf",
                        "checksum_sha256": "pdfhash2",
                    },
                    "updated_at": "2026-05-27T20:16:00Z",
                },
                "cargue_pdf_habilitado": True,
            }
        },
        estado_borrador=EstadoBloque.BORRADOR,
    )

    session = AsyncMock()
    mock_result_prog = MagicMock()
    mock_result_prog.scalar_one_or_none.return_value = draft_programa
    mock_result_proj = MagicMock()
    mock_result_proj.scalar_one_or_none.return_value = draft_proyecto
    session.execute.side_effect = [mock_result_prog, mock_result_proj]

    app.dependency_overrides[get_async_session] = lambda: session
    client = TestClient(app)

    response = client.get(f"/api/v1/drafts/{referencia_id}/estado-documental")

    app.dependency_overrides.clear()

    assert response.status_code == 200
    res_json = response.json()
    assert res_json["programa_excel"]["original_filename"] == "programa.xlsx"
    assert res_json["programa_pdf"]["original_filename"] == "programa.pdf"
    assert res_json["proyecto_excel"]["original_filename"] == "proyecto.xlsx"
    assert res_json["proyecto_pdf"]["original_filename"] == "proyecto.pdf"
    assert res_json["programa_importado"] is True
    assert res_json["proyecto_importado"] is True
    assert res_json["documentos_habilitados"] is True
    assert res_json["cargue_pdf_habilitado"] is True
