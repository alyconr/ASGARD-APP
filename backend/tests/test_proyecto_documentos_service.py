"""Tests for project PDF document service."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest

from src.application.dto.programa_documentos import StoredDocumentDTO
from src.application.services.proyecto_documentos import (
    InvalidProjectPdfUploadError,
    ProjectDocumentService,
    ProjectDraftMissingError,
)
from src.domain.shared.enums import EstadoBloque

pytestmark = pytest.mark.anyio


class MockDraftRepository:
    def __init__(self, draft=None):
        self.draft = draft
        self.saved = False

    async def get_by_block_reference(self, tipo_bloque, referencia_id):
        return self.draft

    async def save(self, draft):
        self.saved = True
        return draft


class MockAuditRepository:
    def __init__(self):
        self.events = []

    async def add_event(self, entidad, entidad_id, accion, detalle=None):
        self.events.append({"entidad": entidad, "accion": accion, "detalle": detalle})


class MockSession:
    def __init__(self):
        self.committed = False
        self.refreshed = False

    async def commit(self):
        self.committed = True

    async def refresh(self, instance):
        self.refreshed = True


class MockStorageService:
    def __init__(self, document=None):
        self.document = document or StoredDocumentDTO(
            original_filename="test.pdf",
            storage_key="proyectos-formativos/test-id/documentos/obj-test.pdf",
            size_bytes=1024,
            content_type="application/pdf",
            checksum_sha256="abc123",
            etag="etag-123",
        )

    async def save_pdf(self, *, key, content, content_type, original_filename):
        return self.document


@pytest.fixture
def draft_factory():
    def _build():
        return MagicMock(
            id=uuid.uuid4(),
            payload_json={
                "meta": {
                    "referenciaId": str(uuid.uuid4()),
                    "touchedSteps": ["fuente-proyecto"],
                    "lastInteractionAt": datetime.now(UTC).isoformat(),
                },
                "documental": {},
            },
            paso_actual="fuente-proyecto",
            estado_borrador=EstadoBloque.BORRADOR,
        )

    return _build


@pytest.fixture
def service(draft_factory):
    session = MockSession()
    draft_repository = MockDraftRepository(draft_factory())
    audit_repository = MockAuditRepository()
    storage_service = MockStorageService()

    return ProjectDocumentService(
        session=session,
        draft_repository=draft_repository,
        audit_repository=audit_repository,
        storage_service=storage_service,
    )


@pytest.fixture
def valid_pdf_content():
    return b"%PDF-1.4 fake pdf content"


class TestUploadAndStoreProjectPdf:
    async def test_upload_accepts_valid_pdf(self, service, valid_pdf_content):
        result = await service.upload_and_store_project_pdf(
            referencia_id=uuid.uuid4(),
            filename="proyecto.pdf",
            content_type="application/pdf",
            content=valid_pdf_content,
        )

        assert result.documento.original_filename == "test.pdf"
        assert result.documento.storage_key.startswith("proyectos-formativos/")
        assert result.documento.content_type == "application/pdf"

    async def test_upload_persists_metadata_in_draft(
        self, service, valid_pdf_content
    ):
        await service.upload_and_store_project_pdf(
            referencia_id=uuid.uuid4(),
            filename="proyecto.pdf",
            content_type="application/pdf",
            content=valid_pdf_content,
        )

        assert service._draft_repository.saved is True

    async def test_upload_sets_proyecto_paso_actual(
        self, service, valid_pdf_content
    ):
        await service.upload_and_store_project_pdf(
            referencia_id=uuid.uuid4(),
            filename="proyecto.pdf",
            content_type="application/pdf",
            content=valid_pdf_content,
        )

        assert service._draft_repository.draft.paso_actual == "fuente-proyecto"

    async def test_upload_rejects_non_pdf(self, service):
        with pytest.raises(
            InvalidProjectPdfUploadError,
            match="Solo se aceptan archivos PDF",
        ):
            await service.upload_and_store_project_pdf(
                referencia_id=uuid.uuid4(),
                filename="image.png",
                content_type="image/png",
                content=b"fake image",
            )

    async def test_upload_rejects_empty_content(self, service):
        with pytest.raises(InvalidProjectPdfUploadError, match="no puede estar vacio"):
            await service.upload_and_store_project_pdf(
                referencia_id=uuid.uuid4(),
                filename="proyecto.pdf",
                content_type="application/pdf",
                content=b"",
            )

    async def test_upload_rejects_missing_filename(self, service):
        with pytest.raises(InvalidProjectPdfUploadError, match="es obligatorio"):
            await service.upload_and_store_project_pdf(
                referencia_id=uuid.uuid4(),
                filename="",
                content_type="application/pdf",
                content=b"content",
            )

    async def test_upload_rejects_missing_draft(self, valid_pdf_content):
        session = MockSession()
        draft_repository = MockDraftRepository(draft=None)
        audit_repository = MockAuditRepository()
        storage_service = MockStorageService()

        service = ProjectDocumentService(
            session=session,
            draft_repository=draft_repository,
            audit_repository=audit_repository,
            storage_service=storage_service,
        )

        with pytest.raises(ProjectDraftMissingError):
            await service.upload_and_store_project_pdf(
                referencia_id=uuid.uuid4(),
                filename="proyecto.pdf",
                content_type="application/pdf",
                content=valid_pdf_content,
            )

    async def test_upload_triggers_audit_event(self, service, valid_pdf_content):
        await service.upload_and_store_project_pdf(
            referencia_id=uuid.uuid4(),
            filename="proyecto.pdf",
            content_type="application/pdf",
            content=valid_pdf_content,
        )

        assert len(service._audit_repository.events) == 1
        event = service._audit_repository.events[0]
        assert event["accion"] == "DOCUMENTO_PROYECTO_ALMACENADO"

    async def test_upload_commits_session(self, service, valid_pdf_content):
        await service.upload_and_store_project_pdf(
            referencia_id=uuid.uuid4(),
            filename="proyecto.pdf",
            content_type="application/pdf",
            content=valid_pdf_content,
        )

        assert service._session.committed is True

    async def test_upload_stores_document_in_minio(self, valid_pdf_content):
        storage = MockStorageService()
        session = MockSession()
        draft_repository = MockDraftRepository(
            MagicMock(
                id=uuid.uuid4(),
                payload_json={"meta": {}, "documental": {}},
                paso_actual="fuente-proyecto",
                estado_borrador=EstadoBloque.BORRADOR,
            )
        )
        audit = MockAuditRepository()

        service = ProjectDocumentService(
            session=session,
            draft_repository=draft_repository,
            audit_repository=audit,
            storage_service=storage,
        )

        await service.upload_and_store_project_pdf(
            referencia_id=uuid.uuid4(),
            filename="proyecto.pdf",
            content_type="application/pdf",
            content=valid_pdf_content,
        )

        assert storage.document.storage_key.startswith("proyectos-formativos/")
