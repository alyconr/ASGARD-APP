"""Tests for project Excel import service."""

from __future__ import annotations

import io
import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from openpyxl import Workbook

from src.application.dto.programa_documentos import StoredDocumentDTO
from src.application.services.proyecto_excel import (
    DocumentStorageProtocol,
    DraftRepositoryProtocol,
    InvalidProjectExcelUploadError,
    ProjectExcelImportService,
    ProjectExcelMissingPreviewError,
    ProjectExcelStorageMissingError,
    ProjectRepositoryProtocol,
)
from src.domain.drafts.types import TipoBloqueBorrador
from src.domain.shared.enums import EstadoBloque


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
    def __init__(self, document=None, content=b""):
        self.document = document or StoredDocumentDTO(
            original_filename="proyecto.xlsx",
            storage_key="proyectos/test-id/excel/test.xlsx",
            size_bytes=1024,
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            checksum_sha256="abc123",
            etag="etag-123",
        )
        self._content = content

    async def save_excel(self, *, key, content, content_type, original_filename):
        self._content = content
        return self.document

    async def read_excel(self, *, key):
        if not self._content:
            raise FileNotFoundError("Excel no encontrado")
        return self._content


class MockProjectRepository:
    def __init__(self):
        self.created_proyectos = []
        self.created_fases = []
        self.created_actividades = []

    async def create_proyecto(self, *, programa_id, codigo_proyecto, nombre_proyecto, version_proyecto):
        p = MagicMock(id=uuid.uuid4())
        p.codigo_proyecto = codigo_proyecto
        self.created_proyectos.append(p)
        return p

    async def create_fase(self, *, proyecto_id, nombre_fase, orden):
        f = MagicMock(id=uuid.uuid4())
        f.nombre_fase = nombre_fase
        self.created_fases.append(f)
        return f

    async def create_actividad(self, *, fase_id, descripcion, orden):
        a = MagicMock(id=uuid.uuid4())
        a.descripcion = descripcion
        self.created_actividades.append(a)
        return a


def create_valid_workbook():
    wb = Workbook()

    proyecto_sheet = wb.active
    proyecto_sheet.title = "Proyecto"
    proyecto_sheet.append(["codigo_proyecto", "nombre_proyecto", "version_proyecto", "programa_referencia", "observaciones"])
    proyecto_sheet.append(["PR-001", "Proyecto de prueba", "1.0", "prog-ref", ""])

    fases_sheet = wb.create_sheet("Fases")
    fases_sheet.append(["fase_id", "nombre_fase", "orden", "descripcion", "observaciones"])
    fases_sheet.append(["F1", "Fase 1", 1, "Descripcion fase 1", ""])
    fases_sheet.append(["F2", "Fase 2", 2, "Descripcion fase 2", ""])

    actividades_sheet = wb.create_sheet("Actividades")
    actividades_sheet.append(["fase_id", "descripcion", "orden", "observaciones"])
    actividades_sheet.append(["F1", "Actividad 1.1", 1, ""])
    actividades_sheet.append(["F1", "Actividad 1.2", 2, ""])
    actividades_sheet.append(["F2", "Actividad 2.1", 1, ""])

    return wb


@pytest.fixture
def draft_factory():
    def _build():
        return MagicMock(
            id=uuid.uuid4(),
            payload_json={
                "meta": {
                    "referenciaId": str(uuid.uuid4()),
                    "programaId": "00000000-0000-0000-0000-000000000000",
                    "touchedSteps": ["datos-proyecto"],
                    "lastInteractionAt": datetime.now(UTC).isoformat(),
                },
                "documental": {},
            },
            paso_actual="datos-proyecto",
            estado_borrador=EstadoBloque.BORRADOR,
        )

    return _build


@pytest.fixture
def service(draft_factory):
    session = MockSession()
    draft_repository = MockDraftRepository(draft_factory())
    audit_repository = MockAuditRepository()
    storage_service = MockStorageService()
    project_repository = MockProjectRepository()

    return ProjectExcelImportService(
        session=session,
        draft_repository=draft_repository,
        audit_repository=audit_repository,
        project_repository=project_repository,
        storage_service=storage_service,
    )


class TestPreviewProjectExcel:
    async def test_preview_accepts_valid_workbook(self, service):
        wb = create_valid_workbook()
        content = io.BytesIO()
        wb.save(content)
        content.seek(0)

        result = await service.preview_project_excel(
            referencia_id=uuid.uuid4(),
            filename="proyecto.xlsx",
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            content=content.read(),
        )

        assert result.valid is True
        assert result.estado_validacion == "VALIDO"
        assert result.proyecto is not None
        assert result.proyecto.codigo_proyecto == "PR-001"
        assert len(result.fases) == 2

    async def test_preview_rejects_missing_sheets(self, service):
        wb = Workbook()
        wb.active.title = "Proyecto"
        wb.active.append(["codigo_proyecto", "nombre_proyecto", "version_proyecto", "programa_referencia", "observaciones"])
        wb.active.append(["PR-001", "Test", "1.0", "", ""])
        content = io.BytesIO()
        wb.save(content)
        content.seek(0)

        result = await service.preview_project_excel(
            referencia_id=uuid.uuid4(),
            filename="proyecto.xlsx",
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            content=content.read(),
        )

        assert result.valid is False
        assert result.estado_validacion == "INVALIDO"
        assert len(result.errores) > 0

    async def test_preview_rejects_non_xlsx(self, service):
        with pytest.raises(InvalidProjectExcelUploadError, match="Solo se aceptan archivos .xlsx"):
            await service.preview_project_excel(
                referencia_id=uuid.uuid4(),
                filename="proyecto.pdf",
                content_type="application/pdf",
                content=b"fake pdf",
            )

    async def test_preview_rejects_empty_content(self, service):
        with pytest.raises(InvalidProjectExcelUploadError, match="esta vacio"):
            await service.preview_project_excel(
                referencia_id=uuid.uuid4(),
                filename="proyecto.xlsx",
                content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                content=b"",
            )

    async def test_preview_rejects_missing_draft(self):
        session = MockSession()
        draft_repository = MockDraftRepository(draft=None)
        audit_repository = MockAuditRepository()
        storage_service = MockStorageService()
        project_repository = MockProjectRepository()

        service = ProjectExcelImportService(
            session=session,
            draft_repository=draft_repository,
            audit_repository=audit_repository,
            project_repository=project_repository,
            storage_service=storage_service,
        )

        wb = create_valid_workbook()
        content = io.BytesIO()
        wb.save(content)
        content.seek(0)

        from src.application.services.proyecto_excel import ProjectExcelDraftMissingError
        with pytest.raises(ProjectExcelDraftMissingError):
            await service.preview_project_excel(
                referencia_id=uuid.uuid4(),
                filename="proyecto.xlsx",
                content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                content=content.read(),
            )

    async def test_preview_persists_in_draft(self, service):
        wb = create_valid_workbook()
        content = io.BytesIO()
        wb.save(content)
        content.seek(0)

        await service.preview_project_excel(
            referencia_id=uuid.uuid4(),
            filename="proyecto.xlsx",
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            content=content.read(),
        )

        assert service._draft_repository.saved is True

    async def test_preview_sets_paso_actual(self, service):
        wb = create_valid_workbook()
        content = io.BytesIO()
        wb.save(content)
        content.seek(0)

        await service.preview_project_excel(
            referencia_id=uuid.uuid4(),
            filename="proyecto.xlsx",
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            content=content.read(),
        )

        assert service._draft_repository.draft.paso_actual == "fuente-proyecto"

    async def test_preview_triggers_audit_event(self, service):
        wb = create_valid_workbook()
        content = io.BytesIO()
        wb.save(content)
        content.seek(0)

        await service.preview_project_excel(
            referencia_id=uuid.uuid4(),
            filename="proyecto.xlsx",
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            content=content.read(),
        )

        assert len(service._audit_repository.events) == 1
        event = service._audit_repository.events[0]
        assert event["accion"] == "EXCEL_PROYECTO_PREVISUALIZADO"


class TestConfirmProjectExcelImport:
    async def test_confirm_materializes_proyecto(self, service):
        wb = create_valid_workbook()
        content = io.BytesIO()
        wb.save(content)
        content.seek(0)

        await service.preview_project_excel(
            referencia_id=uuid.uuid4(),
            filename="proyecto.xlsx",
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            content=content.read(),
        )

        result = await service.confirm_project_excel_import(
            referencia_id=uuid.uuid4(),
        )

        assert result.proyecto_id is not None
        assert result.resumen.proyecto == 1
        assert result.resumen.fases == 2
        assert result.resumen.actividades == 3

    async def test_confirm_materializes_fases(self, service):
        wb = create_valid_workbook()
        content = io.BytesIO()
        wb.save(content)
        content.seek(0)

        await service.preview_project_excel(
            referencia_id=uuid.uuid4(),
            filename="proyecto.xlsx",
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            content=content.read(),
        )

        result = await service.confirm_project_excel_import(
            referencia_id=uuid.uuid4(),
        )

        assert len(result.fase_ids) == 2

    async def test_confirm_materializes_actividades(self, service):
        wb = create_valid_workbook()
        content = io.BytesIO()
        wb.save(content)
        content.seek(0)

        await service.preview_project_excel(
            referencia_id=uuid.uuid4(),
            filename="proyecto.xlsx",
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            content=content.read(),
        )

        result = await service.confirm_project_excel_import(
            referencia_id=uuid.uuid4(),
        )

        assert len(result.actividad_ids) == 3

    async def test_confirm_rejects_missing_preview(self):
        session = MockSession()
        draft_repository = MockDraftRepository(
            MagicMock(
                id=uuid.uuid4(),
                payload_json={"meta": {}, "documental": {}},
                paso_actual="datos-proyecto",
                estado_borrador=EstadoBloque.BORRADOR,
            )
        )
        audit_repository = MockAuditRepository()
        storage_service = MockStorageService()
        project_repository = MockProjectRepository()

        service = ProjectExcelImportService(
            session=session,
            draft_repository=draft_repository,
            audit_repository=audit_repository,
            project_repository=project_repository,
            storage_service=storage_service,
        )

        with pytest.raises(ProjectExcelMissingPreviewError):
            await service.confirm_project_excel_import(
                referencia_id=uuid.uuid4(),
            )

    async def test_confirm_commits_session(self, service):
        wb = create_valid_workbook()
        content = io.BytesIO()
        wb.save(content)
        content.seek(0)

        await service.preview_project_excel(
            referencia_id=uuid.uuid4(),
            filename="proyecto.xlsx",
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            content=content.read(),
        )

        await service.confirm_project_excel_import(
            referencia_id=uuid.uuid4(),
        )

        assert service._session.committed is True

    async def test_confirm_stores_excel_in_minio(self):
        storage = MockStorageService()
        session = MockSession()
        draft_repository = MockDraftRepository(
            MagicMock(
                id=uuid.uuid4(),
                payload_json={"meta": {}, "documental": {}},
                paso_actual="datos-proyecto",
                estado_borrador=EstadoBloque.BORRADOR,
            )
        )
        audit = MockAuditRepository()
        project_repository = MockProjectRepository()

        service = ProjectExcelImportService(
            session=session,
            draft_repository=draft_repository,
            audit_repository=audit,
            project_repository=project_repository,
            storage_service=storage,
        )

        wb = create_valid_workbook()
        content = io.BytesIO()
        wb.save(content)
        content.seek(0)

        await service.preview_project_excel(
            referencia_id=uuid.uuid4(),
            filename="proyecto.xlsx",
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            content=content.read(),
        )

        await service.confirm_project_excel_import(
            referencia_id=uuid.uuid4(),
        )

        assert storage.document.storage_key.startswith("proyectos/")
