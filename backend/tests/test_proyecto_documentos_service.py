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
    def __init__(self, drafts=None):
        if drafts is None:
            self.drafts = {}
        elif isinstance(drafts, list):
            self.drafts = {
                (
                    d.tipo_bloque if hasattr(d, "tipo_bloque") else "PROYECTO",
                    d.referencia_id if hasattr(d, "referencia_id") else None,
                ): d
                for d in drafts
            }
        else:
            self.drafts = {
                (
                    "PROYECTO",
                    drafts.referencia_id if hasattr(drafts, "referencia_id") else None,
                ): drafts
            }
        self.saved = False

    @property
    def draft(self):
        for (tipo, ref), d in self.drafts.items():
            if tipo == "PROYECTO":
                return d
        return next(iter(self.drafts.values())) if self.drafts else None

    async def get_by_block_reference(self, tipo_bloque, referencia_id):
        val = self.drafts.get((tipo_bloque, referencia_id))
        if val is not None:
            return val
        for (tipo, ref), d in self.drafts.items():
            if tipo == tipo_bloque:
                return d
        return None

    async def save(self, draft):
        self.saved = True
        self.drafts[(draft.tipo_bloque, draft.referencia_id)] = draft
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
            storage_key="proyectos-formativos/diseno-de-soluciones-tecnologicas-987654/documentos/proyecto-formativo.pdf",
            size_bytes=1024,
            content_type="application/pdf",
            checksum_sha256="abc123",
            etag="etag-123",
        )

    async def save_pdf(self, *, key, content, content_type, original_filename):
        return self.document


@pytest.fixture
def draft_factory():
    def _build(referencia_id=None):
        ref_id = referencia_id or uuid.uuid4()
        return MagicMock(
            id=uuid.uuid4(),
            tipo_bloque="PROYECTO",
            referencia_id=ref_id,
            payload_json={
                "meta": {
                    "referenciaId": str(ref_id),
                    "touchedSteps": ["fuente-proyecto"],
                    "lastInteractionAt": datetime.now(UTC).isoformat(),
                },
                "proyecto": {
                    "nombre_proyecto": "Diseño de Soluciones Tecnologicas",
                    "codigo_proyecto": "987654",
                },
                "documental": {
                    "fuente_estructurada": {"confirmacion": {"estado": "IMPORTADO"}}
                },
            },
            paso_actual="fuente-proyecto",
            estado_borrador=EstadoBloque.BORRADOR,
        )

    return _build


@pytest.fixture
def program_draft_factory():
    def _build(referencia_id):
        return MagicMock(
            id=uuid.uuid4(),
            tipo_bloque="PROGRAMA",
            referencia_id=referencia_id,
            payload_json={
                "meta": {
                    "referenciaId": str(referencia_id),
                },
                "documental": {
                    "programa_excel": {"confirmacion": {"estado": "IMPORTADO"}}
                },
            },
            paso_actual="origen-documental",
            estado_borrador=EstadoBloque.BORRADOR,
        )

    return _build


@pytest.fixture
def service(draft_factory, program_draft_factory):
    session = MockSession()
    ref_id = uuid.uuid4()
    proj = draft_factory(referencia_id=ref_id)
    prog = program_draft_factory(referencia_id=ref_id)
    draft_repository = MockDraftRepository([proj, prog])
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

    async def test_upload_persists_metadata_in_draft(self, service, valid_pdf_content):
        await service.upload_and_store_project_pdf(
            referencia_id=uuid.uuid4(),
            filename="proyecto.pdf",
            content_type="application/pdf",
            content=valid_pdf_content,
        )

        assert service._draft_repository.saved is True

    async def test_upload_sets_proyecto_paso_actual(self, service, valid_pdf_content):
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
        draft_repository = MockDraftRepository(drafts=[])
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
        ref_id = uuid.uuid4()
        proj_draft = MagicMock(
            id=uuid.uuid4(),
            tipo_bloque="PROYECTO",
            referencia_id=ref_id,
            payload_json={
                "meta": {},
                "proyecto": {
                    "nombre_proyecto": "Diseño de Soluciones Tecnologicas",
                    "codigo_proyecto": "987654",
                },
                "documental": {
                    "fuente_estructurada": {"confirmacion": {"estado": "IMPORTADO"}}
                },
            },
            paso_actual="fuente-proyecto",
            estado_borrador=EstadoBloque.BORRADOR,
        )
        prog_draft = MagicMock(
            id=uuid.uuid4(),
            tipo_bloque="PROGRAMA",
            referencia_id=ref_id,
            payload_json={
                "meta": {},
                "documental": {
                    "programa_excel": {"confirmacion": {"estado": "IMPORTADO"}}
                },
            },
            paso_actual="origen-documental",
            estado_borrador=EstadoBloque.BORRADOR,
        )
        draft_repository = MockDraftRepository([proj_draft, prog_draft])
        audit = MockAuditRepository()

        service = ProjectDocumentService(
            session=session,
            draft_repository=draft_repository,
            audit_repository=audit,
            storage_service=storage,
        )

        await service.upload_and_store_project_pdf(
            referencia_id=ref_id,
            filename="proyecto.pdf",
            content_type="application/pdf",
            content=valid_pdf_content,
        )

        assert storage.document.storage_key.startswith("proyectos-formativos/")
